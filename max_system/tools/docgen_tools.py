"""文档生成MCP工具"""

import json
import logging
from datetime import datetime

from max_system.config.settings import MaxSettings

logger = logging.getLogger(__name__)


async def docgen_generate_doc(args: dict) -> dict:
    doc_type = args.get("doc_type", "")
    data = json.loads(args["data"]) if isinstance(args.get("data"), str) else args.get("data", {})

    templates = {
        "量房单": "📐 量房确认单\n━━━━━━━━━━━━━━━━\n",
        "需求分析表": "📋 客户需求分析表\n━━━━━━━━━━━━━━━━\n",
        "设计说明": "🎨 设计方案说明\n━━━━━━━━━━━━━━━━\n",
        "施工交底": "🔨 施工技术交底\n━━━━━━━━━━━━━━━━\n",
        "验收单": "✅ 验收确认单\n━━━━━━━━━━━━━━━━\n",
        "竣工报告": "🏠 竣工验收报告\n━━━━━━━━━━━━━━━━\n",
        "报价单": "💰 装修预算报价单\n━━━━━━━━━━━━━━━━\n",
    }

    header = templates.get(doc_type, f"📄 {doc_type}\n━━━━━━━━━━━━━━━━\n")
    lines = [header, f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]

    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"\n{key}:")
            for item in value:
                lines.append(f"  - {item}")
        elif isinstance(value, dict):
            lines.append(f"\n{key}:")
            for k, v in value.items():
                lines.append(f"  {k}: {v}")
        else:
            lines.append(f"{key}: {value}")

    lines.append("\n⚠️ 此文档由Max系统自动生成，需设计师审核确认后方可使用")
    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


async def docgen_validate_doc(args: dict) -> dict:
    content = args.get("content", "")
    issues = []
    if not content.strip():
        issues.append("文档内容为空")
    if ("价格" in content or "报价" in content) and "设计师审核" not in content:
        issues.append("包含价格信息但缺少设计师审核声明")

    return {"content": [{"type": "text", "text": json.dumps({
        "compliant": len(issues) == 0, "issues": issues, "doc_type": args.get("doc_type", ""),
    }, ensure_ascii=False)}]}


TOOL_DEFS = [
    {
        "name": "docgen_generate_doc",
        "description": "生成标准化文档（量房单、需求分析表、设计说明、施工交底、验收单、竣工报告等）。",
        "parameters": {
            "type": "object",
            "properties": {
                "doc_type": {"type": "string", "description": "文档类型"},
                "data": {"type": "string", "description": "文档数据JSON字符串"},
            },
            "required": ["doc_type", "data"],
        },
    },
    {
        "name": "docgen_validate_doc",
        "description": "验证文档内容是否符合公司模板规范。",
        "parameters": {
            "type": "object",
            "properties": {
                "doc_type": {"type": "string", "description": "文档类型"},
                "content": {"type": "string", "description": "文档内容"},
            },
            "required": ["doc_type", "content"],
        },
    },
]


def register_tools(settings: MaxSettings):
    handlers = {
        "docgen_generate_doc": docgen_generate_doc,
        "docgen_validate_doc": docgen_validate_doc,
    }
    return [(d["name"], handlers[d["name"]], d) for d in TOOL_DEFS]
