"""MediaPro自媒体官专用工具：文案生成、案例包装、账号运营、线索转化、内容复盘"""

import json
import logging
from datetime import datetime

from max_system.config.settings import MaxSettings

logger = logging.getLogger(__name__)

# 内容素材库（内存存储）
_content_db: list[dict] = []
_lead_pool: list[dict] = []


# ============ 1. 文案生成 ============

async def contentgen_draft(args: dict) -> dict:
    """生成自媒体文案草稿"""
    platform = args.get("platform", "小红书")  # 小红书/抖音/微信朋友圈/公众号
    topic = args.get("topic", "")
    style = args.get("style", "种草分享")  # 种草分享/干货科普/案例展示/热点蹭流/业主故事
    key_points = args.get("key_points", "")
    target_audience = args.get("target_audience", "装修人群")

    draft = {
        "平台": platform,
        "主题": topic,
        "风格": style,
        "目标受众": target_audience,
    }

    if platform == "小红书":
        draft.update(_gen_xiaohongshu(topic, style, key_points, target_audience))
    elif platform == "抖音":
        draft.update(_gen_douyin(topic, style, key_points, target_audience))
    elif platform == "微信朋友圈":
        draft.update(_gen_wechat_moments(topic, style, key_points))
    elif platform == "公众号":
        draft.update(_gen_wechat_article(topic, style, key_points, target_audience))

    draft["生成时间"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    draft["备注"] = "AI生成草稿，发布前请设计师审核修改"

    _content_db.append(draft)

    return {"content": [{"type": "text", "text": json.dumps(draft, ensure_ascii=False, indent=2)}]}


def _gen_xiaohongshu(topic, style, key_points, audience):
    """小红书文案"""
    # 标题模板
    title_templates = {
        "种草分享": f"装修终于毕业了！{topic}全记录，踩坑+省钱攻略",
        "干货科普": f"装修必看！{topic}避坑指南，别再花冤枉钱了",
        "案例展示": f"实景分享｜{topic}，入住3个月真实感受",
        "热点蹭流": f"2024装修趋势｜{topic}，这样装太高级了",
        "业主故事": f"从毛坯到梦想家｜{topic}的装修故事",
    }
    title = title_templates.get(style, f"{topic}分享")

    body = f"""{title}

姐妹们！关于{topic}，我有话说！

{key_points or "装修这条路走了大半年，总结几点心得："}

1. 前期规划比什么都重要，千万别着急开工
2. 找靠谱的公司真的省心太多
3. 材料环保不能省，家里有老人小孩的更要注意
4. 预算一定要留10-15%的余量

关于{topic}还有什么想问的，评论区见！

"""

    tags = ["#装修", "#装修日记", f"#{topic}", "#斑马精装", "#装修避坑", "#装修干货"]

    return {
        "标题": title,
        "正文": body.strip(),
        "标签": tags,
        "配图建议": [
            "封面: 效果图或实景全景，加文字标注",
            "图2-4: 施工细节对比图",
            "图5-6: 完工实景多角度",
        ],
        "发布时间建议": "晚8-10点（小红书用户活跃高峰）",
    }


def _gen_douyin(topic, style, key_points, audience):
    """抖音短视频脚本"""
    return {
        "标题": f"装修人必看！{topic}",
        "视频时长": "30-60秒",
        "脚本": [
            {"时间": "0-3秒", "画面": "震撼的前后对比/效果展示", "旁白": f"关于{topic}，90%的人都做错了！"},
            {"时间": "3-15秒", "画面": "常见错误展示", "旁白": key_points or "很多人装修时忽略了这点，入住后后悔莫及"},
            {"时间": "15-25秒", "画面": "正确做法展示", "旁白": "正确做法是这样的，不仅好看还实用"},
            {"时间": "25-30秒", "画面": "公司案例/联系方式", "旁白": "关注我，装修不踩坑"},
        ],
        "BGM建议": "热门轻快BGM",
        "发布时间建议": "午休12-14点或晚7-9点",
    }


def _gen_wechat_moments(topic, style, key_points, audience):
    """微信朋友圈文案"""
    return {
        "正文": f"关于{topic}，一句话总结：{key_points or '装修找对人，省心一大半'}。有需要了解的朋友私聊我~",
        "配图": "1张完工实景+1张施工对比",
        "发布时间建议": "早8点或晚8点",
    }


def _gen_wechat_article(topic, style, key_points, audience):
    """公众号长文"""
    return {
        "标题": f"装修避坑 | {topic}全攻略，看完省3万",
        "摘要": f"关于{topic}，我们总结了最实用的避坑指南和省钱技巧",
        "大纲": [
            f"一、{topic}常见的3个大坑",
            "二、如何避坑：关键决策清单",
            "三、真实案例：我们是怎么做的",
            "四、预算规划：钱花在哪最值",
            "五、设计师建议",
        ],
        "字数建议": "1500-2500字",
        "发布时间建议": "工作日晚8点",
    }


# ============ 2. 案例包装 ============

async def casepack_package(args: dict) -> dict:
    """包装项目案例为营销素材"""
    project_name = args.get("project_name", "")
    client_name = args.get("client_name", "")
    unit_type = args.get("unit_type", "")
    style = args.get("style", "")
    highlights = args.get("highlights", "")  # 设计亮点
    budget = args.get("budget", "")
    before_after = args.get("before_after", "")  # 改造前后对比

    package = {
        "项目": project_name,
        "案例包装": {
            "标题": f"{style or ''}{unit_type or ''}实景 | {highlights or '品质装修'}",
            "一句话卖点": highlights or f"{style or '精装'}品质，{unit_type or ''}完美落地",
            "基本信息": {
                "户型": unit_type or "待补充",
                "风格": style or "待补充",
                "预算": budget or "待补充",
            },
            "设计亮点": [
                highlights or "待补充",
                "施工工艺展示点",
                "材料品质体现点",
            ],
            "内容矩阵": {
                "小红书": f"实景分享｜{style or ''}{unit_type or ''}完工记录",
                "抖音": f"装修前后大变身！{unit_type or ''}改造全过程",
                "朋友圈": f"又一个完美交付的项目，{highlights or '品质看得见'}",
            },
            "拍摄建议": [
                "全景: 客厅/主卧广角，体现空间感",
                "细节: 材质特写（木饰面/瓷砖/五金）",
                "对比: 改造前后同角度对比",
                "生活化: 摆设软装后的入住感",
            ],
        },
        "客户授权": "⚠️ 发布前必须取得客户书面授权",
    }

    return {"content": [{"type": "text", "text": json.dumps(package, ensure_ascii=False, indent=2)}]}


# ============ 3. 账号运营计划 ============

async def accountopt_plan(args: dict) -> dict:
    """生成账号运营优化计划"""
    platform = args.get("platform", "小红书")
    current_status = args.get("current_status", "")  # 当前账号状况
    goal = args.get("goal", "涨粉获客")  # 涨粉获客/品牌曝光/内容沉淀
    period = args.get("period", "月度")  # 月度/季度

    plan = {
        "平台": platform,
        "目标": goal,
        "周期": period,
        "内容规划": {},
        "发布节奏": {},
        "运营动作": [],
    }

    if platform == "小红书":
        plan["内容规划"] = {
            "种草分享": "2篇/周（完工案例+业主体验）",
            "干货科普": "1篇/周（装修避坑+选材指南）",
            "热点蹭流": "1篇/周（装修趋势+节日热点）",
            "视频笔记": "1篇/周（施工过程/改造对比）",
        }
        plan["发布节奏"] = {
            "工作日": "晚8-10点发布",
            "周末": "下午2-4点发布",
            "每周": "4-5篇，保持活跃度",
        }
        plan["运营动作"] = [
            "评论区积极互动，引导私聊咨询",
            "关注同城装修话题，蹭本地流量",
            "定期复盘爆文逻辑，复制成功模式",
            "置顶笔记保持更新（服务介绍+案例合集）",
        ]
    elif platform == "抖音":
        plan["内容规划"] = {
            "改造对比": "2条/周（前后变身类）",
            "施工记录": "1条/周（工艺展示类）",
            "干货分享": "1条/周（避坑+选材）",
            "直播": "1次/周（在线答疑+工地实况）",
        }
        plan["发布节奏"] = {
            "最佳时间": "12:00-14:00, 19:00-21:00",
            "每周": "3-4条视频 + 1次直播",
        }
        plan["运营动作"] = [
            "使用热门BGM和话题标签",
            "前3秒必须抓眼球（对比/悬念/数字）",
            "评论区引导私信留资",
            "定期DOU+投放优质内容",
        ]

    plan["KPI建议"] = {
        "小红书": {"粉丝增长": "200+/月", "笔记曝光": "5000+/篇", "私信咨询": "10+/周"},
        "抖音": {"粉丝增长": "500+/月", "视频播放": "10000+/条", "私信留资": "15+/周"},
    }.get(platform, {})

    return {"content": [{"type": "text", "text": json.dumps(plan, ensure_ascii=False, indent=2)}]}


# ============ 4. 线索转化判定 ============

async def leadtransfer_qualify(args: dict) -> dict:
    """判定自媒体线索质量并转交Talker"""
    lead_source = args.get("lead_source", "")  # 线索来源: 小红书私信/抖音评论/微信添加
    lead_content = args.get("lead_content", "")  # 线索内容
    contact_info = args.get("contact_info", "")  # 联系方式
    platform = args.get("platform", "小红书")

    # 线索质量评估
    quality_score = 0
    quality_reasons = []

    # 高意图信号
    high_intent_signals = ["装修", "报价", "面积", "户型", "什么时候", "多少钱", "预算", "签约", "开工"]
    for signal in high_intent_signals:
        if signal in lead_content:
            quality_score += 2
            quality_reasons.append(f"包含高意图关键词: {signal}")

    # 中意图信号
    mid_intent_signals = ["风格", "效果", "案例", "看一下", "了解", "咨询", "推荐"]
    for signal in mid_intent_signals:
        if signal in lead_content:
            quality_score += 1
            quality_reasons.append(f"包含中意图关键词: {signal}")

    # 有联系方式加分
    if contact_info:
        quality_score += 2
        quality_reasons.append("已留下联系方式")

    # 来源渠道权重
    source_weights = {"微信添加": 3, "小红书私信": 2, "抖音评论": 1}
    quality_score += source_weights.get(lead_source, 1)
    quality_reasons.append(f"来源渠道: {lead_source}")

    # 分级
    if quality_score >= 6:
        quality = "A级-高意向"
        transfer_urgency = "立即转交Talker，24小时内联系"
    elif quality_score >= 3:
        quality = "B级-中意向"
        transfer_urgency = "转交Talker，48小时内跟进"
    else:
        quality = "C级-低意向"
        transfer_urgency = "先回复引导获取更多信息"

    result = {
        "线索来源": f"{platform}-{lead_source}",
        "线索内容": lead_content,
        "联系方式": contact_info or "未提供",
        "质量评分": quality_score,
        "评级": quality,
        "评分依据": quality_reasons,
        "建议动作": transfer_urgency,
        "转交Talker的任务描述": f"【自媒体线索】{platform}收到{quality}客户咨询: {lead_content[:100]}",
        "判定时间": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    _lead_pool.append(result)

    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}


# ============ 5. 内容复盘分析 ============

async def datareview_analyze(args: dict) -> dict:
    """生成内容运营数据分析报告"""
    platform = args.get("platform", "全部")
    period = args.get("period", "本月")  # 本周/本月/本季度

    # 从内容库统计
    total_content = len(_content_db)
    by_platform = {}
    for c in _content_db:
        p = c.get("平台", "未知")
        by_platform[p] = by_platform.get(p, 0) + 1

    # 从线索池统计
    total_leads = len(_lead_pool)
    a_leads = sum(1 for l in _lead_pool if "A级" in l.get("评级", ""))
    b_leads = sum(1 for l in _lead_pool if "B级" in l.get("评级", ""))

    report = {
        "复盘周期": period,
        "内容产出": {
            "总发布量": total_content,
            "各平台分布": by_platform or {"提示": "暂无发布记录"},
        },
        "线索转化": {
            "总线索数": total_leads,
            "A级（高意向）": a_leads,
            "B级（中意向）": b_leads,
            "C级（低意向）": total_leads - a_leads - b_leads,
            "转化率": f"{(a_leads / total_leads * 100):.1f}%" if total_leads > 0 else "0%",
        },
        "优化建议": [
            "爆文分析: 找出互动率最高的内容，总结成功要素",
            "发布时间: 根据数据调整发布时间到流量高峰",
            "内容方向: 加大高转化率类型内容的产出比例",
            "互动策略: 评论区和私信响应速度影响转化",
        ],
        "下一步计划": [
            "制定下期内容日历",
            "优化低效内容类型",
            "测试新内容形式（直播/视频）",
        ],
        "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    return {"content": [{"type": "text", "text": json.dumps(report, ensure_ascii=False, indent=2)}]}


# ============ 工具定义和注册 ============

TOOL_DEFS = [
    {
        "name": "contentgen_draft",
        "description": "生成自媒体文案草稿，支持小红书/抖音/朋友圈/公众号多平台。",
        "parameters": {
            "type": "object",
            "properties": {
                "platform": {"type": "string", "description": "平台: 小红书/抖音/微信朋友圈/公众号"},
                "topic": {"type": "string", "description": "文案主题"},
                "style": {"type": "string", "description": "风格: 种草分享/干货科普/案例展示/热点蹭流/业主故事"},
                "key_points": {"type": "string", "description": "核心要点"},
                "target_audience": {"type": "string", "description": "目标受众"},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "casepack_package",
        "description": "包装项目案例为多平台营销素材，含标题、卖点、拍摄建议。",
        "parameters": {
            "type": "object",
            "properties": {
                "project_name": {"type": "string", "description": "项目名称"},
                "client_name": {"type": "string", "description": "客户姓名"},
                "unit_type": {"type": "string", "description": "户型面积"},
                "style": {"type": "string", "description": "装修风格"},
                "highlights": {"type": "string", "description": "设计亮点"},
                "budget": {"type": "string", "description": "预算范围"},
                "before_after": {"type": "string", "description": "改造前后对比说明"},
            },
            "required": ["project_name"],
        },
    },
    {
        "name": "accountopt_plan",
        "description": "生成自媒体账号运营优化计划，含内容规划、发布节奏、KPI建议。",
        "parameters": {
            "type": "object",
            "properties": {
                "platform": {"type": "string", "description": "平台: 小红书/抖音"},
                "current_status": {"type": "string", "description": "当前账号状况描述"},
                "goal": {"type": "string", "description": "运营目标: 涨粉获客/品牌曝光/内容沉淀"},
                "period": {"type": "string", "description": "规划周期: 月度/季度"},
            },
            "required": [],
        },
    },
    {
        "name": "leadtransfer_qualify",
        "description": "评估自媒体线索质量并生成转交Talker的任务描述，自动按意图强度分级。",
        "parameters": {
            "type": "object",
            "properties": {
                "lead_source": {"type": "string", "description": "线索来源: 小红书私信/抖音评论/微信添加/公众号留言"},
                "lead_content": {"type": "string", "description": "线索内容"},
                "contact_info": {"type": "string", "description": "客户联系方式"},
                "platform": {"type": "string", "description": "来源平台"},
            },
            "required": ["lead_content"],
        },
    },
    {
        "name": "datareview_analyze",
        "description": "生成内容运营数据复盘报告，含内容产出统计、线索转化分析、优化建议。",
        "parameters": {
            "type": "object",
            "properties": {
                "platform": {"type": "string", "description": "分析平台: 全部/小红书/抖音"},
                "period": {"type": "string", "description": "复盘周期: 本周/本月/本季度"},
            },
            "required": [],
        },
    },
]


def register_tools(settings: MaxSettings):
    handlers = {
        "contentgen_draft": contentgen_draft,
        "casepack_package": casepack_package,
        "accountopt_plan": accountopt_plan,
        "leadtransfer_qualify": leadtransfer_qualify,
        "datareview_analyze": datareview_analyze,
    }
    return [(d["name"], handlers[d["name"]], d) for d in TOOL_DEFS]
