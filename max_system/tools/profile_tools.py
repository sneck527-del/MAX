"""设计师Profile工具：对话式自定义公司信息"""

import json
import logging

from max_system.config.profile import ProfileManager, KEY_ALIASES, resolve_key

logger = logging.getLogger(__name__)

_profile_mgr: ProfileManager | None = None


async def profile_get(args: dict) -> dict:
    if _profile_mgr is None:
        return {"content": [{"type": "text", "text": "Profile系统未初始化"}]}

    key = args.get("key", "")
    if key:
        key = resolve_key(key)
        value = await _profile_mgr.get(key)
        if value:
            return {"content": [{"type": "text", "text": f"{key}: {value}"}]}
        return {"content": [{"type": "text", "text": f"未找到配置项: {key}"}]}

    profile = await _profile_mgr.get_all()
    lines = []
    for k, v in profile.items():
        if v:
            lines.append(f"- {k}: {v}")
    text = "\n".join(lines) if lines else "Profile为空，尚未配置任何公司信息"
    return {"content": [{"type": "text", "text": text}]}


async def profile_update(args: dict) -> dict:
    if _profile_mgr is None:
        return {"content": [{"type": "text", "text": "Profile系统未初始化"}]}

    updates = args.get("updates", {})
    if updates:
        updates = {resolve_key(k): v for k, v in updates.items()}
    else:
        key = resolve_key(args.get("key", ""))
        value = args.get("value", "")
        if not key:
            return {"content": [{"type": "text", "text": "请指定要修改的配置项"}]}
        updates = {key: value}

    await _profile_mgr.set_many(updates)
    summary = ", ".join(f"{k}={v}" for k, v in updates.items())
    logger.info("Profile更新: %s", summary)
    return {"content": [{"type": "text", "text": f"已更新: {summary}"}]}


async def profile_reset(args: dict) -> dict:
    if _profile_mgr is None:
        return {"content": [{"type": "text", "text": "Profile系统未初始化"}]}

    await _profile_mgr.reset()
    return {"content": [{"type": "text", "text": "Profile已重置为默认值"}]}


_KEY_HELP = (
    "可用配置项（中文/英文均可）: "
    "公司名称/company_name, 公司口号/company_tagline, 设计风格/design_style, "
    "目标客群/target_client, 城市/city, 服务类型/service_types, "
    "价格区间/price_range, 质保月数/warranty_months, 付款节点/payment_stages, "
    "品牌调性/brand_tone, 禁用词/forbidden_words, 自媒体平台/media_platforms, "
    "管理费率/management_fee_rate, 税率/tax_rate, "
    "垃圾清运费/garbage_fee, 成品保护费/protection_fee"
)

TOOL_DEFS = [
    {
        "name": "profile_get",
        "description": "读取设计师的公司信息配置。不传key则返回所有配置项。用于了解当前公司的名称、风格、客群、品牌调性等信息。",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": _KEY_HELP,
                },
            },
            "required": [],
        },
    },
    {
        "name": "profile_update",
        "description": "修改设计师的公司信息配置。设计师说'把我们公司名改成XX'或'品牌调性调整为XX'时使用。支持中英文key。",
        "parameters": {
            "type": "object",
            "properties": {
                "updates": {
                    "type": "object",
                    "description": "要修改的配置项，key-value形式。key支持中文，如{\"公司名称\": \"XX设计\", \"设计风格\": \"极简\"}",
                },
                "key": {
                    "type": "string",
                    "description": f"单个配置项名称（与updates二选一）。{_KEY_HELP}",
                },
                "value": {
                    "type": "string",
                    "description": "单个配置项的值（与key配对使用）",
                },
            },
            "required": [],
        },
    },
    {
        "name": "profile_reset",
        "description": "重置所有公司信息配置为默认值。设计师说'重置配置'或'恢复默认'时使用。",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


def register_tools(settings):
    handlers = {
        "profile_get": profile_get,
        "profile_update": profile_update,
        "profile_reset": profile_reset,
    }
    return [(d["name"], handlers[d["name"]], d) for d in TOOL_DEFS]


def set_profile_manager(mgr: ProfileManager) -> None:
    global _profile_mgr
    _profile_mgr = mgr


def get_profile_manager() -> ProfileManager | None:
    return _profile_mgr
