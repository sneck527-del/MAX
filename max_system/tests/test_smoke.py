"""端到端冒烟测试：验证系统初始化、工具注册、编排器完整链路"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture
async def orch():
    """创建已初始化的编排器"""
    from max_system.config.settings import MaxSettings
    from max_system.core.orchestrator import MaxOrchestrator

    settings = MaxSettings()
    orch = MaxOrchestrator(settings)
    await orch.initialize()
    return orch


class TestSystemInit:
    """系统初始化冒烟测试"""

    @pytest.mark.asyncio
    async def test_orchestrator_initializes(self, orch):
        assert orch._initialized is True
        assert len(orch._tools) == 46

    @pytest.mark.asyncio
    async def test_profile_manager_works(self, orch):
        assert orch.profile_manager is not None
        profile = await orch.profile_manager.get_all()
        assert isinstance(profile, dict)

    @pytest.mark.asyncio
    async def test_system_prompt_includes_all_components(self, orch):
        prompt = await orch._build_max_system_prompt()
        assert "可用工具" in prompt
        assert "飞书" in prompt
        assert "feishu_send_message" in prompt
        assert "profile_get" in prompt
        assert "knowledge_search" in prompt

    @pytest.mark.asyncio
    async def test_all_tool_groups_registered(self, orch):
        names = set(orch._tools.keys())

        # 10 feishu tools
        assert "feishu_send_message" in names
        assert "feishu_create_task" in names
        assert "feishu_complete_task" in names

        # 3 knowledge tools
        assert "knowledge_search" in names
        assert "knowledge_catalog" in names
        assert "knowledge_compliance_check" in names

        # 3 quote tools
        assert "quote_query_materials" in names
        assert "quote_query_construction" in names
        assert "quote_calculate_summary" in names

        # 4 clientmgr tools
        assert "clientmgr_create_client" in names
        assert "clientmgr_query_clients" in names

        # 4 sales tools
        assert "leadcatch_classify" in names
        assert "needanaly_report" in names

        # 5 service tools
        assert "returnvisit_schedule" in names
        assert "issuefix_track" in names

        # 3 marketing tools
        assert "leadtransfer_qualify" in names
        assert "casepack_package" in names

        # 3 profile tools
        assert "profile_get" in names
        assert "profile_update" in names

        # 3 schedule tools
        assert "schedule_create" in names
        assert "schedule_list" in names


class TestDispatchFlow:
    """完整dispatch流程测试（mock LLM）"""

    @pytest.mark.asyncio
    async def test_dispatch_text_response(self, orch):
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "这是Max的回复"
        mock_resp.choices[0].message.tool_calls = None

        with patch.object(orch.llm, "chat", new_callable=AsyncMock, return_value=mock_resp):
            result = await orch.dispatch("你好", session_id="smoke_test")
            assert result == "这是Max的回复"

    @pytest.mark.asyncio
    async def test_dispatch_with_tool_call(self, orch):
        mock_tool_resp = MagicMock()
        mock_tool_resp.choices = [MagicMock()]
        mock_tool = MagicMock()
        mock_tool.id = "call_001"
        mock_tool.function.name = "profile_get"
        mock_tool.function.arguments = '{"key": "company_name"}'
        mock_tool_resp.choices[0].message.content = None
        mock_tool_resp.choices[0].message.tool_calls = [mock_tool]
        mock_tool_resp.choices[0].message.model_dump.return_value = {}

        mock_final_resp = MagicMock()
        mock_final_resp.choices = [MagicMock()]
        mock_final_resp.choices[0].message.content = "查询结果"
        mock_final_resp.choices[0].message.tool_calls = None

        with patch.object(orch.llm, "chat", new_callable=AsyncMock, side_effect=[mock_tool_resp, mock_final_resp]):
            result = await orch.dispatch("查询公司信息", session_id="smoke_test")
            assert result == "查询结果"

    @pytest.mark.asyncio
    async def test_stream_yields_chunks(self, orch):
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta = MagicMock()
        chunk1.choices[0].delta.content = "Hello"

        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta = MagicMock()
        chunk2.choices[0].delta.content = " World"

        async def mock_stream(*args, **kwargs):
            yield chunk1
            yield chunk2

        with patch.object(orch.llm, "chat_stream", side_effect=mock_stream):
            chunks = []
            async for chunk in orch.dispatch_stream("hi"):
                chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0] == {"type": "text", "content": "Hello"}
        assert chunks[1] == {"type": "text", "content": " World"}

    @pytest.mark.asyncio
    async def test_dispatch_with_none_delta_chunk(self, orch):
        chunk = MagicMock()
        chunk.choices = None

        async def mock_stream(*args, **kwargs):
            yield chunk

        with patch.object(orch.llm, "chat_stream", side_effect=mock_stream):
            chunks = []
            async for chunk in orch.dispatch_stream("hi"):
                chunks.append(chunk)

        assert len(chunks) == 0
