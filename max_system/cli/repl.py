"""CLI交互式REPL：在终端直接与Max对话"""

import asyncio
import logging
import sys
import time

from max_system.config.settings import get_settings
from max_system.core.orchestrator import MaxOrchestrator
from max_system.core.intent_router import IntentRouter
from max_system.audit.store import AuditStore
from max_system.audit.logger import set_audit_store

logger = logging.getLogger(__name__)


def print_banner(settings):
    provider = settings.llm_provider
    model = settings.llm_model if provider == "deepseek" else settings.ollama_model
    print()
    print("=" * 60)
    print("  Max 多Agent室内设计AI助手系统  |  CLI 模式")
    print("  斑马精装")
    print("=" * 60)
    print(f"  LLM: {provider} / {model}")
    print(f"  飞书: {'已配置' if settings.feishu_app_id else '未配置'}")
    print(f"  Obsidian: {settings.obsidian_vault_path}")
    print("  输入消息与Max对话，输入 /quit 退出")
    print("  输入 /help 查看帮助")
    print("=" * 60)
    print()


async def run_repl():
    """启动CLI交互循环"""
    settings = get_settings()

    # 初始化审计存储
    audit_store = AuditStore(settings.audit_db_path)
    await audit_store.initialize()
    set_audit_store(audit_store)

    # 初始化编排器
    orchestrator = MaxOrchestrator(settings)
    await orchestrator.initialize()

    # 测试LLM连接
    print("正在测试LLM连接...")
    conn_result = await orchestrator.llm.test_connection()
    if conn_result["connected"]:
        print(f"  [OK] {conn_result['provider']} / {conn_result['model']} 连接成功")
        print(f"  回复: {conn_result.get('reply', '')}")
    else:
        print(f"  [ERR] 连接失败: {conn_result.get('error', '未知错误')}")
        print("  请检查 .env 中的 LLM 配置")
        await audit_store.close()
        return

    print_banner(settings)

    # 对话历史（按session维护）
    session_id = "cli_session"
    history: list[dict] = []

    try:
        while True:
            try:
                user_input = input("设计师 > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\n再见！")
                break

            if not user_input:
                continue

            if user_input == "/quit":
                print("再见！")
                break
            elif user_input == "/help":
                _print_help()
                continue
            elif user_input == "/status":
                _print_status(orchestrator)
                continue
            elif user_input == "/clear":
                history.clear()
                print("对话历史已清空\n")
                continue
            elif user_input == "/model":
                # 切换模型
                print(f"当前: {orchestrator.llm.provider_name} / {orchestrator.llm.model}")
                print("输入 deepseek 或 ollama 切换:")
                try:
                    choice = input("  > ").strip()
                    if choice in ("deepseek", "ollama"):
                        orchestrator.llm = __import__(
                            "max_system.core.llm_client", fromlist=["LLMClient"]
                        ).LLMClient(settings, provider=choice)
                        print(f"  已切换到: {orchestrator.llm.provider_name} / {orchestrator.llm.model}\n")
                except (EOFError, KeyboardInterrupt):
                    pass
                continue
            elif user_input.startswith("/"):
                print(f"未知命令: {user_input}，输入 /help 查看帮助\n")
                continue

            # 发送到Max
            print()
            start_time = time.time()

            try:
                response = await orchestrator.dispatch(
                    user_input, session_id=session_id, history=history or None
                )
                elapsed = time.time() - start_time

                # 保存对话历史
                history.append({"role": "user", "content": user_input})
                history.append({"role": "assistant", "content": response})

                # 限制历史长度
                max_msgs = 40
                if len(history) > max_msgs:
                    history[:] = history[-max_msgs:]

                print(response)
                print(f"\n[{elapsed:.1f}s | {orchestrator.llm.provider_name}/{orchestrator.llm.model}]")
            except Exception as e:
                print(f"执行出错: {e}")

            print()

    finally:
        await audit_store.close()


def _print_help():
    print("""
可用命令:
  /quit    退出CLI
  /status  查看系统状态
  /model   切换LLM（deepseek/ollama）
  /clear   清空对话历史
  /help    显示此帮助

对话说明:
  直接输入消息与Max对话
  Max会自动调度Talker/AfterPro/MediaPro/Helper处理
  示例:
    "帮我分析一下新客户张先生的需求"
    "写一篇小红书文案"
    "创建客户档案"
""")


def _print_status(orchestrator: MaxOrchestrator):
    print(f"""
系统状态:
  LLM: {orchestrator.llm.provider_name} / {orchestrator.llm.model}
  Agent数: {len(orchestrator.agent_prompts)}
  工具数: {len(orchestrator._tools)}
  已注册Agent: {', '.join(orchestrator.agent_prompts.keys())}
  已注册工具: {', '.join(orchestrator._tools.keys())}
""")
