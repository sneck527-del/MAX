"""测试LLM客户端"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestLLMClientInit:
    """LLMClient初始化测试"""

    def test_default_provider_deepseek(self):
        from max_system.config.settings import MaxSettings
        from max_system.core.llm_client import LLMClient

        settings = MaxSettings()
        client = LLMClient(settings)

        assert client.provider_name == "deepseek"
        assert client.model == "deepseek-chat"

    def test_ollama_provider(self):
        from max_system.config.settings import MaxSettings
        from max_system.core.llm_client import LLMClient

        settings = MaxSettings(llm_provider="ollama")
        client = LLMClient(settings)

        assert client.provider_name == "ollama"
        assert client.model == "qwen3.5"

    def test_override_provider(self):
        from max_system.config.settings import MaxSettings
        from max_system.core.llm_client import LLMClient

        settings = MaxSettings(llm_provider="deepseek")
        client = LLMClient(settings, provider="ollama")

        assert client.provider_name == "ollama"


class TestSanitize:
    """_sanitize测试"""

    def test_removes_surrogate_chars(self):
        from max_system.core.llm_client import LLMClient

        result = LLMClient._sanitize("hello\ud800world")
        assert "hello" in result
        assert "world" in result
        assert "\ud800" not in result

    def test_recursive_dict(self):
        from max_system.core.llm_client import LLMClient

        data = {"msg": "hello\ud800", "nested": {"text": "world\udfff"}}
        result = LLMClient._sanitize(data)
        assert "\ud800" not in result["msg"]
        assert "\udfff" not in result["nested"]["text"]

    def test_recursive_list(self):
        from max_system.core.llm_client import LLMClient

        data = ["hello\ud800", "normal"]
        result = LLMClient._sanitize(data)
        assert "\ud800" not in result[0]
        assert result[1] == "normal"

    def test_non_string_passthrough(self):
        from max_system.core.llm_client import LLMClient

        assert LLMClient._sanitize(42) == 42
        assert LLMClient._sanitize(None) is None
        assert LLMClient._sanitize(3.14) == 3.14


class TestBuildToolDefinitions:
    """build_tool_definitions测试"""

    def test_converts_to_openai_format(self):
        from max_system.core.llm_client import LLMClient

        tools_config = [
            {
                "name": "search",
                "description": "Search the knowledge base",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        ]
        result = LLMClient.build_tool_definitions(tools_config)

        assert len(result) == 1
        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "search"

    def test_default_parameters(self):
        from max_system.core.llm_client import LLMClient

        tools_config = [
            {"name": "noop", "description": "Does nothing"},
        ]
        result = LLMClient.build_tool_definitions(tools_config)

        assert result[0]["function"]["parameters"] == {
            "type": "object",
            "properties": {},
        }

    def test_empty_list(self):
        from max_system.core.llm_client import LLMClient

        result = LLMClient.build_tool_definitions([])
        assert result == []


class TestChatMocked:
    """chat() mocked测试"""

    @pytest.mark.asyncio
    async def test_chat_calls_openai(self):
        from max_system.config.settings import MaxSettings
        from max_system.core.llm_client import LLMClient

        settings = MaxSettings()
        client = LLMClient(settings)

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello!"

        with patch.object(client._client.chat.completions, "create", new_callable=AsyncMock, return_value=mock_response):
            result = await client.chat([{"role": "user", "content": "hi"}])

        assert result is mock_response

    @pytest.mark.asyncio
    async def test_simple_chat(self):
        from max_system.config.settings import MaxSettings
        from max_system.core.llm_client import LLMClient

        settings = MaxSettings()
        client = LLMClient(settings)

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello there!"

        with patch.object(client._client.chat.completions, "create", new_callable=AsyncMock, return_value=mock_response):
            reply = await client.simple_chat("You are helpful.", "Hi")

        assert reply == "Hello there!"


class TestConnectionTest:
    """test_connection测试"""

    @pytest.mark.asyncio
    async def test_connection_success(self):
        from max_system.config.settings import MaxSettings
        from max_system.core.llm_client import LLMClient

        settings = MaxSettings()
        client = LLMClient(settings)

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "你好，很高兴为您服务"

        with patch.object(client._client.chat.completions, "create", new_callable=AsyncMock, return_value=mock_response):
            result = await client.test_connection()

        assert result["connected"] is True
        assert result["provider"] == "deepseek"

    @pytest.mark.asyncio
    async def test_connection_failure(self):
        from max_system.config.settings import MaxSettings
        from max_system.core.llm_client import LLMClient

        settings = MaxSettings()
        client = LLMClient(settings)

        with patch.object(client._client.chat.completions, "create", new_callable=AsyncMock, side_effect=Exception("API error")):
            result = await client.test_connection()

        assert result["connected"] is False
        assert "error" in result
