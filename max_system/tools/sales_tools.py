"""谈单工具：线索捕获、需求分析、合同信息查询、销售统计"""

import json
import logging
from datetime import datetime, timedelta

from max_system.config.settings import MaxSettings
from max_system.tools.clientmgr_tools import _clients_db
from max_system.tools.clientmgr_tools import clientmgr_sync_client

logger = logging.getLogger(__name__)


# ============ 1. 线索捕获分级 ============

async def leadcatch_classify(args: dict) -> dict:
    """对客户线索进行标准化登记和意向分级"""
    name = args.get("name", "")
    phone = args.get("phone", "")
    city = args.get("city", "")
    community = args.get("community", "")
    unit_type = args.get("unit_type", "")
    budget = args.get("budget", "")
    stage = args.get("stage", "")
    style = args.get("style", "")
    source = args.get("source", "")
    core_needs = args.get("core_needs", "")

    score = 0
    reasons = []
    if budget and ("万" in budget):
        try:
            budget_val = float("".join(c for c in budget if c.isdigit() or c == "."))
            if budget_val >= 30:
                score += 3
                reasons.append(f"预算充足({budget})")
            elif budget_val >= 15:
                score += 2
                reasons.append(f"预算中等({budget})")
        except ValueError:
            pass

    if stage in ("已交房", "准备装修", "马上开工"):
        score += 2
        reasons.append(f"装修阶段紧急({stage})")
    elif stage in ("已收房", "设计中"):
        score += 1
        reasons.append(f"已有进展({stage})")

    if unit_type and ("别墅" in unit_type or "大平层" in unit_type):
        score += 2
        reasons.append(f"高端户型({unit_type})")

    if source in ("老客户推荐", "已签客户介绍", "朋友推荐"):
        score += 2
        reasons.append(f"推荐来源({source})")

    if core_needs and len(core_needs) > 10:
        score += 1
        reasons.append("需求描述详细")

    intent = "高" if score >= 6 else ("中" if score >= 3 else "低")

    client_id = f"C{datetime.now().strftime('%Y%m%d%H%M%S')}"

    follow_up = []
    if intent == "高":
        follow_up = ["24小时内电话回访", "3天内安排量房", "准备同户型案例"]
    elif intent == "中":
        follow_up = ["48小时内微信跟进", "发送公司案例集", "了解具体工期要求"]
    else:
        follow_up = ["1周内轻量跟进", "先发送风格参考", "持续朋友圈触达"]

    result = {
        "client_id": client_id,
        "name": name,
        "intent": intent,
        "score": score,
        "reasons": reasons,
        "follow_up": follow_up,
        "registered_at": datetime.now().isoformat(),
    }

    _clients_db[client_id] = {
        "client_id": client_id,
        "name": name, "phone": phone, "city": city,
        "unit_type": unit_type, "budget": budget, "source": source,
        "status": "新建", "intent": intent,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "preferences": {},
        "last_contact": datetime.now().isoformat(),
    }
    try:
        await clientmgr_sync_client(client_id)
    except Exception:
        pass

    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}


# ============ 2. 需求分析 — 查询客户数据 ============

async def needanaly_report(args: dict) -> dict:
    """查询客户信息，返回结构化数据供LLM分析"""
    client_name = args.get("client_name", "")
    client_id = args.get("client_id", "")

    client = None
    if client_id and client_id in _clients_db:
        client = _clients_db[client_id]
    elif client_name:
        for c in _clients_db.values():
            if c.get("name") == client_name:
                client = c
                break

    if not client:
        return {"content": [{"type": "text", "text": f"未找到客户: {client_name or client_id}，请先通过leadcatch_classify登记客户信息"}]}

    # 更新最后联系时间
    _update_client_last_contact(client_name)

    # 返回原始客户数据，由LLM自行分析
    data = {
        "client_id": client.get("client_id", ""),
        "name": client.get("name", ""),
        "phone": client.get("phone", ""),
        "city": client.get("city", ""),
        "unit_type": client.get("unit_type", ""),
        "budget": client.get("budget", ""),
        "source": client.get("source", ""),
        "intent": client.get("intent", ""),
        "status": client.get("status", ""),
        "created_at": client.get("created_at", ""),
        "updated_at": client.get("updated_at", ""),
    }

    return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}]}


# ============ 3. 合同信息查询 ============

async def contractpro_draft(args: dict) -> dict:
    """查询客户和报价数据，返回结构化信息供LLM生成合同"""
    client_name = args.get("client_name", "")
    client_id = args.get("client_id", "")

    client = None
    if client_id and client_id in _clients_db:
        client = _clients_db[client_id]
    elif client_name:
        for c in _clients_db.values():
            if c.get("name") == client_name:
                client = c
                break

    # 更新最后联系时间
    _update_client_last_contact(client_name)

    # 查询报价数据
    quote_data = {}
    try:
        from max_system.tools.quote_tools import _materials_db, _construction_db
        if args.get("material_category"):
            cat = args["material_category"]
            if cat in _materials_db:
                quote_data["materials"] = _materials_db[cat]
        if args.get("construction_trade"):
            trade = args["construction_trade"]
            if trade in _construction_db:
                quote_data["construction"] = _construction_db[trade]
    except ImportError:
        pass

    result = {
        "client": client or {"message": f"未找到客户 {client_name or client_id}，请先登记"},
        "quote_data": quote_data,
        "note": "以上为客户和报价数据，请据此生成合同草稿。合同必须经设计师和法务终审。",
    }

    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}


# ============ 4. 销售数据统计 ============

