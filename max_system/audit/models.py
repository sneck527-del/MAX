"""审计日志数据模型"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any

from max_system.config.schema import RiskLevel


@dataclass
class AuditEntry:
    """审计日志条目"""
    timestamp: str
    session_id: str
    user_id: str
    action: str  # "dispatch", "tool_call", "approval", "response"
    agent: str  # "max", "talker", "afterpro", "mediapro", "helper"
    tool_name: str | None = None
    tool_input: dict | None = None
    tool_output: dict | None = None
    result_status: str = "success"  # "success", "blocked", "error"
    risk_level: str = "low"  # "low", "medium", "high"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def create(
        cls,
        session_id: str,
        user_id: str,
        action: str,
        agent: str,
        **kwargs,
    ) -> "AuditEntry":
        return cls(
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            user_id=user_id,
            action=action,
            agent=agent,
            **kwargs,
        )


@dataclass
class TaskLog:
    """任务执行日志"""
    task_id: str
    session_id: str
    user_id: str
    agent: str
    input_message: str
    output_message: str
    status: str  # "pending", "running", "completed", "failed"
    created_at: str = ""
    completed_at: str = ""
    duration_ms: int = 0
    risk_level: str = "low"

    def to_dict(self) -> dict:
        return asdict(self)
