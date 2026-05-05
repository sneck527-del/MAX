"""测试初始化引导流程"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from max_system.core.onboarding import (
    _extract_profile_updates,
    _build_profile_summary,
    process_card_action,
    get_first_card,
)


class TestExtractProfileUpdates:
    """测试表单值提取"""

    def test_simple_fields(self):
        form = {"company_name": "测试工作室", "design_style": "现代简约", "city": "北京"}
        updates = _extract_profile_updates(form)
        assert updates["company_name"] == "测试工作室"
        assert updates["design_style"] == "现代简约"
        assert updates["city"] == "北京"

    def test_multi_select_joins(self):
        form = {"target_client": ["首次装修", "改善型装修"]}
        updates = _extract_profile_updates(form)
        assert "首次装修" in updates["target_client"]
        assert "改善型装修" in updates["target_client"]

    def test_empty_form(self):
        updates = _extract_profile_updates({})
        assert updates == {}

    def test_unknown_fields_ignored(self):
        form = {"random_field": "value", "company_name": "test"}
        updates = _extract_profile_updates(form)
        assert "random_field" not in updates
        assert updates["company_name"] == "test"

    def test_empty_values_skipped(self):
        form = {"company_name": ""}
        updates = _extract_profile_updates(form)
        assert "company_name" not in updates


class TestBuildProfileSummary:
    """测试摘要构建"""

    def test_converts_keys_to_chinese(self):
        profile = {"company_name": "TestCo", "design_style": "Modern"}
        summary = _build_profile_summary(profile)
        assert "公司名称" in summary
        assert summary["公司名称"] == "TestCo"
        assert "设计风格" in summary

    def test_all_labels_present(self):
        profile = {
            "company_name": "a", "design_style": "b", "city": "c",
            "target_client": "d", "service_types": "e",
            "brand_tone": "f", "price_range": "g",
        }
        summary = _build_profile_summary(profile)
        assert len(summary) == 7
        for label in ["公司名称", "设计风格", "所在城市", "目标客户", "服务类型", "品牌调性", "价格区间"]:
            assert label in summary


class TestProcessCardAction:
    """测试卡片动作处理"""

    @pytest.mark.asyncio
    async def test_step_1_to_2(self):
        """步骤1: 填完基本信息 → 返回卡片2"""
        profile_mgr = AsyncMock()
        profile_mgr.set_many = AsyncMock()

        action = {"action": "onboarding", "step": "2", "card": "1"}
        form = {"company_name": "测试", "design_style": "现代简约", "city": "北京"}

        next_card, finished = await process_card_action(action, form, profile_mgr)

        assert finished is False
        assert next_card is not None
        assert "2/3" in next_card["header"]["title"]["content"]
        # 验证 profile 已保存
        profile_mgr.set_many.assert_called_once()

    @pytest.mark.asyncio
    async def test_step_2_to_3(self):
        """步骤2: 填完品牌信息 → 返回卡片3（确认卡）"""
        profile_mgr = AsyncMock()
        profile_mgr.set_many = AsyncMock()
        profile_mgr.get_all = AsyncMock(return_value={
            "company_name": "测试工作室",
            "design_style": "现代简约",
            "city": "北京",
            "target_client": "首次装修",
            "service_types": "全案设计",
            "brand_tone": "专业严谨",
            "price_range": "20-50万",
        })

        action = {"action": "onboarding", "step": "3", "card": "2"}
        form = {"target_client": ["首次装修"], "brand_tone": "专业严谨"}

        next_card, finished = await process_card_action(action, form, profile_mgr)

        assert finished is False
        assert next_card is not None
        assert "3/3" in next_card["header"]["title"]["content"]
        assert next_card["header"]["template"] == "green"

    @pytest.mark.asyncio
    async def test_finish(self):
        """步骤3: 确认完成 → finished=True"""
        profile_mgr = AsyncMock()
        profile_mgr.set_many = AsyncMock()

        action = {"action": "onboarding", "step": "finish", "card": "3"}
        form = {}

        next_card, finished = await process_card_action(action, form, profile_mgr)

        assert finished is True
        assert next_card is None

    @pytest.mark.asyncio
    async def test_restart(self):
        """从确认页回到步骤1"""
        profile_mgr = AsyncMock()
        profile_mgr.set_many = AsyncMock()

        action = {"action": "onboarding", "step": "1", "card": "3"}
        form = {}

        next_card, finished = await process_card_action(action, form, profile_mgr)

        assert finished is False
        assert "1/3" in next_card["header"]["title"]["content"]

    @pytest.mark.asyncio
    async def test_bad_step_defaults_to_card_1(self):
        """无效步骤 → 默认回到卡片1"""
        profile_mgr = AsyncMock()
        profile_mgr.set_many = AsyncMock()

        action = {"action": "onboarding", "step": "99", "card": "1"}
        form = {}

        next_card, finished = await process_card_action(action, form, profile_mgr)

        assert finished is False
        assert next_card is not None
        assert "1/3" in next_card["header"]["title"]["content"]


class TestGetFirstCard:
    """测试首张卡片获取"""

    def test_returns_card_1(self):
        card = get_first_card()
        assert card["header"]["template"] == "blue"
        assert "1/3" in card["header"]["title"]["content"]
        # 必须是有效的飞书卡片结构
        assert "config" in card
        assert "elements" in card
        assert card["config"]["wide_screen_mode"] is True
