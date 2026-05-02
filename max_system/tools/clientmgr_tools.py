"""客户管理MCP工具 — 飞书多维表格持久化 + 内存缓存"""

import json
import logging
from datetime import datetime
from typing import Any

from max_system.config.settings import MaxSettings

logger = logging.getLogger(__name__)

# ============ 内存缓存 ============

_clients_db: dict[str, dict] = {}          # client_id → client dict
_client_bitable_mapping: dict[str, str] = {}  # client_id → bitable record_id
_cache_loaded: bool = False
_settings: MaxSettings | None = None
_api_client: Any = None  # lazy import FeishuApiClient

# ============ 字段名映射（内部key ↔ 多维表格中文field name）============

INTERNAL_TO_BITABLE = {
    "client_id": "客户编号",
    "name": "客户姓名",
    "phone": "联系电话",
    "city": "城市",
    "unit_type": "户型面积",
    "budget": "预算",
    "source": "来源渠道",
    "status": "客户状态",
    "intent": "意向等级",
    "tags": "标签",
    "follower": "跟进人",
    "remark": "备注",
    "created_at": "创建时间",
    "updated_at": "更新时间",
}
BITABLE_TO_INTERNAL = {v: k for k, v in INTERNAL_TO_BITABLE.items()}


def _to_bitable_fields(client_data: dict) -> dict:
    """将内部client dict转为bitable field_name→value格式"""
    return {INTERNAL_TO_BITABLE.get(k, k): v for k, v in client_data.items() if v is not None and v != ""}


def _from_bitable_fields(fields: dict, field_map: dict[str, str]) -> dict:
    """将bitable返回的field_id→value转为内部client dict"""
    result = {}
    for fid, fname in field_map.items():
        internal_key = BITABLE_TO_INTERNAL.get(fname, fname)
        val = fields.get(fid)
        if val is not None:
            result[internal_key] = val
    return result


def _get_client_table_id() -> str:
    if _settings is None:
        raise RuntimeError("clientmgr_tools 未初始化")
    return _settings.bitable_table_clients


def _ensure_api_client():
    """懒初始化 FeishuApiClient"""
    global _api_client
    if _api_client is None and _settings and _settings.feishu_bitable_app_token:
        from max_system.integrations.feishu.api_client import FeishuApiClient
        _api_client = FeishuApiClient(_settings)


async def _load_from_bitable() -> bool:
    """从多维表格加载客户数据到内存缓存。返回是否成功。"""
    global _cache_loaded
    if _cache_loaded:
        return True
    if not _settings or not _settings.feishu_bitable_app_token:
        _cache_loaded = True
        return False

    _ensure_api_client()
    if _api_client is None:
        _cache_loaded = True
        return False

    try:
        table_id = _get_client_table_id()
        field_map = await _api_client.get_field_mapping(table_id)

        all_records = []
        page_token = ""
        while True:
            result = await _api_client.read_bitable(
                table_id=table_id, page_size=500, page_token=page_token
            )
            items = result.get("data", {}).get("items", [])
            all_records.extend(items)
            if not result.get("data", {}).get("has_more"):
                break
            page_token = result.get("data", {}).get("page_token", "")

        for record in all_records:
            record_id = record.get("record_id", "")
            fields = record.get("fields", {})
            client_data = _from_bitable_fields(fields, field_map)
            cid = client_data.get("client_id", "")
            if cid:
                _clients_db[cid] = client_data
                _client_bitable_mapping[cid] = record_id

        logger.info("从多维表格加载 %d 条客户记录", len(all_records))
    except Exception as e:
        logger.warning("从多维表格加载客户数据失败: %s，使用内存模式", e)

    _cache_loaded = True
    return True


async def _sync_to_bitable(client_id: str) -> str | None:
    """将客户数据同步到多维表格。返回 record_id。"""
    if not _settings or not _settings.feishu_bitable_app_token:
        return None
    if client_id not in _clients_db:
        return None

    _ensure_api_client()
    if _api_client is None:
        return None

    table_id = _get_client_table_id()
    fields = _to_bitable_fields(_clients_db[client_id])
    record_id = _client_bitable_mapping.get(client_id)

    try:
        if record_id:
            await _api_client.update_bitable_record(table_id, record_id, fields)
        else:
            result = await _api_client.write_bitable(table_id, [fields])
            new_records = result.get("data", {}).get("records", [])
            if new_records:
                record_id = new_records[0].get("record_id", "")
                _client_bitable_mapping[client_id] = record_id
        return record_id
    except Exception as e:
        logger.warning("同步客户 %s 到多维表格失败: %s", client_id, e)
        return None


