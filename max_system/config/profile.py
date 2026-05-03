"""设计师Profile管理 — 对话式自定义，SQLite存储"""

import logging
from datetime import datetime
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

# 中文→英文键名映射
KEY_ALIASES: dict[str, str] = {
    "公司名称": "company_name",
    "公司名": "company_name",
    "公司口号": "company_tagline",
    "口号": "company_tagline",
    "设计风格": "design_style",
    "风格": "design_style",
    "目标客群": "target_client",
    "客群": "target_client",
    "城市": "city",
    "所在城市": "city",
    "服务类型": "service_types",
    "价格区间": "price_range",
    "质保月数": "warranty_months",
    "质保期": "warranty_months",
    "付款节点": "payment_stages",
    "品牌调性": "brand_tone",
    "调性": "brand_tone",
    "禁用词": "forbidden_words",
    "自媒体平台": "media_platforms",
    "平台": "media_platforms",
    "自动跟进天数": "auto_followup_days",
    "回访节点": "visit_schedule_days",
    "质保提醒天数": "warranty_remind_before_days",
    # 报价汇总费率
    "管理费率": "management_fee_rate",
    "管理费比例": "management_fee_rate",
    "税率": "tax_rate",
    "税金比例": "tax_rate",
    "垃圾清运费": "garbage_fee",
    "成品保护费": "protection_fee",
}


def resolve_key(key: str) -> str:
    """将中文key转为英文key，英文key原样返回"""
    return KEY_ALIASES.get(key, key)


# 默认profile模板（空白默认值，首次引导时由设计师自己设定）
DEFAULTS: dict[str, str] = {
    "company_name": "",
    "company_tagline": "",
    "design_style": "",
    "target_client": "",
    "city": "",
    "service_types": "",
    "price_range": "",
    "warranty_months": "",
    "payment_stages": "",
    "brand_tone": "",
    "forbidden_words": "",
    "media_platforms": "",
    "auto_followup_days": "",
    "visit_schedule_days": "",
    "warranty_remind_before_days": "",
    # 报价汇总费率（行业通用默认值）
    "management_fee_rate": "8",
    "tax_rate": "3.41",
    "garbage_fee": "800",
    "protection_fee": "500",
}


class ProfileManager:
    """设计师Profile管理器，SQLite持久化"""

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(str(self._db_path))
        await self._db.execute(
            "CREATE TABLE IF NOT EXISTS designer_profile "
            "(key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT)"
        )
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    def _ensure_db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("ProfileManager未初始化，请先调用initialize()")
        return self._db

    async def get(self, key: str) -> str | None:
        db = self._ensure_db()
        async with db.execute(
            "SELECT value FROM designer_profile WHERE key = ?", (key,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else DEFAULTS.get(key, "")

    async def get_all(self) -> dict[str, str]:
        db = self._ensure_db()
        result = dict(DEFAULTS)
        async with db.execute("SELECT key, value FROM designer_profile") as cur:
            async for row in cur:
                result[row[0]] = row[1]
        return result

    async def set(self, key: str, value: str) -> None:
        db = self._ensure_db()
        now = datetime.now().isoformat()
        await db.execute(
            "INSERT OR REPLACE INTO designer_profile (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, now),
        )
        await db.commit()

    async def set_many(self, updates: dict[str, str]) -> None:
        db = self._ensure_db()
        now = datetime.now().isoformat()
        await db.executemany(
            "INSERT OR REPLACE INTO designer_profile (key, value, updated_at) VALUES (?, ?, ?)",
            [(k, v, now) for k, v in updates.items()],
        )
        await db.commit()

    async def reset(self) -> None:
        db = self._ensure_db()
        await db.execute("DELETE FROM designer_profile")
        await db.commit()

    async def is_empty(self) -> bool:
        """检查是否为首次使用（无任何自定义profile）"""
        db = self._ensure_db()
        async with db.execute("SELECT COUNT(*) FROM designer_profile") as cur:
            row = await cur.fetchone()
            return row[0] == 0

    def build_prompt_section(self, profile: dict[str, str]) -> str:
        """根据profile生成提示词注入段"""
        lines = ["## 公司信息"]
        if profile.get("company_name"):
            lines.append(f"你是{profile['company_name']}的设计师助手。")
        if profile.get("company_tagline"):
            lines.append(f"公司口号：{profile['company_tagline']}")
        if profile.get("design_style"):
            lines.append(f"主打风格：{profile['design_style']}")
        if profile.get("target_client"):
            lines.append(f"目标客群：{profile['target_client']}")
        if profile.get("city"):
            lines.append(f"所在城市：{profile['city']}")
        if profile.get("service_types"):
            lines.append(f"服务类型：{profile['service_types']}")
        if profile.get("price_range"):
            lines.append(f"价格区间：{profile['price_range']}")
        if profile.get("payment_stages"):
            lines.append(f"付款节点：{profile['payment_stages']}")
        if profile.get("warranty_months"):
            lines.append(f"质保期：{profile['warranty_months']}个月")
        if profile.get("brand_tone"):
            lines.append(f"品牌调性：{profile['brand_tone']}")
        if profile.get("forbidden_words"):
            lines.append(f"禁用词：{profile['forbidden_words']}")
        if profile.get("media_platforms"):
            lines.append(f"自媒体平台：{profile['media_platforms']}")
        if profile.get("auto_followup_days"):
            lines.append(f"自动跟进天数：{profile['auto_followup_days']}天")
        if profile.get("visit_schedule_days"):
            lines.append(f"竣工回访节点：竣工后{profile['visit_schedule_days']}天")
        if profile.get("warranty_remind_before_days"):
            lines.append(f"质保到期提前{profile['warranty_remind_before_days']}天提醒")

        if len(lines) == 1:
            return ""
        return "\n".join(lines)
