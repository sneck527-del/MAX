"""共享数据模型"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IntentCategory(str, Enum):
    TALKER = "talker"
    AFTERPRO = "afterpro"
    MEDIAPRO = "mediapro"
    HELPER = "helper"
    MAX_DIRECT = "max_direct"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class NormalizedCommand:
    """从飞书消息解析后的标准化指令"""
    chat_id: str
    user_id: str
    user_name: str
    message_type: str  # "text", "post", "image"
    text: str
    is_group: bool
    is_mentioned: bool
    should_respond: bool  # 单聊始终响应，群聊仅@时响应
    intent: IntentCategory | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """子Agent执行结果"""
    task_id: str
    agent: str
    status: str  # "success", "partial", "failed", "needs_approval"
    content: str
    artifacts: list[dict] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    needs_human_review: bool = False
    feishu_sync_status: str = "pending"
    obsidian_path: str | None = None


@dataclass
class AuditEntry:
    """审计日志条目"""
    timestamp: str
    session_id: str
    user_id: str
    action: str  # "dispatch", "tool_call", "approval", "response"
    agent: str
    tool_name: str | None = None
    tool_input: dict | None = None
    tool_output: dict | None = None
    result_status: str = "success"
    risk_level: RiskLevel = RiskLevel.LOW
