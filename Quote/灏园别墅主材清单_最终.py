
import json
from datetime import datetime

# 房间数据
with open("项目/灏园别墅_20260425/数据/房间信息.json", "r", encoding="utf-8") as f:
    room_data = json.load(f)

# 按楼层组织
rooms_by_floor = {
    "一层": [],
    "二层": [],
    "三层": [],
    "地下室": [],
    "庭院": []
}

for room in room_data['房间']:
    floor_name = room['名称'].split('-')[0]
    if floor_name in rooms_by_floor:
        rooms_by_floor[floor_name].append(room)

# 添加庭院
rooms_by_floor["庭院"].append({
    "名称": "庭院",
    "地面面积": 127.635,
    "墙面面积": 0,
    "顶面面积": 0
})

# 主材清单
material_list = {
    "房间主材": [],
    "设备类": [],
    "上下水类": [],
    "强弱电类": [],
    "拆除砌筑类": []
}

# 处理每个房间
for floor, rooms in rooms_by_floor.items():
    for room in rooms:
        room_name = room['名称']
        floor_area = room['地面面积']
        wall_area = room['墙面面积']
        ceiling_area = room['顶面面积']
        
        room_materials = {
            "房间名称": room_name,
            "楼层": floor,
            "地面面积": floor_area,
            "墙面面积": wall_area,
            "顶面面积": ceiling_area,
            "项目": []
        }
        
        # 地面材料
        if room_name in ["一层-客厅", "一层-餐厅", "一层-玄关", "一层-厨房", "一层-楼梯间"]:
            room_materials["项目"].append({
                "类别": "地面",
                "名称": "地砖1800x900",
                "数量": round(floor_area, 2),
                "单位": "平方米"
            })
        elif room_name == "庭院":
            room_materials["项目"].append({
                "类别": "地面",
                "名称": "火烧板800x800",
                "数量": round(floor_area, 2),
                "单位": "平方米"
            })
        else:
            room_materials["项目"].append({
                "类别": "地面",
                "名称": "地砖750x1500",
                "数量": round(floor_area, 2),
                "单位": "平方米"
            })
        
        # 顶面材料
        if "卫生间" in room_name or "设备间" in room_name or "厨房" in room_name:
            room_materials["项目"].append({
                "类别": "顶面",
                "名称": "集成大板吊顶",
                "数量": round(ceiling_area, 2),
                "单位": "平方米"
            })
        elif "车库" in room_name:
            room_materials["项目"].append({
                "类别": "顶面",
                "名称": "木饰面吊顶",
                "数量": round(ceiling_area, 2),
                "单位": "平方米"
            })
            room_materials["项目"].append({
                "类别": "顶面",
                "名称": "软膜天花",
                "数量": round(ceiling_area * 0.5, 2),
                "单位": "平方米"
            })
        elif room_name == "庭院":
            pass
        else:
            room_materials["项目"].append({
                "类别": "顶面",
                "名称": "无主灯造型吊顶",
                "数量": round(ceiling_area, 2),
                "单位": "平方米"
            })
        
        # 墙面材料
        if "卫生间" in room_name:
            room_materials["项目"].append({
                "类别": "墙面",
                "名称": "墙砖750x1500",
                "数量": round(wall_area, 2),
                "单位": "平方米"
            })
        elif "厨房" in room_name:
            room_materials["项目"].append({
                "类别": "墙面",
                "名称": "墙砖900x1800",
                "数量": round(wall_area, 2),
                "单位": "平方米"
            })
        elif "洗衣房" in room_name or "设备间" in room_name or "车库" in room_name:
            room_materials["项目"].append({
                "类别": "墙面",
                "名称": "集成PET墙板",
                "数量": round(wall_area, 2),
                "单位": "平方米"
            })
        elif "卧室" in room_name or "衣帽间" in room_name:
            room_materials["项目"].append({
                "类别": "墙面",
                "名称": "壁布",
                "数量": round(wall_area, 2),
                "单位": "平方米"
            })
        elif room_name == "庭院":
            pass
        else:
            room_materials["项目"].append({
                "类别": "墙面",
                "名称": "护墙板",
                "数量": round(wall_area, 2),
                "单位": "平方米"
            })
        
        # 防水
        has_waterproof = False
        if "卫生间" in room_name:
            has_waterproof = True
        if floor == "地下室":
            has_waterproof = True
        
        if has_waterproof:
            import math
            perimeter = math.sqrt(floor_area) * 4
            shower_area = 0
            if floor not in ["一层", "地下室"] and "卫生间" in room_name:
                shower_area = 1.8 * 1.8
            waterproof_area = floor_area + 0.3 * perimeter + shower_area
            
            if floor == "地下室":
                room_materials["项目"].append({
                    "类别": "防水",
                    "名称": "地面墙面防水",
                    "数量": round(floor_area + wall_area, 2),
                    "单位": "平方米"
                })
            else:
                room_materials["项目"].append({
                    "类别": "防水",
                    "名称": "墙地面防水",
                    "数量": round(waterproof_area, 2),
                    "单位": "平方米"
                })
        
        material_list["房间主材"].append(room_materials)

