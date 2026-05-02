"""Talker谈单官专用工具：线索捕获、需求分析、话术生成、谈单策划、合同草稿、销售统计"""

import json
import logging
from datetime import datetime

from max_system.config.settings import MaxSettings
from max_system.tools.clientmgr_tools import _clients_db
from max_system.tools.clientmgr_tools import clientmgr_sync_client

logger = logging.getLogger(__name__)


# ============ 1. 线索捕获分级 ============

async def leadcatch_classify(args: dict) -> dict:
    """对客户线索进行标准化登记和意向分级"""
    name = args.get("name", "")
    phone = args.get("phone", "")
    city = args.get("city", "")
    community = args.get("community", "")
    unit_type = args.get("unit_type", "")
    budget = args.get("budget", "")
    stage = args.get("stage", "")
    style = args.get("style", "")
    source = args.get("source", "")
    core_needs = args.get("core_needs", "")

    # 意向分级逻辑
    score = 0
    reasons = []
    if budget and ("万" in budget):
        try:
            budget_val = float("".join(c for c in budget if c.isdigit() or c == "."))
            if budget_val >= 30:
                score += 3
                reasons.append(f"预算充足({budget})")
            elif budget_val >= 15:
                score += 2
                reasons.append(f"预算中等({budget})")
        except ValueError:
            pass

    if stage in ("已交房", "准备装修", "马上开工"):
        score += 2
        reasons.append(f"装修阶段紧急({stage})")
    elif stage in ("已收房", "设计中"):
        score += 1
        reasons.append(f"已有进展({stage})")

    if unit_type and ("别墅" in unit_type or "大平层" in unit_type):
        score += 2
        reasons.append(f"高端户型({unit_type})")

    if source in ("老客户推荐", "已签客户介绍", "朋友推荐"):
        score += 2
        reasons.append(f"推荐来源({source})")

    if core_needs and len(core_needs) > 10:
        score += 1
        reasons.append("需求描述详细")

    if score >= 6:
        intent = "高"
    elif score >= 3:
        intent = "中"
    else:
        intent = "低"

    # 生成客户编号
    client_id = f"C{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # 跟进建议
    follow_up = []
    if intent == "高":
        follow_up = ["24小时内电话回访", "3天内安排量房", "准备同户型案例"]
    elif intent == "中":
        follow_up = ["48小时内微信跟进", "发送公司案例集", "了解具体工期要求"]
    else:
        follow_up = ["1周内轻量跟进", "先发送风格参考", "持续朋友圈触达"]

    result = {
        "client_id": client_id,
        "name": name,
        "intent": intent,
        "score": score,
        "reasons": reasons,
        "follow_up": follow_up,
        "registered_at": datetime.now().isoformat(),
    }

    # 同步写入客户管理
    _clients_db[client_id] = {
        "client_id": client_id,
        "name": name, "phone": phone, "city": city,
        "unit_type": unit_type, "budget": budget, "source": source,
        "status": "新建", "intent": intent,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    # 同步到飞书多维表格
    try:
        await clientmgr_sync_client(client_id)
    except Exception:
        pass

    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}


# ============ 2. 需求分析报告 ============

async def needanaly_report(args: dict) -> dict:
    """生成客户需求深度分析报告"""
    client_name = args.get("client_name", "")
    family = args.get("family", "")          # 家庭构成
    habits = args.get("habits", "")          # 生活习惯
    spatial = args.get("spatial", "")        # 空间需求
    aesthetic = args.get("aesthetic", "")     # 审美偏好
    budget_timeline = args.get("budget_timeline", "")  # 预算工期
    pain_points = args.get("pain_points", "")  # 核心痛点

    report = {
        "客户": client_name,
        "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "基本信息": {
            "家庭构成": family or "待补充",
            "生活习惯": habits or "待补充",
        },
        "功能需求": spatial or "待补充",
        "审美偏好": aesthetic or "待补充",
        "预算与工期": budget_timeline or "待补充",
        "核心痛点": pain_points or "待补充",
        "设计要点": _extract_design_points(spatial, aesthetic, pain_points),
        "谈单切入点": _extract_entry_points(pain_points, budget_timeline),
    }

    return {"content": [{"type": "text", "text": json.dumps(report, ensure_ascii=False, indent=2)}]}


