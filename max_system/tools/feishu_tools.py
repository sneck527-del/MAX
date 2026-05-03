"""飞书MCP工具：消息、多维表格、审批、日历、任务"""

import json
import logging

from max_system.config.settings import MaxSettings
from max_system.integrations.feishu.api_client import FeishuApiClient

logger = logging.getLogger(__name__)

_api_client: FeishuApiClient | None = None


def _get_api_client() -> FeishuApiClient:
    if _api_client is None:
        raise RuntimeError("飞书API客户端未初始化")
    return _api_client


# ============ 工具实现 ============

async def feishu_send_message(args: dict) -> dict:
    client = _get_api_client()
    await client.send_message(
        chat_id=args["chat_id"],
        text=args["text"],
        msg_type=args.get("msg_type", "text"),
    )
    return {"content": [{"type": "text", "text": f"消息已发送"}]}


async def feishu_read_bitable(args: dict) -> dict:
    client = _get_api_client()
    table_id = args["table_id"]
    field_map = await client.get_field_mapping(table_id)
    result = await client.read_bitable(
        table_id=table_id,
        filter_expr=args.get("filter", ""),
        page_size=args.get("page_size", 100),
    )
    records = result.get("data", {}).get("items", [])
    transformed = []
    for record in records:
        record_id = record.get("record_id", "")
        fields = record.get("fields", {})
        renamed = {field_map.get(k, k): v for k, v in fields.items()}
        transformed.append({"record_id": record_id, "fields": renamed})
    return {"content": [{"type": "text", "text": json.dumps(transformed, ensure_ascii=False)}]}


async def feishu_write_bitable(args: dict) -> dict:
    client = _get_api_client()
    records = json.loads(args["records"]) if isinstance(args.get("records"), str) else args.get("records", [])
    await client.write_bitable(table_id=args["table_id"], records=records)
    return {"content": [{"type": "text", "text": f"成功写入 {len(records)} 条记录"}]}


async def feishu_create_approval(args: dict) -> dict:
    client = _get_api_client()
    result = await client.create_approval(
        approval_code=args["approval_code"],
        user_id=args["user_id"],
        form=args["form"],
    )
    instance_code = result.get("data", {}).get("instance_code", "")
    return {"content": [{"type": "text", "text": f"审批已创建: {instance_code}"}]}


# ============ 日历 ============


async def feishu_create_calendar_event(args: dict) -> dict:
    client = _get_api_client()
    result = await client.create_calendar_event(
        calendar_id=args["calendar_id"],
        summary=args["summary"],
        start_time=args["start_time"],
        end_time=args["end_time"],
        description=args.get("description", ""),
    )
    event_id = result.get("data", {}).get("event", {}).get("event_id", "")
    return {"content": [{"type": "text", "text": f"日历事件已创建: {event_id}"}]}


async def feishu_list_calendar_events(args: dict) -> dict:
    client = _get_api_client()
    result = await client.list_calendar_events(
        calendar_id=args["calendar_id"],
        start_time=args.get("start_time", ""),
        end_time=args.get("end_time", ""),
        page_size=args.get("page_size", 50),
    )
    events = result.get("data", {}).get("items", [])
    summary = []
    for ev in events:
        summary.append({
            "event_id": ev.get("event_id", ""),
            "summary": ev.get("summary", ""),
            "start_time": ev.get("start_time", {}).get("timestamp", ""),
            "end_time": ev.get("end_time", {}).get("timestamp", ""),
        })
    return {"content": [{"type": "text", "text": json.dumps(summary, ensure_ascii=False)}]}


async def feishu_delete_calendar_event(args: dict) -> dict:
    client = _get_api_client()
    await client.delete_calendar_event(
        calendar_id=args["calendar_id"],
        event_id=args["event_id"],
    )
    return {"content": [{"type": "text", "text": f"日历事件已删除: {args['event_id']}"}]}


# ============ 任务 ============


async def feishu_create_task(args: dict) -> dict:
    client = _get_api_client()
    result = await client.create_task(
        summary=args["summary"],
        description=args.get("description", ""),
        due_time=args.get("due_time", ""),
    )
    task = result.get("data", {}).get("task", {})
    task_id = task.get("id", "")
    return {"content": [{"type": "text", "text": f"任务已创建: {task_id} - {args['summary']}"}]}


async def feishu_list_tasks(args: dict) -> dict:
    client = _get_api_client()
    result = await client.list_tasks(
        start_time=args.get("start_time", ""),
        end_time=args.get("end_time", ""),
        status=args.get("status", "1"),  # 1=未完成
        page_size=args.get("page_size", 50),
    )
    tasks = result.get("data", {}).get("items", [])
    summary = []
    for t in tasks:
        summary.append({
            "task_id": t.get("id", ""),
            "summary": t.get("summary", ""),
            "due_time": t.get("due", {}).get("time", "") if t.get("due") else "",
            "status": t.get("status", ""),
            "completed_at": t.get("completed_at", ""),
        })
    return {"content": [{"type": "text", "text": json.dumps(summary, ensure_ascii=False)}]}


async def feishu_complete_task(args: dict) -> dict:
    client = _get_api_client()
    await client.complete_task(args["task_id"])
    return {"content": [{"type": "text", "text": f"任务已完成: {args['task_id']}"}]}


# ============ 工具定义 ============

