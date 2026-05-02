
import json
import pandas as pd
from datetime import datetime

# 1. 读取灏园别墅完整清单
with open("项目/灏园别墅_20260425/报价/灏园别墅主材清单_最终修正版.json", "r", encoding="utf-8") as f:
    material_list = json.load(f)

# 2. 创建装饰公司标准价格库（根据市场行情）
price_library = {
    "地砖1800x900": {"price": 280, "unit": "平方米", "desc": "1800x900规格地砖铺贴（含辅料）"},
    "地砖750x1500": {"price": 220, "unit": "平方米", "desc": "750x1500规格地砖铺贴（含辅料）"},
    "火烧板800x800": {"price": 150, "unit": "平方米", "desc": "800x800火烧板铺贴（庭院）"},
    "墙砖750x1500": {"price": 200, "unit": "平方米", "desc": "750x1500墙砖铺贴（含辅料）"},
    "墙砖900x1800": {"price": 260, "unit": "平方米", "desc": "900x1800墙砖铺贴（含辅料）"},
    "集成PET墙板": {"price": 320, "unit": "平方米", "desc": "集成PET墙板安装"},
    "无主灯造型吊顶": {"price": 380, "unit": "平方米", "desc": "轻钢龙骨石膏板吊顶，含造型设计"},
    "集成大板吊顶": {"price": 420, "unit": "平方米", "desc": "集成大板吊顶（含龙骨）"},
    "木饰面吊顶": {"price": 480, "unit": "平方米", "desc": "木饰面吊顶"},
    "软膜天花": {"price": 260, "unit": "平方米", "desc": "软膜天花吊顶"},
    "墙地面防水": {"price": 120, "unit": "平方米", "desc": "聚氨酯防水涂料，涂刷2遍，含闭水试验"},
    "地面墙面防水": {"price": 110, "unit": "平方米", "desc": "地下室地面墙面防潮防水（专用材料）"},
    "壁布": {"price": 160, "unit": "平方米", "desc": "墙布铺贴（含基膜胶水）"},
    "护墙板": {"price": 380, "unit": "平方米", "desc": "护墙板安装（含基层）"}
}

# 3. 定制家具价格
custom_furniture_prices = {
    "一层厨房地柜": {"price": 1800, "unit": "米", "desc": "厨房地柜（颗粒板）"},
    "一层厨房吊柜": {"price": 1200, "unit": "米", "desc": "厨房吊柜（颗粒板）"},
    "一层厨房台面": {"price": 1500, "unit": "米", "desc": "石英石台面"},
    "一层玄关鞋柜": {"price": 2200, "unit": "平方米", "desc": "玄关鞋柜定制"},
    "二层儿童房衣柜": {"price": 2200, "unit": "平方米", "desc": "儿童房衣柜（多层板）"},
    "二层儿童房2衣柜": {"price": 2200, "unit": "平方米", "desc": "儿童房衣柜（多层板）"},
    "二层主卧大衣柜": {"price": 2500, "unit": "平方米", "desc": "主卧大衣柜（多层板）"},
    "三层次卧衣柜": {"price": 2200, "unit": "平方米", "desc": "次卧衣柜（多层板）"},
    "三层主卧大衣柜": {"price": 2500, "unit": "平方米", "desc": "主卧大衣柜（多层板）"},
    "三层衣帽间定制": {"price": 2800, "unit": "平方米", "desc": "衣帽间定制（多层板）"},
    "地下室衣帽间定制": {"price": 2600, "unit": "平方米", "desc": "地下室衣帽间定制（多层板）"},
    "地下室洗衣柜": {"price": 2000, "unit": "米", "desc": "洗衣柜定制"},
    "电视柜（客厅）": {"price": 2200, "unit": "米", "desc": "电视柜定制"},
    "酒柜（餐厅）": {"price": 2600, "unit": "平方米", "desc": "酒柜定制"}
}

