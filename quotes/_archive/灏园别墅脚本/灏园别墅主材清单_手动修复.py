
import json

# 加载清单
with open("项目/灏园别墅_20260425/报价/灏园别墅主材清单.json", "r", encoding="utf-8") as f:
    material_list = json.load(f)

# 修复二三层卫生间和卧室
for room in material_list["房间主材"]:
    room_name = room["房间名称"]
    
    # 修复二三层卫生间
    if "卫生间" in room_name and (room["楼层"] == "二层" or room["楼层"] == "三层"):
        # 顶面改为集成大板吊顶
        for item in room["项目"]:
            if item["类别"] == "顶面" and "无主灯" in item["名称"]:
                item["名称"] = "集成大板吊顶"
        
        # 墙面改为墙砖
        for item in room["项目"]:
            if item["类别"] == "墙面" and "护墙板" in item["名称"]:
                item["名称"] = "墙砖750x1500"
        
        # 添加防水（二三层卫生间需要淋浴防水）
        has_waterproof = any(item["类别"] == "防水" for item in room["项目"])
        if not has_waterproof:
            import math
            floor_area = room["地面面积"]
            perimeter = math.sqrt(floor_area) * 4
            shower_area = 1.8 * 1.8
            waterproof_area = floor_area + 0.3 * perimeter + shower_area
            
            room["项目"].append({
                "类别": "防水",
                "名称": "墙地面防水",
                "数量": round(waterproof_area, 2),
                "单位": "平方米"
            })
    
    # 修复二三层卧室为壁布
    elif "卧室" in room_name and (room["楼层"] == "二层" or room["楼层"] == "三层"):
        for item in room["项目"]:
            if item["类别"] == "墙面" and "护墙板" in item["名称"]:
                item["名称"] = "壁布"

# 保存修复后的清单
with open("项目/灏园别墅_20260425/报价/灏园别墅主材清单.json", "w", encoding="utf-8") as f:
    json.dump(material_list, f, ensure_ascii=False, indent=2)

# 输出最终清单
print("=" * 80)
print("灏园别墅 - 主材清单")
print("=" * 80)

# 按楼层分组
floors = ["一层", "二层", "三层", "地下室", "庭院"]

for floor in floors:
    print("\n" + "=" * 80)
    print(f"{floor}")
    print("=" * 80)
    
    for room in material_list["房间主材"]:
        if room["楼层"] == floor:
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

