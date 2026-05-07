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
        on_card_action: Callable[[dict], Awaitable[None]] | None = None,
    ):
        self.settings = settings
        self.on_message = on_message
        self.on_card_action = on_card_action
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

            # 注册卡片交互事件
            if self.on_card_action is not None:
                handler_builder.register_p2_card_action_trigger(self._handle_card_action_event)

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

            # 文件消息：提取 file_key 和 file_name
            file_key = ""
            file_name = ""
            if message_type == "file":
                if isinstance(content, str):
                    try:
                        content = json.loads(content)
                    except json.JSONDecodeError:
                        pass
                if isinstance(content, dict):
                    file_key = content.get("file_key", "")
                    file_name = content.get("file_name", "")

            mentions = message.mentions if hasattr(message, 'mentions') else []
            is_mentioned = bool(mentions)

            logger.info("收到飞书消息: chat=%s, type=%s, text=%s, file_key=%s, mentioned=%s",
                       chat_id[:10] if chat_id else "N/A", message_type,
                       text[:80] if text else "(空)",
                       file_key[:10] if file_key else "N/A",
                       is_mentioned)

            payload = {
                "chat_id": chat_id,
                "user_id": user_id,
                "user_name": "",
                "chat_type": chat_type,
                "message_type": message_type,
                "message_id": message_id,
                "text": text,
                "file_key": file_key,
                "file_name": file_name,
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

    def _handle_card_action_event(self, data, **kwargs):
        """处理飞书卡片交互事件（同步回调）"""
        try:
            logger.info("========== 收到飞书卡片交互事件 ==========")
            logger.info("data type: %s", type(data).__name__)

            event_data = data.event if hasattr(data, 'event') else data
            if event_data is None:
                logger.warning("卡片交互事件 data.event 为空，跳过")
                return

            action = event_data.action if hasattr(event_data, 'action') else None
            operator = event_data.operator if hasattr(event_data, 'operator') else None
            context = event_data.context if hasattr(event_data, 'context') else None

            if action is None:
                logger.warning("卡片交互缺少 action 数据，跳过")
                return

            action_value = action.value if hasattr(action, 'value') else {}
            form_value = action.form_value if hasattr(action, 'form_value') else {}
            action_tag = action.tag if hasattr(action, 'tag') else ""

            open_chat_id = context.open_chat_id if context and hasattr(context, 'open_chat_id') else ""
            open_message_id = context.open_message_id if context and hasattr(context, 'open_message_id') else ""

            user_id = ""
            if operator:
                user_id = operator.open_id if hasattr(operator, 'open_id') and operator.open_id else ""
                if not user_id:
                    user_id = operator.user_id if hasattr(operator, 'user_id') and operator.user_id else ""

            logger.info("卡片交互: action=%s, value=%s, form_values=%d, chat=%s, user=%s",
                       action_tag, str(action_value)[:100], len(form_value) if form_value else 0,
                       open_chat_id[:10] if open_chat_id else "N/A",
                       user_id[:10] if user_id else "N/A")

            payload = {
                "message_type": "card_action",
                "chat_id": open_chat_id,
                "user_id": user_id,
                "message_id": open_message_id,
                "text": json.dumps({"action_value": action_value, "form_value": form_value}, ensure_ascii=False),
                "action_value": action_value,
                "form_value": form_value,
                "is_mentioned": False,
            }

            if self._main_loop and not self._main_loop.is_closed():
                asyncio.run_coroutine_threadsafe(self.on_card_action(payload), self._main_loop)
                logger.info("已调度卡片交互到主事件循环")

        except Exception as e:
            logger.error("处理卡片交互事件失败: %s", e, exc_info=True)

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
