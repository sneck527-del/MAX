"""审计记录器：统一入口"""

import logging
from datetime import datetime

from max_system.audit.models import AuditEntry, TaskLog
from max_system.audit.store import AuditStore
from max_system.config.schema import NormalizedCommand

logger = logging.getLogger(__name__)

_store: AuditStore | None = None


def get_audit_store() -> AuditStore | None:
    return _store


def set_audit_store(store: AuditStore) -> None:
    global _store
    _store = store


async def log_dispatch(command: NormalizedCommand, agent: str, result_status: str = "success") -> None:
    """记录调度事件"""
    if not _store:
        return
    entry = AuditEntry.create(
        session_id=command.chat_id,
        user_id=command.user_id,
        action="dispatch",
        agent=agent,
        result_status=result_status,
    )
    await _store.log(entry)


async def log_tool_call(
    session_id: str,
    user_id: str,
    agent: str,
    tool_name: str,
    tool_input: dict | None = None,
    tool_output: dict | None = None,
    result_status: str = "success",
    risk_level: str = "low",
) -> None:
    """记录工具调用"""
    if not _store:
        return
    entry = AuditEntry.create(
        session_id=session_id,
        user_id=user_id,
        action="tool_call",
        agent=agent,
        tool_name=tool_name,
        tool_input=tool_input,
        tool_output=tool_output,
        result_status=result_status,
        risk_level=risk_level,
    )
    await _store.log(entry)


async def log_response(
    session_id: str,
    user_id: str,
    agent: str,
    result_status: str = "success",
) -> None:
    """记录响应事件"""
    if not _store:
        return
    entry = AuditEntry.create(
        session_id=session_id,
        user_id=user_id,
        action="response",
        agent=agent,
        result_status=result_status,
    )
    await _store.log(entry)