TOOL_DEFS = [
    {
        "name": "feishu_send_message",
        "description": "发送消息到飞书聊天。设计师让你'通知XX'或'发消息给XX'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "chat_id": {"type": "string", "description": "聊天ID"},
                "text": {"type": "string", "description": "消息内容"},
                "msg_type": {"type": "string", "description": "消息类型: text/interactive", "enum": ["text", "interactive"]},
            },
            "required": ["chat_id", "text"],
        },
    },
    {
        "name": "feishu_read_bitable",
        "description": "读取飞书多维表格记录。支持过滤和分页。先调用此工具查看表结构再写入。",
        "parameters": {
            "type": "object",
            "properties": {
                "table_id": {"type": "string", "description": "表格ID"},
                "filter": {"type": "string", "description": "过滤表达式"},
                "page_size": {"type": "integer", "description": "每页条数"},
            },
            "required": ["table_id"],
        },
    },
    {
        "name": "feishu_write_bitable",
        "description": "写入飞书多维表格记录。records为JSON字符串，字段名用中文。",
        "parameters": {
            "type": "object",
            "properties": {
                "table_id": {"type": "string", "description": "表格ID"},
                "records": {"type": "string", "description": "记录列表JSON字符串"},
            },
            "required": ["table_id", "records"],
        },
    },
    {
        "name": "feishu_create_approval",
        "description": "创建飞书审批实例。",
        "parameters": {
            "type": "object",
            "properties": {
                "approval_code": {"type": "string", "description": "审批定义code"},
                "user_id": {"type": "string", "description": "发起人用户ID"},
                "form": {"type": "string", "description": "表单内容JSON字符串"},
            },
            "required": ["approval_code", "user_id", "form"],
        },
    },
    {
        "name": "feishu_create_calendar_event",
        "description": "在飞书日历中创建日程事件。设计师说'帮我安排一个XX日程'或'在日历上记一下XX'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "calendar_id": {"type": "string", "description": "日历ID（必填），可通过飞书日历页面获取"},
                "summary": {"type": "string", "description": "日程标题"},
                "start_time": {"type": "string", "description": "开始时间，格式如 2026-05-10T14:00:00+08:00"},
                "end_time": {"type": "string", "description": "结束时间，格式如 2026-05-10T15:00:00+08:00"},
                "description": {"type": "string", "description": "日程详细描述"},
            },
            "required": ["calendar_id", "summary", "start_time", "end_time"],
        },
    },
    {
        "name": "feishu_list_calendar_events",
        "description": "查询飞书日历中的日程列表。设计师问'今天有什么安排'或'这周有什么日程'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "calendar_id": {"type": "string", "description": "日历ID（必填）"},
                "start_time": {"type": "string", "description": "查询开始时间"},
                "end_time": {"type": "string", "description": "查询结束时间"},
                "page_size": {"type": "integer", "description": "返回数量，默认50"},
            },
            "required": ["calendar_id"],
        },
    },
    {
        "name": "feishu_delete_calendar_event",
        "description": "删除飞书日历中的日程事件。设计师说'取消XX日程'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "calendar_id": {"type": "string", "description": "日历ID"},
                "event_id": {"type": "string", "description": "日程事件ID"},
            },
            "required": ["calendar_id", "event_id"],
        },
    },
    {
        "name": "feishu_create_task",
        "description": "在飞书中创建待办任务。设计师说'帮我设一个待办'或'记一下XX事情要XX时间完成'时使用。支持设置截止时间和提醒。",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "任务标题"},
                "description": {"type": "string", "description": "任务详细描述"},
                "due_time": {"type": "string", "description": "截止时间，ISO格式 2026-05-10T18:00:00+08:00"},
            },
            "required": ["summary"],
        },
    },
    {
        "name": "feishu_list_tasks",
        "description": "查询飞书中的待办任务列表。设计师问'我有哪些待办'或'还有什么没做完的'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "start_time": {"type": "string", "description": "查询开始时间"},
                "end_time": {"type": "string", "description": "查询结束时间"},
                "status": {"type": "string", "description": "状态: 1=未完成, 2=已完成"},
                "page_size": {"type": "integer", "description": "返回数量，默认50"},
            },
            "required": [],
        },
    },
    {
        "name": "feishu_complete_task",
        "description": "完成（勾选）飞书中的待办任务。设计师说'XX任务做完了'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "任务ID"},
            },
            "required": ["task_id"],
        },
    },
]


def register_tools(settings: MaxSettings):
    """注册飞书工具，返回 [(name, callable, tool_def), ...]"""
    global _api_client
    _api_client = FeishuApiClient(settings)

    handlers = {
        "feishu_send_message": feishu_send_message,
        "feishu_read_bitable": feishu_read_bitable,
        "feishu_write_bitable": feishu_write_bitable,
        "feishu_create_approval": feishu_create_approval,
        "feishu_create_calendar_event": feishu_create_calendar_event,
        "feishu_list_calendar_events": feishu_list_calendar_events,
        "feishu_delete_calendar_event": feishu_delete_calendar_event,
        "feishu_create_task": feishu_create_task,
        "feishu_list_tasks": feishu_list_tasks,
        "feishu_complete_task": feishu_complete_task,
    }

    return [(d["name"], handlers[d["name"]], d) for d in TOOL_DEFS]