def _extract_design_points(spatial, aesthetic, pain_points):
    points = []
    if spatial:
        if "收纳" in spatial or "储物" in spatial:
            points.append("重点规划收纳系统，全屋定制柜体")
        if "办公" in spatial or "书房" in spatial:
            points.append("规划独立工作区，兼顾采光与安静")
        if "儿童" in spatial:
            points.append("儿童房安全设计，考虑成长性")
        if "开放" in spatial or "互动" in spatial:
            points.append("公共区域开放布局，增强家庭互动")
    if aesthetic:
        if any(s in aesthetic for s in ["简约", "极简", "干净"]):
            points.append("简约风格，注重材质质感和线条比例")
        if any(s in aesthetic for s in ["温暖", "木色", "自然"]):
            points.append("暖色调为主，大量木饰面运用")
    if pain_points:
        if "采光" in pain_points:
            points.append("优化采光方案，浅色系+镜面/玻璃拓展视觉")
        if "层高" in pain_points or "压抑" in pain_points:
            points.append("简化吊顶，用纵向线条拉伸层高感")
    return points or ["待进一步沟通确认"]


def _extract_entry_points(pain_points, budget_timeline):
    entries = []
    if pain_points:
        if "噪音" in pain_points:
            entries.append("隔音方案作为卖点，展示同小区隔音改造案例")
        if "漏水" in pain_points or "渗水" in pain_points:
            entries.append("防水工艺作为核心卖点，展示10年质保体系")
        if "收纳" in pain_points:
            entries.append("全屋收纳系统方案，展示收纳前后对比")
    if budget_timeline:
        if "急" in budget_timeline or "尽快" in budget_timeline:
            entries.append("工期承诺+施工组织方案，打消进度顾虑")
        if "预算有限" in budget_timeline or "控制" in budget_timeline:
            entries.append("分阶段装修方案+性价比材料推荐")
    return entries or ["从设计效果和施工品质切入"]


# ============ 3. 话术生成 ============

async def talkscript_generate(args: dict) -> dict:
    """生成谈单话术"""
    client_name = args.get("client_name", "")
    stage = args.get("stage", "初次沟通")       # 沟通阶段
    client_type = args.get("client_type", "首次装修")  # 客户类型
    channel = args.get("channel", "微信")        # 沟通渠道
    key_points = args.get("key_points", "")      # 关键点

    scripts = _build_script(stage, client_type, channel, key_points)

    result = {
        "客户": client_name,
        "阶段": stage,
        "客户类型": client_type,
        "渠道": channel,
        "话术": scripts,
    }

    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}


def _build_script(stage, client_type, channel, key_points):
    scripts = []

    if stage == "初次沟通":
        scripts.append({
            "场景": "破冰开场",
            "话术": "您好，我是斑马精装的设计顾问。看到您在关注装修，想了解一下您家是什么情况？是已经收房了还是还在看阶段？",
            "要点": "先了解阶段，不急于推销",
        })
        scripts.append({
            "场景": "需求探询",
            "话术": "方便说一下您家的户型和面积吗？家里几口人住，有没有特别想要的功能或者风格？",
            "要点": "从户型切入，自然过渡到需求和风格",
        })
        if client_type == "首次装修":
            scripts.append({
                "场景": "建立信任",
                "话术": "第一次装修确实容易踩坑，您最担心什么问题？我们可以先聊聊，帮您避避坑。",
                "要点": "共情+专业形象",
            })
    elif stage == "方案讲解":
        scripts.append({
            "场景": "方案呈现",
            "话术": "根据您的需求，我们做了这个方案。最大的改动在这里——把原有的隔墙打开，客厅和餐厅连成整体空间，采光和通风都好了很多。您看看这个效果。",
            "要点": "先说改动逻辑，再展示效果",
        })
    elif stage == "异议处理":
        scripts.append({
            "场景": "价格异议",
            "话术": "理解您的顾虑。这个报价确实不低，但您看看这里——我们用的是XX品牌的环保材料，质保10年。如果换便宜的材料，省个一两万，但3年后可能要重新做，反而更贵。",
            "要点": "认同+对比长期成本",
        })
    elif stage == "促单成交":
        scripts.append({
            "场景": "临门一脚",
            "话术": "这个方案您也看了，整体效果和预算都在预期范围内。这个月我们刚好有老客户回馈活动，签约送全屋窗帘，名额就剩两个了。您看这周方便来签个合同吗？",
            "要点": "制造紧迫感+附加优惠",
        })

    if key_points:
        scripts.append({
            "场景": "针对本次重点",
            "话术": f"关于您提到的{key_points}，我们的做法是...",
            "要点": "针对客户具体关注点展开",
        })

    return scripts


# ============ 4. 谈单策划 ============

