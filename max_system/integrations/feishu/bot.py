"""飞书机器人：Webhook处理、事件分发"""

import asyncio
import hashlib
import json
import logging

from max_system.config.settings import MaxSettings
from max_system.core.session_manager import SessionManager
from max_system.core.orchestrator import MaxOrchestrator
from max_system.integrations.feishu.adapter import FeishuAdapter
from max_system.integrations.feishu.api_client import FeishuApiClient
from max_system.integrations.feishu.event_types import FeishuEventType

logger = logging.getLogger(__name__)


class FeishuBot:
    """飞书机器人核心"""

    def __init__(
        self,
        orchestrator: MaxOrchestrator,
        session_manager: SessionManager,
        settings: MaxSettings,
    ):
        self.orchestrator = orchestrator
        self.session_manager = session_manager
        self.settings = settings
        self.adapter = FeishuAdapter()
        self.api_client = FeishuApiClient(settings)

    async def close(self) -> None:
        await self.api_client.close()

    async def handle_event(self, body: dict) -> dict:
        """处理飞书Webhook事件"""
        if body.get("type") == "url_verification":
            return {"challenge": body.get("challenge", "")}

        if not self._verify_signature(body):
            logger.warning("飞书事件签名验证失败")
            return {"status": "error", "message": "签名验证失败"}

        header = body.get("header", {})
        event_type = header.get("event_type", "")

        if event_type == FeishuEventType.MESSAGE_RECEIVE:
            asyncio.create_task(self._handle_message(body))
            return {"status": "ok"}

        elif event_type in (FeishuEventType.APPROVAL_APPROVED, FeishuEventType.APPROVAL_REJECTED):
            approval_event = self.adapter.parse_approval_event(body)
            if approval_event:
                asyncio.create_task(self._handle_approval(approval_event))
            return {"status": "ok"}

        return {"status": "ignored"}

    async def _handle_message(self, payload: dict) -> None:
        """异步处理消息事件"""
        msg_event = self.adapter.parse_message_event(payload)
        if not msg_event:
            return

        command = self.adapter.to_normalized_command(msg_event)

        if not command.should_respond:
            return

        try:
            session = await self.session_manager.get_or_create(command.chat_id)
            self.session_manager.add_message(session, "user", command.text)

            history = self.session_manager.get_history(session)

            response = await self.orchestrator.dispatch(
                command.text, session_id=command.chat_id, user_id=command.user_id,
                history=history[:-1],  # 排除刚添加的当前消息（dispatch会自己加）
            )

            if response:
                self.session_manager.add_message(session, "assistant", response)
                await self._send_long_message(command.chat_id, response)

        except Exception as e:
            logger.error("处理飞书消息失败: %s", e, exc_info=True)
            await self.api_client.send_message(
                command.chat_id, f"处理异常，请稍后重试。错误: {str(e)[:200]}"
            )

    async def _handle_approval(self, event) -> None:
        logger.info("收到审批回调: %s, instance=%s", event.status, event.instance_code)

    async def _send_long_message(self, chat_id: str, text: str, max_len: int = 4000) -> None:
        if len(text) <= max_len:
            await self.api_client.send_message(chat_id, text)
            return
        for i in range(0, len(text), max_len):
            await self.api_client.send_message(chat_id, text[i:i + max_len])
            if i + max_len < len(text):
                await asyncio.sleep(0.5)

    def _verify_signature(self, body: dict) -> bool:
        if not self.settings.feishu_verification_token:
            return True
        token = self.settings.feishu_verification_token
        timestamp = body.get("header", {}).get("timestamp", "")
        nonce = body.get("header", {}).get("nonce", "")
        if not timestamp or not nonce:
            return True
        sign_base = f"{timestamp}{nonce}{token}"
        expected = hashlib.sha256(sign_base.encode()).hexdigest()
        actual = body.get("header", {}).get("sign", "")
        return actual == expected
