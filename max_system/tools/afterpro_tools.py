"""AfterPro售后官专用工具：竣工回访、问题处理、售后台账、老客户维护、客诉处理"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from max_system.config.settings import MaxSettings
from max_system.tools.clientmgr_tools import _clients_db

logger = logging.getLogger(__name__)

# ============ 内存缓存 ============

_afterlog_db: dict[str, dict] = {}
_issue_counter = 0
_issue_bitable_mapping: dict[str, str] = {}  # issue_id → bitable record_id
_settings: MaxSettings | None = None
_api_client: Any = None


# ============ 字段名映射（内部key ↔ 售后维保台账bitable字段）============

ISSUE_TO_BITABLE = {
    "问题编号": "问题编号",
    "项目": "项目名称",
    "问题描述": "问题描述",
    "严重程度": "优先级",
    "责任判定": "责任判定",
    "处理时限": "处理时限",
    "联系人": "客户姓名",
    "状态": "处理状态",
    "创建时间": "提报日期",
}
BITABLE_TO_ISSUE = {v: k for k, v in ISSUE_TO_BITABLE.items()}

VISIT_TO_BITABLE = {
    "项目": "项目名称",
    "客户": "客户姓名",
    "回访类型": "回访方式",
    "计划日期": "回访日期",
    "特别备注": "跟进事项",
    "创建时间": "创建时间",
}


def _get_after_sales_table_id() -> str:
    if _settings is None:
        raise RuntimeError("afterpro_tools 未初始化")
    return _settings.bitable_table_after_sales


def _get_visit_table_id() -> str:
    if _settings is None:
        raise RuntimeError("afterpro_tools 未初始化")
    return _settings.bitable_table_visits


def _ensure_api_client():
    global _api_client
    if _api_client is None and _settings and _settings.feishu_bitable_app_token:
        from max_system.integrations.feishu.api_client import FeishuApiClient
        _api_client = FeishuApiClient(_settings)


async def _sync_issue_to_bitable(issue: dict) -> str | None:
    """同步售后问题到多维表格"""
    if not _settings or not _settings.feishu_bitable_app_token:
        return None
    _ensure_api_client()
    if _api_client is None:
        return None

    table_id = _get_after_sales_table_id()
    fields = {ISSUE_TO_BITABLE.get(k, k): v for k, v in issue.items() if v}
    issue_id = issue.get("问题编号", "")
    record_id = _issue_bitable_mapping.get(issue_id)

    try:
        if record_id:
            await _api_client.update_bitable_record(table_id, record_id, fields)
        else:
            result = await _api_client.write_bitable(table_id, [fields])
            new_records = result.get("data", {}).get("records", [])
            if new_records:
                record_id = new_records[0].get("record_id", "")
                _issue_bitable_mapping[issue_id] = record_id
        return record_id
    except Exception as e:
        logger.warning("同步售后问题 %s 失败: %s", issue_id, e)
        return None


async def _sync_visit_to_bitable(schedule: dict) -> None:
    """同步回访计划到回访记录表"""
    if not _settings or not _settings.feishu_bitable_app_token:
        return
    _ensure_api_client()
    if _api_client is None:
        return

    table_id = _get_visit_table_id()
    fields = {VISIT_TO_BITABLE.get(k, k): v for k, v in schedule.items() if v}
    try:
        await _api_client.write_bitable(table_id, [fields])
    except Exception as e:
        logger.warning("同步回访计划失败: %s", e)


def _next_issue_id() -> str:
    global _issue_counter
    _issue_counter += 1
    return f"ISS-{datetime.now().strftime('%Y%m%d')}-{_issue_counter:04d}"


# ============ 1. 竣工回访排程 ============

async def returnvisit_schedule(args: dict) -> dict:
    """安排竣工回访计划"""
    project_name = args.get("project_name", "")
    client_name = args.get("client_name", "")
    visit_type = args.get("visit_type", "竣工3个月回访")
    key_items = args.get("key_items", "")
    special_notes = args.get("special_notes", "")

    days_map = {
        "竣工3个月回访": 90,
        "竣工6个月回访": 180,
        "竣工1年回访": 365,
        "年度回访": 365,
    }
    days = days_map.get(visit_type, 90)
    plan_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

    checklist = [
        "墙面有无开裂/起皮",
        "门窗开关是否顺畅",
        "水电设备运行正常",
        "厨卫防水有无渗漏",
        "定制柜体有无变形",
        "地板有无起翘/异响",
    ]
    if key_items:
        checklist.append(f"重点关注: {key_items}")

    schedule = {
        "项目": project_name,
        "客户": client_name,
        "回访类型": visit_type,
        "计划日期": plan_date,
        "检查清单": checklist,
        "特别备注": special_notes or "无",
        "回访话术要点": [
            "先问候入住体验，拉近距离",
            "按清单逐项检查，记录问题",
            "小问题当场安排，大问题48小时内给方案",
            "结束时询问是否有转介绍意向",
        ],
        "创建时间": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    # 同步到回访记录表
    await _sync_visit_to_bitable(schedule)

    return {"content": [{"type": "text", "text": json.dumps(schedule, ensure_ascii=False, indent=2)}]}


# ============ 2. 问题处理追踪 ============

async def issuefix_track(args: dict) -> dict:
    """创建并追踪售后问题处理"""
    project_name = args.get("project_name", "")
    issue_desc = args.get("issue_desc", "")
    severity = args.get("severity", "一般")
    responsibility = args.get("responsibility", "待判定")
    contact = args.get("contact", "")

    issue_id = _next_issue_id()

    deadline_map = {
        "紧急": "24小时",
        "重要": "48小时",
        "一般": "7个工作日",
        "轻微": "15个工作日",
    }
    deadline = deadline_map.get(severity, "7个工作日")

    flow = []
    if severity in ("紧急", "重要"):
        flow.append("1. 立即通知设计师和项目经理")
        flow.append("2. 2小时内到达现场确认问题")
    flow.append("3. 判定责任归属，确定整改方案")
    flow.append("4. 安排施工人员整改")
    flow.append("5. 整改完成通知客户验收")
    flow.append("6. 验收通过后归档关闭")

    scripts = []
    if severity == "紧急":
        scripts.append("话术: 非常抱歉给您带来不便，我们已经安排人员今天上门处理，请您放心。")
    else:
        scripts.append("话术: 感谢您反馈的问题，我们会在约定时间内处理完毕，有进展随时跟您沟通。")

    issue = {
        "问题编号": issue_id,
        "项目": project_name,
        "问题描述": issue_desc,
        "严重程度": severity,
        "责任判定": responsibility,
        "处理时限": deadline,
        "联系人": contact,
        "处理流程": flow,
        "沟通话术": scripts,
        "状态": "待处理",
        "创建时间": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    _afterlog_db[issue_id] = issue
    # 同步到售后维保台账
    await _sync_issue_to_bitable(issue)

    return {"content": [{"type": "text", "text": json.dumps(issue, ensure_ascii=False, indent=2)}]}


# ============ 3. 售后台账更新 ============

async def afterlog_update(args: dict) -> dict:
    """查询或更新售后台账"""
    action = args.get("action", "query")
    issue_id = args.get("issue_id", "")
    status = args.get("status", "")
    note = args.get("note", "")
    project_name = args.get("project_name", "")

    if action == "update" and issue_id:
        if issue_id not in _afterlog_db:
            return {"content": [{"type": "text", "text": f"未找到问题编号: {issue_id}"}]}
        entry = _afterlog_db[issue_id]
        if status:
            entry["状态"] = status
        if note:
            entry.setdefault("处理记录", [])
            entry["处理记录"].append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {note}")
        entry["更新时间"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        # 同步到多维表格
        await _sync_issue_to_bitable(entry)
        return {"content": [{"type": "text", "text": json.dumps(entry, ensure_ascii=False, indent=2)}]}

    if action == "summary":
        total = len(_afterlog_db)
        pending = sum(1 for v in _afterlog_db.values() if v.get("状态") == "待处理")
        processing = sum(1 for v in _afterlog_db.values() if v.get("状态") == "处理中")
        closed = sum(1 for v in _afterlog_db.values() if v.get("状态") == "已关闭")
        summary = {
            "售后台账汇总": {
                "总问题数": total,
                "待处理": pending,
                "处理中": processing,
                "已关闭": closed,
            },
            "紧急待处理": [
                f"{k}: {v['问题描述'][:30]}"
                for k, v in _afterlog_db.items()
                if v.get("严重程度") in ("紧急", "重要") and v.get("状态") != "已关闭"
            ],
        }
        return {"content": [{"type": "text", "text": json.dumps(summary, ensure_ascii=False, indent=2)}]}

    # 默认查询
    if issue_id and issue_id in _afterlog_db:
        return {"content": [{"type": "text", "text": json.dumps(_afterlog_db[issue_id], ensure_ascii=False, indent=2)}]}

    if project_name:
        results = {k: v for k, v in _afterlog_db.items() if project_name in v.get("项目", "")}
    else:
        results = _afterlog_db

    return {"content": [{"type": "text", "text": json.dumps(results or {"提示": "暂无售后记录"}, ensure_ascii=False, indent=2)}]}


# ============ 4. 老客户维护提醒 ============

async def clientcare_reminder(args: dict) -> dict:
    """生成老客户维护提醒和方案"""
    period = args.get("period", "本月")
    care_type = args.get("care_type", "常规维护")

    reminders = []
    for cid, client in _clients_db.items():
        if client.get("status") not in ("已签约", "已完工"):
            continue
        name = client.get("name", "未知")
        created = client.get("created_at", "")

        if care_type == "常规维护":
            reminders.append({
                "客户": name,
                "类型": "季度回访",
                "建议动作": "电话问候入住体验，了解是否有问题需要处理",
            })
        elif care_type == "节日关怀":
            reminders.append({
                "客户": name,
                "类型": "节日祝福",
                "建议动作": "发送节日祝福+小礼品（绿植/香薰）",
            })
        elif care_type == "入住周年":
            if created:
                reminders.append({
                    "客户": name,
                    "类型": "入住周年",
                    "建议动作": "周年回访+免费小保养服务（墙面补漆/五金调试）",
                })
        elif care_type == "转介绍请求":
            reminders.append({
                "客户": name,
                "类型": "转介绍邀约",
                "建议动作": "沟通满意度后，自然引入转介绍话题，提供推荐奖励方案",
            })

    plan = {
        "维护周期": period,
        "关怀类型": care_type,
        "待维护客户": len(reminders),
        "提醒列表": reminders[:20],
        "维护预算建议": {
            "常规回访": "0元（电话/微信）",
            "节日礼品": "50-100元/户",
            "周年保养": "200-500元/户（含人工）",
            "转介绍奖励": "500-1000元/单（成功签约后）",
        },
        "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    return {"content": [{"type": "text", "text": json.dumps(plan, ensure_ascii=False, indent=2)}]}


# ============ 5. 客诉处理方案 ============

async def complaintpro_handle(args: dict) -> dict:
    """生成客诉处理方案"""
    source = args.get("source", "")
    content = args.get("content", "")
    severity = args.get("severity", "一般投诉")
    client_name = args.get("client_name", "")
    project_name = args.get("project_name", "")

    impact = {}
    if severity == "重大投诉":
        impact = {
            "等级": "红色预警",
            "可能后果": ["客户要求退单/赔偿", "社交媒体负面曝光", "影响品牌口碑"],
            "升级条件": "24小时内未解决则升级至公司管理层",
        }
    elif severity == "严重投诉":
        impact = {
            "等级": "橙色预警",
            "可能后果": ["客户不满加剧", "可能影响尾款收取", "同行获知影响竞争力"],
            "升级条件": "48小时内未解决则升级至部门负责人",
        }
    else:
        impact = {
            "等级": "黄色预警",
            "可能后果": ["客户体验下降", "转介绍意愿降低"],
            "升级条件": "7天内未解决则升级至项目经理",
        }

    handle_plan = []
    if severity == "重大投诉":
        handle_plan = [
            "1. 立即上报公司管理层和法务",
            "2. 2小时内联系客户，表达高度重视",
            "3. 项目经理+设计师当天上门沟通",
            "4. 48小时内给出书面解决方案",
            "5. 持续跟进至客户满意",
        ]
    elif severity == "严重投诉":
        handle_plan = [
            "1. 4小时内联系客户，表示歉意和重视",
            "2. 项目经理24小时内上门核实情况",
            "3. 3个工作日内给出解决方案",
            "4. 整改完成后邀请客户验收",
        ]
    else:
        handle_plan = [
            "1. 24小时内回复客户，了解详情",
            "2. 安排对应责任人核实处理",
            "3. 7个工作日内完成整改",
            "4. 回访确认客户满意",
        ]

    scripts = []
    if severity in ("重大投诉", "严重投诉"):
        scripts.append("首次沟通: 非常抱歉给您带来这样的困扰，我已经把情况上报到公司最高层，我们会用最快的速度给您一个满意的答复。请您放心，我们一定负责到底。")
        scripts.append("方案沟通: 经过我们团队的紧急讨论，这是我们的解决方案，请您看看是否可以接受。如果有任何不满意的地方，我们继续调整。")
    else:
        scripts.append("首次沟通: 感谢您反馈这个问题，我们非常重视。我这边先记录下来，马上安排人跟您对接处理。")
        scripts.append("回访确认: 问题已经处理好了，您看看是否满意？如果还有其他需要我们改进的地方，随时联系我们。")

    result = {
        "客诉处理方案": {
            "客户": client_name,
            "项目": project_name,
            "投诉来源": source,
            "投诉内容": content,
            "严重程度": severity,
            "影响评估": impact,
            "处理方案": handle_plan,
            "沟通话术": scripts,
            "风险升级预警": impact.get("升级条件", ""),
            "创建时间": datetime.now().strftime("%Y-%m-%d %H:%M"),
        },
    }

    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}


# ============ 工具定义和注册 ============

TOOL_DEFS = [
    {
        "name": "returnvisit_schedule",
        "description": "安排竣工回访计划，自动生成回访时间、检查清单和话术要点，同步到飞书回访记录表。",
        "parameters": {
            "type": "object",
            "properties": {
                "project_name": {"type": "string", "description": "项目名称"},
                "client_name": {"type": "string", "description": "客户姓名"},
                "visit_type": {"type": "string", "description": "回访类型: 竣工3个月回访/竣工6个月回访/竣工1年回访/年度回访"},
                "key_items": {"type": "string", "description": "重点检查项"},
                "special_notes": {"type": "string", "description": "特别备注"},
            },
            "required": ["project_name"],
        },
    },
    {
        "name": "issuefix_track",
        "description": "创建售后问题处理工单，自动同步到飞书售后维保台账。",
        "parameters": {
            "type": "object",
            "properties": {
                "project_name": {"type": "string", "description": "项目名称"},
                "issue_desc": {"type": "string", "description": "问题描述"},
                "severity": {"type": "string", "description": "严重程度: 紧急/重要/一般/轻微"},
                "responsibility": {"type": "string", "description": "责任判定: 施工责任/材料问题/客户使用/自然损耗/待判定"},
                "contact": {"type": "string", "description": "客户联系方式"},
            },
            "required": ["project_name", "issue_desc"],
        },
    },
    {
        "name": "afterlog_update",
        "description": "查询或更新售后台账，支持按问题编号查询、更新状态、汇总统计，更新同步到飞书。",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "操作: query/update/summary"},
                "issue_id": {"type": "string", "description": "问题编号（查询/更新时必填）"},
                "status": {"type": "string", "description": "更新状态: 待处理/处理中/已关闭"},
                "note": {"type": "string", "description": "处理备注"},
                "project_name": {"type": "string", "description": "项目名称（筛选查询）"},
            },
            "required": [],
        },
    },
    {
        "name": "clientcare_reminder",
        "description": "生成老客户维护提醒和关怀方案。",
        "parameters": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "维护周期: 本月/本季度"},
                "care_type": {"type": "string", "description": "关怀类型: 常规维护/节日关怀/入住周年/转介绍请求"},
            },
            "required": [],
        },
    },
    {
        "name": "complaintpro_handle",
        "description": "生成客诉处理方案，包含影响评估、处理流程、沟通话术和风险升级预警。",
        "parameters": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "投诉来源"},
                "content": {"type": "string", "description": "投诉内容"},
                "severity": {"type": "string", "description": "严重程度: 一般投诉/严重投诉/重大投诉"},
                "client_name": {"type": "string", "description": "客户姓名"},
                "project_name": {"type": "string", "description": "项目名称"},
            },
            "required": ["content"],
        },
    },
]


def register_tools(settings: MaxSettings):
    global _settings
    _settings = settings
    handlers = {
        "returnvisit_schedule": returnvisit_schedule,
        "issuefix_track": issuefix_track,
        "afterlog_update": afterlog_update,
        "clientcare_reminder": clientcare_reminder,
        "complaintpro_handle": complaintpro_handle,
    }
    return [(d["name"], handlers[d["name"]], d) for d in TOOL_DEFS]