async def planpro_create(args: dict) -> dict:
    """生成谈单策划方案"""
    client_name = args.get("client_name", "")
    unit_type = args.get("unit_type", "")
    budget = args.get("budget", "")
    style = args.get("style", "")
    pain_points = args.get("pain_points", "")

    plan = {
        "客户": client_name,
        "户型": unit_type,
        "预算": budget,
        "风格": style,
        "核心目标": f"拿下{client_name}的{unit_type or ''}项目签约",
        "流程规划": [
            "第一步：需求深度沟通，确认功能布局和风格方向",
            "第二步：3天内出初步方案，突出核心痛点的解决方案",
            "第三步：方案讲解，重点展示效果图和同户型案例",
            "第四步：报价沟通，按预算做增减项方案",
            "第五步：促单签约，利用时效优惠促成",
        ],
        "切入点": [],
        "亮点包装": [],
        "风险预判": [],
    }

    # 根据痛点生成切入点
    if pain_points:
        if "收纳" in pain_points:
            plan["切入点"].append("全屋收纳系统作为核心卖点，展示收纳量对比")
        if "采光" in pain_points:
            plan["切入点"].append("采光优化方案，展示改造前后对比图")
        if "环保" in pain_points:
            plan["切入点"].append("环保材料体系+检测报告+E0级认证")

    if style:
        plan["亮点包装"].append(f"{style}风格案例集，3套同小区案例")
    if unit_type and ("别墅" in unit_type or "大平层" in unit_type):
        plan["亮点包装"].append("高端项目施工工艺展示，精工细作对比图")
    plan["亮点包装"].append("10年质保承诺书+在建工地参观安排")

    plan["风险预判"] = [
        "客户可能对价格敏感，准备分档报价方案",
        "竞品对比，提前准备差异化优势清单",
        "家庭成员意见不一致，建议安排全家到场面谈",
    ]

    return {"content": [{"type": "text", "text": json.dumps(plan, ensure_ascii=False, indent=2)}]}


# ============ 5. 合同草稿 ============

async def contractpro_draft(args: dict) -> dict:
    """生成合同草稿（需设计师终审）"""
    client_name = args.get("client_name", "")
    address = args.get("address", "")
    area = args.get("area", "")
    total_price = args.get("total_price", "")
    duration = args.get("duration", "")
    payment_method = args.get("payment_method", "分期付款")

    draft = {
        "文档类型": "装修施工合同（草稿）",
        "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "⚠️ 警告": "此为AI生成的合同草稿，必须经设计师和公司法务终审后方可使用",
        "甲方": {
            "姓名": client_name,
            "地址": address,
        },
        "乙方": {
            "公司": "斑马精装",
        },
        "工程概况": {
            "施工地址": address,
            "建筑面积": f"{area}平方米",
            "承包方式": "包工包料",
        },
        "工期": duration or "开工后90个工作日",
        "合同总价": f"{total_price}元" if total_price else "待确认",
        "付款方式": _build_payment_plan(payment_method, total_price),
        "质保": {
            "隐蔽工程": "5年",
            "表面工程": "2年",
            "防水工程": "10年",
        },
        "需要设计师确认的条款": [
            "合同总价是否准确",
            "付款比例是否符合公司政策",
            "工期是否合理",
            "特殊约定条款是否需要补充",
        ],
    }

    return {"content": [{"type": "text", "text": json.dumps(draft, ensure_ascii=False, indent=2)}]}


def _build_payment_plan(method, total_price):
    if method == "分期付款":
        return [
            "签约时付30%（首付款）",
            "水电完工付30%",
            "泥木完工付25%",
            "竣工验收付15%",
        ]
    elif method == "一次性付款":
        return ["签约时付全款（享受98折优惠）"]
    return ["待确认付款方式"]


# ============ 6. 销售数据统计 ============

async def datastat_report(args: dict) -> dict:
    """生成销售数据统计报告"""
    period = args.get("period", "本月")  # 本日/本周/本月/本季度

    # 从客户数据库统计
    total = len(_clients_db)
    high_intent = sum(1 for c in _clients_db.values() if c.get("intent") == "高")
    mid_intent = sum(1 for c in _clients_db.values() if c.get("intent") == "中")
    low_intent = sum(1 for c in _clients_db.values() if c.get("intent") == "低")

    signed = sum(1 for c in _clients_db.values() if c.get("status") == "已签约")
    in_progress = sum(1 for c in _clients_db.values() if c.get("status") == "跟进中")

    conversion_rate = f"{(signed / total * 100):.1f}%" if total > 0 else "0%"

    report = {
        "统计周期": period,
        "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "总量统计": {
            "总线索数": total,
            "高意向": high_intent,
            "中意向": mid_intent,
            "低意向": low_intent,
        },
        "转化漏斗": {
            "新建线索": total - signed - in_progress,
            "跟进中": in_progress,
            "已签约": signed,
            "转化率": conversion_rate,
        },
        "待跟进预警": [],
        "建议": [],
    }

    # 待跟进预警
    for cid, client in _clients_db.items():
        if client.get("status") == "新建":
            report["待跟进预警"].append(f"{client.get('name', '未知')}（{client.get('intent', '?')}意向，待首次跟进）")

    if high_intent > 0 and signed < high_intent:
        report["建议"].append(f"有{high_intent}个高意向客户未签约，建议优先安排方案沟通")

    if low_intent > high_intent:
        report["建议"].append("低意向客户占比偏高，建议优化获客渠道质量")

    return {"content": [{"type": "text", "text": json.dumps(report, ensure_ascii=False, indent=2)}]}


