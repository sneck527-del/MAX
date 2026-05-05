"""测试编排器"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestOrchestratorInit:
    """MaxOrchestrator初始化测试"""

    @pytest.mark.asyncio
    async def test_init_not_initialized(self):
        from max_system.config.settings import MaxSettings
        from max_system.core.orchestrator import MaxOrchestrator

        orch = MaxOrchestrator(MaxSettings())
        assert orch._initialized is False
        assert len(orch._tools) == 0

    @pytest.mark.asyncio
    async def test_initialize_registers_tools(self):
        from max_system.config.settings import MaxSettings
        from max_system.core.orchestrator import MaxOrchestrator

        orch = MaxOrchestrator(MaxSettings())
        await orch.initialize()

        assert orch._initialized is True
        assert len(orch._tools) > 0
        assert len(orch._tool_defs) > 0
        assert orch.profile_manager is not None

    @pytest.mark.asyncio
    async def test_close_cleans_up(self):
        from max_system.config.settings import MaxSettings
        from max_system.core.orchestrator import MaxOrchestrator

        orch = MaxOrchestrator(MaxSettings())
        await orch.initialize()
        await orch.close()

    @pytest.mark.asyncio
    async def test_double_initialize_is_idempotent(self):
        from max_system.config.settings import MaxSettings
        from max_system.core.orchestrator import MaxOrchestrator

        orch = MaxOrchestrator(MaxSettings())
        await orch.initialize()
        tool_count = len(orch._tools)
        await orch.initialize()
        assert len(orch._tools) == tool_count


class TestToolRegistration:
    """工具注册测试"""

    @pytest.mark.asyncio
    async def test_all_38_tools_registered(self):
        from max_system.config.settings import MaxSettings
        from max_system.core.orchestrator import MaxOrchestrator

        orch = MaxOrchestrator(MaxSettings())
        await orch.initialize()

        assert len(orch._tools) == 46
        assert len(orch._tool_defs) == 46

    @pytest.mark.asyncio
    async def test_key_tool_groups_present(self):
        from max_system.config.settings import MaxSettings
        from max_system.core.orchestrator import MaxOrchestrator

        orch = MaxOrchestrator(MaxSettings())
        await orch.initialize()

        tool_names = set(orch._tools.keys())

        feishu_tools = {
            "feishu_send_message", "feishu_read_bitable",
            "feishu_write_bitable", "feishu_create_approval",
            "feishu_create_task", "feishu_list_tasks",
            "feishu_complete_task",
        }
        assert feishu_tools.issubset(tool_names), f"Missing: {feishu_tools - tool_names}"

        profile_tools = {"profile_get", "profile_update", "profile_reset"}
        assert profile_tools.issubset(tool_names), f"Missing: {profile_tools - tool_names}"

        schedule_tools = {"schedule_create", "schedule_list", "schedule_cancel"}
        assert schedule_tools.issubset(tool_names), f"Missing: {schedule_tools - tool_names}"


class TestSystemPrompt:
    """系统提示构建测试"""

    @pytest.mark.asyncio
    async def test_build_system_prompt(self):
        from max_system.config.settings import MaxSettings
        from max_system.core.orchestrator import MaxOrchestrator

        orch = MaxOrchestrator(MaxSettings())
        await orch.initialize()

        prompt = await orch._build_max_system_prompt()
        assert "Max" in prompt or "可用工具" in prompt
        assert "飞书" in prompt

    @pytest.mark.asyncio
    async def test_system_prompt_lists_tools(self):
        from max_system.config.settings import MaxSettings
        from max_system.core.orchestrator import MaxOrchestrator

        orch = MaxOrchestrator(MaxSettings())
        await orch.initialize()

        prompt = await orch._build_max_system_prompt()
        assert "feishu_send_message" in prompt
        assert "profile_get" in prompt


class TestExecuteTool:
    """工具执行测试"""

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        from max_system.config.settings import MaxSettings
        from max_system.core.orchestrator import MaxOrchestrator

        orch = MaxOrchestrator(MaxSettings())
        await orch.initialize()

        result = await orch._execute_tool("nonexistent_tool", {}, "test", "user1")
        assert "未知工具" in result

    @pytest.mark.asyncio
    async def test_tool_with_content_dict(self):
        from max_system.config.settings import MaxSettings
        from max_system.core.orchestrator import MaxOrchestrator

        orch = MaxOrchestrator(MaxSettings())
        await orch.initialize()

        orch._tools["test_tool"] = AsyncMock(return_value={
            "content": [{"type": "text", "text": "Hello World"}]
        })

        result = await orch._execute_tool("test_tool", {}, "test", "user1")
        assert result == "Hello World"

    @pytest.mark.asyncio
    async def test_tool_exception_returns_error(self):
        from max_system.config.settings import MaxSettings
        from max_system.core.orchestrator import MaxOrchestrator

        orch = MaxOrchestrator(MaxSettings())
        await orch.initialize()

        orch._tools["broken_tool"] = AsyncMock(side_effect=RuntimeError("Boom!"))

        result = await orch._execute_tool("broken_tool", {}, "test", "user1")
        assert "工具执行失败" in result
        assert "Boom!" in result


class TestProcessResponse:
    """_process_response测试"""

    @pytest.mark.asyncio
    async def test_direct_text_response(self):
        from max_system.config.settings import MaxSettings
        from max_system.core.orchestrator import MaxOrchestrator

        orch = MaxOrchestrator(MaxSettings())
        await orch.initialize()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "你好，我是Max"
        mock_response.choices[0].message.tool_calls = None

        result = await orch._process_response(mock_response, [], "test", "user1")
        assert result == "你好，我是Max"

    @pytest.mark.asyncio
    async def test_depth_limit(self):
        from max_system.config.settings import MaxSettings
        from max_system.core.orchestrator import MaxOrchestrator

        orch = MaxOrchestrator(MaxSettings())

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None

        result = await orch._process_response(mock_response, [], "test", "user1", depth=6)
        assert "深度超限" in result

    @pytest.mark.asyncio
    async def test_empty_content_defaults_to_empty_string(self):
        from max_system.config.settings import MaxSettings
        from max_system.core.orchestrator import MaxOrchestrator

        orch = MaxOrchestrator(MaxSettings())
        await orch.initialize()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_response.choices[0].message.tool_calls = []

        result = await orch._process_response(mock_response, [], "test", "user1")
        assert result == ""


class TestDispatch:
    """dispatch测试"""

    @pytest.mark.asyncio
    async def test_dispatch_returns_response(self):
        from max_system.config.settings import MaxSettings
        from max_system.core.orchestrator import MaxOrchestrator

        orch = MaxOrchestrator(MaxSettings())
        await orch.initialize()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "回复文本"
        mock_response.choices[0].message.tool_calls = None

        with patch.object(orch.llm, "chat", new_callable=AsyncMock, return_value=mock_response):
            result = await orch.dispatch("你好", session_id="test_session")
            assert result == "回复文本"