# 4. 门窗类价格
door_window_prices = {
    "别墅入户大门": {"price": 18000, "unit": "樘", "desc": "别墅入户铜门或铸铝门"},
    "卧室木门": {"price": 3800, "unit": "樘", "desc": "实木复合卧室门"},
    "卫生间钛镁合金门": {"price": 2600, "unit": "樘", "desc": "钛镁合金平开门"},
    "厨房推拉门": {"price": 3800, "unit": "樘", "desc": "厨房推拉门（窄边）"},
    "书房门": {"price": 3500, "unit": "樘", "desc": "实木复合书房门"},
    "衣帽间门": {"price": 3200, "unit": "樘", "desc": "衣帽间门"},
    "保姆房门": {"price": 2800, "unit": "樘", "desc": "保姆房门"},
    "阳台推拉门": {"price": 4200, "unit": "樘", "desc": "阳台推拉门（窄边）"},
    "门套/窗套": {"price": 180, "unit": "米", "desc": "门套/窗套"},
    "全屋窗台石": {"price": 320, "unit": "米", "desc": "窗台石（人造石）"},
    "全屋飘窗石": {"price": 380, "unit": "米", "desc": "飘窗石（人造石）"}
}

# 5. 石材类价格
stone_prices = {
    "全屋门槛石": {"price": 320, "unit": "米", "desc": "门槛石（大理石）"},
    "淋浴基石": {"price": 650, "unit": "条", "desc": "淋浴基石（大理石）"},
    "挡水条": {"price": 280, "unit": "米", "desc": "挡水条（大理石）"},
    "楼梯踏步石材": {"price": 1200, "unit": "步", "desc": "楼梯踏步（大理石）"},
    "楼梯平台石材": {"price": 1500, "unit": "平方米", "desc": "楼梯平台（大理石）"}
}

# 6. 灯具类价格
light_prices = {
    "客厅主灯": {"price": 5800, "unit": "个", "desc": "客厅主灯（现代简约）"},
    "餐厅吊灯": {"price": 3500, "unit": "个", "desc": "餐厅吊灯"},
    "卧室主灯": {"price": 2200, "unit": "个", "desc": "卧室主灯"},
    "厨房灯": {"price": 420, "unit": "个", "desc": "厨房LED平板灯"},
    "卫生间浴霸/风暖": {"price": 1800, "unit": "个", "desc": "浴霸/风暖"},
    "全屋筒灯": {"price": 120, "unit": "个", "desc": "LED筒灯"},
    "全屋射灯": {"price": 160, "unit": "个", "desc": "LED射灯"},
    "全屋LED灯带": {"price": 65, "unit": "米", "desc": "LED灯带"},
    "阳台灯": {"price": 320, "unit": "个", "desc": "阳台LED灯"},
    "楼梯感应灯": {"price": 280, "unit": "个", "desc": "楼梯感应灯"},
    "车库灯": {"price": 420, "unit": "个", "desc": "车库LED灯"}
}

# 7. 五金类价格
hardware_prices = {
    "全屋门吸": {"price": 85, "unit": "个", "desc": "门吸"},
    "全屋合页": {"price": 95, "unit": "个", "desc": "不锈钢合页"},
    "全屋门锁": {"price": 680, "unit": "套", "desc": "门锁"},
    "全屋窗帘轨道": {"price": 180, "unit": "米", "desc": "窗帘轨道"},
    "全屋窗帘盒": {"price": 120, "unit": "米", "desc": "窗帘盒"},
    "橱柜五金": {"price": 1500, "unit": "套", "desc": "橱柜五金（铰链、拉手、拉篮）"},
    "衣柜五金": {"price": 850, "unit": "套", "desc": "衣柜五金（铰链、拉手、抽屉）"},
    "卫浴五金": {"price": 850, "unit": "套", "desc": "卫浴五金（毛巾架、置物架、纸巾架）"},
    "挂衣杆": {"price": 95, "unit": "米", "desc": "挂衣杆"},
    "抽屉轨道": {"price": 160, "unit": "个", "desc": "抽屉轨道"}
}

