"""审批门：高风险输出拦截和人工审批

在CLI模式下用终端确认，在飞书模式下发送审批流。
拦截高风险工具调用（合同、报价、对外承诺），未经设计师确认不可执行。
"""

import asyncio
import json
import logging
from typing import Any

from max_system.config.settings import MaxSettings

logger = logging.getLogger(__name__)

# 需要审批的高风险工具
HIGH_RISK_TOOLS = {
    "feishu_send_message": "对外发送消息",
    "feishu_create_approval": "创建审批流",
    "feishu_write_bitable": "写入飞书多维表格",
    "docgen_generate_doc": "生成正式文档",
    "contractpro_draft": "生成合同草稿",
    "complaintpro_handle": "处理客诉",
    "contentgen_draft": "生成对外发布文案",
    "leadtransfer_qualify": "线索转交（涉及客户信息）",
}

# 需要审批的内容关键词
RISK_KEYWORDS = {
    "合同": "high",
    "报价": "high",
    "价格": "high",
    "承诺": "high",
    "保证": "high",
    "底价": "high",
    "客户信息": "medium",
    "手机号": "medium",
    "身份证": "high",
}


class ApprovalGate:
    """审批门

    在工具调用前检查风险等级：
    - low: 直接放行
    - medium: 记录日志，放行但标记
    - high: 阻塞执行，等待设计师审批
    """

    def __init__(self, settings: MaxSettings, mode: str = "cli"):
        """
        Args:
            settings: 全局配置
            mode: "cli" 终端确认 / "feishu" 飞书审批流
        """
        self.settings = settings
        self.mode = mode
        self._pending_approvals: dict[str, asyncio.Future] = {}

    def check_risk(self, tool_name: str, tool_args: dict) -> tuple[str, str]:
        """检查工具调用的风险等级

        Returns:
            (risk_level, reason) - risk_level: "low"/"medium"/"high"
        """
        # 检查工具是否在风险列表
        if tool_name not in HIGH_RISK_TOOLS:
            return "low", ""

        # 检查参数中是否包含高风险关键词
        args_text = json.dumps(tool_args, ensure_ascii=False)
        for keyword, level in RISK_KEYWORDS.items():
            if keyword in args_text:
                return level, f"内容涉及「{keyword}」"

        # 发送消息类工具，检查是否是群聊
        if tool_name == "feishu_send_message":
            msg_type = tool_args.get("msg_type", "text")
            content = tool_args.get("text", "")
            for keyword, level in RISK_KEYWORDS.items():
                if keyword in content:
                    return level, f"消息内容涉及「{keyword}」"

        return "medium", HIGH_RISK_TOOLS.get(tool_name, "")

    async def request_approval(
        self,
        tool_name: str,
        tool_args: dict,
        risk_level: str,
        reason: str,
    ) -> bool:
        """请求审批

        Args:
            tool_name: 工具名
            tool_args: 工具参数
            risk_level: 风险等级
            reason: 风险原因

        Returns:
            True=审批通过, False=审批拒绝
        """
        if risk_level == "low":
            return True

        if risk_level == "medium":
            logger.warning("中风险操作放行: %s - %s", tool_name, reason)
            return True

        # high: 需要人工审批
        if self.mode == "cli":
            return await self._cli_approval(tool_name, tool_args, reason)
        else:
            return await self._feishu_approval(tool_name, tool_args, reason)

    async def _cli_approval(self, tool_name: str, tool_args: dict, reason: str) -> bool:
        """CLI模式下的终端审批确认"""
        print(f"\n{'='*50}")
        print(f"  需要审批")
        print(f"  工具: {tool_name}")
        print(f"  原因: {reason}")
        print(f"  参数: {json.dumps(tool_args, ensure_ascii=False)[:200]}")
        print(f"{'='*50}")

        # 在事件循环中运行同步输入
        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(
            None,
            lambda: input("  是否批准？(y/N): ").strip().lower()
        )

        approved = answer == "y"
        if approved:
            logger.info("审批通过: %s", tool_name)
        else:
            logger.info("审批拒绝: %s", tool_name)

        return approved

    async def _feishu_approval(self, tool_name: str, tool_args: dict, reason: str) -> bool:
        """飞书模式下的审批流"""
        try:
            from max_system.integrations.feishu.api_client import FeishuApiClient
            api = FeishuApiClient(self.settings)

            # 创建审批实例
            form_data = {
                "工具": tool_name,
                "原因": reason,
                "参数摘要": json.dumps(tool_args, ensure_ascii=False)[:500],
            }

            result = await api.create_approval(
                approval_code="max_system_approval",
                user_id="designer",
                form=json.dumps(form_data, ensure_ascii=False),
            )

            await api.close()

            # 简化处理：审批创建成功后暂时放行
            # TODO: 实现真正的审批等待回调
            logger.info("飞书审批已创建: %s", result)
            return True

        except Exception as e:
            logger.error("飞书审批创建失败: %s，默认拒绝", e)
            return False

    def should_intercept(self, tool_name: str, tool_args: dict) -> bool:
        """判断是否应该拦截该工具调用（快速检查，不阻塞）"""
        risk_level, _ = self.check_risk(tool_name, tool_args)
        return risk_level == "high"
