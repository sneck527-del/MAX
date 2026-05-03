"""自媒体工具：线索转化、案例数据查询、内容数据复盘"""

import json
import logging
from datetime import datetime

from max_system.config.settings import MaxSettings

logger = logging.getLogger(__name__)

# 内容素材库（内存存储）
_content_db: list[dict] = []
_lead_pool: list[dict] = []


# ============ 1. 线索转化判定 ============

async def leadtransfer_qualify(args: dict) -> dict:
    """评估自媒体线索质量，按意图强度分级"""
    lead_source = args.get("lead_source", "")
    lead_content = args.get("lead_content", "")
    contact_info = args.get("contact_info", "")
    platform = args.get("platform", "小红书")

    quality_score = 0
    quality_reasons = []

    high_intent_signals = ["装修", "报价", "面积", "户型", "什么时候", "多少钱", "预算", "签约", "开工"]
    for signal in high_intent_signals:
        if signal in lead_content:
            quality_score += 2
            quality_reasons.append(f"包含高意图关键词: {signal}")

    mid_intent_signals = ["风格", "效果", "案例", "看一下", "了解", "咨询", "推荐"]
    for signal in mid_intent_signals:
        if signal in lead_content:
            quality_score += 1
            quality_reasons.append(f"包含中意图关键词: {signal}")

    if contact_info:
        quality_score += 2
        quality_reasons.append("已留下联系方式")

    source_weights = {"微信添加": 3, "小红书私信": 2, "抖音评论": 1}
    quality_score += source_weights.get(lead_source, 1)
    quality_reasons.append(f"来源渠道: {lead_source}")

    if quality_score >= 6:
        quality = "A级-高意向"
        transfer_urgency = "24小时内联系"
    elif quality_score >= 3:
        quality = "B级-中意向"
        transfer_urgency = "48小时内跟进"
    else:
        quality = "C级-低意向"
        transfer_urgency = "先回复引导获取更多信息"

    result = {
        "线索来源": f"{platform}-{lead_source}",
        "线索内容": lead_content,
        "联系方式": contact_info or "未提供",
        "质量评分": quality_score,
        "评级": quality,
        "评分依据": quality_reasons,
        "建议动作": transfer_urgency,
        "判定时间": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    _lead_pool.append(result)

    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}


# ============ 2. 案例数据查询 ============

async def casepack_package(args: dict) -> dict:
    """查询客户项目数据，返回结构化信息供LLM包装为营销素材"""
    project_name = args.get("project_name", "")
    client_name = args.get("client_name", "")

    # 从客户数据库查询项目数据
    project_data = {}
    try:
        from max_system.tools.clientmgr_tools import _clients_db
        for c in _clients_db.values():
            if client_name and c.get("name") == client_name:
                project_data = c
                break
            if project_name and project_name in c.get("name", ""):
                project_data = c
                break
    except ImportError:
        pass

    if not project_data:
        return {"content": [{"type": "text", "text": f"未找到项目: {project_name or client_name}，请确认客户已登记"}]}

    return {"content": [{"type": "text", "text": json.dumps({
        "project_data": project_data,
        "note": "请根据以上项目数据生成营销素材。发布前必须取得客户书面授权。",
    }, ensure_ascii=False, indent=2)}]}


# ============ 3. 内容数据复盘 ============

async def datareview_analyze(args: dict) -> dict:
    """从内容库和线索池统计数据"""
    platform = args.get("platform", "全部")
    period = args.get("period", "本月")

    total_content = len(_content_db)
    by_platform = {}
    for c in _content_db:
        p = c.get("平台", "未知")
        by_platform[p] = by_platform.get(p, 0) + 1

    total_leads = len(_lead_pool)
    a_leads = sum(1 for l in _lead_pool if "A级" in l.get("评级", ""))
    b_leads = sum(1 for l in _lead_pool if "B级" in l.get("评级", ""))

    report = {
        "复盘周期": period,
        "内容产出": {
            "总发布量": total_content,
            "各平台分布": by_platform or {"提示": "暂无发布记录"},
        },
        "线索转化": {
            "总线索数": total_leads,
            "A级（高意向）": a_leads,
            "B级（中意向）": b_leads,
            "C级（低意向）": total_leads - a_leads - b_leads,
            "转化率": f"{(a_leads / total_leads * 100):.1f}%" if total_leads > 0 else "0%",
        },
        "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    return {"content": [{"type": "text", "text": json.dumps(report, ensure_ascii=False, indent=2)}]}


# ============ 工具定义和注册 ============

TOOL_DEFS = [
    {
        "name": "leadtransfer_qualify",
        "description": "评估自媒体线索质量并按意图强度分级。设计师收到小红书/抖音/微信线索时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "lead_source": {"type": "string", "description": "线索来源: 小红书私信/抖音评论/微信添加/公众号留言"},
                "lead_content": {"type": "string", "description": "线索内容"},
                "contact_info": {"type": "string", "description": "客户联系方式"},
                "platform": {"type": "string", "description": "来源平台"},
            },
            "required": ["lead_content"],
        },
    },
    {
        "name": "casepack_package",
        "description": "查询客户项目数据（户型、风格、预算等），用于生成营销素材。输入客户姓名或项目名。",
        "parameters": {
            "type": "object",
            "properties": {
                "project_name": {"type": "string", "description": "项目名称"},
                "client_name": {"type": "string", "description": "客户姓名"},
            },
            "required": [],
        },
    },
    {
        "name": "datareview_analyze",
        "description": "内容运营数据复盘，含内容产出统计、线索转化分析。",
        "parameters": {
            "type": "object",
            "properties": {
                "platform": {"type": "string", "description": "分析平台: 全部/小红书/抖音"},
                "period": {"type": "string", "description": "复盘周期: 本周/本月/本季度"},
            },
            "required": [],
        },
    },
]


def register_tools(settings: MaxSettings):
    handlers = {
        "leadtransfer_qualify": leadtransfer_qualify,
        "casepack_package": casepack_package,
        "datareview_analyze": datareview_analyze,
    }
    return [(d["name"], handlers[d["name"]], d) for d in TOOL_DEFS]
