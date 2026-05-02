"""FastAPI应用工厂"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from max_system.config.settings import get_settings
from max_system.core.orchestrator import MaxOrchestrator
from max_system.core.session_manager import SessionManager
from max_system.integrations.feishu.bot import FeishuBot
from max_system.audit.store import AuditStore
from max_system.audit.logger import set_audit_store

logger = logging.getLogger(__name__)

orchestrator: MaxOrchestrator | None = None
session_manager: SessionManager | None = None
feishu_bot: FeishuBot | None = None
audit_store: AuditStore | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator, session_manager, feishu_bot, audit_store

    settings = get_settings()

    audit_store = AuditStore(settings.audit_db_path)
    await audit_store.initialize()
    set_audit_store(audit_store)

    orchestrator = MaxOrchestrator(settings)
    await orchestrator.initialize()

    session_manager = SessionManager()
    await session_manager.start()

    feishu_bot = FeishuBot(orchestrator, session_manager, settings)

    from max_system.api.routes.feishu_webhook import set_bot
    from max_system.api.routes.task_status import set_audit_store as set_task_audit_store
    set_bot(feishu_bot)
    set_task_audit_store(audit_store)

    logger.info("Max系统启动完成 (LLM: %s/%s)", orchestrator.llm.provider_name, orchestrator.llm.model)

    yield

    if feishu_bot:
        await feishu_bot.close()
    if session_manager:
        await session_manager.stop()
    if audit_store:
        await audit_store.close()
    logger.info("Max系统已关闭")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Max 多Agent室内设计AI助手系统",
        version="0.1.0",
        lifespan=lifespan,
    )

    from max_system.api.routes.health import router as health_router
    from max_system.api.routes.feishu_webhook import router as feishu_router
    from max_system.api.routes.task_status import router as task_router

    app.include_router(health_router, tags=["健康检查"])
    app.include_router(feishu_router, tags=["飞书Webhook"])
    app.include_router(task_router, tags=["任务状态"])

    return app