# ============ 工具实现 ============


async def clientmgr_create_client(args: dict) -> dict:
    client_id = f"C{datetime.now().strftime('%Y%m%d%H%M%S')}"
    client = {
        "client_id": client_id,
        "name": args.get("name", ""),
        "phone": args.get("phone", ""),
        "city": args.get("city", ""),
        "unit_type": args.get("unit_type", ""),
        "budget": args.get("budget", ""),
        "source": args.get("source", ""),
        "status": "新建",
        "intent": "待评估",
        "tags": args.get("tags", ""),
        "follower": args.get("follower", ""),
        "remark": args.get("remark", ""),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    _clients_db[client_id] = client
    # 同步到多维表格（后台执行，不阻塞返回）
    await _sync_to_bitable(client_id)

    return {"content": [{"type": "text", "text": json.dumps({
        "success": True, "client_id": client_id,
        "message": f"客户 {args.get('name', '')} 已创建，编号: {client_id}",
    }, ensure_ascii=False)}]}


async def clientmgr_update_client(args: dict) -> dict:
    client_id = args.get("client_id", "")
    updates = json.loads(args["updates"]) if isinstance(args.get("updates"), str) else args.get("updates", {})

    await _load_from_bitable()  # 确保缓存加载

    if client_id not in _clients_db:
        return {"content": [{"type": "text", "text": f"客户 {client_id} 不存在"}], "is_error": True}
    _clients_db[client_id].update(updates)
    _clients_db[client_id]["updated_at"] = datetime.now().isoformat()
    await _sync_to_bitable(client_id)

    return {"content": [{"type": "text", "text": json.dumps({
        "success": True, "client_id": client_id, "message": "客户记录已更新",
    }, ensure_ascii=False)}]}


async def clientmgr_query_clients(args: dict) -> dict:
    await _load_from_bitable()  # 确保缓存加载

    name = args.get("name", "").lower()
    status = args.get("status", "")
    intent = args.get("intent", "")
    results = []
    for client in _clients_db.values():
        if name and name not in client.get("name", "").lower():
            continue
        if status and status != client.get("status", ""):
            continue
        if intent and intent != client.get("intent", ""):
            continue
        results.append(client)
    return {"content": [{"type": "text", "text": json.dumps(results, ensure_ascii=False)}]}


async def clientmgr_sync_client(client_id: str) -> dict:
    """供其他模块调用的公开同步接口：将指定客户同步到多维表格"""
    if client_id not in _clients_db:
        return {"success": False, "message": f"客户 {client_id} 不存在"}
    record_id = await _sync_to_bitable(client_id)
    return {"success": True, "record_id": record_id, "message": "已同步"}


# ============ 工具定义 ============

TOOL_DEFS = [
    {
        "name": "clientmgr_create_client",
        "description": "创建新客户记录，同步到飞书客户信息多维表格。",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "客户姓名"},
                "phone": {"type": "string", "description": "联系电话"},
                "city": {"type": "string", "description": "所在城市"},
                "unit_type": {"type": "string", "description": "户型: 如180㎡大平层"},
                "budget": {"type": "string", "description": "预算范围"},
                "source": {"type": "string", "description": "来源渠道"},
                "tags": {"type": "string", "description": "客户标签"},
                "follower": {"type": "string", "description": "跟进人"},
                "remark": {"type": "string", "description": "备注"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "clientmgr_update_client",
        "description": "更新客户记录信息，同步到飞书多维表格。",
        "parameters": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "客户编号"},
                "updates": {"type": "string", "description": "更新字段JSON字符串"},
            },
            "required": ["client_id", "updates"],
        },
    },
    {
        "name": "clientmgr_query_clients",
        "description": "查询客户记录，支持按名称、状态、意向等级筛选。",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "客户姓名关键词"},
                "status": {"type": "string", "description": "状态: 新建/跟进中/已签约/已归档"},
                "intent": {"type": "string", "description": "意向: 待评估/高/中/低"},
            },
            "required": [],
        },
    },
]


def register_tools(settings: MaxSettings):
    global _settings
    _settings = settings
    handlers = {
        "clientmgr_create_client": clientmgr_create_client,
        "clientmgr_update_client": clientmgr_update_client,
        "clientmgr_query_clients": clientmgr_query_clients,
    }
    return [(d["name"], handlers[d["name"]], d) for d in TOOL_DEFS]
