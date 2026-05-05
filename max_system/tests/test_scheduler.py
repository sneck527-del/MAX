"""测试定时任务调度器"""

import pytest
import tempfile
from pathlib import Path


class TestJobStore:
    """JobStore CRUD测试"""

    @pytest.fixture
    async def store(self):
        from max_system.core.scheduler import JobStore

        tmp = tempfile.mkdtemp()
        db_path = Path(tmp) / "test_schedule.db"
        s = JobStore(db_path)
        await s.initialize()
        yield s
        await s.close()

    @pytest.mark.asyncio
    async def test_add_and_list_job(self, store):
        job_id = await store.add_job(
            description="测试任务",
            trigger_time="2026-01-01T00:00:00",
            chat_id="chat_001",
        )
        assert len(job_id) == 12

        jobs = await store.list_jobs()
        assert len(jobs) == 1
        assert jobs[0]["description"] == "测试任务"
        assert jobs[0]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_list_by_status(self, store):
        await store.add_job("pending task", "2026-01-01T00:00:00")
        await store.add_job("another", "2026-01-02T00:00:00")

        jobs = await store.list_jobs(status="pending")
        assert len(jobs) == 2

        jobs = await store.list_jobs(status="cancelled")
        assert len(jobs) == 0

    @pytest.mark.asyncio
    async def test_cancel_job(self, store):
        job_id = await store.add_job("可取消任务", "2026-01-01T00:00:00")
        cancelled = await store.cancel_job(job_id)
        assert cancelled is True

        jobs = await store.list_jobs(status="cancelled")
        assert len(jobs) == 1

    @pytest.mark.asyncio
    async def test_cancel_nonexistent(self, store):
        cancelled = await store.cancel_job("nonexistent")
        assert cancelled is False

    @pytest.mark.asyncio
    async def test_get_due_jobs(self, store):
        from datetime import datetime, timedelta

        past = (datetime.now() - timedelta(hours=1)).isoformat()
        await store.add_job("过期任务", past)

        future = (datetime.now() + timedelta(days=7)).isoformat()
        await store.add_job("未来任务", future)

        due = await store.get_due_jobs()
        assert len(due) == 1
        assert due[0]["description"] == "过期任务"

    @pytest.mark.asyncio
    async def test_mark_done(self, store):
        job_id = await store.add_job("完成测试", "2026-01-01T00:00:00")
        await store.mark_done(job_id)

        jobs = await store.list_jobs(status="done")
        assert len(jobs) == 1
        assert jobs[0]["last_run"] != ""

    @pytest.mark.asyncio
    async def test_reschedule(self, store):
        from datetime import datetime, timedelta

        job_id = await store.add_job("循环任务", "2026-01-01T00:00:00", recurrence="1d")
        next_run = (datetime.now() + timedelta(days=1)).isoformat()
        await store.reschedule(job_id, next_run)

        jobs = await store.list_jobs()
        assert jobs[0]["next_run"] == next_run
        assert jobs[0]["last_run"] != ""
        assert jobs[0]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_payload_storage(self, store):
        payload = {"callback_url": "https://example.com", "data": {"x": 1}}
        job_id = await store.add_job(
            "带payload", "2026-01-01T00:00:00", payload=payload
        )

        jobs = await store.list_jobs()
        import json
        stored = json.loads(jobs[0]["payload"])
        assert stored == payload

    @pytest.mark.asyncio
    async def test_uninitialized_store_raises(self):
        from max_system.core.scheduler import JobStore

        s = JobStore(Path("/tmp/nonexistent.db"))
        with pytest.raises(RuntimeError, match="未初始化"):
            await s.add_job("test", "2026-01-01")


class TestRecurrenceCalc:
    """循环间隔计算测试"""

    def test_daily(self):
        from max_system.core.scheduler import MaxScheduler

        result = MaxScheduler._calc_next_run("2026-01-01T10:00:00", "1d")
        assert "2026-01-02T10:00:00" in result

    def test_hourly(self):
        from max_system.core.scheduler import MaxScheduler

        result = MaxScheduler._calc_next_run("2026-01-01T10:00:00", "2h")
        assert "2026-01-01T12:00:00" in result

    def test_weekly(self):
        from max_system.core.scheduler import MaxScheduler

        result = MaxScheduler._calc_next_run("2026-01-01T10:00:00", "1w")
        assert "2026-01-08T10:00:00" in result

    def test_invalid_input(self):
        from max_system.core.scheduler import MaxScheduler

        assert MaxScheduler._calc_next_run("", "1d") is None
        assert MaxScheduler._calc_next_run("not-a-date", "1d") is None
        assert MaxScheduler._calc_next_run("2026-01-01T10:00:00", "1x") is None


class TestMaxScheduler:
    """MaxScheduler测试"""

    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        from max_system.core.scheduler import JobStore, MaxScheduler
        import tempfile

        tmp = tempfile.mkdtemp()
        db_path = Path(tmp) / "test_sched.db"
        store = JobStore(db_path)
        await store.initialize()

        scheduler = MaxScheduler(store)
        await scheduler.start()
        assert scheduler._running is True

        await scheduler.stop()
        assert scheduler._running is False
        await store.close()

    @pytest.mark.asyncio
    async def test_trigger_callback_fires(self):
        from max_system.core.scheduler import JobStore, MaxScheduler
        import tempfile
        from datetime import datetime, timedelta

        tmp = tempfile.mkdtemp()
        db_path = Path(tmp) / "test_sched2.db"
        store = JobStore(db_path)
        await store.initialize()

        past = (datetime.now() - timedelta(hours=1)).isoformat()
        await store.add_job("待触发", past)

        calls = []

        async def on_trigger(job):
            calls.append(job)

        scheduler = MaxScheduler(store)
        scheduler.set_trigger_callback(on_trigger)
        await scheduler.start()

        import asyncio
        await asyncio.sleep(1.5)

        await scheduler.stop()
        await store.close()

        assert len(calls) >= 1
        assert calls[0]["description"] == "待触发"