def _compute_period_cutoff(period: str) -> datetime | None:
    """根据周期描述计算起始时间，返回None表示不限时间（全量统计）。"""
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    period_map = {
        "本日": today,
        "本周": today - timedelta(days=today.weekday()),
        "本月": today.replace(day=1),
        "本季": today.replace(month=((today.month - 1) // 3) * 3 + 1, day=1),
        "本年": today.replace(month=1, day=1),
        "上周": today - timedelta(days=today.weekday() + 7),
        "上月": (today.replace(day=1) - timedelta(days=1)).replace(day=1),
    }

    return period_map.get(period, None)


def _filter_clients_by_period(clients: dict, cutoff: datetime | None) -> list:
    """过滤客户列表，只保留created_at >= cutoff的客户。
    如果cutoff为None则返回全部。对于没有created_at字段的记录，为保证向后兼容，将其计入。
    """
    if cutoff is None:
        return list(clients.values())

    filtered = []
    for c in clients.values():
        created_str = c.get("created_at", "")
        if not created_str:
            # 没有created_at字段，向后兼容：计入统计
            filtered.append(c)
            continue
        try:
            created_dt = datetime.fromisoformat(created_str)
            if created_dt >= cutoff:
                filtered.append(c)
        except (ValueError, TypeError):
            # 解析失败，向后兼容：计入统计
            filtered.append(c)
    return filtered


async def datastat_report(args: dict) -> dict:
    """从客户数据库统计销售数据，支持按周期过滤。"""
    period = args.get("period", "本月")

    cutoff = _compute_period_cutoff(period)
    filtered_clients = _filter_clients_by_period(_clients_db, cutoff)

    total = len(filtered_clients)
    high_intent = sum(1 for c in filtered_clients if c.get("intent") == "高")
    mid_intent = sum(1 for c in filtered_clients if c.get("intent") == "中")
    low_intent = sum(1 for c in filtered_clients if c.get("intent") == "低")

    signed = sum(1 for c in filtered_clients if c.get("status") == "已签约")
    in_progress = sum(1 for c in filtered_clients if c.get("status") == "跟进中")

    conversion_rate = f"{(signed / total * 100):.1f}%" if total > 0 else "0%"

    report = {
        "统计周期": period,
        "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "筛选起始时间": cutoff.strftime("%Y-%m-%d %H:%M") if cutoff else "无限制（全量统计）",
        "总量统计": {
            "总线索数": total,
            "高意向": high_intent,
            "中意向": mid_intent,
            "低意向": low_intent,
        },
        "转化漏斗": {
            "新建线索": total - signed - in_progress,
            "跟进中": in_progress,
            "已签约": signed,
            "转化率": conversion_rate,
        },
        "待跟进预警": [],
        "建议": [],
    }

    for c in filtered_clients:
        if c.get("status") == "新建":
            report["待跟进预警"].append(f"{c.get('name', '未知')}（{c.get('intent', '?')}意向，待首次跟进）")

    if high_intent > 0 and signed < high_intent:
        report["建议"].append(f"有{high_intent}个高意向客户未签约，建议优先安排方案沟通")

    if low_intent > high_intent:
        report["建议"].append("低意向客户占比偏高，建议优化获客渠道质量")

    return {"content": [{"type": "text", "text": json.dumps(report, ensure_ascii=False, indent=2)}]}


def _update_client_last_contact(client_name: str) -> None:
    """更新客户最后联系时间。如果客户不存在，静默跳过。"""
    if not client_name:
        return
    for c in _clients_db.values():
        if c.get("name", "").lower() == client_name.lower():
            c["last_contact"] = datetime.now().isoformat()
            if "preferences" not in c or not isinstance(c.get("preferences"), dict):
                c["preferences"] = {}
            break


# ============ 工具定义和注册 ============

TOOL_DEFS = [
    {
        "name": "leadcatch_classify",
        "description": "客户线索捕获与意向分级。输入客户基本信息，自动评估意向等级（高/中/低），生成跟进建议。",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "客户姓名"},
                "phone": {"type": "string", "description": "联系电话"},
                "city": {"type": "string", "description": "城市"},
                "community": {"type": "string", "description": "小区名称"},
                "unit_type": {"type": "string", "description": "户型面积，如180㎡大平层"},
                "budget": {"type": "string", "description": "预算范围，如60-80万"},
                "stage": {"type": "string", "description": "装修阶段: 已交房/准备装修/设计中/还在看"},
                "style": {"type": "string", "description": "风格偏好"},
                "source": {"type": "string", "description": "来源渠道: 小红书/抖音/朋友推荐/门店等"},
                "core_needs": {"type": "string", "description": "核心需求描述"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "needanaly_report",
        "description": "查询客户详细信息（户型、预算、意向、状态等），用于需求分析。输入客户姓名或编号。",
        "parameters": {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "客户姓名"},
                "client_id": {"type": "string", "description": "客户编号"},
            },
            "required": [],
        },
    },
    {
        "name": "contractpro_draft",
        "description": "查询客户和报价数据，用于生成合同。输入客户姓名和需要查询的材料/施工类别。",
        "parameters": {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "客户姓名"},
                "client_id": {"type": "string", "description": "客户编号"},
                "material_category": {"type": "string", "description": "需要查询的材料类别（可选）"},
                "construction_trade": {"type": "string", "description": "需要查询的施工工种（可选）"},
            },
            "required": [],
        },
    },
    {
        "name": "datastat_report",
        "description": "销售数据统计，包含线索总量、意向分级、转化漏斗、待跟进预警。",
        "parameters": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "统计周期: 本日/本周/本月/本季度"},
            },
            "required": [],
        },
    },
]


def register_tools(settings: MaxSettings):
    handlers = {
        "leadcatch_classify": leadcatch_classify,
        "needanaly_report": needanaly_report,
        "contractpro_draft": contractpro_draft,
        "datastat_report": datastat_report,
    }
    return [(d["name"], handlers[d["name"]], d) for d in TOOL_DEFS]
