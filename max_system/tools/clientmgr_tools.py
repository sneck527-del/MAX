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
    "phone": "联系方式",
    "city": "项目地址",
    "unit_type": "户型",
    "budget": "报价",
    "design_fee": "设计费",
    "source": "客户来源",
    "client_type": "客户类型",
    "type": "类型",
    "status": "服务阶段",
    "intent": "落单进度",
    "follower": "分派设计师",
    "remark": "备注",
    "created_at": "录入时间",
    "follow_up_at": "跟进时间",
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
        "design_fee": args.get("design_fee", ""),
        "source": args.get("source", ""),
        "client_type": args.get("client_type", ""),
        "type": args.get("type", ""),
        "status": args.get("status", "新建"),
        "intent": args.get("intent", "待评估"),
        "follower": args.get("follower", ""),
        "remark": args.get("remark", ""),
        "created_at": datetime.now().isoformat(),
        "follow_up_at": "",
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


# ============ 客户标签与报表 ============

async def client_tag_and_report(args: dict) -> dict:
    """客户标签化管理 + 跟进报表 + 逾期预警"""
    from datetime import timedelta
    action = args.get("action", "report")
    tag_client_id = args.get("client_id", "")
    tag_labels = args.get("labels", "")

    if action == "tag" and tag_client_id and tag_labels:
        if tag_client_id in _clients_db:
            labels = [l.strip() for l in tag_labels.split(",") if l.strip()]
            _clients_db[tag_client_id]["tags"] = labels
            _clients_db[tag_client_id]["updated_at"] = datetime.now().isoformat()
            return {"content": [{"type": "text", "text": json.dumps({
                "success": True, "client_id": tag_client_id, "labels": labels,
            }, ensure_ascii=False)}]}
        return {"content": [{"type": "text", "text": f"客户 {tag_client_id} 不存在"}]}

    tag_system = {
        "意向标签": ["高意向-急跟", "中意向-培育", "低意向-长线"],
        "来源标签": ["小红书", "抖音", "老客户介绍", "门店", "朋友圈"],
        "阶段标签": ["初次接触", "方案沟通", "报价谈判", "已签约", "施工中", "已竣工"],
        "户型标签": ["别墅", "大平层", "普通住宅", "小户型"],
        "风格标签": ["现代简约", "新中式", "轻奢", "北欧", "日式"],
    }

    auto_tags = {}
    for cid, c in _clients_db.items():
        tags = []
        intent = c.get("intent", "")
        if intent == "高":
            tags.append("高意向-急跟")
        elif intent == "中":
            tags.append("中意向-培育")
        else:
            tags.append("低意向-长线")

        unit = c.get("unit_type", "")
        if "别墅" in unit:
            tags.append("别墅")
        elif "大平层" in unit:
            tags.append("大平层")

        source = c.get("source", "")
        for s in ["小红书", "抖音", "朋友", "门店"]:
            if s in source:
                tags.append({"小红书": "小红书", "抖音": "抖音", "朋友": "老客户介绍", "门店": "门店"}.get(s, s))

        status = c.get("status", "")
        status_map = {"新建": "初次接触", "跟进中": "方案沟通", "已签约": "已签约"}
        if status in status_map:
            tags.append(status_map[status])

        auto_tags[cid] = tags

    if action == "overdue":
        now = datetime.now()
        overdue = []
        for cid, c in _clients_db.items():
            updated = c.get("updated_at", "")
            if updated and c.get("status") in ("新建", "跟进中"):
                try:
                    updated_dt = datetime.fromisoformat(updated)
                    if (now - updated_dt) > timedelta(days=7):
                        overdue.append({
                            "client_id": cid,
                            "name": c.get("name", ""),
                            "intent": c.get("intent", ""),
                            "last_contact": updated,
                            "days_since": (now - updated_dt).days,
                        })
                except ValueError:
                    pass
        overdue.sort(key=lambda x: x["days_since"], reverse=True)

        return {"content": [{"type": "text", "text": json.dumps({
            "逾期未跟进客户": len(overdue),
            "列表": overdue[:20],
            "建议动作": "逐一联系客户，更新跟进状态",
        }, ensure_ascii=False, indent=2)}]}

    total = len(_clients_db)
    by_intent = {"高": 0, "中": 0, "低": 0, "待评估": 0}
    by_status = {}
    for c in _clients_db.values():
        i = c.get("intent", "待评估")
        by_intent[i] = by_intent.get(i, 0) + 1
        s = c.get("status", "未知")
        by_status[s] = by_status.get(s, 0) + 1

    report = {
        "客户标签体系": tag_system,
        "客户统计": {
            "总客户数": total,
            "意向分布": by_intent,
            "状态分布": by_status,
        },
        "自动标签": auto_tags,
        "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    return {"content": [{"type": "text", "text": json.dumps(report, ensure_ascii=False, indent=2)}]}


# ============ 工具定义 ============

TOOL_DEFS = [
    {
        "name": "clientmgr_create_client",
        "description": "创建新客户记录，同步到飞书客户信息多维表格。",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "客户姓名"},
                "phone": {"type": "string", "description": "联系方式"},
                "city": {"type": "string", "description": "项目地址"},
                "unit_type": {"type": "string", "description": "户型: 如大平层/别墅/复式"},
                "budget": {"type": "string", "description": "报价/预算金额"},
                "design_fee": {"type": "string", "description": "设计费"},
                "source": {"type": "string", "description": "客户来源: 小红书/抖音/朋友推荐/门店"},
                "client_type": {"type": "string", "description": "客户类型"},
                "type": {"type": "string", "description": "类型: 全案/半包/纯设计"},
                "follower": {"type": "string", "description": "分派设计师"},
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
        "description": "查询客户记录，支持按名称、服务阶段、落单进度筛选。",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "客户姓名关键词"},
                "status": {"type": "string", "description": "服务阶段: 新建/量房/方案/签约/施工/完工/归档"},
                "intent": {"type": "string", "description": "落单进度: 待评估/意向/谈判/签约/已签约"},
            },
            "required": [],
        },
    },
    {
        "name": "client_tag_and_report",
        "description": "客户标签化管理、统计报表与逾期预警。支持report/tag/overdue三种操作。",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "操作: report(报表)/tag(打标签)/overdue(逾期预警)", "enum": ["report", "tag", "overdue"]},
                "client_id": {"type": "string", "description": "客户编号（tag操作时需要）"},
                "labels": {"type": "string", "description": "标签，逗号分隔（tag操作时需要）"},
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
        "client_tag_and_report": client_tag_and_report,
    }
    return [(d["name"], handlers[d["name"]], d) for d in TOOL_DEFS]
