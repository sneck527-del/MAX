"""定时任务调度器：SQLite持久化 + 异步执行"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Awaitable

import aiosqlite

logger = logging.getLogger(__name__)

CREATE_SCHEDULE_TABLE = """
CREATE TABLE IF NOT EXISTS scheduled_jobs (
    job_id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    trigger_time TEXT NOT NULL,
    recurrence TEXT DEFAULT '',
    payload TEXT DEFAULT '{}',
    chat_id TEXT DEFAULT '',
    status TEXT DEFAULT 'pending',
    created_at TEXT NOT NULL,
    last_run TEXT DEFAULT '',
    next_run TEXT DEFAULT ''
)
"""


class JobStore:
    """SQLite持久化的定时任务存储"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(str(self.db_path))
        self._db.row_factory = aiosqlite.Row
        await self._db.execute(CREATE_SCHEDULE_TABLE)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    def _ensure_db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("JobStore未初始化")
        return self._db

    async def add_job(
        self,
        description: str,
        trigger_time: str,
        chat_id: str = "",
        recurrence: str = "",
        payload: dict | None = None,
    ) -> str:
        db = self._ensure_db()
        job_id = uuid.uuid4().hex[:12]
        now = datetime.now().isoformat()
        await db.execute(
            """INSERT INTO scheduled_jobs
               (job_id, description, trigger_time, recurrence, payload, chat_id, status, created_at, next_run)
               VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
            (job_id, description, trigger_time, recurrence,
             json.dumps(payload or {}, ensure_ascii=False), chat_id, now, trigger_time),
        )
        await db.commit()
        return job_id

    async def list_jobs(self, status: str = "") -> list[dict]:
        db = self._ensure_db()
        if status:
            cursor = await db.execute(
                "SELECT * FROM scheduled_jobs WHERE status = ? ORDER BY next_run", (status,)
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM scheduled_jobs ORDER BY next_run"
            )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def cancel_job(self, job_id: str) -> bool:
        db = self._ensure_db()
        cursor = await db.execute(
            "UPDATE scheduled_jobs SET status = 'cancelled' WHERE job_id = ? AND status = 'pending'",
            (job_id,),
        )
        await db.commit()
        return cursor.rowcount > 0

    async def get_due_jobs(self) -> list[dict]:
        """获取所有到期的待执行任务"""
        db = self._ensure_db()
        now = datetime.now().isoformat()
        cursor = await db.execute(
            "SELECT * FROM scheduled_jobs WHERE status = 'pending' AND next_run <= ?",
            (now,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def mark_done(self, job_id: str) -> None:
        db = self._ensure_db()
        now = datetime.now().isoformat()
        await db.execute(
            "UPDATE scheduled_jobs SET status = 'done', last_run = ? WHERE job_id = ?",
            (now, job_id),
        )
        await db.commit()

    async def reschedule(self, job_id: str, next_run: str) -> None:
        """重新调度循环任务"""
        db = self._ensure_db()
        now = datetime.now().isoformat()
        await db.execute(
            "UPDATE scheduled_jobs SET last_run = ?, next_run = ? WHERE job_id = ?",
            (now, next_run, job_id),
        )
        await db.commit()


class MaxScheduler:
    """Max定时任务调度器"""

    def __init__(self, store: JobStore):
        self.store = store
        self._running = False
        self._task: asyncio.Task | None = None
        self._on_trigger: Callable[[dict], Awaitable[None]] | None = None

    def set_trigger_callback(self, callback: Callable[[dict], Awaitable[None]]) -> None:
        self._on_trigger = callback

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("定时任务调度器已启动")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("定时任务调度器已停止")

    async def _poll_loop(self) -> None:
        while self._running:
            try:
                jobs = await self.store.get_due_jobs()
                for job in jobs:
                    if self._on_trigger:
                        try:
                            await self._on_trigger(job)
                        except Exception as e:
                            logger.error("定时任务 %s 执行回调失败: %s", job["job_id"], e)

                    # 处理循环任务
                    recurrence = job.get("recurrence", "")
                    if recurrence:
                        next_run = self._calc_next_run(job["next_run"], recurrence)
                        if next_run:
                            await self.store.reschedule(job["job_id"], next_run)
                            continue

                    await self.store.mark_done(job["job_id"])

            except Exception as e:
                logger.error("调度循环异常: %s", e)

            await asyncio.sleep(60)

    @staticmethod
    def _calc_next_run(current: str, recurrence: str) -> str | None:
        try:
            dt = datetime.fromisoformat(current)
        except (ValueError, TypeError):
            return None

        if recurrence.endswith("d"):
            days = int(recurrence[:-1])
            return (dt + timedelta(days=days)).isoformat()
        elif recurrence.endswith("h"):
            hours = int(recurrence[:-1])
            return (dt + timedelta(hours=hours)).isoformat()
        elif recurrence.endswith("w"):
            weeks = int(recurrence[:-1])
            return (dt + timedelta(weeks=weeks)).isoformat()
        return None
