"""自媒体工具：线索转化、案例数据查询、内容数据复盘（SQLite持久化）"""

import json
import logging
from datetime import datetime, timedelta

import aiosqlite

from max_system.config.settings import MaxSettings

logger = logging.getLogger(__name__)

# 内容素材库（内存存储 + SQLite持久化）
_content_db: list[dict] = []
_lead_pool: list[dict] = []

_settings: MaxSettings | None = None
_db_path: str = ""
_db_initialized: bool = False
_data_restored: bool = False

# ============ SQLite持久化 ============


async def _ensure_initialized():
    """确保数据库表存在且数据已恢复到内存。"""
    global _db_initialized, _data_restored
    if not _db_path:
        return

    # 初始化表结构（仅一次）
    if not _db_initialized:
        try:
            conn = await _init_db()
            await conn.close()
            _db_initialized = True
        except Exception as e:
            logger.warning("营销工具数据库初始化失败: %s", e)
            return

    # 从SQLite恢复数据（仅一次）
    if not _data_restored:
        try:
            await _restore_leads()
            await _restore_content()
            _data_restored = True
        except Exception as e:
            logger.warning("恢复营销数据失败: %s", e)


async def _init_db() -> aiosqlite.Connection:
    """初始化SQLite连接并创建表。"""
    conn = await aiosqlite.connect(_db_path)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS marketing_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS marketing_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    await conn.commit()
    return conn


async def _restore_leads():
    """从SQLite恢复线索数据到内存。"""
    global _lead_pool
    if not _db_path:
        return
    try:
        conn = await aiosqlite.connect(_db_path)
        cursor = await conn.execute("SELECT data_json FROM marketing_leads ORDER BY id ASC")
        rows = await cursor.fetchall()
        _lead_pool = [json.loads(row[0]) for row in rows]
        await conn.close()
        if _lead_pool:
            logger.info("从SQLite恢复 %d 条线索记录", len(_lead_pool))
    except Exception as e:
        logger.warning("恢复线索数据失败: %s", e)


async def _restore_content():
    """从SQLite恢复内容数据到内存。"""
    global _content_db
    if not _db_path:
        return
    try:
        conn = await aiosqlite.connect(_db_path)
        cursor = await conn.execute("SELECT data_json FROM marketing_content ORDER BY id ASC")
        rows = await cursor.fetchall()
        _content_db = [json.loads(row[0]) for row in rows]
        await conn.close()
        if _content_db:
            logger.info("从SQLite恢复 %d 条内容记录", len(_content_db))
    except Exception as e:
        logger.warning("恢复内容数据失败: %s", e)


async def _persist_lead(lead_data: dict):
    """持久化一条线索到SQLite。"""
    if not _db_path:
        return
    try:
        conn = await aiosqlite.connect(_db_path)
        await conn.execute(
            "INSERT INTO marketing_leads (data_json) VALUES (?)",
            (json.dumps(lead_data, ensure_ascii=False),),
        )
        await conn.commit()
        await conn.close()
    except Exception as e:
        logger.warning("持久化线索失败: %s", e)


async def _persist_content(content_data: dict):
    """持久化一条内容到SQLite。"""
    if not _db_path:
        return
    try:
        conn = await aiosqlite.connect(_db_path)
        await conn.execute(
            "INSERT INTO marketing_content (data_json) VALUES (?)",
            (json.dumps(content_data, ensure_ascii=False),),
        )
        await conn.commit()
        await conn.close()
    except Exception as e:
        logger.warning("持久化内容失败: %s", e)


# ============ 周期过滤辅助函数 ============


def _compute_period_cutoff(period: str) -> datetime | None:
    """根据周期描述计算起始时间，返回None表示不限时间。"""
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


def _filter_by_created_at(items: list[dict], cutoff: datetime | None) -> list[dict]:
    """按created_at过滤，无created_at字段则计入（向后兼容）。"""
    if cutoff is None:
        return items

    filtered = []
    for item in items:
        created_str = item.get("created_at", "")
        if not created_str:
            filtered.append(item)
            continue
        try:
            created_dt = datetime.fromisoformat(created_str)
            if created_dt >= cutoff:
                filtered.append(item)
        except (ValueError, TypeError):
            filtered.append(item)
    return filtered


# ============ 1. 线索转化判定 ============


async def leadtransfer_qualify(args: dict) -> dict:
    """评估自媒体线索质量，按意图强度分级"""
    await _ensure_initialized()
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

    now_iso = datetime.now().isoformat()

    result = {
        "线索来源": f"{platform}-{lead_source}",
        "线索内容": lead_content,
        "联系方式": contact_info or "未提供",
        "质量评分": quality_score,
        "评级": quality,
        "评分依据": quality_reasons,
        "建议动作": transfer_urgency,
        "判定时间": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "created_at": now_iso,
    }

    _lead_pool.append(result)

    # 持久化到SQLite
    await _persist_lead(result)

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
    """从内容库和线索池统计数据，支持按周期过滤"""
    await _ensure_initialized()
    platform = args.get("platform", "全部")
    period = args.get("period", "本月")

    # 计算时间截断点
    cutoff = _compute_period_cutoff(period)

    # 按时间和平台过滤
    filtered_content = _filter_by_created_at(_content_db, cutoff)
    filtered_leads = _filter_by_created_at(_lead_pool, cutoff)

    if platform and platform != "全部":
        filtered_content = [c for c in filtered_content if c.get("平台", "") == platform]
        filtered_leads = [l for l in filtered_leads if platform in l.get("线索来源", "")]

    total_content = len(filtered_content)
    by_platform = {}
    for c in filtered_content:
        p = c.get("平台", "未知")
        by_platform[p] = by_platform.get(p, 0) + 1

    total_leads = len(filtered_leads)
    a_leads = sum(1 for l in filtered_leads if "A级" in l.get("评级", ""))
    b_leads = sum(1 for l in filtered_leads if "B级" in l.get("评级", ""))

    report = {
        "复盘周期": period,
        "筛选起始时间": cutoff.strftime("%Y-%m-%d %H:%M") if cutoff else "无限制（全量统计）",
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

    # 内容库为空时的提示
    if not _content_db:
        report["提示"] = "暂无内容发布数据，请先通过内容生成工具创建营销内容"

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
        "description": "内容运营数据复盘，含内容产出统计、线索转化分析。支持按周期和平台过滤。",
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
    global _settings, _db_path, _db_initialized, _data_restored
    _settings = settings
    _db_path = str(settings.get_db_path())
    # 重置状态以支持重新注册（例如测试中反复import）
    _db_initialized = False
    _data_restored = False

    handlers = {
        "leadtransfer_qualify": leadtransfer_qualify,
        "casepack_package": casepack_package,
        "datareview_analyze": datareview_analyze,
    }
    return [(d["name"], handlers[d["name"]], d) for d in TOOL_DEFS]
