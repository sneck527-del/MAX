"""飞书事件适配器：解析Webhook事件、格式化响应"""

import json
import logging

from max_system.config.schema import NormalizedCommand
from max_system.integrations.feishu.event_types import (
    FeishuEventType,
    FeishuMessageEvent,
    FeishuApprovalEvent,
)

logger = logging.getLogger(__name__)


class FeishuAdapter:
    """解析飞书Webhook事件为内部数据结构"""

    def parse_message_event(self, payload: dict) -> FeishuMessageEvent | None:
        """解析消息接收事件"""
        try:
            event = payload.get("event", payload.get("data", {}))

            # 提取基本信息
            chat_id = event.get("chat_id", "")
            user_id = event.get("sender", {}).get("sender_id", {}).get("user_id", "")
            user_name = event.get("sender", {}).get("sender_id", {}).get("name", "")
            chat_type = event.get("chat_type", "p2p")
            message_id = event.get("message_id", "")
            message_type = event.get("message_type", "text")

            # 提取消息文本
            text = self._extract_text(event, message_type)

            # 检测是否@了机器人
            mentions = event.get("mentions", [])
            is_mentioned = len(mentions) > 0

            return FeishuMessageEvent(
                event_type=FeishuEventType.MESSAGE_RECEIVE,
                chat_id=chat_id,
                user_id=user_id,
                user_name=user_name,
                chat_type=chat_type,
                message_id=message_id,
                message_type=message_type,
                text=text,
                is_mentioned=is_mentioned,
                raw=payload,
            )
        except Exception as e:
            logger.error("解析飞书消息事件失败: %s", e)
            return None

    def parse_approval_event(self, payload: dict) -> FeishuApprovalEvent | None:
        """解析审批事件"""
        try:
            event = payload.get("event", payload.get("data", {}))
            status = event.get("status", "")

            return FeishuApprovalEvent(
                event_type=(
                    FeishuEventType.APPROVAL_APPROVED
                    if status == "approved"
                    else FeishuEventType.APPROVAL_REJECTED
                ),
                approval_code=event.get("approval_code", ""),
                instance_code=event.get("instance_code", ""),
                user_id=event.get("user_id", ""),
                status=status,
                raw=payload,
            )
        except Exception as e:
            logger.error("解析飞书审批事件失败: %s", e)
            return None

    def to_normalized_command(self, msg_event: FeishuMessageEvent) -> NormalizedCommand:
        """将飞书消息事件转换为标准化指令"""
        is_group = msg_event.chat_type == "group"
        should_respond = not is_group or msg_event.is_mentioned

        # 去除@机器人的文本
        clean_text = msg_event.text
        if msg_event.is_mentioned:
            import re
            clean_text = re.sub(r'@_user_\d+\s*', '', clean_text).strip()

        return NormalizedCommand(
            chat_id=msg_event.chat_id,
            user_id=msg_event.user_id,
            user_name=msg_event.user_name,
            message_type=msg_event.message_type,
            text=clean_text,
            is_group=is_group,
            is_mentioned=msg_event.is_mentioned,
            should_respond=should_respond,
        )

    def _extract_text(self, event: dict, message_type: str) -> str:
        """从事件中提取消息文本"""
        content = event.get("message", event).get("content", "{}")

        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                return content

        if message_type == "text":
            return content.get("text", "")
        elif message_type == "post":
            # 富文本：提取所有文本内容
            parts = []
            for lang_content in content.get("content", []):
                for block in lang_content:
                    if isinstance(block, dict) and block.get("tag") == "text":
                        parts.append(block.get("text", ""))
            return " ".join(parts)
        else:
            return json.dumps(content, ensure_ascii=False)
