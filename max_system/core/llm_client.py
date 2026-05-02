"""LLM客户端：封装DeepSeek/Ollama API调用（OpenAI兼容格式）"""

import json
import logging
from typing import AsyncIterator

from openai import AsyncOpenAI

from max_system.config.settings import MaxSettings

logger = logging.getLogger(__name__)


class LLMClient:
    """统一LLM客户端

    支持DeepSeek（云端）和Ollama（本地），均使用OpenAI兼容格式。
    提供对话补全、流式输出、函数调用能力。
    """

    def __init__(self, settings: MaxSettings, provider: str | None = None):
        self.settings = settings
        self.provider = provider or settings.llm_provider

        if self.provider == "ollama":
            self._api_key = settings.ollama_api_key
            self._base_url = settings.ollama_base_url
            self._model = settings.ollama_model
        else:
            self._api_key = settings.llm_api_key
            self._base_url = settings.llm_base_url
            self._model = settings.llm_model

        self._client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
        )

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return self.provider

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict:
        """非流式对话补全"""
        kwargs: dict = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature or self.settings.llm_temperature,
            "max_tokens": max_tokens or self.settings.llm_max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = await self._client.chat.completions.create(**kwargs)
        return response

    async def chat_stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator:
        """流式对话补全"""
        kwargs: dict = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature or self.settings.llm_temperature,
            "max_tokens": self.settings.llm_max_tokens,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        stream = await self._client.chat.completions.create(**kwargs)
        async for chunk in stream:
            yield chunk

    async def simple_chat(self, system_prompt: str, user_message: str) -> str:
        """简单对话：单轮问答"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        response = await self.chat(messages)
        return response.choices[0].message.content or ""

    async def test_connection(self) -> dict:
        """测试LLM连接"""
        try:
            messages = [
                {"role": "user", "content": "你好，请用一句话回复"},
            ]
            response = await self.chat(messages, max_tokens=100)
            reply = response.choices[0].message.content or ""
            return {
                "connected": True,
                "provider": self.provider,
                "model": self._model,
                "reply": reply[:50],
            }
        except Exception as e:
            return {
                "connected": False,
                "provider": self.provider,
                "model": self._model,
                "error": str(e),
            }

    @staticmethod
    def build_tool_definitions(tools_config: list[dict]) -> list[dict]:
        """将内部工具配置转换为OpenAI function calling格式"""
        openai_tools = []
        for tool in tools_config:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool.get("parameters", {
                        "type": "object",
                        "properties": {},
                    }),
                },
            })
        return openai_tools