# ============ 工具定义和注册 ============

TOOL_DEFS = [
    {
        "name": "leadcatch_classify",
        "description": "客户线索捕获与意向分级。输入客户基本信息，自动评估意向等级（高/中/低），生成跟进建议。",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "客户姓名"},
                "phone": {"type": "string", "description": "联系电话"},
                "city": {"type": "string", "description": "城市"},
                "community": {"type": "string", "description": "小区名称"},
                "unit_type": {"type": "string", "description": "户型面积，如180㎡大平层"},
                "budget": {"type": "string", "description": "预算范围，如60-80万"},
                "stage": {"type": "string", "description": "装修阶段: 已交房/准备装修/设计中/还在看"},
                "style": {"type": "string", "description": "风格偏好"},
                "source": {"type": "string", "description": "来源渠道: 小红书/抖音/朋友推荐/门店等"},
                "core_needs": {"type": "string", "description": "核心需求描述"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "needanaly_report",
        "description": "生成客户需求深度分析报告，包含功能需求、审美偏好、核心痛点、设计要点、谈单切入点。",
        "parameters": {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "客户姓名"},
                "family": {"type": "string", "description": "家庭构成，如一家三口+老人"},
                "habits": {"type": "string", "description": "生活习惯"},
                "spatial": {"type": "string", "description": "空间需求，如需要书房、收纳要多"},
                "aesthetic": {"type": "string", "description": "审美偏好，如喜欢温暖简约"},
                "budget_timeline": {"type": "string", "description": "预算和工期要求"},
                "pain_points": {"type": "string", "description": "核心痛点，如采光差、收纳不够"},
            },
            "required": ["client_name"],
        },
    },
    {
        "name": "talkscript_generate",
        "description": "生成谈单话术，支持不同阶段（初次沟通/方案讲解/异议处理/促单成交）、不同客户类型和渠道。",
        "parameters": {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "客户姓名"},
                "stage": {"type": "string", "description": "沟通阶段: 初次沟通/需求沟通/方案讲解/异议处理/促单成交"},
                "client_type": {"type": "string", "description": "客户类型: 首次装修/改善型/别墅客户/投资客"},
                "channel": {"type": "string", "description": "沟通渠道: 微信/电话/面谈/群聊"},
                "key_points": {"type": "string", "description": "本次沟通要重点解决的事项"},
            },
            "required": ["client_name"],
        },
    },
    {
        "name": "planpro_create",
        "description": "生成谈单策划方案，包含核心目标、流程规划、切入点、亮点包装、风险预判。",
        "parameters": {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "客户姓名"},
                "unit_type": {"type": "string", "description": "户型面积"},
                "budget": {"type": "string", "description": "预算范围"},
                "style": {"type": "string", "description": "风格偏好"},
                "pain_points": {"type": "string", "description": "客户核心痛点"},
            },
            "required": ["client_name"],
        },
    },
    {
        "name": "contractpro_draft",
        "description": "生成装修施工合同草稿。注意：生成的草稿必须经设计师和公司法务终审后才可使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "甲方姓名"},
                "address": {"type": "string", "description": "施工地址"},
                "area": {"type": "string", "description": "建筑面积（平方米）"},
                "total_price": {"type": "string", "description": "合同总价（元）"},
                "duration": {"type": "string", "description": "工期约定"},
                "payment_method": {"type": "string", "description": "付款方式: 分期付款/一次性付款"},
            },
            "required": ["client_name"],
        },
    },
    {
        "name": "datastat_report",
        "description": "生成销售数据统计报告，包含线索总量、意向分级、转化漏斗、待跟进预警。",
        "parameters": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "统计周期: 本日/本周/本月/本季度"},
            },
            "required": [],
        },
    },
]


def register_tools(settings: MaxSettings):
    handlers = {
        "leadcatch_classify": leadcatch_classify,
        "needanaly_report": needanaly_report,
        "talkscript_generate": talkscript_generate,
        "planpro_create": planpro_create,
        "contractpro_draft": contractpro_draft,
        "datastat_report": datastat_report,
    }
    return [(d["name"], handlers[d["name"]], d) for d in TOOL_DEFS]
