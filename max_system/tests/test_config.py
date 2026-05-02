"""测试配置模块"""

import pytest
from pathlib import Path


class TestAgentRegistry:
    """Agent注册表测试"""

    def test_agent_specs_defined(self):
        from max_system.config.agent_registry import AGENT_SPECS, AGENT_TOOLS

        assert len(AGENT_SPECS) == 4
        assert "talker" in AGENT_SPECS
        assert "afterpro" in AGENT_SPECS
        assert "mediapro" in AGENT_SPECS
        assert "helper" in AGENT_SPECS

        # 每个Agent必须有工具权限定义
        for name in AGENT_SPECS:
            assert name in AGENT_TOOLS, f"{name} 缺少 AGENT_TOOLS 定义"
            assert len(AGENT_TOOLS[name]) > 0, f"{name} 工具列表为空"

    def test_agent_spec_structure(self):
        from max_system.config.agent_registry import AGENT_SPECS

        for name, (directory, skills, description) in AGENT_SPECS.items():
            assert isinstance(directory, str), f"{name} 目录不是字符串"
            assert isinstance(skills, (list, tuple)), f"{name} 技能列表不是列表"
            assert isinstance(description, str) and len(description) > 0, f"{name} 描述为空"
            assert len(skills) > 0, f"{name} 没有技能"


class TestSchema:
    """数据模型测试"""

    def test_intent_category_values(self):
        from max_system.config.schema import IntentCategory

        values = [e.value for e in IntentCategory]
        assert "talker" in values
        assert "afterpro" in values
        assert "mediapro" in values
        assert "helper" in values
        assert "max_direct" in values

    def test_normalized_command_fields(self):
        from max_system.config.schema import NormalizedCommand, IntentCategory

        cmd = NormalizedCommand(
            chat_id="test123",
            user_id="user1",
            user_name="设计师",
            message_type="text",
            text="帮我分析需求",
            is_group=False,
            is_mentioned=False,
            should_respond=True,
            intent=IntentCategory.TALKER,
        )
        assert cmd.chat_id == "test123"
        assert cmd.text == "帮我分析需求"
        assert cmd.intent == IntentCategory.TALKER
