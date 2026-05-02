"""测试意图路由器"""

import pytest
from max_system.config.schema import IntentCategory


class TestIntentRouter:
    """意图分类测试"""

    def setup_method(self):
        from max_system.core.intent_router import IntentRouter
        self.router = IntentRouter()

    def test_talker_intent(self):
        result = self.router.classify("帮我分析客户张先生的需求")
        assert result == IntentCategory.TALKER

    def test_afterpro_intent(self):
        result = self.router.classify("安排一下竣工回访")
        assert result == IntentCategory.AFTERPRO

    def test_mediapro_intent(self):
        result = self.router.classify("写一篇小红书文案")
        assert result == IntentCategory.MEDIAPRO

    def test_helper_intent(self):
        result = self.router.classify("帮我归档项目文档到Obsidian")
        assert result == IntentCategory.HELPER

    def test_max_direct_intent(self):
        result = self.router.classify("当前系统状态怎么样")
        assert result == IntentCategory.MAX_DIRECT

    def test_augment_message_talker(self):
        augmented = self.router.augment_message("客户说预算30万")
        assert "路由提示" in augmented
        assert "谈单类" in augmented

    def test_augment_message_direct(self):
        original = "你好"
        augmented = self.router.augment_message(original)
        assert augmented == original
