"""知识库MCP工具：搜索、合规检查"""

import json
import logging
import re
from pathlib import Path

from max_system.config.settings import MaxSettings

logger = logging.getLogger(__name__)

_kb_path: Path | None = None


async def knowledge_search(args: dict) -> dict:
    kb = _kb_path
    if not kb or not kb.exists():
        return {"content": [{"type": "text", "text": "知识库目录尚未配置或不存在"}]}

    query = args["query"].lower()
    category = args.get("category", "")
    top_k = args.get("top_k", 5)

    results = []
    search_dirs = [kb / category] if category and (kb / category).exists() else [
        kb / "company_standards", kb / "case_database",
        kb / "material_database", kb / "customer_service",
        kb / "media_materials",
    ]

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for f in search_dir.rglob("*.md"):
            content = f.read_text(encoding="utf-8", errors="ignore")
            if query in content.lower():
                idx = content.lower().find(query)
                snippet = content[max(0, idx - 100):min(len(content), idx + len(query) + 200)]
                results.append({"file": str(f.relative_to(kb)), "snippet": snippet})
                if len(results) >= top_k:
                    break
        if len(results) >= top_k:
            break

    return {"content": [{"type": "text", "text": json.dumps(results, ensure_ascii=False)}]}


async def knowledge_compliance_check(args: dict) -> dict:
    kb = _kb_path
    if not kb or not kb.exists():
        return {"content": [{"type": "text", "text": "知识库未配置，无法进行合规检查"}]}

    content = args["content"]
    violations = []

    safety_keywords = ["承重墙拆除", "梁体切割", "楼板开洞", "擅自改动结构"]
    for kw in safety_keywords:
        if kw in content:
            violations.append(f"红线违规: 涉及结构安全 - '{kw}'")

    if "底价" in content or "采购价" in content:
        violations.append("数据安全: 内容中包含供应商底价信息")

    if re.search(r"1[3-9]\d{9}", content):
        violations.append("隐私风险: 内容中包含手机号码")

    return {"content": [{"type": "text", "text": json.dumps({
        "compliant": len(violations) == 0, "violations": violations,
    }, ensure_ascii=False)}]}


TOOL_DEFS = [
    {
        "name": "knowledge_search",
        "description": "搜索公司知识库，包含公司标准、案例、材料库、客服话术等。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
                "category": {"type": "string", "description": "类别: company_standards/case_database/material_database/customer_service/media_materials"},
                "top_k": {"type": "integer", "description": "返回结果数量"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "knowledge_compliance_check",
        "description": "检查内容是否符合公司标准和合规要求。",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "要检查的内容"},
                "check_type": {"type": "string", "description": "检查类型: contract/quotation/publicity/after_sales"},
            },
            "required": ["content"],
        },
    },
]


def register_tools(settings: MaxSettings):
    global _kb_path
    _kb_path = settings.knowledge_base_path
    _kb_path.mkdir(parents=True, exist_ok=True)

    handlers = {
        "knowledge_search": knowledge_search,
        "knowledge_compliance_check": knowledge_compliance_check,
    }
    return [(d["name"], handlers[d["name"]], d) for d in TOOL_DEFS]
