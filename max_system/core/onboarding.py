"""初始化引导流程：管理多步骤飞书卡片式引导

Onboarding flow:
   Card 1 (step=1): 公司名 + 设计风格 + 城市
   Card 2 (step=2): 客户群 + 服务类型 + 品牌调性 + 价格区间
   Card 3 (step=3): 确认摘要 → finish

All state is derived from the card action value; no persistent state needed.
ProfileManager.set_many() stores responses after each step.
"""

import logging
from typing import Any

from max_system.integrations.feishu import card_builder as cb

logger = logging.getLogger(__name__)

# ============ 表单字段名 → Profile Key 映射 ============

_FORM_TO_PROFILE_KEY = {
    "company_name": "company_name",
    "design_style": "design_style",
    "city": "city",
    "target_client": "target_client",
    "service_types": "service_types",
    "brand_tone": "brand_tone",
    "price_range": "price_range",
}

# ============ 多选字段（值可能是 list，需要 join） ============

_MULTI_SELECT_FIELDS = {"target_client", "service_types"}


def _extract_profile_updates(form_value: dict) -> dict[str, str]:
    """从卡片 form_value 中提取 Profile 更新字段。

    form_value 的 key 是卡片元素 name（英文），
    多选字段的值可能是 list，需要用逗号拼接。
    """
    updates = {}
    for form_key, profile_key in _FORM_TO_PROFILE_KEY.items():
        if form_key in form_value:
            val = form_value[form_key]
            if form_key in _MULTI_SELECT_FIELDS and isinstance(val, list):
                val = "、".join(val)  # 中文顿号分隔
            if val:
                updates[profile_key] = str(val).strip()
    return updates


def _build_profile_summary(updates: dict[str, str]) -> dict[str, str]:
    """构建展示用的中文摘要"""
    label_map = {
        "company_name": "公司名称",
        "design_style": "设计风格",
        "city": "所在城市",
        "target_client": "目标客户",
        "service_types": "服务类型",
        "brand_tone": "品牌调性",
        "price_range": "价格区间",
    }
    return {label_map.get(k, k): v for k, v in updates.items()}


async def process_card_action(
    action_value: dict[str, str],
    form_value: dict[str, Any],
    profile_mgr,
) -> tuple[dict | None, bool]:
    """处理卡片动作，返回 (next_card_dict, is_finished)。

    Args:
        action_value: 按钮的 value 字段，含 action/step/card
        form_value: 卡片 form_value，含用户填写的数据
        profile_mgr: ProfileManager 实例

    Returns:
        (next_card, is_finished): next_card 是飞书卡片 JSON dict，
        is_finished=True 表示引导完成。
    """
    step = action_value.get("step", "1")
    current_card = int(action_value.get("card", "0"))

    # 提取并保存 profile 更新
    updates = _extract_profile_updates(form_value)
    if updates:
        try:
            await profile_mgr.set_many(updates)
            logger.info("引导步骤 %s: 已保存 %d 个字段", step, len(updates))
        except Exception as e:
            logger.error("保存 profile 失败: %s", e)
            return cb.build_onboarding_error_card(str(e)), False

    # 步骤路由
    if step == "finish":
        logger.info("引导流程完成")
        return None, True

    target_step = int(step)

    if target_step == 1:
        return cb.build_onboarding_card_1(1), False
    elif target_step == 2:
        return cb.build_onboarding_card_2(2), False
    elif target_step == 3:
        # 汇总已有 profile 数据构建确认卡片
        try:
            all_profile = await profile_mgr.get_all()
        except Exception:
            all_profile = {}
        # 合并刚更新的数据
        all_profile.update(updates)
        profile_summary = _build_profile_summary(all_profile)
        return cb.build_onboarding_card_3(profile_summary), False
    else:
        # 默认回到第一步
        logger.warning("未知的引导步骤: %s，重置到第1步", step)
        return cb.build_onboarding_card_1(1), False


def get_first_card() -> dict:
    """获取引导的第一张卡片（用于首次使用触发）"""
    return cb.build_onboarding_card_1(1)
