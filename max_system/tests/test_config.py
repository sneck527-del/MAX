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


class TestProfileKeyResolution:
    """Profile中文key别名解析测试"""

    def test_chinese_to_english_keys(self):
        from max_system.config.profile import resolve_key
        assert resolve_key("公司名称") == "company_name"
        assert resolve_key("公司名") == "company_name"
        assert resolve_key("设计风格") == "design_style"
        assert resolve_key("风格") == "design_style"
        assert resolve_key("品牌调性") == "brand_tone"
        assert resolve_key("管理费率") == "management_fee_rate"
        assert resolve_key("税率") == "tax_rate"

    def test_english_key_passthrough(self):
        from max_system.config.profile import resolve_key
        assert resolve_key("company_name") == "company_name"
        assert resolve_key("unknown_key") == "unknown_key"

    def test_all_aliases_have_valid_targets(self):
        from max_system.config.profile import KEY_ALIASES, DEFAULTS
        for cn_key, en_key in KEY_ALIASES.items():
            assert en_key in DEFAULTS, f"别名 {cn_key} -> {en_key} 的英文key不在DEFAULTS中"

    def test_defaults_include_fee_rates(self):
        from max_system.config.profile import DEFAULTS
        assert DEFAULTS["management_fee_rate"] == "8"
        assert DEFAULTS["tax_rate"] == "3.41"
        assert DEFAULTS["garbage_fee"] == "800"
        assert DEFAULTS["protection_fee"] == "500"


class TestProfileManager:
    """ProfileManager SQLite读写测试"""

    @pytest.fixture
    async def temp_profile(self, tmp_path):
        from max_system.config.profile import ProfileManager
        db_path = tmp_path / "test.db"
        mgr = ProfileManager(db_path)
        await mgr.initialize()
        yield mgr
        await mgr.close()

    @pytest.mark.asyncio
    async def test_is_empty_on_fresh_db(self, temp_profile):
        assert await temp_profile.is_empty()

    @pytest.mark.asyncio
    async def test_set_and_get(self, temp_profile):
        await temp_profile.set("company_name", "测试设计工作室")
        val = await temp_profile.get("company_name")
        assert val == "测试设计工作室"

    @pytest.mark.asyncio
    async def test_default_fallback(self, temp_profile):
        val = await temp_profile.get("company_name")
        assert val == ""  # DEFAULTS fallback

    @pytest.mark.asyncio
    async def test_set_many_and_get_all(self, temp_profile):
        await temp_profile.set_many({"company_name": "XX设计", "city": "杭州"})
        all_data = await temp_profile.get_all()
        assert all_data["company_name"] == "XX设计"
        assert all_data["city"] == "杭州"
        # 未设置的项应返回默认值
        assert all_data["management_fee_rate"] == "8"

    @pytest.mark.asyncio
    async def test_reset(self, temp_profile):
        await temp_profile.set("company_name", "测试")
        await temp_profile.reset()
        assert await temp_profile.is_empty()

    @pytest.mark.asyncio
    async def test_build_prompt_section(self, temp_profile):
        from max_system.config.profile import ProfileManager
        profile = {"company_name": "梦想改造家", "design_style": "极简", "city": "上海"}
        section = temp_profile.build_prompt_section(profile)
        assert "梦想改造家" in section
        assert "极简" in section
        assert "上海" in section

    @pytest.mark.asyncio
    async def test_build_prompt_section_empty(self, temp_profile):
        section = temp_profile.build_prompt_section({})
        assert section == ""


class TestLLMClientSanitize:
    """LLMClient surrogate字符清理测试"""

    def test_sanitize_string_with_surrogates(self):
        from max_system.core.llm_client import LLMClient
        bad_str = "hello\ud800world\udfff"
        cleaned = LLMClient._sanitize(bad_str)
        assert "\ud800" not in cleaned
        assert "\udfff" not in cleaned
        assert "hello" in cleaned
        assert "world" in cleaned

    def test_sanitize_normal_string(self):
        from max_system.core.llm_client import LLMClient
        normal = "这是一段正常的文本 hello 123"
        assert LLMClient._sanitize(normal) == normal

    def test_sanitize_nested_dict(self):
        from max_system.core.llm_client import LLMClient
        data = {"text": "bad\ud800str", "nested": {"more": "also\udfff"}}
        cleaned = LLMClient._sanitize(data)
        assert "\ud800" not in cleaned["text"]
        assert "\udfff" not in cleaned["nested"]["more"]

    def test_sanitize_list(self):
        from max_system.core.llm_client import LLMClient
        data = ["good", "bad\ud800", "fine"]
        cleaned = LLMClient._sanitize(data)
        assert "\ud800" not in cleaned[1]

    def test_build_tool_definitions(self):
        from max_system.core.llm_client import LLMClient
        tool_config = [{
            "name": "test_tool",
            "description": "a test tool",
            "parameters": {"type": "object", "properties": {"q": {"type": "string"}}},
        }]
        openai_tools = LLMClient.build_tool_definitions(tool_config)
        assert len(openai_tools) == 1
        assert openai_tools[0]["type"] == "function"
        assert openai_tools[0]["function"]["name"] == "test_tool"
        assert openai_tools[0]["function"]["description"] == "a test tool"
