"""飞书MCP工具：消息、多维表格、审批、日历"""

import json
import logging
from typing import Callable

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
    result = await client.send_message(
        chat_id=args["chat_id"],
        text=args["text"],
        msg_type=args.get("msg_type", "text"),
    )
    return {"content": [{"type": "text", "text": f"消息已发送到聊天 {args['chat_id']}"}]}


async def feishu_read_bitable(args: dict) -> dict:
    client = _get_api_client()
    table_id = args["table_id"]

    # 获取字段名映射（field_id → 中文field_name）
    field_map = await client.get_field_mapping(table_id)

    result = await client.read_bitable(
        table_id=table_id,
        filter_expr=args.get("filter", ""),
        page_size=args.get("page_size", 100),
    )
    records = result.get("data", {}).get("items", [])

    # 将 field_id 替换为中文 field_name
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
    result = await client.write_bitable(table_id=args["table_id"], records=records)
    return {"content": [{"type": "text", "text": f"成功写入 {len(records)} 条记录"}]}


async def feishu_create_approval(args: dict) -> dict:
    client = _get_api_client()
    result = await client.create_approval(
        approval_code=args["approval_code"],
        user_id=args["user_id"],
        form=args["form"],
    )
    instance_code = result.get("data", {}).get("instance_code", "")
    return {"content": [{"type": "text", "text": f"审批已创建，实例编号: {instance_code}"}]}


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
    return {"content": [{"type": "text", "text": f"日历事件已创建，ID: {event_id}"}]}


# ============ 工具定义 ============

TOOL_DEFS = [
    {
        "name": "feishu_send_message",
        "description": "发送消息到飞书聊天。支持文本和卡片消息。",
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
        "description": "读取飞书多维表格记录。支持过滤和分页。",
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
        "description": "写入飞书多维表格记录。records为JSON字符串。",
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
        "description": "创建飞书日历事件。",
        "parameters": {
            "type": "object",
            "properties": {
                "calendar_id": {"type": "string", "description": "日历ID"},
                "summary": {"type": "string", "description": "事件标题"},
                "start_time": {"type": "string", "description": "开始时间戳"},
                "end_time": {"type": "string", "description": "结束时间戳"},
                "description": {"type": "string", "description": "事件描述"},
            },
            "required": ["calendar_id", "summary", "start_time", "end_time"],
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
    }

    return [(d["name"], handlers[d["name"]], d) for d in TOOL_DEFS]
