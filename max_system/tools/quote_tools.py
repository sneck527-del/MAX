"""报价数据MCP工具：材料库、施工库查询 + 费用汇总计算"""

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


async def _get_fee_config() -> dict:
    """从Profile读取费率配置，未配置则用行业默认值"""
    defaults = {"management_fee_rate": 8.0, "tax_rate": 3.41, "garbage_fee": 800.0, "protection_fee": 500.0}
    try:
        from max_system.tools.profile_tools import get_profile_manager
        mgr = get_profile_manager()
        if mgr is not None:
            for key in list(defaults):
                val = await mgr.get(key)
                if val:
                    try:
                        defaults[key] = float(val)
                    except (ValueError, TypeError):
                        pass
    except Exception:
        pass
    return defaults


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


async def quote_calculate_summary(args: dict) -> dict:
    """费用汇总计算 — 根据报价项目列表计算管理费、税金、清运费、成品保护费，汇总报价总计"""
    items = args.get("items", [])
    if isinstance(items, str):
        items = json.loads(items)

    if not items:
        return {"content": [{"type": "text", "text": "请提供报价项目列表，每项含 quantity（数量）、unit_price（单价）、可选的 name（名称）和 type（engineering/material）"}]}

    cfg = await _get_fee_config()

    eng_total = 0.0
    prod_total = 0.0
    detail = []

    for item in items:
        qty = max(0.0, float(item.get("quantity", 0)))
        unit_price = max(0.0, float(item.get("unit_price", 0)))
        amount = qty * unit_price
        item_type = item.get("type", "engineering")
        if item_type in ("product", "material"):
            prod_total += amount
        else:
            eng_total += amount
        detail.append({
            "name": item.get("name", ""),
            "type": item_type,
            "quantity": qty,
            "unit_price": unit_price,
            "amount": round(amount, 2),
        })

    subtotal = eng_total + prod_total
    mgmt = subtotal * cfg["management_fee_rate"] / 100.0
    tax = subtotal * cfg["tax_rate"] / 100.0
    garbage = cfg["garbage_fee"]
    protection = cfg["protection_fee"]
    grand_total = subtotal + mgmt + tax + garbage + protection

    summary = {
        "items": detail,
        "工程小计": round(eng_total, 2),
        "产品小计": round(prod_total, 2),
        "直接费用合计": round(subtotal, 2),
        "管理费": round(mgmt, 2),
        "管理费比例": f"{cfg['management_fee_rate']}%",
        "税金": round(tax, 2),
        "税金比例": f"{cfg['tax_rate']}%",
        "垃圾清运费": garbage,
        "成品保护费": protection,
        "报价总计": round(grand_total, 2),
    }

    return {"content": [{"type": "text", "text": json.dumps(summary, ensure_ascii=False)}]}


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
    {
        "name": "quote_calculate_summary",
        "description": "报价汇总计算：根据施工项目和产品清单的明细列表，自动计算管理费、税金、垃圾清运费、成品保护费，汇总报价总计。设计师说'帮我算一下总价'或'汇总一下报价'时使用。费率可从Profile读取（管理费率/税率/垃圾清运费/成品保护费），未配置时使用行业默认值。",
        "parameters": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "description": "报价项目列表。每项需含 quantity（数量）和 unit_price（单价），可选 name（名称）和 type（engineering=施工/material=主材）",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "项目名称"},
                            "type": {"type": "string", "description": "类型: engineering(施工) 或 material(主材)", "enum": ["engineering", "material"]},
                            "quantity": {"type": "number", "description": "数量"},
                            "unit_price": {"type": "number", "description": "单价"},
                        },
                        "required": ["quantity", "unit_price"],
                    },
                },
            },
            "required": ["items"],
        },
    },
]


def register_tools(settings: MaxSettings):
    global _quote_path
    _quote_path = settings.get_quote_data_path()

    handlers = {
        "quote_query_materials": quote_query_materials,
        "quote_query_construction": quote_query_construction,
        "quote_calculate_summary": quote_calculate_summary,
    }
    return [(d["name"], handlers[d["name"]], d) for d in TOOL_DEFS]
