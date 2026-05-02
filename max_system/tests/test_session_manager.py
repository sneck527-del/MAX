"""测试会话管理器"""

import pytest
from max_system.core.session_manager import SessionManager


@pytest.mark.asyncio
async def test_session_lifecycle():
    mgr = SessionManager()
    await mgr.start()

    session = await mgr.get_or_create("chat_001")
    assert session is not None
    assert len(session.messages) == 0

    mgr.add_message(session, "user", "你好")
    assert len(session.messages) == 1

    mgr.add_message(session, "assistant", "你好，有什么需要？")
    assert len(session.messages) == 2

    history = mgr.get_history(session)
    assert len(history) == 2

    await mgr.close_session("chat_001")
    await mgr.stop()


@pytest.mark.asyncio
async def test_session_history_trim():
    mgr = SessionManager()
    await mgr.start()

    session = await mgr.get_or_create("chat_002")
    for i in range(50):
        mgr.add_message(session, "user", f"msg_{i}")
        mgr.add_message(session, "assistant", f"resp_{i}")

    # Should be trimmed to 40 (MAX_HISTORY_TURNS * 2)
    assert len(session.messages) <= 40
    await mgr.stop()


@pytest.mark.asyncio
async def test_multiple_sessions():
    mgr = SessionManager()
    await mgr.start()

    s1 = await mgr.get_or_create("chat_a")
    s2 = await mgr.get_or_create("chat_b")

    mgr.add_message(s1, "user", "for chat_a")
    mgr.add_message(s2, "user", "for chat_b")

    assert len(mgr.get_history(s1)) == 1
    assert len(mgr.get_history(s2)) == 1

    assert mgr.active_count > 0

    await mgr.stop()
