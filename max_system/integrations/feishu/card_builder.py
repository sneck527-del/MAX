"""飞书卡片消息构建器：生成交互式卡片 JSON"""

import json
from typing import Any

# ============ 原子元素 ============


def _plain_text(content: str) -> dict:
    return {"tag": "plain_text", "content": content}


def _lark_md(content: str) -> dict:
    return {"tag": "lark_md", "content": content}


def _div(text: str) -> dict:
    return {"tag": "div", "text": _lark_md(text)}


def _hr() -> dict:
    return {"tag": "hr"}


def _note(text: str) -> dict:
    return {"tag": "note", "elements": [_plain_text(text)]}


def _input_field(name: str, label: str, placeholder: str = "", required: bool = False) -> dict:
    el = {
        "tag": "input",
        "name": name,
        "placeholder": {"tag": "plain_text", "content": placeholder},
    }
    if required:
        el["required"] = True
    return el


def _select_field(name: str, options: list[tuple[str, str]], placeholder: str = "") -> dict:
    opts = [{"value": v, "text": _plain_text(label)} for v, label in options]
    return {
        "tag": "select_static",
        "name": name,
        "placeholder": _plain_text(placeholder),
        "options": opts,
    }


def _multi_select_field(name: str, options: list[tuple[str, str]], placeholder: str = "") -> dict:
    opts = [{"value": v, "text": _plain_text(label)} for v, label in options]
    return {
        "tag": "multi_select_static",
        "name": name,
        "placeholder": _plain_text(placeholder),
        "options": opts,
    }


def _button(text: str, value: dict, btn_type: str = "primary") -> dict:
    return {
        "tag": "action",
        "actions": [{
            "tag": "button",
            "text": _plain_text(text),
            "type": btn_type,
            "value": value,
        }],
    }


def _double_button(btn1_text: str, btn1_value: dict, btn2_text: str, btn2_value: dict) -> dict:
    """两个按钮并排：主按钮 + 次按钮"""
    return {
        "tag": "action",
        "actions": [
            {
                "tag": "button",
                "text": _plain_text(btn1_text),
                "type": "primary",
                "value": btn1_value,
            },
            {
                "tag": "button",
                "text": _plain_text(btn2_text),
                "type": "default",
                "value": btn2_value,
            },
        ],
    }


def _card(header_title: str, elements: list[dict], color: str = "blue") -> dict:
    return {
        "config": {"wide_screen_mode": True, "enable_forward": False},
        "header": {
            "title": _plain_text(header_title),
            "template": color,
        },
        "elements": elements,
    }


# ============ 风格选项 ============

STYLE_OPTIONS = [
    ("现代简约", "现代简约"),
    ("新中式", "新中式"),
    ("轻奢风", "轻奢风"),
    ("北欧风", "北欧风"),
    ("日式", "日式"),
    ("工业风", "工业风"),
    ("混搭", "混搭"),
    ("法式奶油", "法式奶油"),
    ("美式", "美式"),
    ("其他", "其他"),
]

# ============ 客户群选项 ============

CLIENT_TYPE_OPTIONS = [
    ("首次装修", "首次装修"),
    ("改善型装修", "改善型装修"),
    ("别墅/豪宅", "别墅/豪宅"),
    ("投资客户", "投资客户"),
    ("商业空间", "商业空间"),
]

# ============ 服务类型选项 ============

SERVICE_TYPE_OPTIONS = [
    ("全案设计", "全案设计"),
    ("半包施工", "半包施工"),
    ("纯设计", "纯设计"),
    ("软装搭配", "软装搭配"),
    ("全屋定制", "全屋定制"),
]

# ============ 品牌调性选项 ============

BRAND_TONE_OPTIONS = [
    ("专业严谨", "专业严谨"),
    ("轻松亲切", "轻松亲切"),
    ("高端雅致", "高端雅致"),
    ("年轻时尚", "年轻时尚"),
    ("温暖贴心", "温暖贴心"),
]

# ============ 价格区间选项 ============

PRICE_RANGE_OPTIONS = [
    ("10-20万", "10-20万"),
    ("20-50万", "20-50万"),
    ("50-100万", "50-100万"),
    ("100万以上", "100万以上"),
]

# ============ 城市选项（Top 30） ============

CITY_OPTIONS = [
    ("北京", "北京"), ("上海", "上海"), ("广州", "广州"), ("深圳", "深圳"),
    ("杭州", "杭州"), ("成都", "成都"), ("武汉", "武汉"), ("南京", "南京"),
    ("重庆", "重庆"), ("苏州", "苏州"), ("西安", "西安"), ("长沙", "长沙"),
    ("天津", "天津"), ("郑州", "郑州"), ("济南", "济南"), ("青岛", "青岛"),
    ("合肥", "合肥"), ("福州", "福州"), ("厦门", "厦门"), ("东莞", "东莞"),
    ("大连", "大连"), ("宁波", "宁波"), ("昆明", "昆明"), ("无锡", "无锡"),
    ("佛山", "佛山"), ("沈阳", "沈阳"), ("温州", "温州"), ("珠海", "珠海"),
    ("南昌", "南昌"), ("其他", "其他"),
]

