"""报价数据MCP工具：材料库、施工库查询 + 费用汇总计算 + Excel导入"""

import json
import logging
import os
import tempfile
from pathlib import Path

from max_system.config.settings import MaxSettings

logger = logging.getLogger(__name__)

# ============ 模块级全局（默认路径） ============

_quote_path: Path | None = None
_materials_db: dict | None = None
_construction_db: dict | None = None
_loaded_path: Path | None = None  # 跟踪缓存的workspace路径，切换时自动重载


def _get_active_quotes_path() -> Path:
    """获取当前活跃工作区的 quotes 路径。

    优先从 workspace context 获取，回退到全局默认路径。
    """
    try:
        from max_system.core.orchestrator import _current_workspace
        ws = _current_workspace.get()
        if ws is not None:
            return ws.quotes_path
    except Exception:
        pass
    return _quote_path or Path("quotes")


def _load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _seed_defaults(quotes_path: Path) -> None:
    """如果工作区没有报价数据，从全局默认目录复制。"""
    global _quote_path
    default_src = _quote_path or Path("quotes")
    for filename in ("材料库.json", "施工库.json"):
        dst = quotes_path / filename
        if not dst.exists():
            src = default_src / filename
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def _ensure_loaded():
    global _materials_db, _construction_db, _loaded_path
    quotes_path = _get_active_quotes_path()
    if _loaded_path != quotes_path:
        _seed_defaults(quotes_path)
        _materials_db = _load_json(quotes_path / "材料库.json")
        _construction_db = _load_json(quotes_path / "施工库.json")
        _loaded_path = quotes_path


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


async def quote_import_excel(args: dict) -> dict:
    """从飞书消息中下载Excel文件，解析并导入报价数据。

    支持两种情况：
    1. 传 file_key：从飞书消息中下载文件 → 解析 → 导入
    2. 传 file_path：直接解析本地文件 → 导入
    """
    import asyncio

    file_key = args.get("file_key", "")
    file_name = args.get("file_name", "")
    file_path = args.get("file_path", "")

    temp_file = None
    actual_path = file_path

    # 从飞书下载文件
    if file_key and not file_path:
        # 获取 FeishuApiClient
        try:
            from max_system.tools.feishu_tools import _get_api_client
            client = _get_api_client()
        except Exception:
            pass
        else:
            try:
                # 下载文件
                file_data = await client.download_file_by_key(file_key)
                # 写入临时文件
                suffix = ".xlsx"
                if file_name:
                    ext = os.path.splitext(file_name)[1].lower()
                    if ext in (".xlsx", ".xls"):
                        suffix = ext
                tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix, prefix="max_quote_")
                os.close(tmp_fd)
                Path(tmp_path).write_bytes(file_data)
                actual_path = tmp_path
                temp_file = tmp_path
            except Exception as e:
                return {"content": [{"type": "text", "text": json.dumps({
                    "success": False,
                    "message": f"从飞书下载文件失败: {e}",
                }, ensure_ascii=False)}]}

    if not actual_path:
        return {"content": [{"type": "text", "text": json.dumps({
            "success": False,
            "message": "请提供 file_key（从飞书下载）或 file_path（本地文件路径）",
        }, ensure_ascii=False)}]}

    try:
        from max_system.integrations.quotes.excel_importer import parse_excel, save_to_workspace

        # 解析Excel
        result = parse_excel(actual_path)
        if not result["success"]:
            # 清理临时文件
            if temp_file:
                try:
                    Path(temp_file).unlink(missing_ok=True)
                except OSError:
                    pass
            return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}

        # 保存到工作区
        quotes_path = _get_active_quotes_path()
        save_result = save_to_workspace(result["data"], quotes_path, result["type"])

        # 清除缓存，让下次查询加载新数据
        global _materials_db, _construction_db, _loaded_path
        _loaded_path = None
        if result["type"] == "materials":
            _materials_db = None
        else:
            _construction_db = None

        # 清理临时文件
        if temp_file:
            try:
                Path(temp_file).unlink(missing_ok=True)
            except OSError:
                pass

        response = {
            "success": True,
            "type": result["type"],
            "message": result["message"] + "。" + save_result["message"],
            "rows_imported": result["rows_imported"],
            "sheets_processed": result["sheets_processed"],
            "saved_to": save_result["path"] if save_result["success"] else "内存（未持久化）",
        }

        return {"content": [{"type": "text", "text": json.dumps(response, ensure_ascii=False)}]}

    except Exception as e:
        if temp_file:
            try:
                Path(temp_file).unlink(missing_ok=True)
            except OSError:
                pass
        return {"content": [{"type": "text", "text": json.dumps({
            "success": False,
            "message": f"导入失败: {e}",
        }, ensure_ascii=False)}]}


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
    {
        "name": "quote_import_excel",
        "description": "导入Excel报价文件到报价库。设计师发送Excel文件后使用此工具解析并导入。支持材料库和施工库两种格式，自动识别列名（类别/名称/单价等）并转为标准格式。数据会持久化到工作区，下次查询即可使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "file_key": {"type": "string", "description": "飞书文件消息的 file_key（从飞书下载时使用）"},
                "file_name": {"type": "string", "description": "文件名（如：主材报价表.xlsx），用于确定扩展名"},
                "file_path": {"type": "string", "description": "本地文件路径（直接解析本地文件时使用，CLI模式下）"},
            },
            "required": [],
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
        "quote_import_excel": quote_import_excel,
    }
    return [(d["name"], handlers[d["name"]], d) for d in TOOL_DEFS]
