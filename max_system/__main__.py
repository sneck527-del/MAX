"""Max系统入口点"""

import asyncio
import logging
import sys

from max_system.config.settings import get_settings


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def main():
    setup_logging()
    settings = get_settings()

    mode = "feishu"  # 默认：飞书长连接模式
    args = sys.argv[1:]
    if args:
        first = args[0]
        if first in ("cli", "--cli", "-i"):
            mode = "cli"
        elif first in ("webhook", "--webhook", "-w"):
            mode = "webhook"
        elif first in ("feishu", "--feishu", "-f"):
            mode = "feishu"

    if mode == "cli":
        _run_cli()
    elif mode == "webhook":
        _run_webhook()
    else:
        _run_feishu()


def _run_cli():
    """CLI交互模式"""
    asyncio.run(_async_cli())


async def _async_cli():
    from max_system.cli.repl import run_repl
    await run_repl()


def _run_webhook():
    """Webhook服务模式"""
    import uvicorn
    settings = get_settings()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("  Max 多Agent室内设计AI助手系统  |  Webhook模式")
    logger.info("=" * 60)

    from max_system.api.app import create_app
    app = create_app()

    uvicorn.run(app, host=settings.webhook_host, port=settings.webhook_port, log_level="info")


def _run_feishu():
    """飞书长连接模式（默认）"""
    settings = get_settings()
    logger = logging.getLogger(__name__)

    print("=" * 60)
    print("  Max 多Agent室内设计AI助手系统  |  飞书长连接模式")
    print("  斑马精装")
    print("=" * 60)
    print(f"  LLM: {settings.llm_provider} / {settings.llm_model}")
    print(f"  飞书App ID: {settings.feishu_app_id[:10]}...")
    print(f"  Obsidian: {settings.obsidian_vault_path}")
    print("=" * 60)

    asyncio.run(_async_feishu())


async def _async_feishu():
    """飞书长连接异步主循环"""
    import time
    from max_system.config.settings import get_settings
    from max_system.core.orchestrator import MaxOrchestrator
    from max_system.core.session_manager import SessionManager
    from max_system.integrations.feishu.long_conn import FeishuLongConn
    from max_system.integrations.feishu.api_client import FeishuApiClient
    from max_system.audit.store import AuditStore
    from max_system.audit.logger import set_audit_store

    settings = get_settings()

    # 初始化审计
    audit_store = AuditStore(settings.audit_db_path)
    await audit_store.initialize()
    set_audit_store(audit_store)

    # 初始化编排器
    orchestrator = MaxOrchestrator(settings)
    await orchestrator.initialize()

    # 测试LLM连接
    print("\n正在测试LLM连接...")
    conn = await orchestrator.llm.test_connection()
    if conn["connected"]:
        print(f"  LLM连接成功: {conn['provider']}/{conn['model']}")
    else:
        print(f"  LLM连接失败: {conn.get('error', '')}")
        await audit_store.close()
        return

    # 初始化会话管理
    session_manager = SessionManager()
    await session_manager.start()

    # 飞书API客户端（用于主动发消息）
    feishu_api = FeishuApiClient(settings)

    # 消息处理回调
    async def handle_feishu_message(payload: dict):
        chat_id = payload.get("chat_id", "")
        chat_type = payload.get("chat_type", "p2p")
        text = payload.get("text", "")
        user_id = payload.get("user_id", "")
        is_mentioned = payload.get("is_mentioned", False)

        # 群聊未@机器人，不响应
        if chat_type == "group" and not is_mentioned:
            return

        try:
            # 会话上下文
            session = await session_manager.get_or_create(chat_id)
            session_manager.add_message(session, "user", text)
            history = session_manager.get_history(session)

            # 调度到Max
            response = await orchestrator.dispatch(
                text, session_id=chat_id, user_id=user_id,
                history=history[:-1],  # 排除刚添加的当前消息
            )

            # 发送响应
            if response:
                session_manager.add_message(session, "assistant", response)
                # 分段发送超长消息
                max_len = 4000
                if len(response) <= max_len:
                    await feishu_api.send_message(chat_id, response)
                else:
                    for i in range(0, len(response), max_len):
                        await feishu_api.send_message(chat_id, response[i:i + max_len])
                        await asyncio.sleep(0.5)

        except Exception as e:
            logging.getLogger(__name__).error("处理飞书消息失败: %s", e, exc_info=True)
            try:
                await feishu_api.send_message(chat_id, f"处理异常，请稍后重试。")
            except Exception:
                pass

    # 启动飞书长连接（在独立线程+独立事件循环中运行）
    feishu_conn = FeishuLongConn(settings, handle_feishu_message)
    main_loop = asyncio.get_event_loop()

    print("\n正在连接飞书长连接...")
    feishu_conn.start(main_loop=main_loop)

    # 等待连接建立
    await asyncio.sleep(3)
    print("飞书长连接已启动，等待消息中...")
    print("按 Ctrl+C 退出\n")

    # 保持主线程运行
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n正在关闭...")
    finally:
        await session_manager.stop()
        await feishu_api.close()
        await audit_store.close()
        print("Max系统已关闭")


if __name__ == "__main__":
    main()