# ============ 初始化引导卡片 ============


def build_onboarding_card_1(step: int = 1) -> dict:
    """第一张卡片：公司基本信息"""
    elements = [
        _div("**你好设计师！** 🎉\n我是 Max，你的 AI 室内设计助手。先花 2 分钟让我了解你的工作室——以后每次对话我都会记住这些信息，越用越懂你。"),
        _hr(),
        _div("**公司 / 工作室名称**"),
        _input_field("company_name", "公司名称", "如：斑马精装设计工作室", required=True),
        _div("**主打设计风格**（最能代表你作品的方向）"),
        _select_field("design_style", STYLE_OPTIONS, "请选择一个风格"),
        _div("**所在城市**（你主要服务的城市）"),
        _select_field("city", CITY_OPTIONS, "请选择城市"),
        _hr(),
        _button("下一步 →", {"action": "onboarding", "step": str(step + 1), "card": str(step)}),
        _note(f"第 {step}/3 步 · 约1分钟"),
    ]
    return _card(f"让 Max 更了解你 ({step}/3)", elements, "blue")


def build_onboarding_card_2(step: int = 2) -> dict:
    """第二张卡片：客户群与品牌"""
    elements = [
        _div("**第二步！** 告诉我你的客户和品牌定位，我会用匹配的风格和话术来服务。"),
        _hr(),
        _div("**主要客户群体**（可多选）"),
        _multi_select_field("target_client", CLIENT_TYPE_OPTIONS, "请选择1-3类客户群"),
        _div("**服务类型**（可多选）"),
        _multi_select_field("service_types", SERVICE_TYPE_OPTIONS, "请选择你的服务范围"),
        _div("**品牌调性**（你和客户沟通的风格）"),
        _select_field("brand_tone", BRAND_TONE_OPTIONS, "请选择品牌调性"),
        _div("**主力价格区间**（大多数项目的报价范围）"),
        _select_field("price_range", PRICE_RANGE_OPTIONS, "请选择价格区间"),
        _hr(),
        _double_button(
            "下一步 →", {"action": "onboarding", "step": str(step + 1), "card": str(step)},
            "← 返回修改", {"action": "onboarding", "step": str(step - 1), "card": str(step)},
        ),
        _note(f"第 {step}/3 步 · 约1分钟"),
    ]
    return _card(f"客户与品牌定位 ({step}/3)", elements, "blue")


def build_onboarding_card_3(profile_data: dict[str, str], step: int = 3) -> dict:
    """第三张卡片：确认信息，完成配置"""
    # 构建摘要文本
    summary_lines = [
        f"**公司/工作室：**{profile_data.get('company_name', '未填写')}",
        f"**设计风格：**{profile_data.get('design_style', '未填写')}",
        f"**所在城市：**{profile_data.get('city', '未填写')}",
        f"**目标客户：**{profile_data.get('target_client', '未填写')}",
        f"**服务类型：**{profile_data.get('service_types', '未填写')}",
        f"**品牌调性：**{profile_data.get('brand_tone', '未填写')}",
        f"**价格区间：**{profile_data.get('price_range', '未填写')}",
    ]

    elements = [
        _div("**配置摘要** ✅\n\n" + "\n".join(summary_lines)),
        _hr(),
        _div("点击「**开始使用 Max**」，我会根据这些信息为你提供个性化的 AI 设计助手服务。\n\n配置会保存在你的工作区中，随时可以说\"**修改公司信息**\"来调整。"),
        _hr(),
        _double_button(
            "开始使用 Max", {"action": "onboarding", "step": "finish", "card": str(step)},
            "重新填写", {"action": "onboarding", "step": "1", "card": str(step)},
        ),
        _note("完成配置 · 即将开始"),
    ]
    return _card("配置完成！({}/{})".format(step, step), elements, "green")


# ============ 卡片更新函数（用于覆盖已发送的卡片，展示不同状态） ============


def build_onboarding_error_card(error_msg: str) -> dict:
    """构建错误提示卡片（用于toast反馈）"""
    return {
        "toast": {
            "type": "error",
            "content": error_msg,
            "i18n": {"zh_cn": error_msg},
        },
    }


def build_onboarding_toast(msg: str, level: str = "success") -> dict:
    """构建提示toast响应"""
    return {
        "toast": {
            "type": "error" if level == "error" else "success",
            "content": msg,
            "i18n": {"zh_cn": msg},
        },
    }
