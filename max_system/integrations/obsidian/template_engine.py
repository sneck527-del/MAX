"""Obsidian模板引擎：公司标准模板 + frontmatter应用"""

import logging
from datetime import datetime
from typing import Any

from max_system.config.settings import MaxSettings

logger = logging.getLogger(__name__)


class TemplateEngine:
    """模板引擎

    提供公司标准文档模板，自动填充变量和frontmatter。
    用于Helper的DocGen技能。
    """

    # 内置文档模板
    TEMPLATES = {
        "客户线索初访表": {
            "folder": "客户",
            "fields": ["客户姓名", "联系方式", "城市小区", "户型面积", "装修阶段", "预算范围", "风格偏好", "核心需求", "来源渠道", "意向等级"],
        },
        "需求分析报告": {
            "folder": "项目",
            "fields": ["基本信息", "功能需求", "审美偏好", "预算工期", "核心痛点", "设计要点", "谈单切入点"],
        },
        "谈单预案": {
            "folder": "项目",
            "fields": ["核心目标", "流程规划", "切入点", "亮点包装", "风险预判", "支撑材料"],
        },
        "合同草稿": {
            "folder": "项目",
            "fields": ["甲方信息", "乙方信息", "工程概况", "工期约定", "付款方式", "材料约定", "验收标准", "违约责任"],
        },
        "竣工回访记录": {
            "folder": "项目",
            "fields": ["项目名称", "客户姓名", "回访时间", "回访类型", "整体满意度", "问题记录", "客户建议", "转介绍意向"],
        },
        "售后问题处理单": {
            "folder": "项目",
            "fields": ["项目名称", "问题描述", "责任判定", "整改方案", "整改工期", "沟通话术", "验收标准"],
        },
        "投诉处理方案": {
            "folder": "项目",
            "fields": ["投诉来源", "投诉内容", "影响评估", "处理方案", "风险升级预警", "跟进计划"],
        },
        "小红书文案": {
            "folder": "素材",
            "fields": ["标题", "正文", "标签", "发布时间"],
        },
        "短视频脚本": {
            "folder": "素材",
            "fields": ["主题", "时长", "场景", "画面", "旁白", "字幕"],
        },
        "项目总览": {
            "folder": "项目",
            "fields": ["客户信息", "设计师", "项目阶段", "关键节点", "待办事项", "风险提示"],
        },
    }

    def __init__(self, settings: MaxSettings):
        self.settings = settings

    def list_templates(self) -> list[dict]:
        """列出所有可用模板"""
        return [
            {"name": name, "fields": info["fields"]}
            for name, info in self.TEMPLATES.items()
        ]

    def render(
        self,
        template_name: str,
        data: dict[str, Any],
        project_name: str = "",
    ) -> tuple[str, str, list[str]]:
        """渲染模板，返回 (relative_path, content, tags)

        Args:
            template_name: 模板名称
            data: 填充数据
            project_name: 所属项目名（可选，用于路径）

        Returns:
            (文件相对路径, 文件内容, 标签列表)
        """
        template = self.TEMPLATES.get(template_name)
        if not template:
            # 非标准模板，直接输出
            content = self._render_freeform(template_name, data)
            path = f"知识库/{template_name}.md"
            return path, content, [template_name]

        # 构建文件路径
        folder = template["folder"]
        if project_name and folder == "项目":
            safe_name = "".join(c for c in project_name if c.isalnum() or c in " _-")[:50]
            path = f"项目/{safe_name}/{template_name}.md"
        elif project_name and folder == "客户":
            safe_name = "".join(c for c in project_name if c.isalnum() or c in " _-")[:30]
            path = f"客户/{safe_name}.md"
        else:
            path = f"{folder}/{template_name}.md"

        # 渲染内容
        tags = [template_name]
        if project_name:
            tags.append(f"项目/{project_name}")

        lines = [f"# {template_name}", ""]

        if project_name:
            lines.append(f"项目: {project_name}")
            lines.append("")

        lines.append(f"日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("")

        for field in template["fields"]:
            value = data.get(field, "")
            if isinstance(value, list):
                lines.append(f"## {field}")
                for item in value:
                    lines.append(f"- {item}")
                lines.append("")
            elif isinstance(value, dict):
                lines.append(f"## {field}")
                for k, v in value.items():
                    lines.append(f"- {k}: {v}")
                lines.append("")
            elif value:
                lines.append(f"## {field}")
                lines.append(str(value))
                lines.append("")

        content = "\n".join(lines)
        return path, content, tags

    def _render_freeform(self, title: str, data: dict) -> str:
        """渲染非标准模板"""
        lines = [f"# {title}", ""]
        lines.append(f"日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("")

        for key, value in data.items():
            if isinstance(value, list):
                lines.append(f"## {key}")
                for item in value:
                    lines.append(f"- {item}")
            elif isinstance(value, dict):
                lines.append(f"## {key}")
                for k, v in value.items():
                    lines.append(f"- {k}: {v}")
            else:
                lines.append(f"{key}: {value}")
            lines.append("")

        return "\n".join(lines)