# 8. 设备类价格
equipment_prices = {
    "中央空调": {"price": 85000, "unit": "套", "desc": "中央空调（一拖六或一拖七）"},
    "新风系统": {"price": 28000, "unit": "套", "desc": "中央新风系统"},
    "全屋净水系统": {"price": 15000, "unit": "套", "desc": "全屋净水系统（前置+中央净水+末端直饮）"},
    "全屋智能家居": {"price": 35000, "unit": "套", "desc": "全屋智能家居（智能开关、智能门锁、智能窗帘等）"},
    "智能坐便器": {"price": 4200, "unit": "套", "desc": "智能坐便器"},
    "淋浴花洒": {"price": 2200, "unit": "套", "desc": "恒温淋浴花洒"},
    "浴缸+龙头": {"price": 8500, "unit": "套", "desc": "独立浴缸+龙头"},
    "浴室风暖": {"price": 1800, "unit": "套", "desc": "浴室风暖"},
    "厨房集成灶": {"price": 12000, "unit": "套", "desc": "集成灶"},
    "嵌入式洗碗机": {"price": 6500, "unit": "套", "desc": "嵌入式洗碗机"},
    "嵌入式蒸烤箱": {"price": 8500, "unit": "套", "desc": "嵌入式蒸烤箱"},
    "嵌入式冰箱": {"price": 18000, "unit": "套", "desc": "嵌入式冰箱"},
    "全屋灯具": {"price": 35000, "unit": "套", "desc": "全屋灯具（含所有室内灯具）"},
    "电动晾衣架": {"price": 2500, "unit": "套", "desc": "电动晾衣架"}
}

# 9. 上下水类价格
plumbing_prices = {
    "PPR给水管": {"price": 120, "unit": "米", "desc": "PPR给水管（含辅料安装）"},
    "PVC排水管": {"price": 95, "unit": "米", "desc": "PVC排水管（含辅料安装）"},
    "角阀": {"price": 85, "unit": "个", "desc": "角阀（含安装）"},
    "水龙头": {"price": 650, "unit": "套", "desc": "面盆/厨房水龙头（含安装）"},
    "水槽": {"price": 2200, "unit": "套", "desc": "厨房水槽（含龙头）"},
    "淋浴房": {"price": 5500, "unit": "套", "desc": "淋浴房（含安装）"},
    "浴室柜": {"price": 4500, "unit": "套", "desc": "浴室柜（含台盆、龙头）"},
    "卫浴挂件": {"price": 850, "unit": "套", "desc": "卫浴挂件套装"}
}

# 10. 强弱电类价格
electrical_prices = {
    "国标电线2.5mm": {"price": 95, "unit": "米", "desc": "国标铜芯电线2.5mm（含穿线）"},
    "国标电线4mm": {"price": 125, "unit": "米", "desc": "国标铜芯电线4mm（含穿线）"},
    "国标电线6mm": {"price": 160, "unit": "米", "desc": "国标铜芯电线6mm（含穿线）"},
    "穿线管": {"price": 42, "unit": "米", "desc": "PVC穿线管"},
    "底盒": {"price": 18, "unit": "个", "desc": "开关插座底盒"},
    "开关面板": {"price": 85, "unit": "个", "desc": "开关面板（含安装）"},
    "插座面板": {"price": 75, "unit": "个", "desc": "插座面板（含安装）"},
    "强电箱": {"price": 1800, "unit": "套", "desc": "强电箱（含空开）"},
    "弱电箱": {"price": 1200, "unit": "套", "desc": "弱电箱（含模块）"},
    "网线": {"price": 42, "unit": "米", "desc": "六类网线（含布线）"},
    "电话线": {"price": 18, "unit": "米", "desc": "电话线（含布线）"},
    "有线电视线": {"price": 28, "unit": "米", "desc": "有线电视线（含布线）"}
}