# 设备
material_list["设备类"] = [
    {"名称": "中央空调", "数量": 1, "单位": "套"},
    {"名称": "新风系统", "数量": 1, "单位": "套"},
    {"名称": "全屋净水系统", "数量": 1, "单位": "套"},
    {"名称": "全屋智能家居", "数量": 1, "单位": "套"},
    {"名称": "智能坐便器", "数量": 6, "单位": "套"},
    {"名称": "淋浴花洒", "数量": 6, "单位": "套"},
    {"名称": "浴缸+龙头", "数量": 2, "单位": "套"},
    {"名称": "浴室风暖", "数量": 6, "单位": "套"},
    {"名称": "厨房集成灶", "数量": 1, "单位": "套"},
    {"名称": "嵌入式洗碗机", "数量": 1, "单位": "套"},
    {"名称": "嵌入式蒸烤箱", "数量": 1, "单位": "套"},
    {"名称": "嵌入式冰箱", "数量": 2, "单位": "套"},
    {"名称": "全屋灯具", "数量": 1, "单位": "套"},
    {"名称": "电动晾衣架", "数量": 2, "单位": "套"}
]

# 上下水
material_list["上下水类"] = [
    {"名称": "PPR给水管", "数量": 200, "单位": "米"},
    {"名称": "PVC排水管", "数量": 100, "单位": "米"},
    {"名称": "角阀", "数量": 30, "单位": "个"},
    {"名称": "水龙头", "数量": 10, "单位": "套"},
    {"名称": "水槽", "数量": 2, "单位": "套"},
    {"名称": "淋浴房", "数量": 4, "单位": "套"},
    {"名称": "浴室柜", "数量": 6, "单位": "套"},
    {"名称": "卫浴挂件", "数量": 6, "单位": "套"}
]

# 强弱电
material_list["强弱电类"] = [
    {"名称": "国标电线2.5mm", "数量": 1000, "单位": "米"},
    {"名称": "国标电线4mm", "数量": 500, "单位": "米"},
    {"名称": "国标电线6mm", "数量": 100, "单位": "米"},
    {"名称": "穿线管", "数量": 500, "单位": "米"},
    {"名称": "底盒", "数量": 100, "单位": "个"},
    {"名称": "开关面板", "数量": 80, "单位": "个"},
    {"名称": "插座面板", "数量": 120, "单位": "个"},
    {"名称": "强电箱", "数量": 1, "单位": "套"},
    {"名称": "弱电箱", "数量": 1, "单位": "套"},
    {"名称": "网线", "数量": 300, "单位": "米"},
    {"名称": "电话线", "数量": 100, "单位": "米"},
    {"名称": "有线电视线", "数量": 100, "单位": "米"}
]

# 拆除砌筑
material_list["拆除砌筑类"] = [
    {"名称": "墙体拆除", "数量": 30, "单位": "平方米"},
    {"名称": "建筑垃圾清运", "数量": 1, "单位": "户"},
    {"名称": "砌筑新墙体", "数量": 40, "单位": "平方米"},
    {"名称": "地面找平", "数量": 619, "单位": "平方米"},
    {"名称": "地面回填", "数量": 50, "单位": "平方米"},
    {"名称": "下水管静音处理", "数量": 50, "单位": "米"},
    {"名称": "烟道挂网", "数量": 10, "单位": "米"},
    {"名称": "红砖包管道", "数量": 30, "单位": "米"}
]

# 保存
with open("项目/灏园别墅_20260425/报价/灏园别墅主材清单.json", "w", encoding="utf-8") as f:
    json.dump(material_list, f, ensure_ascii=False, indent=2)

# 生成报告
print("=" * 80)
print("灏园别墅 - 主材清单")
print("=" * 80)
print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("")

for floor in rooms_by_floor.keys():
    print("\n" + "=" * 80)
    print(f"{floor}")
    print("=" * 80)
    
    floor_rooms = [r for r in material_list["房间主材"] if r["楼层"] == floor]
    for room in floor_rooms:
        print(f"\n【{room['房间名称']}】")
        print(f"  地面: {room['地面面积']}㎡ | 墙面: {room['墙面面积']}㎡ | 顶面: {room['顶面面积']}㎡")
        for item in room["项目"]:
            print(f"    [{item['类别']}] {item['名称']}: {item['数量']} {item['单位']}")

print("\n" + "=" * 80)
print("【设备类】")
print("=" * 80)
for item in material_list["设备类"]:
    print(f"  {item['名称']}: {item['数量']} {item['单位']}")

print("\n" + "=" * 80)
print("【上下水类】")
print("=" * 80)
for item in material_list["上下水类"]:
    print(f"  {item['名称']}: {item['数量']} {item['单位']}")

print("\n" + "=" * 80)
print("【强弱电类】")
print("=" * 80)
for item in material_list["强弱电类"]:
    print(f"  {item['名称']}: {item['数量']} {item['单位']}")

print("\n" + "=" * 80)
print("【拆除砌筑类】")
print("=" * 80)
for item in material_list["拆除砌筑类"]:
    print(f"  {item['名称']}: {item['数量']} {item['单位']}")

print("\n" + "=" * 80)
print("清单已保存至: 项目/灏园别墅_20260425/报价/灏园别墅主材清单.json")
print("=" * 80)

