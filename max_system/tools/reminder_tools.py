"""主动提醒工具：检查客户跟进状态，生成智能提醒"""

import json
import logging
from datetime import datetime, timedelta

from max_system.config.settings import MaxSettings
from max_system.tools.clientmgr_tools import _get_clients_db, _load_from_bitable

logger = logging.getLogger(__name__)


async def _check_proactive_reminders() -> dict:
    """检查所有客户，生成主动提醒列表。

    检查项：
    1. 过期未跟进：last_contact > 7天前
    2. 竣工未回访：status含"竣工" 且 completed_at > 90天
    3. 签约未开工：status="已签约" 或 intent="已签约" 且 > 30天

    Returns:
        dict with "reminders" list and "count"
    """
    await _load_from_bitable()

    now = datetime.now()
    reminders = []
    clients_db = _get_clients_db()

    for client_id, client in clients_db.items():
        name = client.get("name", "未知")

        # 1. 过期未跟进检查
        last_contact_str = client.get("last_contact") or client.get("updated_at") or client.get("created_at")
        if last_contact_str:
            try:
                last_contact = datetime.fromisoformat(last_contact_str.replace("Z", "+00:00").split("+")[0].split(".")[0])
                days_since_contact = (now - last_contact.replace(tzinfo=None)).days
                if days_since_contact > 7:
                    reminders.append({
                        "type": "stale_client",
                        "client_id": client_id,
                        "client_name": name,
                        "message": f"{name}已{days_since_contact}天未跟进，建议联系",
                        "days": days_since_contact,
                    })
            except (ValueError, TypeError):
                pass

        # 2. 竣工后回访检查
        status = client.get("status", "")
        if "竣工" in status:
            completed_at_str = client.get("completed_at")
            if completed_at_str:
                try:
                    completed_at = datetime.fromisoformat(completed_at_str.replace("Z", "+00:00").split("+")[0].split(".")[0])
                    days_since_complete = (now - completed_at.replace(tzinfo=None)).days
                    if days_since_complete > 90:
                        months = days_since_complete // 30
                        reminders.append({
                            "type": "post_completion",
                            "client_id": client_id,
                            "client_name": name,
                            "message": f"{name}项目竣工{months}个月，建议回访",
                            "days": days_since_complete,
                        })
                except (ValueError, TypeError):
                    pass

        # 3. 签约未开工检查
        if status == "已签约" or client.get("intent") == "已签约":
            sign_time_str = client.get("updated_at") or client.get("created_at")
            if sign_time_str:
                try:
                    sign_time = datetime.fromisoformat(sign_time_str.replace("Z", "+00:00").split("+")[0].split(".")[0])
                    days_since_sign = (now - sign_time.replace(tzinfo=None)).days
                    if days_since_sign > 30:
                        reminders.append({
                            "type": "contract_no_start",
                            "client_id": client_id,
                            "client_name": name,
                            "message": f"{name}合同已签{days_since_sign}天未开工",
                            "days": days_since_sign,
                        })
                except (ValueError, TypeError):
                    pass

    return {"reminders": reminders, "count": len(reminders)}


async def reminder_check(args: dict) -> dict:
    """手动触发客户提醒检查，返回所有待处理提醒。"""
    result = await _check_proactive_reminders()

    if result["count"] == 0:
        return {"content": [{"type": "text", "text": json.dumps({
            "message": "当前没有待处理的客户提醒",
            "reminders": [],
            "count": 0,
        }, ensure_ascii=False)}]}

    return {"content": [{"type": "text", "text": json.dumps({
        "message": f"发现 {result['count']} 条待处理提醒",
        "reminders": result["reminders"],
        "count": result["count"],
    }, ensure_ascii=False)}]}


TOOL_DEFS = [
    {
        "name": "reminder_check",
        "description": "检查所有客户状态，生成主动提醒列表。包括：过期未跟进（>7天）、竣工未回访（>90天）、签约未开工（>30天）。",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


def register_tools(settings: MaxSettings):
    handlers = {
        "reminder_check": reminder_check,
    }
    return [(d["name"], handlers[d["name"]], d) for d in TOOL_DEFS]
