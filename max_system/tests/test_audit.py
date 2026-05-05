"""测试审计日志模块"""

import pytest
import tempfile
from pathlib import Path


class TestAuditStore:
    """AuditStore测试"""

    @pytest.fixture
    async def store(self):
        from max_system.audit.store import AuditStore

        tmp = tempfile.mkdtemp()
        db_path = Path(tmp) / "test_audit.db"
        s = AuditStore(db_path)
        await s.initialize()
        yield s
        await s.close()

    @pytest.mark.asyncio
    async def test_log_and_query(self, store):
        from max_system.audit.models import AuditEntry

        entry = AuditEntry.create(
            session_id="chat_001",
            user_id="user_1",
            action="tool_call",
            agent="max",
            tool_name="feishu_send_message",
            tool_input={"text": "hello"},
        )
        await store.log(entry)

        results = await store.query(session_id="chat_001")
        assert len(results) >= 1
        assert results[0]["tool_name"] == "feishu_send_message"

    @pytest.mark.asyncio
    async def test_query_filter_by_action(self, store):
        from max_system.audit.models import AuditEntry

        await store.log(AuditEntry.create("s1", "u1", "dispatch", "max"))
        await store.log(AuditEntry.create("s1", "u1", "tool_call", "max", tool_name="t1"))
        await store.log(AuditEntry.create("s2", "u2", "response", "max"))

        results = await store.query(action="tool_call")
        assert len(results) >= 1
        assert all(r["action"] == "tool_call" for r in results)

    @pytest.mark.asyncio
    async def test_query_limit(self, store):
        from max_system.audit.models import AuditEntry

        for i in range(5):
            await store.log(AuditEntry.create(f"s{i}", f"u{i}", "dispatch", "max"))

        results = await store.query(limit=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_log_task(self, store):
        from max_system.audit.models import TaskLog

        task = TaskLog(
            task_id="T001",
            session_id="s1",
            user_id="u1",
            agent="max",
            input_message="hello",
            output_message="",
            status="pending",
        )
        await store.log_task(task)

        # Verify via raw SQL since there's no task query method
        cursor = await store._db.execute("SELECT * FROM task_log WHERE task_id = ?", ("T001",))
        rows = await cursor.fetchall()
        assert len(rows) == 1

    @pytest.mark.asyncio
    async def test_update_task(self, store):
        from max_system.audit.models import TaskLog

        task = TaskLog(
            task_id="T002",
            session_id="s1",
            user_id="u1",
            agent="max",
            input_message="hello",
            output_message="done",
            status="completed",
            completed_at="2026-01-01T00:00:00",
            duration_ms=1500,
        )
        await store.log_task(task)

        cursor = await store._db.execute("SELECT * FROM task_log WHERE task_id = ?", ("T002",))
        row = await cursor.fetchone()
        assert row["status"] == "completed"
        assert row["duration_ms"] == 1500


class TestAuditEntry:
    """AuditEntry模型测试"""

    def test_create_basic(self):
        from max_system.audit.models import AuditEntry

        entry = AuditEntry.create(
            session_id="s1",
            user_id="u1",
            action="dispatch",
            agent="max",
        )
        assert entry.session_id == "s1"
        assert entry.action == "dispatch"
        assert entry.timestamp != ""

    def test_create_with_tool(self):
        from max_system.audit.models import AuditEntry

        entry = AuditEntry.create(
            session_id="s1",
            user_id="u1",
            action="tool_call",
            agent="max",
            tool_name="search",
            tool_input={"q": "test"},
            risk_level="medium",
        )
        assert entry.tool_name == "search"
        assert entry.risk_level == "medium"

    def test_to_dict(self):
        from max_system.audit.models import AuditEntry

        entry = AuditEntry.create("s1", "u1", "dispatch", "max")
        d = entry.to_dict()
        assert d["session_id"] == "s1"
        assert "timestamp" in d


class TestTaskLog:
    """TaskLog模型测试"""

    def test_basic(self):
        from max_system.audit.models import TaskLog

        task = TaskLog(
            task_id="T1",
            session_id="s1",
            user_id="u1",
            agent="max",
            input_message="in",
            output_message="out",
            status="completed",
            duration_ms=100,
        )
        assert task.task_id == "T1"
        assert task.status == "completed"

    def test_to_dict(self):
        from max_system.audit.models import TaskLog

        task = TaskLog("T1", "s1", "u1", "max", "in", "out", "pending")
        d = task.to_dict()
        assert d["task_id"] == "T1"
        assert d["status"] == "pending"
