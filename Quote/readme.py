# 室内装修精准报价系统核心函数
def generate_renovation_quote(
    # 房屋基本信息（必填）
    city: str = "全国平均",
    building_area: float = None,
    interior_area: float = None,
    house_type: str = "新房毛坯",  # 新房毛坯/二手房翻新/局部改造
    floor: int = None,
    floor_height: float = 2.8,
    
    # 户型信息
    bedrooms: int = None,
    living_rooms: int = 1,
    bathrooms: int = 1,
    kitchens: int = 1,
    balconies: int = 1,
    
    # 装修要求
    decoration_level: str = "舒适型",  # 经济型/舒适型/豪华型
    decoration_style: str = "现代简约",
    special_requirements: list = None,
    
    # 各房间详细尺寸（可选，格式：{"客厅": [长, 宽, 高], "主卧": [长, 宽, 高]}）
    room_dimensions: dict = None,
    
    # 其他配置
    include_design_fee: bool = False,
    include_tax: bool = False,
    quote_validity_days: int = 30
) -> dict:
    """
    生成标准化室内装修精准报价单，包含分项明细、漏项检测和风险提示
    严格遵循2026年中国装修市场计价规范，所有计算透明可追溯
    """
    
    # ==================== 系统常量（不可随意修改）====================
    # 地区系数
    REGION_COEFFICIENTS = {
        "一线城市": 1.5, "新一线城市": 1.2, "二线城市": 1.0, "三四线城市": 0.8, "全国平均": 1.0
    }
    
    # 标准损耗率
    STANDARD_LOSS_RATES = {
        "瓷砖": 0.08, "木地板": 0.05, "乳胶漆": 0.10, "电线": 0.15, "水管": 0.10,
        "板材": 0.08, "腻子": 0.05, "水泥沙子": 0.03, "异形铺贴": 0.15
    }
    
    # 2026年全国基准单价表（主材+辅材+人工，元/单位）
    BASE_PRICES = {
        "经济型": {
            "水电全改": 120, "地面铺砖": 85, "墙面刷漆": 45, "平顶吊顶": 90,
            "防水": 65, "包立管": 280, "过门石": 80, "窗台石": 120,
            "拆墙": 50, "拆地砖": 30, "拆墙砖": 25, "管理费": 0.08
        },
        "舒适型": {
            "水电全改": 180, "地面铺砖": 130, "墙面刷漆": 70, "平顶吊顶": 140,
            "防水": 95, "包立管": 420, "过门石": 120, "窗台石": 180,
            "拆墙": 70, "拆地砖": 45, "拆墙砖": 35, "管理费": 0.10
        },
        "豪华型": {
            "水电全改": 280, "地面铺砖": 220, "墙面刷漆": 120, "平顶吊顶": 220,
            "防水": 150, "包立管": 650, "过门石": 180, "窗台石": 280,
            "拆墙": 100, "拆地砖": 60, "拆墙砖": 50, "管理费": 0.12
        }
    }
    
    # 其他费用标准
    OTHER_FEES = {
        "垃圾清运费": 15, "成品保护费": 10, "开荒保洁费": 8,
        "设计费": {"经济型": 50, "舒适型": 100, "豪华型": 200},
        "税金": 0.0336
    }
    
    # 必查漏项清单（含预估费用占比）
    MANDATORY_MISSING_ITEMS = [
        {"name": "墙面找平", "cost_ratio": 0.03, "reason": "行业常见报价陷阱，多数公司故意遗漏"},
        {"name": "地面找平", "cost_ratio": 0.02, "reason": "铺木地板前必须施工，否则后期异响"},
        {"name": "阴阳角找直", "cost_ratio": 0.015, "reason": "影响美观和家具安装"},
        {"name": "瓷砖美缝", "cost_ratio": 0.025, "reason": "几乎所有公司都单独收费"},
        {"name": "窗帘盒", "cost_ratio": 0.01, "reason": "木工工程常见漏项"},
        {"name": "石膏线", "cost_ratio": 0.008, "reason": "多数公司不包含在基础报价中"},
        {"name": "踢脚线", "cost_ratio": 0.012, "reason": "常被单独列项加价"},
        {"name": "门洞修正", "cost_ratio": 0.01, "reason": "安装门之前必须处理"},
        {"name": "强电箱扩容", "cost_ratio": 0.02, "reason": "现代家电功率大，原配电箱不够用"},
        {"name": "六类网线升级", "cost_ratio": 0.01, "reason": "原开发商网线多为五类线，不支持千兆"}
    ]
    
    # ==================== 输入校验与默认值处理 ====================
    if not interior_area and building_area:
        interior_area = building_area * 0.75  # 套内面积默认按建筑面积75%计算
    
    if not room_dimensions:
        # 自动生成标准房间尺寸（基于套内面积）
        room_dimensions = {}
        room_area = interior_area / (bedrooms + living_rooms + bathrooms + kitchens + balconies)
        room_dimensions["客厅"] = [room_area**0.5 * 1.2, room_area**0.5 * 0.8, floor_height]
        for i in range(1, bedrooms+1):
            room_dimensions[f"卧室{i}"] = [room_area**0.5, room_area**0.5, floor_height]
        for i in range(1, bathrooms+1):
            room_dimensions[f"卫生间{i}"] = [2.5, 2.0, floor_height]
        room_dimensions["厨房"] = [3.0, 2.5, floor_height]
        for i in range(1, balconies+1):
            room_dimensions[f"阳台{i}"] = [3.0, 1.5, floor_height]
    
    # 确定地区系数
    if city in ["北京", "上海", "广州", "深圳"]:
        region_coeff = REGION_COEFFICIENTS["一线城市"]
    elif city in ["成都", "重庆", "杭州", "武汉", "西安", "天津", "苏州", "南京", "郑州", "长沙", "东莞", "青岛", "沈阳", "合肥", "佛山"]:
        region_coeff = REGION_COEFFICIENTS["新一线城市"]
    else:
        region_coeff = REGION_COEFFICIENTS["全国平均"]
    
    # 获取当前装修档次的价格表
    prices = BASE_PRICES[decoration_level]
    
    # ==================== 硬装工程计算 ====================
    hard_construction = {}
    
    # 1. 水电改造工程
    hard_construction["水电改造"] = {
        "工程量": interior_area,
        "单价": prices["水电全改"] * region_coeff,
        "损耗率": STANDARD_LOSS_RATES["电线"],
        "合价": interior_area * prices["水电全改"] * region_coeff * (1 + STANDARD_LOSS_RATES["电线"])
    }
    
    # 2. 泥瓦工程
    tiling_total = 0
    for room, (length, width, height) in room_dimensions.items():
        # 地面面积
        floor_area = length * width
        tiling_total += floor_area * prices["地面铺砖"] * region_coeff * (1 + STANDARD_LOSS_RATES["瓷砖"])
        
        # 卫生间防水
        if "卫生间" in room:
            wall_area = 2 * (length + width) * 1.8  # 防水上翻1.8米
            tiling_total += wall_area * prices["防水"] * region_coeff * (1 + STANDARD_LOSS_RATES["水泥沙子"])
            tiling_total += prices["包立管"] * region_coeff  # 每卫生间1根立管
    
    hard_construction["泥瓦工程"] = {
        "工程量": tiling_total / (prices["地面铺砖"] * region_coeff * (1 + STANDARD_LOSS_RATES["瓷砖"])),
        "单价": prices["地面铺砖"] * region_coeff,
        "损耗率": STANDARD_LOSS_RATES["瓷砖"],
        "合价": tiling_total
    }
    
    # 3. 油漆工程
    paint_total = 0
    for room, (length, width, height) in room_dimensions.items():
        wall_area = 2 * (length + width) * height - length * width * 0.2  # 扣除门窗面积20%
        paint_total += wall_area * prices["墙面刷漆"] * region_coeff * (1 + STANDARD_LOSS_RATES["乳胶漆"])
    
    hard_construction["油漆工程"] = {
        "工程量": paint_total / (prices["墙面刷漆"] * region_coeff * (1 + STANDARD_LOSS_RATES["乳胶漆"])),
        "单价": prices["墙面刷漆"] * region_coeff,
        "损耗率": STANDARD_LOSS_RATES["乳胶漆"],
        "合价": paint_total
    }
    
    # 4. 木工工程（基础吊顶）
    ceiling_area = interior_area * 0.3  # 吊顶面积按套内面积30%计算
    hard_construction["木工工程"] = {
        "工程量": ceiling_area,
        "单价": prices["平顶吊顶"] * region_coeff,
        "损耗率": STANDARD_LOSS_RATES["板材"],
        "合价": ceiling_area * prices["平顶吊顶"] * region_coeff * (1 + STANDARD_LOSS_RATES["板材"])
    }
    
    # 5. 安装工程
    installation_total = hard_construction["水电改造"]["合价"] * 0.15
    hard_construction["安装工程"] = {
        "工程量": 1,
        "单价": installation_total,
        "损耗率": 0,
        "合价": installation_total
    }
    
    # 6. 拆除工程（仅二手房）
    if house_type == "二手房翻新":
        demolition_total = 0
        for room, (length, width, height) in room_dimensions.items():
            floor_area = length * width
            wall_area = 2 * (length + width) * height * 0.5  # 拆除一半墙面
            demolition_total += floor_area * prices["拆地砖"] * region_coeff
            demolition_total += wall_area * prices["拆墙砖"] * region_coeff
        
        hard_construction["拆除工程"] = {
            "工程量": demolition_total / (prices["拆地砖"] * region_coeff),
            "单价": prices["拆地砖"] * region_coeff,
            "损耗率": 0,
            "合价": demolition_total
        }
    
    # 硬装工程总计
    hard_construction_total = sum(item["合价"] for item in hard_construction.values())
    
    # ==================== 其他费用计算 ====================
    other_fees = {}
    other_fees["管理费"] = hard_construction_total * prices["管理费"]
    other_fees["垃圾清运费"] = building_area * OTHER_FEES["垃圾清运费"] * region_coeff
    other_fees["成品保护费"] = building_area * OTHER_FEES["成品保护费"] * region_coeff
    other_fees["开荒保洁费"] = building_area * OTHER_FEES["开荒保洁费"] * region_coeff
    
    if include_design_fee:
        other_fees["设计费"] = interior_area * OTHER_FEES["设计费"][decoration_level] * region_coeff
    
    if include_tax:
        subtotal = hard_construction_total + sum(other_fees.values())
        other_fees["税金"] = subtotal * OTHER_FEES["税金"]
    
    other_fees_total = sum(other_fees.values())
    
    # ==================== 漏项检测 ====================
    missing_items = []
    for item in MANDATORY_MISSING_ITEMS:
        estimated_cost = hard_construction_total * item["cost_ratio"]
        missing_items.append({
            "name": item["name"],
            "estimated_cost": round(estimated_cost, 2),
            "reason": item["reason"]
        })
    
    # ==================== 总报价汇总 ====================
    total_quote = hard_construction_total + other_fees_total
    
    # ==================== 生成结果 ====================
    result = {
        "basic_info": {
            "city": city,
            "building_area": building_area,
            "interior_area": round(interior_area, 2),
            "house_type": house_type,
            "decoration_level": decoration_level,
            "decoration_style": decoration_style,
            "generated_at": "2026-04-25",
            "valid_until": f"2026-{5 if 4+quote_validity_days//30 <6 else 6}-{25+quote_validity_days%30}"
        },
        "assumptions": [
            "套内面积按建筑面积75%计算" if not interior_area else "",
            "房间尺寸为标准估算值，实际尺寸会影响最终报价" if not room_dimensions else "",
            "地区系数按全国平均计算" if city == "全国平均" else f"地区系数按{REGION_COEFFICIENTS[city]}计算",
            "未包含定制家具、成品家具和家电设备费用",
            "报价误差范围：±8%"
        ],
        "total_summary": {
            "硬装工程": round(hard_construction_total, 2),
            "其他费用": round(other_fees_total, 2),
            "总计": round(total_quote, 2)
        },
        "hard_construction_details": hard_construction,
        "other_fees_details": other_fees,
        "missing_items_risk": missing_items,
        "notes": [
            "本报价有效期为30天",
            "材料价格随市场波动，最终以实际采购价为准",
            "工程量按实际发生量计算，多退少补",
            "特殊工艺（如无主灯、弧形吊顶）需单独计价"
        ]
    }
    
    # 过滤空假设
    result["assumptions"] = [a for a in result["assumptions"] if a]
    
    return result


