"""会话管理器：每个飞书聊天维护独立的对话历史"""

import asyncio
import logging
import time
from typing import Dict, List

logger = logging.getLogger(__name__)

MAX_IDLE_SECONDS = 3600  # 1小时
MAX_HISTORY_TURNS = 20   # 最大对话轮数（每轮=user+assistant=2条）


class SessionInfo:
    """会话元信息"""
    __slots__ = ("messages", "created_at", "last_active")

    def __init__(self):
        self.messages: List[dict] = []
        self.created_at = time.monotonic()
        self.last_active = time.monotonic()


class SessionManager:
    """管理飞书聊天到对话历史的映射

    每个飞书chat_id对应一个独立的对话历史，
    历史跨消息保持，空闲超时后清理。
    """

    def __init__(self):
        self._sessions: Dict[str, SessionInfo] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None

    async def start(self) -> None:
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("会话管理器已启动")

    async def stop(self) -> None:
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None
        self._sessions.clear()
        logger.info("会话管理器已停止")

    async def get_or_create(self, chat_id: str) -> SessionInfo:
        """获取或创建指定聊天的会话"""
        async with self._lock:
            if chat_id not in self._sessions:
                self._sessions[chat_id] = SessionInfo()
                logger.info("为聊天 %s 创建新会话", chat_id)
            info = self._sessions[chat_id]
            info.last_active = time.monotonic()
            return info

    async def close_session(self, chat_id: str) -> None:
        async with self._lock:
            self._sessions.pop(chat_id, None)
            logger.info("已关闭聊天 %s 的会话", chat_id)

    def add_message(self, session: SessionInfo, role: str, content: str) -> None:
        """添加一条消息到会话历史"""
        session.messages.append({"role": role, "content": content})
        self._trim_history(session)

    def get_history(self, session: SessionInfo) -> List[dict]:
        """获取会话历史（用于构建LLM对话）"""
        return list(session.messages)

    def _trim_history(self, session: SessionInfo) -> None:
        """裁剪对话历史，保留最近N轮"""
        max_msgs = MAX_HISTORY_TURNS * 2
        if len(session.messages) > max_msgs:
            session.messages = session.messages[-max_msgs:]

    @property
    def active_count(self) -> int:
        return len(self._sessions)

    async def _cleanup_loop(self) -> None:
        while True:
            await asyncio.sleep(300)
            await self._cleanup_idle()

    async def _cleanup_idle(self) -> None:
        now = time.monotonic()
        to_close = []
        async with self._lock:
            for chat_id, info in self._sessions.items():
                if now - info.last_active > MAX_IDLE_SECONDS:
                    to_close.append(chat_id)
        for chat_id in to_close:
            await self.close_session(chat_id)