# 11. 杂项类价格
misc_prices = {
    "全屋瓷砖美缝": {"price": 65, "unit": "平方米", "desc": "瓷砖美缝（含材料）"},
    "全屋开荒保洁": {"price": 3500, "unit": "户", "desc": "全屋开荒保洁"},
    "全屋精保洁": {"price": 1800, "unit": "户", "desc": "精保洁"},
    "成品保护费": {"price": 1200, "unit": "户", "desc": "成品保护（含电梯走廊等）"},
    "垃圾清运费": {"price": 4500, "unit": "户", "desc": "装修垃圾清运（不含外运）"},
    "垃圾外运费": {"price": 3500, "unit": "户", "desc": "垃圾外运（按实际）"},
    "材料上楼费": {"price": 4500, "unit": "户", "desc": "材料上楼搬运费"},
    "材料运输费": {"price": 2500, "unit": "户", "desc": "材料运输费"},
    "打孔费": {"price": 85, "unit": "个", "desc": "打孔费（空调、热水器等）"},
    "综合管理费": {"price": 18000, "unit": "项", "desc": "综合管理费（10-12%）"},
    "设计费": {"price": 12000, "unit": "项", "desc": "设计费（设计+图纸+服务）"},
    "楼梯扶手": {"price": 850, "unit": "米", "desc": "楼梯扶手（实木或金属）"},
    "楼梯栏杆": {"price": 750, "unit": "米", "desc": "楼梯栏杆（玻璃或金属）"},
    "地下室防潮处理": {"price": 120, "unit": "平方米", "desc": "地下室防潮处理"},
    "电视背景墙造型": {"price": 5500, "unit": "项", "desc": "电视背景墙造型"},
    "沙发背景墙造型": {"price": 4500, "unit": "项", "desc": "沙发背景墙造型"},
    "餐厅背景墙造型": {"price": 3500, "unit": "项", "desc": "餐厅背景墙造型"},
    "主卧背景墙造型": {"price": 3200, "unit": "项", "desc": "主卧背景墙造型"}
}

# 12. 合并所有价格库
all_prices = {}
all_prices.update(price_library)
all_prices.update(custom_furniture_prices)
all_prices.update(door_window_prices)
all_prices.update(stone_prices)
all_prices.update(light_prices)
all_prices.update(hardware_prices)
all_prices.update(equipment_prices)
all_prices.update(plumbing_prices)
all_prices.update(electrical_prices)
all_prices.update(misc_prices)

# 13. 准备Excel数据
excel_data = []
total_amount = 0

# 14. 处理房间主材
for room in material_list["房间主材"]:
    room_name = room["房间名称"]
    for item in room["项目"]:
        item_name = item["名称"]
        qty = item["数量"]
        
        price_info = all_prices.get(item_name, {})
        price = price_info.get("price", 0)
        unit = price_info.get("unit", item["unit"])
        desc = price_info.get("desc", "待确认")
        amount = round(qty * price, 2)
        total_amount += amount
        
        excel_data.append({
            "序号": len(excel_data) + 1,
            "区域": room_name,
            "分类": item["类别"],
            "项目名称": item_name,
            "项目说明": desc,
            "单位": unit,
            "数量": qty,
            "单价": price,
            "合价": amount
        })

# 15. 处理设备类
category_mapping = {
    "设备类": "设备类",
    "上下水类": "上下水类",
    "强弱电类": "强弱电类",
    "定制家具类": "定制家具类",
    "门窗类": "门窗类",
    "石材类": "石材类",
    "灯具类": "灯具类",
    "五金类": "五金类",
    "杂项类": "杂项类"
}

for cat_name, cat_key in category_mapping.items():
    for item in material_list[cat_key]:
        item_name = item["名称"]
        qty = item["数量"]
        
        price_info = all_prices.get(item_name, {})
        price = price_info.get("price", 0)
        unit = price_info.get("unit", item["unit"])
        desc = price_info.get("desc", "待确认")
        amount = round(qty * price, 2)
        total_amount += amount
        
        excel_data.append({
            "序号": len(excel_data) + 1,
            "区域": cat_name,
            "分类": cat_name,
            "项目名称": item_name,
            "项目说明": desc,
            "单位": unit,
            "数量": qty,
            "单价": price,
            "合价": amount
        })

# 16. 添加总价行
excel_data.append({
    "序号": "",
    "区域": "",
    "分类": "合计",
    "项目名称": "项目总价",
    "项目说明": "",
    "单位": "",
    "数量": "",
    "单价": "",
    "合价": total_amount
})

# 17. 保存到Excel
df = pd.DataFrame(excel_data)
excel_file = "项目/灏园别墅_20260425/报价/灏园别墅装修报价单_完整版.xlsx"
df.to_excel(excel_file, index=False, engine='openpyxl')

print("=" * 80)
print("灏园别墅装修报价单（完整版）")
print("=" * 80)
print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"项目总价: ¥{total_amount:,.2f}")
print()
print("文件已保存至:")
print(f"  {excel_file}")
print("=" * 80)
