"""任务状态查询路由"""

from fastapi import APIRouter

from max_system.audit.store import AuditStore

router = APIRouter()

_audit_store: AuditStore | None = None


def set_audit_store(store: AuditStore) -> None:
    global _audit_store
    _audit_store = store


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """查询任务执行状态"""
    if not _audit_store:
        return {"status": "error", "message": "审计存储未初始化"}

    records = await _audit_store.query(session_id=task_id, limit=50)
    return {"task_id": task_id, "audit_records": records}
