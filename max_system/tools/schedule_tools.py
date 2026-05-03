"""定时任务工具：创建/查看/取消提醒"""

import json
import logging

from max_system.core.scheduler import JobStore, MaxScheduler

logger = logging.getLogger(__name__)

_job_store: JobStore | None = None
_scheduler: MaxScheduler | None = None


async def schedule_create(args: dict) -> dict:
    if _job_store is None:
        return {"content": [{"type": "text", "text": "定时任务系统未初始化"}]}

    description = args.get("description", "")
    trigger_time = args.get("trigger_time", "")
    chat_id = args.get("chat_id", "")
    recurrence = args.get("recurrence", "")

    if not description or not trigger_time:
        return {"content": [{"type": "text", "text": "请提供任务描述和触发时间"}]}

    try:
        job_id = await _job_store.add_job(
            description=description,
            trigger_time=trigger_time,
            chat_id=chat_id,
            recurrence=recurrence,
        )
        repeat_info = f"（每{recurrence}重复）" if recurrence else ""
        return {"content": [{"type": "text", "text": f"已创建定时任务: {description}{repeat_info}\n触发时间: {trigger_time}\n任务ID: {job_id}"}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"创建任务失败: {e}"}]}


async def schedule_list(args: dict) -> dict:
    if _job_store is None:
        return {"content": [{"type": "text", "text": "定时任务系统未初始化"}]}

    status = args.get("status", "pending")
    try:
        jobs = await _job_store.list_jobs(status=status)
        if not jobs:
            return {"content": [{"type": "text", "text": "当前没有待执行的定时任务"}]}

        lines = ["定时任务列表："]
        for job in jobs:
            repeat = f" [每{job['recurrence']}]" if job.get("recurrence") else ""
            lines.append(f"  [{job['job_id']}] {job['description']}{repeat} → {job['next_run']}")

        return {"content": [{"type": "text", "text": "\n".join(lines)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"查询任务失败: {e}"}]}


async def schedule_cancel(args: dict) -> dict:
    if _job_store is None:
        return {"content": [{"type": "text", "text": "定时任务系统未初始化"}]}

    job_id = args.get("job_id", "")
    if not job_id:
        return {"content": [{"type": "text", "text": "请提供要取消的任务ID"}]}

    try:
        cancelled = await _job_store.cancel_job(job_id)
        if cancelled:
            return {"content": [{"type": "text", "text": f"已取消任务: {job_id}"}]}
        return {"content": [{"type": "text", "text": f"未找到待执行的任务: {job_id}"}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"取消任务失败: {e}"}]}


TOOL_DEFS = [
    {
        "name": "schedule_create",
        "description": "创建定时提醒任务。设计师说'提醒我XX时候做XX'或'每周X提醒我XX'时使用。trigger_time为ISO格式时间，recurrence为重复规则如7d(每7天)、1w(每周)、1h(每小时)。",
        "parameters": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "任务描述，如'跟进王女士'、'检查施工进度'",
                },
                "trigger_time": {
                    "type": "string",
                    "description": "触发时间，ISO格式如2026-05-10T09:00:00",
                },
                "chat_id": {
                    "type": "string",
                    "description": "飞书聊天ID（用于推送消息，可选）",
                },
                "recurrence": {
                    "type": "string",
                    "description": "重复规则，如7d=每7天，1w=每周，1h=每小时。留空=单次任务",
                },
            },
            "required": ["description", "trigger_time"],
        },
    },
    {
        "name": "schedule_list",
        "description": "查看定时任务列表。设计师说'看看我的提醒'或'有什么待办'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "任务状态筛选: pending/done/cancelled，默认pending",
                },
            },
            "required": [],
        },
    },
    {
        "name": "schedule_cancel",
        "description": "取消定时任务。设计师说'取消XX提醒'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "job_id": {
                    "type": "string",
                    "description": "要取消的任务ID",
                },
            },
            "required": ["job_id"],
        },
    },
]


def register_tools(settings):
    global _job_store, _scheduler

    from max_system.core.scheduler import JobStore, MaxScheduler
    _job_store = JobStore(settings.get_db_path())
    _scheduler = MaxScheduler(_job_store)

    handlers = {
        "schedule_create": schedule_create,
        "schedule_list": schedule_list,
        "schedule_cancel": schedule_cancel,
    }
    return [(d["name"], handlers[d["name"]], d) for d in TOOL_DEFS]


def get_scheduler() -> MaxScheduler | None:
    return _scheduler


def get_job_store() -> JobStore | None:
    return _job_store
