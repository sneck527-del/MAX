"""测试配置模块"""

import pytest
from pathlib import Path


class TestSchema:
    """数据模型测试"""

    def test_risk_level_values(self):
        from max_system.config.schema import RiskLevel

        values = [e.value for e in RiskLevel]
        assert "low" in values
        assert "medium" in values
        assert "high" in values

    def test_normalized_command_fields(self):
        from max_system.config.schema import NormalizedCommand

        cmd = NormalizedCommand(
            chat_id="test123",
            user_id="user1",
            user_name="设计师",
            message_type="text",
            text="帮我分析需求",
            is_group=False,
            is_mentioned=False,
            should_respond=True,
        )
        assert cmd.chat_id == "test123"
        assert cmd.text == "帮我分析需求"
        assert cmd.metadata == {}


class TestSettings:
    """配置设置测试"""

    def test_settings_singleton(self):
        from max_system.config.settings import get_settings, MaxSettings
        s = get_settings()
        assert isinstance(s, MaxSettings)

    def test_path_auto_inference(self):
        from max_system.config.settings import get_settings
        s = get_settings()
        root = s.get_project_root()
        assert root.exists()

    def test_db_path(self):
        from max_system.config.settings import get_settings
        s = get_settings()
        p = s.get_db_path()
        assert p.name == "max.db"


class TestToolRegistration:
    """工具注册测试"""

    def test_register_all_tools(self):
        from max_system.config.settings import get_settings
        from max_system.config.agent_registry import register_all_tools
        s = get_settings()
        tools = register_all_tools(s)
        assert len(tools) > 0
        for name, func, defn in tools:
            assert callable(func)
            assert defn["name"] == name
            assert "parameters" in defn


class TestBitableSchema:
    """Bitable表结构定义测试"""

    def test_table_definitions(self):
        from max_system.config.bitable_schema import BITABLE_TABLES
        assert len(BITABLE_TABLES) == 9
        names = [t["name"] for t in BITABLE_TABLES]
        assert "客户信息" in names
        assert "售后维保台账" in names
        assert "跟进记录表" in names

    def test_table_has_env_key(self):
        from max_system.config.bitable_schema import BITABLE_TABLES
        for t in BITABLE_TABLES:
            assert "env_key" in t
            assert t["env_key"].startswith("BITABLE_TABLE_")

    def test_table_has_fields(self):
        from max_system.config.bitable_schema import BITABLE_TABLES
        for t in BITABLE_TABLES:
            assert "fields" in t
            assert len(t["fields"]) > 0
