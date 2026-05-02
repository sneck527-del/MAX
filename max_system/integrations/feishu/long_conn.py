"""飞书长连接客户端：通过WebSocket接收飞书事件（无需内网穿透）"""

import asyncio
import json
import logging
import threading
from typing import Callable, Awaitable

from max_system.config.settings import MaxSettings

logger = logging.getLogger(__name__)


class FeishuLongConn:
    """飞书长连接客户端

    使用 lark-oapi 的 WebSocket 模式接收事件，
    无需公网IP和内网穿透。
    在独立线程和独立事件循环中运行。
    """

    def __init__(
        self,
        settings: MaxSettings,
        on_message: Callable[[dict], Awaitable[None]],
    ):
        self.settings = settings
        self.on_message = on_message
        self._ws_client = None
        self._main_loop: asyncio.AbstractEventLoop | None = None

    def start(self, main_loop: asyncio.AbstractEventLoop | None = None) -> None:
        """启动长连接（在独立线程+独立事件循环中运行）"""
        self._main_loop = main_loop
        thread = threading.Thread(target=self._run_in_thread, daemon=True)
        thread.start()
        logger.info("飞书长连接线程已启动")

    def _run_in_thread(self) -> None:
        """在独立线程中运行，创建自己的事件循环"""
        from lark_oapi.ws import Client as WsClient
        from lark_oapi.event.dispatcher_handler import EventDispatcherHandler

        # 为这个线程创建全新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # 构建事件处理器
            handler_builder = EventDispatcherHandler.builder(
                encrypt_key=self.settings.feishu_encrypt_key,
                verification_token=self.settings.feishu_verification_token,
            )

            # 注册消息接收事件
            handler_builder.register_p2_im_message_receive_v1(self._handle_message_event)

            handler = handler_builder.build()

            # 创建长连接客户端
            self._ws_client = WsClient(
                app_id=self.settings.feishu_app_id,
                app_secret=self.settings.feishu_app_secret,
                event_handler=handler,
                auto_reconnect=True,
            )

            logger.info("飞书长连接客户端启动中...")
            self._ws_client.start()  # 阻塞调用，使用本线程的事件循环

        except Exception as e:
            logger.error("飞书长连接异常: %s", e, exc_info=True)
        finally:
            loop.close()

    def _handle_message_event(self, data, **kwargs):
        """处理飞书消息接收事件（同步回调）"""
        try:
            logger.info("========== 收到飞书事件回调 ==========")
            logger.info("data type: %s", type(data).__name__)

            event_data = data.event if hasattr(data, 'event') else data
            logger.info("event_data type: %s, has event attr: %s",
                       type(event_data).__name__, hasattr(data, 'event'))

            message = event_data.message if hasattr(event_data, 'message') else {}
            sender = event_data.sender if hasattr(event_data, 'sender') else {}
            logger.info("message type: %s, sender type: %s",
                       type(message).__name__, type(sender).__name__)

            chat_id = message.chat_id if hasattr(message, 'chat_id') else ""
            chat_type = message.chat_type if hasattr(message, 'chat_type') else "p2p"
            message_type = message.message_type if hasattr(message, 'message_type') else "text"
            content = message.content if hasattr(message, 'content') else "{}"
            message_id = message.message_id if hasattr(message, 'message_id') else ""

            sender_id = sender.sender_id if hasattr(sender, 'sender_id') else {}
            user_id = sender_id.user_id if hasattr(sender_id, 'user_id') else ""

            text = self._extract_text(content, message_type)

            mentions = message.mentions if hasattr(message, 'mentions') else []
            is_mentioned = bool(mentions)

            logger.info("收到飞书消息: chat=%s, type=%s, text=%s, mentioned=%s",
                       chat_id[:10] if chat_id else "N/A", message_type,
                       text[:80] if text else "(空)", is_mentioned)

            payload = {
                "chat_id": chat_id,
                "user_id": user_id,
                "user_name": "",
                "chat_type": chat_type,
                "message_type": message_type,
                "message_id": message_id,
                "text": text,
                "is_mentioned": is_mentioned,
            }

            # 在主事件循环中调度异步回调
            if self._main_loop and not self._main_loop.is_closed():
                asyncio.run_coroutine_threadsafe(self.on_message(payload), self._main_loop)
                logger.info("已调度消息到主事件循环")
            else:
                logger.warning("主事件循环不可用，跳过消息处理")

        except Exception as e:
            logger.error("处理飞书消息事件失败: %s", e, exc_info=True)

    def _extract_text(self, content, message_type: str) -> str:
        """提取消息文本"""
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                return content

        if message_type == "text":
            return content.get("text", "")
        elif message_type == "post":
            parts = []
            for lang_content in content.get("content", []):
                for block in lang_content:
                    if isinstance(block, dict) and block.get("tag") == "text":
                        parts.append(block.get("text", ""))
            return " ".join(parts)
        else:
            return json.dumps(content, ensure_ascii=False)
