"""SQLite后端审计日志存储"""

import json
import logging
from pathlib import Path
from typing import Any

import aiosqlite

from max_system.audit.models import AuditEntry, TaskLog

logger = logging.getLogger(__name__)

CREATE_AUDIT_TABLE = """
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    agent TEXT NOT NULL,
    tool_name TEXT,
    tool_input TEXT,
    tool_output TEXT,
    result_status TEXT DEFAULT 'success',
    risk_level TEXT DEFAULT 'low'
)
"""

CREATE_TASK_TABLE = """
CREATE TABLE IF NOT EXISTS task_log (
    task_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    agent TEXT NOT NULL,
    input_message TEXT,
    output_message TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT,
    completed_at TEXT,
    duration_ms INTEGER DEFAULT 0,
    risk_level TEXT DEFAULT 'low'
)
"""


class AuditStore:
    """SQLite审计日志存储"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """初始化数据库连接和表结构"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(str(self.db_path))
        self._db.row_factory = aiosqlite.Row
        await self._db.execute(CREATE_AUDIT_TABLE)
        await self._db.execute(CREATE_TASK_TABLE)
        await self._db.commit()
        logger.info("审计数据库已初始化: %s", self.db_path)

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    async def log(self, entry: AuditEntry) -> None:
        """写入审计日志"""
        if not self._db:
            return
        try:
            await self._db.execute(
                """INSERT INTO audit_log
                   (timestamp, session_id, user_id, action, agent, tool_name,
                    tool_input, tool_output, result_status, risk_level)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry.timestamp,
                    entry.session_id,
                    entry.user_id,
                    entry.action,
                    entry.agent,
                    entry.tool_name,
                    json.dumps(entry.tool_input, ensure_ascii=False) if entry.tool_input else None,
                    json.dumps(entry.tool_output, ensure_ascii=False) if entry.tool_output else None,
                    entry.result_status,
                    entry.risk_level,
                ),
            )
            await self._db.commit()
        except Exception as e:
            logger.error("写入审计日志失败: %s", e)

    async def log_task(self, task: TaskLog) -> None:
        """写入任务日志"""
        if not self._db:
            return
        try:
            await self._db.execute(
                """INSERT OR REPLACE INTO task_log
                   (task_id, session_id, user_id, agent, input_message,
                    output_message, status, created_at, completed_at, duration_ms, risk_level)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    task.task_id,
                    task.session_id,
                    task.user_id,
                    task.agent,
                    task.input_message,
                    task.output_message,
                    task.status,
                    task.created_at,
                    task.completed_at,
                    task.duration_ms,
                    task.risk_level,
                ),
            )
            await self._db.commit()
        except Exception as e:
            logger.error("写入任务日志失败: %s", e)

    async def query(
        self,
        session_id: str | None = None,
        action: str | None = None,
        agent: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """查询审计日志"""
        if not self._db:
            return []

        conditions = []
        params: list[Any] = []
        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        if action:
            conditions.append("action = ?")
            params.append(action)
        if agent:
            conditions.append("agent = ?")
            params.append(agent)

        where = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)

        cursor = await self._db.execute(
            f"SELECT * FROM audit_log WHERE {where} ORDER BY id DESC LIMIT ?",
            params,
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
