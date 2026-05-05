"""测试飞书卡片构建器"""

import json
import pytest
from max_system.integrations.feishu import card_builder as cb


class TestCardElements:
    """测试原子元素构建"""

    def test_plain_text(self):
        result = cb._plain_text("Hello")
        assert result == {"tag": "plain_text", "content": "Hello"}

    def test_lark_md(self):
        result = cb._lark_md("**bold**")
        assert result == {"tag": "lark_md", "content": "**bold**"}

    def test_div(self):
        result = cb._div("Hello World")
        assert result["tag"] == "div"
        assert result["text"]["tag"] == "lark_md"
        assert "Hello World" in result["text"]["content"]

    def test_hr(self):
        result = cb._hr()
        assert result == {"tag": "hr"}

    def test_input_field(self):
        result = cb._input_field("company_name", "Company", placeholder="Enter name", required=True)
        assert result["tag"] == "input"
        assert result["name"] == "company_name"
        assert result["required"] is True
        assert result["placeholder"]["content"] == "Enter name"

    def test_input_field_optional(self):
        result = cb._input_field("city", "City")
        assert "required" not in result

    def test_select_field(self):
        options = [("a", "Option A"), ("b", "Option B")]
        result = cb._select_field("style", options, placeholder="Choose...")
        assert result["tag"] == "select_static"
        assert result["name"] == "style"
        assert len(result["options"]) == 2
        assert result["options"][0]["value"] == "a"
        assert result["options"][0]["text"]["content"] == "Option A"

    def test_multi_select_field(self):
        options = [("a", "A"), ("b", "B"), ("c", "C")]
        result = cb._multi_select_field("types", options)
        assert result["tag"] == "multi_select_static"
        assert len(result["options"]) == 3

    def test_button(self):
        value = {"action": "test", "id": "1"}
        result = cb._button("Click me", value)
        assert result["tag"] == "action"
        assert len(result["actions"]) == 1
        btn = result["actions"][0]
        assert btn["tag"] == "button"
        assert btn["type"] == "primary"
        assert btn["value"] == value

    def test_double_button(self):
        result = cb._double_button(
            "OK", {"action": "ok"},
            "Cancel", {"action": "cancel"},
        )
        assert len(result["actions"]) == 2
        assert result["actions"][0]["type"] == "primary"
        assert result["actions"][1]["type"] == "default"

    def test_card_structure(self):
        elements = [cb._div("Hello")]
        card = cb._card("My Title", elements, "red")
        assert card["config"]["wide_screen_mode"] is True
        assert card["config"]["enable_forward"] is False
        assert card["header"]["title"]["content"] == "My Title"
        assert card["header"]["template"] == "red"
        assert card["elements"] == elements


class TestOnboardingCards:
    """测试引导卡片构建"""

    def test_card_1_basic_structure(self):
        card = cb.build_onboarding_card_1()
        assert card["header"]["template"] == "blue"
        assert "1/3" in card["header"]["title"]["content"]
        # Should have form elements
        elements = card["elements"]
        tags = [e["tag"] for e in elements]
        assert "input" in tags
        assert "select_static" in tags
        assert "action" in tags
        # Action button should have onboarding value
        action = elements[-2]  # second to last is the button, last is note
        btn = action["actions"][0]
        assert btn["value"]["action"] == "onboarding"
        assert btn["value"]["step"] == "2"

    def test_card_2_basic_structure(self):
        card = cb.build_onboarding_card_2()
        assert "2/3" in card["header"]["title"]["content"]
        elements = card["elements"]
        tags = [e["tag"] for e in elements]
        assert "multi_select_static" in tags
        assert "select_static" in tags
        # Should have double button (back + next)
        action_tags = [e for e in elements if e["tag"] == "action"]
        assert len(action_tags) == 1
        assert len(action_tags[0]["actions"]) == 2  # two buttons

    def test_card_3_summary(self):
        profile = {
            "company_name": "测试工作室",
            "design_style": "现代简约",
            "city": "北京",
            "target_client": "首次装修",
            "service_types": "全案设计",
            "brand_tone": "专业严谨",
            "price_range": "20-50万",
        }
        card = cb.build_onboarding_card_3(profile)
        assert "3/3" in card["header"]["title"]["content"]
        assert card["header"]["template"] == "green"
        elements_text = json.dumps(card["elements"], ensure_ascii=False)
        assert "测试工作室" in elements_text
        assert "现代简约" in elements_text
        assert "北京" in elements_text

    def test_card_3_has_finish_and_restart_buttons(self):
        card = cb.build_onboarding_card_3({"company_name": "test"})
        action = [e for e in card["elements"] if e["tag"] == "action"]
        assert len(action) == 1
        buttons = action[0]["actions"]
        finish_btn = buttons[0]
        restart_btn = buttons[1]
        assert finish_btn["value"]["step"] == "finish"
        assert restart_btn["value"]["step"] == "1"


class TestCardJSONValidity:
    """确保卡片 JSON 符合基本结构"""

    def test_card_1_is_valid_json(self):
        card = cb.build_onboarding_card_1()
        s = json.dumps(card, ensure_ascii=False)
        assert len(s) > 0
        # Must have required top-level keys
        assert "config" in card
        assert "header" in card
        assert "elements" in card

    def test_card_2_is_valid_json(self):
        card = cb.build_onboarding_card_2()
        s = json.dumps(card, ensure_ascii=False)
        assert len(s) > 0

    def test_card_3_is_valid_json(self):
        card = cb.build_onboarding_card_3({"company_name": "test"})
        s = json.dumps(card, ensure_ascii=False)
        assert len(s) > 0

    def test_cards_all_different(self):
        c1 = json.dumps(cb.build_onboarding_card_1(), sort_keys=True)
        c2 = json.dumps(cb.build_onboarding_card_2(), sort_keys=True)
        c3 = json.dumps(cb.build_onboarding_card_3({"company_name": "x"}), sort_keys=True)
        assert c1 != c2
        assert c2 != c3
        assert c1 != c3


class TestOptions:
    """测试选项数据"""

    def test_style_options_not_empty(self):
        assert len(cb.STYLE_OPTIONS) >= 5

    def test_city_options_not_empty(self):
        assert len(cb.CITY_OPTIONS) >= 20

    def test_client_type_options_not_empty(self):
        assert len(cb.CLIENT_TYPE_OPTIONS) >= 3

    def test_service_type_options_not_empty(self):
        assert len(cb.SERVICE_TYPE_OPTIONS) >= 3

    def test_brand_tone_options_not_empty(self):
        assert len(cb.BRAND_TONE_OPTIONS) >= 3

    def test_price_range_options_not_empty(self):
        assert len(cb.PRICE_RANGE_OPTIONS) >= 3
