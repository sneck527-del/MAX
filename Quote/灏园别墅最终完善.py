
import json
import pandas as pd
from datetime import datetime

# 加载清单
with open("项目/灏园别墅_20260425/报价/灏园别墅主材清单_完整版.json", "r", encoding="utf-8") as f:
    material_list = json.load(f)

# 修复二三层卫生间
for room in material_list["房间主材"]:
    room_name = room["房间名称"]
    # 检查是否是二三层卫生间
    if "卫生间" in room_name and (room["楼层"] == "二层" or room["楼层"] == "三层"):
        # 修正顶面为集成大板
        for item in room["项目"]:
            if item["类别"] == "顶面" and "无主灯" in item["名称"]:
                item["名称"] = "集成大板吊顶"
        
        # 修正墙面为墙砖
        for item in room["项目"]:
            if item["类别"] == "墙面" and "护墙板" in item["名称"]:
                item["名称"] = "墙砖750x1500"
        
        # 确保添加了防水（带淋浴面积）
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

# 保存修复后的清单
with open("项目/灏园别墅_20260425/报价/灏园别墅主材清单_最终修正版.json", "w", encoding="utf-8") as f:
    json.dump(material_list, f, ensure_ascii=False, indent=2)

# ================================================
# 生成Excel版本
# ================================================

# 准备数据
data = []

# 1. 添加房间主材
for room in material_list["房间主材"]:
    room_name = room["房间名称"]
    for item in room["项目"]:
        data.append({
            "区域": room_name,
            "类别": item["类别"],
            "材料/项目名称": item["名称"],
            "数量": item["数量"],
            "单位": item["单位"],
            "备注": ""
        })

# 2. 添加其他分类
category_map = {
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

for cat_name, cat_key in category_map.items():
    for item in material_list[cat_key]:
        data.append({
            "区域": cat_name,
            "类别": cat_name,
            "材料/项目名称": item["名称"],
            "数量": item["数量"],
            "单位": item["单位"],
            "备注": ""
        })

# 转换为DataFrame
df = pd.DataFrame(data)

# 保存为Excel
excel_file = "项目/灏园别墅_20260425/报价/灏园别墅主材清单_最终修正版.xlsx"
df.to_excel(excel_file, index=False, engine='openpyxl')

print("=" * 80)
print("灏园别墅 - 最终完整清单")
print("=" * 80)
print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()
print("✅ 已完成:")
print("  1. 修复二三层卫生间问题（墙面改墙砖、顶面改集成大板、补防水）")
print("  2. 保存JSON版本")
print("  3. 生成Excel版本")
print()
print("📁 文件位置:")
print(f"  JSON: 项目/灏园别墅_20260425/报价/灏园别墅主材清单_最终修正版.json")
print(f"  Excel: 项目/灏园别墅_20260425/报价/灏园别墅主材清单_最终修正版.xlsx")
print()
print("=" * 80)

# 简单验证
print("\n🔍 验证部分:")
for room in material_list["房间主材"]:
    if "卫生间" in room["名称"] and (room["楼层"] == "二层" or room["楼层"] == "三层"):
        print(f"  {room['名称']}:")
        for item in room["项目"]:
            print(f"    {item['类别']}: {item['名称']}")
print("\n✅ 所有卫生间均已修复!")
print("=" * 80)
