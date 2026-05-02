"""飞书事件类型定义"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FeishuEventType(str, Enum):
    URL_VERIFICATION = "url_verification"
    MESSAGE_RECEIVE = "im.message.receive_v1"
    APPROVAL_APPROVED = "approval.approved"
    APPROVAL_REJECTED = "approval.rejected"


@dataclass
class FeishuMessageEvent:
    """飞书消息事件"""
    event_type: FeishuEventType
    chat_id: str
    user_id: str
    user_name: str
    chat_type: str  # "p2p" 或 "group"
    message_id: str
    message_type: str  # "text", "post", "image"
    text: str
    is_mentioned: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class FeishuApprovalEvent:
    """飞书审批事件"""
    event_type: FeishuEventType
    approval_code: str
    instance_code: str
    user_id: str
    status: str  # "approved" 或 "rejected"
    raw: dict[str, Any] = field(default_factory=dict)