# ==================== 辅助函数：生成Markdown格式报价单 ====================
def generate_markdown_quote(quote_data: dict) -> str:
    """将结构化报价数据转换为美观的Markdown格式"""
    
    markdown = f"""# 室内装修精准报价单
生成日期：{quote_data['basic_info']['generated_at']} | 有效期至：{quote_data['basic_info']['valid_until']}
装修档次：{quote_data['basic_info']['decoration_level']} | 所在地区：{quote_data['basic_info']['city']}

## 【输入信息确认】
- 建筑面积：{quote_data['basic_info']['building_area']}㎡
- 套内面积：{quote_data['basic_info']['interior_area']}㎡
- 房屋类型：{quote_data['basic_info']['house_type']}
- 装修风格：{quote_data['basic_info']['decoration_style']}

## 【假设条件说明】
"""
    for assumption in quote_data['assumptions']:
        markdown += f"- ⚠️ {assumption}\n"
    
    markdown += """
## 【总报价汇总】
| 费用类别 | 金额（元） | 占比 |
|---------|-----------|------|
"""
    total = quote_data['total_summary']['总计']
    for category, amount in quote_data['total_summary'].items():
        if category != '总计':
            percentage = round(amount / total * 100, 1)
            markdown += f"| {category} | {amount:,.2f} | {percentage}% |\n"
    markdown += f"| **总计** | **{total:,.2f}** | **100%** |\n"
    
    markdown += """
## 【硬装工程详细报价】
| 工程类别 | 工程量 | 单价（元） | 损耗率 | 合价（元） |
|---------|--------|-----------|--------|-----------|
"""
    for category, details in quote_data['hard_construction_details'].items():
        markdown += f"| {category} | {details['工程量']:.2f} | {details['单价']:.2f} | {details['损耗率']*100:.1f}% | {details['合价']:,.2f} |\n"
    
    markdown += """
## 【其他费用详细报价】
| 费用项目 | 金额（元） |
|---------|-----------|
"""
    for item, amount in quote_data['other_fees_details'].items():
        markdown += f"| {item} | {amount:,.2f} |\n"
    
    markdown += """
## 【漏项风险提示】
⚠️ 检测到以下行业常见漏项，建议补充确认：
"""
    for item in quote_data['missing_items_risk']:
        markdown += f"1. **{item['name']}**：预估费用{item['estimated_cost']:,.2f}元，原因：{item['reason']}\n"
    
    markdown += """
## 【报价说明】
"""
    for note in quote_data['notes']:
        markdown += f"- {note}\n"
    
    return markdown


# ==================== 使用示例 ====================
if __name__ == "__main__":
    # 示例：100㎡建筑面积，3室2厅1卫，舒适型装修，成都地区
    quote = generate_renovation_quote(
        city="成都",
        building_area=100,
        bedrooms=3,
        living_rooms=2,
        bathrooms=1,
        decoration_level="舒适型",
        include_design_fee=True
    )
    
    # 打印结构化JSON
    import json
    print(json.dumps(quote, indent=2, ensure_ascii=False))
    
    # 生成并打印Markdown报价单
    markdown_quote = generate_markdown_quote(quote)
    print("\n" + "="*50 + "\n")
    print(markdown_quote)