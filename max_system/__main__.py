"""Max系统入口点"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def main():
    if sys.platform == "win32" and sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    setup_logging()

    args = sys.argv[1:]
    mode = None
    if args:
        first = args[0]
        if first in ("cli", "--cli", "-i"):
            mode = "cli"
        elif first in ("feishu", "--feishu", "-f"):
            mode = "feishu"
        elif first in ("init", "--init"):
            asyncio.run(_run_init())
            return

    if mode is None:
        mode = "feishu"

    if mode == "cli":
        _run_cli()
    else:
        _run_feishu()


async def _run_init():
    """初始化Max系统：检测连接、创建Bitable表、初始化数据库"""
    from max_system.config.bitable_schema import BITABLE_TABLES
    from max_system.config.settings import get_settings

    settings = get_settings()
    print("=" * 60)
    print("  Max 系统初始化")
    print("=" * 60)

    # Step 1: 检查.env
    env_path = Path(".env")
    if not env_path.exists():
        print("\n未找到 .env 文件。请先配置以下信息：")
        print("  LLM_API_KEY=你的DeepSeek_API_Key")
        print("  FEISHU_APP_ID=cli_xxxxx")
        print("  FEISHU_APP_SECRET=xxxxx")
        print("  FEISHU_BITABLE_APP_TOKEN=xxxxx")
        print("\n正在创建 .env 文件...")
        env_path.write_text(
            "# Max 系统配置文件\n"
            "LLM_API_KEY=\n"
            "FEISHU_APP_ID=\n"
            "FEISHU_APP_SECRET=\n"
            "FEISHU_BITABLE_APP_TOKEN=\n",
            encoding="utf-8",
        )
        print("已创建 .env 模板，请编辑后重新运行 python -m max_system init")
        return

    # Step 2: 检测LLM连接
    print("\n[1/4] 检测LLM连接...")
    if settings.llm_api_key:
        from max_system.core.llm_client import LLMClient
        llm = LLMClient(settings)
        conn = await llm.test_connection()
        if conn["connected"]:
            print(f"  LLM连接成功: {conn['provider']}/{conn['model']}")
        else:
            print(f"  LLM连接失败: {conn.get('error', '')}")
            print("  请检查 .env 中的 LLM_API_KEY 和 LLM_BASE_URL")
    else:
        print("  必须配置 LLM_API_KEY 才能使用Max，请在 .env 中设置")

    # Step 3: 检测飞书连接
    print("\n[2/4] 检测飞书连接...")
    if settings.feishu_app_id and settings.feishu_app_secret:
        from max_system.integrations.feishu.api_client import FeishuApiClient
        try:
            feishu = FeishuApiClient(settings)
            token = await feishu._get_tenant_token()
            if token:
                print(f"  飞书连接成功")
            else:
                print("  飞书连接失败：无法获取token")
        except Exception as e:
            print(f"  飞书连接失败: {e}")
    else:
        print("  必须配置 FEISHU_APP_ID 和 FEISHU_APP_SECRET 才能使用飞书功能")

    # Step 4: 创建Bitable表
    print("\n[3/4] 创建飞书多维表格...")
    env_updates = {}
    if settings.feishu_bitable_app_token and settings.feishu_app_id:
        from max_system.integrations.feishu.api_client import FeishuApiClient
        try:
            feishu = FeishuApiClient(settings)
            existing = await feishu.list_bitable_tables()
            existing_names = {t["name"]: t["table_id"] for t in existing}

            for table_def in BITABLE_TABLES:
                name = table_def["name"]
                env_key = table_def["env_key"]
                if name in existing_names:
                    tid = existing_names[name]
                    print(f"  [跳过] {name}（已存在）")
                    env_updates[env_key] = tid
                else:
                    print(f"  [创建] {name} ...", end=" ", flush=True)
                    try:
                        resp = await feishu.create_bitable_table(name)
                        tid = resp.get("data", {}).get("table_id", "")
                        if tid:
                            print(f"成功")
                            env_updates[env_key] = tid
                            new_fields = table_def["fields"]
                            if new_fields:
                                try:
                                    await feishu.batch_create_fields(tid, new_fields)
                                    print(f"    字段创建完成 ({len(new_fields)}个)")
                                except Exception as e:
                                    print(f"    字段创建部分失败: {e}")
                        else:
                            print(f"失败: 返回无table_id")
                    except Exception as e:
                        print(f"失败: {e}")

            await feishu.close()
        except Exception as e:
            print(f"  Bitable操作失败: {e}")
    else:
        print("  必须配置 FEISHU_BITABLE_APP_TOKEN 才能创建多维表格")

    # 自动写入.env
    if env_updates:
        if not env_path.exists():
            env_path.write_text("", encoding="utf-8")
        try:
            from dotenv import set_key
            for key, val in env_updates.items():
                set_key(str(env_path), key.upper(), val)
            print(f"\n  已自动写入 {len(env_updates)} 个表ID到 .env 文件")
        except ImportError:
            print("\n  请将以下值手动写入 .env 文件：")
            for key, val in env_updates.items():
                print(f"    {key}={val}")

    # Step 5: 初始化本地数据库
    print("\n[4/4] 初始化本地数据库...")
    from max_system.config.profile import ProfileManager
    from max_system.audit.store import AuditStore

    db_path = settings.get_db_path()
    try:
        profile = ProfileManager(db_path)
        await profile.initialize()
        await profile.close()

        audit = AuditStore(db_path)
        await audit.initialize()
        await audit.close()

        print(f"  数据库已初始化: {db_path}")
    except Exception as e:
        print(f"  数据库初始化失败: {e}")

    print("\n" + "=" * 60)
    print("  初始化完成!")
    print("=" * 60)
    print("\n下一步：")
    print("  python -m max_system      启动飞书模式（默认）")
    print("  python -m max_system cli  启动CLI测试模式")


def _run_cli():
    """CLI交互模式"""
    asyncio.run(_async_cli())


async def _async_cli():
    from max_system.cli.repl import run_repl
    await run_repl()


def _run_feishu():
    """飞书长连接模式（默认）"""
    from max_system.config.settings import get_settings
    settings = get_settings()

    env_path = Path(".env")
    if not env_path.exists():
        print("错误: 未找到 .env 文件。")
        print("请先运行 python -m max_system init 初始化系统。")
        return

    if not settings.llm_api_key:
        print("错误: LLM_API_KEY 未配置。")
        print("请在 .env 中设置 LLM_API_KEY 后重试。")
        return

    print("=" * 60)
    print("  Max 室内设计AI助手  |  飞书长连接模式")
    print("=" * 60)
    print(f"  LLM: {settings.llm_provider} / {settings.llm_model}")
    print(f"  飞书App ID: {settings.feishu_app_id[:10] if settings.feishu_app_id else 'N/A'}...")
    print("=" * 60)

    asyncio.run(_async_feishu())


async def _on_schedule_trigger(job: dict, feishu_api, orchestrator):
    """定时任务触发回调：通过飞书推送提醒"""
    chat_id = job.get("chat_id", "")
    description = job.get("description", "")

    if chat_id:
        try:
            msg = f"提醒：{description}"
            await feishu_api.send_message(chat_id, msg)
        except Exception as e:
            logging.getLogger(__name__).error("定时任务推送失败: %s", e)


async def _async_feishu():
    """飞书长连接异步主循环"""
    from max_system.config.settings import get_settings
    from max_system.core.orchestrator import MaxOrchestrator
    from max_system.core.session_manager import SessionManager
    from max_system.integrations.feishu.long_conn import FeishuLongConn
    from max_system.integrations.feishu.api_client import FeishuApiClient
    from max_system.audit.store import AuditStore
    from max_system.audit.logger import set_audit_store

    settings = get_settings()

    # 初始化审计
    audit_store = AuditStore(settings.get_db_path())
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

    # 初始化定时任务调度器
    scheduler = None
    from max_system.tools.schedule_tools import get_scheduler, get_job_store
    scheduler = get_scheduler()
    if scheduler:
        job_store = get_job_store()
        if job_store:
            await job_store.initialize()
        scheduler.set_trigger_callback(
            lambda job: _on_schedule_trigger(job, feishu_api, orchestrator)
        )
        await scheduler.start()
        print("  定时任务调度器已启动")

    # 已发送过引导卡片的 chat_id 集合
    _sent_onboarding_cards: set[str] = set()

    # ============ 卡片交互回调 ============

    async def handle_card_action(payload: dict):
        """处理飞书卡片交互事件（按钮点击等）"""
        action_value = payload.get("action_value", {})
        form_value = payload.get("form_value", {})
        chat_id = payload.get("chat_id", "")

        logger = logging.getLogger(__name__)
        logger.info("========== 处理卡片交互 ==========")

        if not isinstance(action_value, dict):
            logger.warning("action_value 不是 dict，跳过")
            return

        if action_value.get("action") != "onboarding":
            logger.info("非引导卡片交互，跳过: %s", action_value.get("action"))
            return

        # 设置 workspace 上下文
        if chat_id:
            from max_system.core.orchestrator import _current_workspace
            workspace = await orchestrator.workspace_manager.get_workspace(chat_id)
            _current_workspace.set(workspace)
            from max_system.tools.clientmgr_tools import set_current_workspace
            set_current_workspace(chat_id)
            profile_mgr = workspace.profile if workspace and workspace.profile else orchestrator.profile_manager
        else:
            profile_mgr = orchestrator.profile_manager

        if profile_mgr is None:
            logger.error("无法获取 profile_mgr")
            return

        try:
            from max_system.core.onboarding import process_card_action
            next_card, is_finished = await process_card_action(
                action_value, form_value, profile_mgr
            )

            if is_finished:
                logger.info("引导流程完成，发送欢迎消息")
                await feishu_api.send_message(
                    chat_id,
                    "配置完成！我是 Max，你的 AI 室内设计助手。有什么可以帮你的？\n\n你可以试试：\n- \"帮我分析一下这个客户\"\n- \"生成张先生的合同\"\n- \"查一下最近的材料报价\"",
                )
                return

            if next_card:
                card_json = json.dumps(next_card, ensure_ascii=False)
                await feishu_api.send_message(chat_id, card_json, msg_type="interactive")
                logger.info("已发送引导卡片 step=%s", action_value.get("step"))

        except Exception as e:
            logger.error("处理卡片交互失败: %s", e, exc_info=True)
            try:
                await feishu_api.send_message(chat_id, "处理失败，请重试。")
            except Exception:
                pass

    async def _send_loading_indicator(chat_id: str) -> str | None:
        """2秒后发送加载提示，返回消息ID以便后续删除"""
        try:
            await asyncio.sleep(2)
            resp = await feishu_api.send_message(chat_id, "⏳ 思考中...")
            return resp.get("data", {}).get("message_id", "")
        except asyncio.CancelledError:
            return None
        except Exception:
            return None

    # 消息处理回调
    async def handle_feishu_message(payload: dict):
        chat_id = payload.get("chat_id", "")
        chat_type = payload.get("chat_type", "p2p")
        text = payload.get("text", "")
        user_id = payload.get("user_id", "")
        is_mentioned = payload.get("is_mentioned", False)

        logger = logging.getLogger(__name__)
        logger.info("========== 处理飞书消息 ==========")
        logger.info("chat_id=%s chat_type=%s text=%s mentioned=%s",
                   chat_id[:10] if chat_id else "N/A", chat_type,
                   text[:50] if text else "(空)", is_mentioned)

        # 群聊未@机器人，不响应
        if chat_type == "group" and not is_mentioned:
            logger.info("群聊未@机器人，忽略")
            return

        # 2秒后显示加载提示
        loading_task = asyncio.create_task(_send_loading_indicator(chat_id))

        try:
            # Set up workspace context for multi-tenant isolation
            if chat_id:
                from max_system.core.orchestrator import _current_workspace
                workspace = await orchestrator.workspace_manager.get_workspace(chat_id)
                _current_workspace.set(workspace)
                # Wire clientmgr workspace
                from max_system.tools.clientmgr_tools import set_current_workspace
                set_current_workspace(chat_id)

            # 首次使用：发送引导卡片
            if chat_id and chat_id not in _sent_onboarding_cards:
                profile_mgr = workspace.profile if workspace and workspace.profile else orchestrator.profile_manager
                if profile_mgr:
                    try:
                        is_first = await profile_mgr.is_empty()
                        if is_first:
                            _sent_onboarding_cards.add(chat_id)
                            from max_system.core.onboarding import get_first_card
                            card = get_first_card()
                            card_json = json.dumps(card, ensure_ascii=False)
                            await feishu_api.send_message(chat_id, card_json, msg_type="interactive")
                            logger.info("已发送引导卡片到 chat=%s", chat_id[:10])
                    except Exception as e:
                        logger.warning("检查首次使用状态失败: %s", e)

            # 会话上下文
            session = await session_manager.get_or_create(chat_id)
            session_manager.add_message(session, "user", text)
            history = session_manager.get_history(session)

            # 调度到Max
            response = await orchestrator.dispatch(
                text, session_id=chat_id, user_id=user_id,
                history=history[:-1],
            )

            # 取消加载提示
            loading_task.cancel()
            try:
                await loading_task
            except asyncio.CancelledError:
                pass

            # 发送响应
            if response:
                session_manager.add_message(session, "assistant", response)
                max_len = 4000
                if len(response) <= max_len:
                    await feishu_api.send_message(chat_id, response)
                else:
                    for i in range(0, len(response), max_len):
                        await feishu_api.send_message(chat_id, response[i:i + max_len])
                        await asyncio.sleep(0.5)

        except Exception as e:
            loading_task.cancel()
            try:
                await loading_task
            except asyncio.CancelledError:
                pass
            logging.getLogger(__name__).error("处理飞书消息失败: %s", e, exc_info=True)
            try:
                await feishu_api.send_message(chat_id, "处理异常，请稍后重试。")
            except Exception:
                pass

    # 启动飞书长连接
    feishu_conn = FeishuLongConn(settings, handle_feishu_message, on_card_action=handle_card_action)
    main_loop = asyncio.get_event_loop()

    print("\n正在连接飞书长连接...")
    feishu_conn.start(main_loop=main_loop)

    await asyncio.sleep(3)
    print("飞书长连接已启动，等待消息中...")
    print("按 Ctrl+C 退出\n")

    # 主动提醒：每24小时检查一次
    last_reminder_check = 0.0

    async def _run_daily_reminder_check():
        """每日检查客户跟进提醒，如有提醒则发送给设计师"""
        nonlocal last_reminder_check
        now = time.time()
        if now - last_reminder_check < 86400:
            return
        last_reminder_check = now
        try:
            from max_system.tools.reminder_tools import _check_proactive_reminders
            result = await _check_proactive_reminders()
            if result["count"] > 0:
                msg_lines = ["[自动提醒] 以下客户需要关注："]
                for r in result["reminders"]:
                    msg_lines.append(f"- {r['message']}")
                msg = "\n".join(msg_lines)
                logger = logging.getLogger(__name__)
                logger.info("发送主动提醒: %d 条", result["count"])
                print(f"\n{'='*40}\n{msg}\n{'='*40}\n")
        except Exception as e:
            logging.getLogger(__name__).warning("主动提醒检查失败: %s", e)

    try:
        while True:
            await asyncio.sleep(1)
            await _run_daily_reminder_check()
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n正在关闭...")
    finally:
        if scheduler:
            await scheduler.stop()
        await session_manager.stop()
        await feishu_api.close()
        await audit_store.close()
        await orchestrator.close()
        print("Max系统已关闭")


if __name__ == "__main__":
    main()
