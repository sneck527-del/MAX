"""报价数据MCP工具：材料库、施工库查询"""

import json
import logging
from pathlib import Path

from max_system.config.settings import MaxSettings

logger = logging.getLogger(__name__)

_quote_path: Path | None = None
_materials_db: dict | None = None
_construction_db: dict | None = None


def _load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _ensure_loaded():
    global _materials_db, _construction_db
    if _materials_db is None:
        _materials_db = _load_json(_quote_path / "材料库.json") if _quote_path else {}
    if _construction_db is None:
        _construction_db = _load_json(_quote_path / "施工库.json") if _quote_path else {}


async def quote_query_materials(args: dict) -> dict:
    _ensure_loaded()
    if not _materials_db:
        return {"content": [{"type": "text", "text": "材料库数据未加载"}]}

    category = args.get("category", "")
    subcategory = args.get("subcategory", "")
    name = args.get("name", "")

    results = []
    data = _materials_db

    if category and category in data:
        cat_data = data[category]
        if isinstance(cat_data, dict):
            if subcategory and subcategory in cat_data:
                items = cat_data[subcategory]
                results = items if isinstance(items, list) else [items]
                if name:
                    results = [i for i in results if name in json.dumps(i, ensure_ascii=False)]
            elif not subcategory:
                for sub_key, sub_val in cat_data.items():
                    if isinstance(sub_val, list):
                        results.extend(sub_val)
                    else:
                        results.append(sub_val)
    elif not category and name:
        for cat_key, cat_val in data.items():
            if isinstance(cat_val, dict):
                for sub_key, sub_val in cat_val.items():
                    if isinstance(sub_val, list):
                        results.extend(i for i in sub_val if name in json.dumps(i, ensure_ascii=False))

    return {"content": [{"type": "text", "text": json.dumps(results[:20], ensure_ascii=False)}]}


async def quote_query_construction(args: dict) -> dict:
    _ensure_loaded()
    if not _construction_db:
        return {"content": [{"type": "text", "text": "施工库数据未加载"}]}

    category = args.get("category", "")
    item_name = args.get("item_name", "")

    results = []
    data = _construction_db

    if category and category in data:
        items = data[category]
        if isinstance(items, list):
            results = items if not item_name else [i for i in items if item_name in json.dumps(i, ensure_ascii=False)]
    elif not category and item_name:
        for cat_key, items in data.items():
            if isinstance(items, list):
                results.extend(i for i in items if item_name in json.dumps(i, ensure_ascii=False))

    return {"content": [{"type": "text", "text": json.dumps(results[:20], ensure_ascii=False)}]}


TOOL_DEFS = [
    {
        "name": "quote_query_materials",
        "description": "查询主材库中的材料信息和价格。支持按类别和名称搜索。",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "材料大类: 门窗/橱柜/地板/瓷砖等"},
                "subcategory": {"type": "string", "description": "材料子类"},
                "name": {"type": "string", "description": "材料名称关键词"},
            },
            "required": [],
        },
    },
    {
        "name": "quote_query_construction",
        "description": "查询施工库中的施工项目和工艺标准。",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "工种: 拆除/砌筑/防水/水电等"},
                "item_name": {"type": "string", "description": "项目名称关键词"},
            },
            "required": [],
        },
    },
]


def register_tools(settings: MaxSettings):
    global _quote_path
    _quote_path = settings.quote_data_path

    handlers = {
        "quote_query_materials": quote_query_materials,
        "quote_query_construction": quote_query_construction,
    }
    return [(d["name"], handlers[d["name"]], d) for d in TOOL_DEFS]
