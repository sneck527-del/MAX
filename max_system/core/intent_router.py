"""意图路由器：根据用户消息内容分类调度方向"""

from max_system.config.schema import IntentCategory


# 关键词→意图映射
INTENT_KEYWORDS: dict[IntentCategory, list[str]] = {
    IntentCategory.TALKER: [
        "线索", "客户", "谈单", "报价", "合同", "需求分析", "跟进",
        "签单", "话术", "预案", "转化", "建档", "量房", "方案",
        "预约", "成交", "客户信息", "意向", "定金",
    ],
    IntentCategory.AFTERPRO: [
        "售后", "回访", "维保", "客诉", "投诉", "整改", "质保",
        "老客户", "维护", "问题处理", "返修", "验收", "竣工",
        "保修", "投诉处理", "满意度",
    ],
    IntentCategory.MEDIAPRO: [
        "自媒体", "小红书", "抖音", "文案", "内容", "账号",
        "获客", "引流", "案例包装", "IP", "视频号", "公众号",
        "笔记", "短视频", "直播", "粉丝", "曝光",
    ],
    IntentCategory.HELPER: [
        "文档", "归档", "知识库", "飞书", "Obsidian", "同步",
        "模板", "台账", "整理", "存档", "导出",
    ],
    IntentCategory.MAX_DIRECT: [
        "状态", "进度", "帮助", "设置", "配置", "规则",
    ],
}


class IntentRouter:
    """基于关键词的意图分类器

    分类结果作为路由提示追加到用户消息前，
    Max最终决定调度方向（关键词分类只是辅助）。
    """

    def classify(self, text: str) -> IntentCategory:
        """根据消息文本分类意图"""
        scores: dict[IntentCategory, int] = {}

        for category, keywords in INTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[category] = score

        if not scores:
            return IntentCategory.MAX_DIRECT

        return max(scores, key=scores.get)

    def augment_message(self, text: str) -> str:
        """在消息前追加路由提示"""
        intent = self.classify(text)

        if intent == IntentCategory.MAX_DIRECT:
            return text

        labels = {
            IntentCategory.TALKER: "谈单类，建议调度Talker处理",
            IntentCategory.AFTERPRO: "售后类，建议调度AfterPro处理",
            IntentCategory.MEDIAPRO: "自媒体类，建议调度MediaPro处理",
            IntentCategory.HELPER: "基础设施类，建议调度Helper处理",
        }

        hint = labels.get(intent, "")
        if hint:
            return f"[路由提示：此指令属于{hint}]\n\n{text}"
        return text
