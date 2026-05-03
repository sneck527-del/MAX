"""共享数据模型"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


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
    metadata: dict[str, Any] = field(default_factory=dict)
