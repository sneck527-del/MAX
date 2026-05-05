"""飞书API客户端：封装lark-oapi SDK调用"""

import json
import logging
from typing import Any

import httpx

from max_system.config.settings import MaxSettings
from max_system.integrations.feishu.field_mapping import FieldMappingCache
from max_system.utils.retry import async_retry

logger = logging.getLogger(__name__)


class FeishuApiClient:
    """飞书开放平台API封装

    提供消息发送、多维表格读写、审批流、日历等功能。
    使用lark-oapi SDK进行认证和API调用。
    """

    def __init__(self, settings: MaxSettings):
        self.settings = settings
        self._tenant_token: str = ""
        self._token_expires: float = 0
        self._http = httpx.AsyncClient(timeout=30.0)
        self._field_cache = FieldMappingCache(ttl_seconds=300)

    async def close(self) -> None:
        await self._http.aclose()

    # ============ 认证 ============

    async def _get_tenant_token(self) -> str:
        """获取飞书tenant_access_token"""
        import time
        if self._tenant_token and time.time() < self._token_expires:
            return self._tenant_token

        resp = await self._http.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={
                "app_id": self.settings.feishu_app_id,
                "app_secret": self.settings.feishu_app_secret,
            },
        )
        data = resp.json()
        self._tenant_token = data["tenant_access_token"]
        self._token_expires = time.time() + data.get("expire", 7200) - 300
        return self._tenant_token

    async def _headers(self) -> dict[str, str]:
        token = await self._get_tenant_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    # ============ 消息 ============

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(httpx.HTTPError,))
    async def send_message(
        self,
        chat_id: str,
        text: str,
        msg_type: str = "text",
    ) -> dict:
        """发送消息到飞书聊天"""
        headers = await self._headers()

        if msg_type == "text":
            content = f'{{"text":"{self._escape_json(text)}"}}'
        else:
            content = text  # interactive card等直接传入

        resp = await self._http.post(
            "https://open.feishu.cn/open-apis/im/v1/messages",
            params={"receive_id_type": "chat_id"},
            headers=headers,
            json={
                "receive_id": chat_id,
                "msg_type": msg_type,
                "content": content,
            },
        )
        resp.raise_for_status()
        return resp.json()

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(httpx.HTTPError,))
    async def reply_message(self, message_id: str, text: str) -> dict:
        """回复消息"""
        headers = await self._headers()
        resp = await self._http.post(
            f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply",
            headers=headers,
            json={
                "msg_type": "text",
                "content": f'{{"text":"{self._escape_json(text)}"}}',
            },
        )
        resp.raise_for_status()
        return resp.json()

    # ============ 多维表格 - 结构管理 ============

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(httpx.HTTPError,))
    async def create_bitable_table(
        self,
        table_name: str,
    ) -> dict:
        """创建多维表格（在指定Base中新建表）"""
        headers = await self._headers()
        resp = await self._http.post(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.settings.feishu_bitable_app_token}/tables",
            headers=headers,
            json={"table": {"name": table_name}},
        )
        resp.raise_for_status()
        return resp.json()

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(httpx.HTTPError,))
    async def batch_create_fields(
        self,
        table_id: str,
        fields: list[dict],
    ) -> dict:
        """批量创建字段（逐字段创建，因batch_create端点不可用）

        fields = [
            {"field_name": "字段名", "type": 1, "property": {}},
        ]
        type: 1=文本 2=数字 5=日期 7=电话 10=单选 11=多选
        """
        headers = await self._headers()
        results = []
        for field in fields:
            try:
                resp = await self._http.post(
                    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.settings.feishu_bitable_app_token}/tables/{table_id}/fields",
                    headers=headers,
                    json=field,
                )
                resp.raise_for_status()
                data = resp.json()
                if data.get("code") == 0:
                    results.append(data["data"]["field"])
            except Exception as e:
                logger.warning("创建字段 '%s' 失败: %s", field.get("field_name"), e)
        return {"code": 0, "data": {"fields": results}}

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(httpx.HTTPError,))
    async def list_bitable_tables(self) -> list[dict]:
        """获取多维表格中所有表列表"""
        headers = await self._headers()
        resp = await self._http.get(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.settings.feishu_bitable_app_token}/tables",
            headers=headers,
            params={"page_size": 100},
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {}).get("items", [])

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(httpx.HTTPError,))
    async def list_bitable_fields(self, table_id: str) -> list[dict]:
        """获取指定表的字段列表"""
        headers = await self._headers()
        resp = await self._http.get(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.settings.feishu_bitable_app_token}/tables/{table_id}/fields",
            headers=headers,
            params={"page_size": 100},
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {}).get("items", [])

    # ============ 多维表格 - 数据读写 ============

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(httpx.HTTPError,))
    async def read_bitable(
        self,
        table_id: str,
        filter_expr: str = "",
        page_size: int = 100,
        page_token: str = "",
    ) -> dict:
        """读取多维表格记录"""
        headers = await self._headers()
        params: dict[str, Any] = {"page_size": page_size}
        if filter_expr:
            params["filter"] = filter_expr
        if page_token:
            params["page_token"] = page_token

        resp = await self._http.get(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.settings.feishu_bitable_app_token}/tables/{table_id}/records",
            headers=headers,
            params=params,
        )
        resp.raise_for_status()
        return resp.json()

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(httpx.HTTPError,))
    async def write_bitable(
        self,
        table_id: str,
        records: list[dict],
    ) -> dict:
        """写入多维表格记录"""
        headers = await self._headers()
        resp = await self._http.post(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.settings.feishu_bitable_app_token}/tables/{table_id}/records/batch_create",
            headers=headers,
            json={"records": [{"fields": r} for r in records]},
        )
        resp.raise_for_status()
        return resp.json()

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(httpx.HTTPError,))
    async def update_bitable_record(
        self,
        table_id: str,
        record_id: str,
        fields: dict,
    ) -> dict:
        """更新多维表格中单条记录"""
        headers = await self._headers()
        resp = await self._http.put(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.settings.feishu_bitable_app_token}"
            f"/tables/{table_id}/records/{record_id}",
            headers=headers,
            json={"fields": fields},
        )
        resp.raise_for_status()
        return resp.json()

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(httpx.HTTPError,))
    async def update_bitable_field(
        self,
        table_id: str,
        field_id: str,
        field_name: str | None = None,
        field_type: int | None = None,
        property: dict | None = None,
    ) -> dict:
        """更新多维表格字段属性（如重命名、改类型）"""
        headers = await self._headers()
        body: dict = {}
        if field_name is not None:
            body["field_name"] = field_name
        if field_type is not None:
            body["type"] = field_type
        if property is not None:
            body["property"] = property
        resp = await self._http.patch(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.settings.feishu_bitable_app_token}"
            f"/tables/{table_id}/fields/{field_id}",
            headers=headers,
            json=body,
        )
        resp.raise_for_status()
        return resp.json()

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(httpx.HTTPError,))
    async def delete_bitable_field(
        self,
        table_id: str,
        field_id: str,
    ) -> dict:
        """删除多维表格字段（列）"""
        headers = await self._headers()
        resp = await self._http.delete(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.settings.feishu_bitable_app_token}"
            f"/tables/{table_id}/fields/{field_id}",
            headers=headers,
        )
        resp.raise_for_status()
        return resp.json()

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(httpx.HTTPError,))
    async def delete_bitable_record(
        self,
        table_id: str,
        record_id: str,
    ) -> dict:
        """删除多维表格中单条记录"""
        headers = await self._headers()
        resp = await self._http.delete(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.settings.feishu_bitable_app_token}"
            f"/tables/{table_id}/records/{record_id}",
            headers=headers,
        )
        resp.raise_for_status()
        return resp.json()

    async def get_field_mapping(self, table_id: str) -> dict[str, str]:
        """获取 field_id → field_name 映射（走缓存）"""
        cached = self._field_cache.get(table_id)
        if cached is not None:
            return cached
        fields = await self.list_bitable_fields(table_id)
        mapping = {
            f["field_id"]: f["field_name"]
            for f in fields if "field_id" in f and "field_name" in f
        }
        self._field_cache.set(table_id, mapping)
        return mapping

    # ============ 消息操作 ============

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(httpx.HTTPError,))
    async def delete_message(self, message_id: str) -> dict:
        """删除飞书消息"""
        headers = await self._headers()
        resp = await self._http.delete(
            f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}",
            headers=headers,
        )
        resp.raise_for_status()
        return resp.json()

    # ============ 审批 ============

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(httpx.HTTPError,))
    async def create_approval(
        self,
        approval_code: str,
        user_id: str,
        form: str,
    ) -> dict:
        """创建审批实例"""
        headers = await self._headers()
        resp = await self._http.post(
            "https://open.feishu.cn/open-apis/approval/v4/instances",
            headers=headers,
            json={
                "approval_code": approval_code,
                "user_id": user_id,
                "form": form,
            },
        )
        resp.raise_for_status()
        return resp.json()

    # ============ 日历 ============

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(httpx.HTTPError,))
    async def create_calendar_event(
        self,
        calendar_id: str,
        summary: str,
        start_time: str,
        end_time: str,
        description: str = "",
    ) -> dict:
        """创建日历事件"""
        headers = await self._headers()
        resp = await self._http.post(
            f"https://open.feishu.cn/open-apis/calendar/v4/calendars/{calendar_id}/events",
            headers=headers,
            json={
                "summary": summary,
                "description": description,
                "start_time": {"timestamp": start_time},
                "end_time": {"timestamp": end_time},
            },
        )
        resp.raise_for_status()
        return resp.json()

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(httpx.HTTPError,))
    async def list_calendar_events(
        self,
        calendar_id: str,
        start_time: str = "",
        end_time: str = "",
        page_size: int = 50,
        page_token: str = "",
    ) -> dict:
        """查询日历事件"""
        headers = await self._headers()
        params: dict[str, Any] = {"page_size": page_size}
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if page_token:
            params["page_token"] = page_token
        resp = await self._http.get(
            f"https://open.feishu.cn/open-apis/calendar/v4/calendars/{calendar_id}/events",
            headers=headers,
            params=params,
        )
        resp.raise_for_status()
        return resp.json()

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(httpx.HTTPError,))
    async def delete_calendar_event(self, calendar_id: str, event_id: str) -> dict:
        """删除日历事件"""
        headers = await self._headers()
        resp = await self._http.delete(
            f"https://open.feishu.cn/open-apis/calendar/v4/calendars/{calendar_id}/events/{event_id}",
            headers=headers,
        )
        resp.raise_for_status()
        return resp.json()

    # ============ 任务 ============

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(httpx.HTTPError,))
    async def create_task(
        self,
        summary: str,
        description: str = "",
        due_time: str = "",
        reminders: list[dict] | None = None,
    ) -> dict:
        """创建飞书任务（待办事项）

        reminders: [{"relative_fire_minute": 30}]  提前30分钟提醒
        """
        headers = await self._headers()
        body: dict[str, Any] = {"summary": summary, "description": description}
        if due_time:
            body["due"] = {"time": due_time}
        if reminders:
            body["reminders"] = reminders
        resp = await self._http.post(
            "https://open.feishu.cn/open-apis/task/v1/tasks",
            headers=headers,
            json=body,
        )
        resp.raise_for_status()
        return resp.json()

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(httpx.HTTPError,))
    async def list_tasks(
        self,
        start_time: str = "",
        end_time: str = "",
        status: str = "",
        page_size: int = 50,
        page_token: str = "",
    ) -> dict:
        """查询飞书任务列表"""
        headers = await self._headers()
        params: dict[str, Any] = {"page_size": page_size}
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if status:
            params["status"] = status
        if page_token:
            params["page_token"] = page_token
        resp = await self._http.get(
            "https://open.feishu.cn/open-apis/task/v1/tasks",
            headers=headers,
            params=params,
        )
        resp.raise_for_status()
        return resp.json()

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(httpx.HTTPError,))
    async def complete_task(self, task_id: str) -> dict:
        """完成任务"""
        headers = await self._headers()
        resp = await self._http.patch(
            f"https://open.feishu.cn/open-apis/task/v1/tasks/{task_id}/complete",
            headers=headers,
            json={},
        )
        resp.raise_for_status()
        return resp.json()

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(httpx.HTTPError,))
    async def add_task_reminder(self, task_id: str, relative_fire_minute: int = 30) -> dict:
        """给任务添加提醒"""
        headers = await self._headers()
        resp = await self._http.post(
            f"https://open.feishu.cn/open-apis/task/v1/tasks/{task_id}/reminders",
            headers=headers,
            content=json.dumps({"relative_fire_minute": relative_fire_minute}).encode("utf-8"),
        )
        resp.raise_for_status()
        return resp.json()

    # ============ 工具方法 ============

    @staticmethod
    def _escape_json(text: str) -> str:
        """转义JSON字符串中的特殊字符"""
        return (
            text.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
        )
