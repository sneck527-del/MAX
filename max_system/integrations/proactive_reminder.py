"""主动提醒引擎：节点到期提醒、每日待办、新线索分析

在系统启动时注册周期性任务，通过飞书主动推送提醒。
"""

import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def _load_construction_db() -> dict:
    """读取施工进度数据库"""
    import json as _json
    from pathlib import Path
    p = Path(__file__).resolve().parent.parent.parent / "data" / "construction" / "schedules_db.json"
    if p.exists():
        try:
            return _json.loads(p.read_text("utf-8"))
        except (_json.JSONDecodeError, OSError):
            pass
    return {}


def _load_clients_db() -> dict:
    """读取客户数据库（同步版本，供 scheduler 回调使用）"""
    try:
        from max_system.tools.clientmgr_tools import _get_clients_db, _load_from_bitable
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                fut = asyncio.run_coroutine_threadsafe(_load_from_bitable(), loop)
                fut.result(timeout=10)
        except RuntimeError:
            pass
        return _get_clients_db()
    except Exception as e:
        logger.warning("读取客户数据库失败: %s", e)
        return {}


def check_upcoming_deadlines(days_ahead: int = 1) -> list[dict]:
    """检查所有施工进度中未来 days_ahead 天内到期的节点

    Returns:
        [{client_name, milestone_name, end_date, project_label, days_left}, ...]
    """
    db = _load_construction_db()
    today = datetime.now().date()
    reminders = []

    for client_name, schedule in db.items():
        milestones = schedule.get("milestones", [])
        for m in milestones:
            if m["status"] == "已完成":
                continue
            end_str = m.get("end_date", "")
            if not end_str:
                continue
            try:
                end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
            except ValueError:
                continue

            days_left = (end_date - today).days
            if 0 <= days_left <= days_ahead:
                reminders.append({
                    "client_name": client_name,
                    "milestone_name": m["name"],
                    "plan_date": m.get("plan_date", ""),
                    "end_date": end_str,
                    "project_label": schedule.get("label", ""),
                    "days_left": days_left,
                    "tasks": m.get("tasks", []),
                    "workers": m.get("workers", []),
                })
            elif days_left < 0:
                # 已延期
                reminders.append({
                    "client_name": client_name,
                    "milestone_name": m["name"],
                    "plan_date": m.get("plan_date", ""),
                    "end_date": end_str,
                    "project_label": schedule.get("label", ""),
                    "days_left": days_left,
                    "tasks": m.get("tasks", []),
                    "workers": m.get("workers", []),
                    "overdue": True,
                })

    return reminders


def generate_deadline_text(reminders: list[dict]) -> str:
    """将到期提醒列表格式化为飞书消息文本"""
    if not reminders:
        return ""

    upcoming = [r for r in reminders if r.get("days_left", 0) >= 0 and not r.get("overdue")]
    overdue = [r for r in reminders if r.get("overdue") or r.get("days_left", 0) < 0]

    lines = []
    if overdue:
        lines.append("🚨 **已延期节点**")
        for r in overdue:
            days = abs(r["days_left"])
            lines.append(f"  ‣ {r['client_name']} · {r['milestone_name']}（已延期 {days} 天）")
        lines.append("")

    if upcoming:
        lines.append("⏰ **今日/明日到期**")
        for r in upcoming:
            dl = r["days_left"]
            when = "今天" if dl == 0 else "明天" if dl == 1 else f"还有 {dl} 天"
            lines.append(f"  ‣ {r['client_name']} · {r['milestone_name']}（{when}到期）")
        lines.append("")

    return "\n".join(lines)


def generate_morning_summary() -> str:
    """生成每日早报摘要"""
    db = _load_construction_db()
    clients = _load_clients_db()
    today = datetime.now().date()

    total_projects = len(db)
    total_clients = len(clients)
    overdue_count = 0
    active_today = []
    progress_lines = []

    for client_name, schedule in db.items():
        milestones = schedule.get("milestones", [])
        total = len(milestones)
        done = sum(1 for m in milestones if m["status"] == "已完成")
        pct = round(done / total * 100) if total else 0
        progress_lines.append(f"  ‣ {client_name}：{done}/{total}（{pct}%）")

        for m in milestones:
            if m["status"] == "已完成":
                continue
            end_str = m.get("end_date", "")
            if end_str:
                try:
                    end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
                    if end_date == today:
                        active_today.append(f"  ‣ {client_name} · {m['name']}（今天到期）")
                    elif end_date < today:
                        overdue_count += 1
                except ValueError:
                    pass

    lines = [
        f"🌅 **早安，今日工作概览**",
        f"日期：{today.strftime('%Y-%m-%d')} 星期{today.weekday() + 1}",
        "",
        f"📊 当前共 {total_projects} 个在建项目，{total_clients} 位客户",
        "",
    ]

    if active_today:
        lines.append("**⚡ 今日待办**")
        lines.extend(active_today)
        lines.append("")

    if overdue_count > 0:
        lines.append(f"**🚨 {overdue_count} 个节点已延期** 建议尽快安排")
        lines.append("")

    lines.append("**📈 各项目进度**")
    lines.extend(progress_lines)

    return "\n".join(lines)


def analyze_new_lead(client_data: dict) -> str | None:
    """分析新线索，生成跟进建议卡片"""
    name = client_data.get("name", "")
    if not name:
        return None

    budget = client_data.get("budget", "")
    area = client_data.get("area", "")
    style = client_data.get("preferences", {}).get("style", "") or client_data.get("style", "")
    source = client_data.get("source", "") or client_data.get("渠道", "")
    status = client_data.get("status", "")

    lines = [
        f"📌 **新线索分析：{name}**",
    ]
    if source:
        lines.append(f"  来源：{source}")
    if budget:
        lines.append(f"  预算：{budget}")
    if area:
        lines.append(f"  面积：{area}")
    if style:
        lines.append(f"  风格偏好：{style}")

    # 简单评分
    score = 0
    hints = []
    try:
        budget_num = float(str(budget).replace("万", "").replace("w", "").replace("W", ""))
        if budget_num >= 30:
            score += 2
            hints.append("预算充足")
        elif budget_num >= 15:
            score += 1
        else:
            hints.append("预算偏低")
    except (ValueError, AttributeError):
        pass

    if style:
        score += 1
    if area:
        try:
            area_num = float(str(area).replace("㎡", "").replace("平", ""))
            if area_num > 120:
                score += 1
        except (ValueError, AttributeError):
            pass

    if status == "高意向" or "意向" in status:
        score += 2
        hints.append("高意向客户")

    level = "🔥 优质" if score >= 4 else "💡 普通" if score >= 2 else "👀 观察"
    lines.append(f"\n  评分：{'★' * min(score, 5)}{'☆' * (5 - min(score, 5))}")
    lines.append(f"  判断：{level}")
    if hints:
        lines.append(f"  特征：{'、'.join(hints)}")

    lines.append(f"\n💬 建议及时跟进，了解详细需求")

    return "\n".join(lines)
