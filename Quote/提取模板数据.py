
import pandas as pd

# 读取轻工辅料模板
print("读取轻工辅料模板...")
df_construction = pd.read_excel("轻工辅料模板.xlsx", sheet_name="Sheet1")

# 解析模板数据
construction_items = []
current_section = ""

for idx, row in df_construction.iterrows():
    cell_0 = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
    
    # 检测结构位置标题
    if "结构位置：" in cell_0 and pd.notna(row.iloc[5]):
        current_section = cell_0
        continue
    
    # 检测有效数据行（有序号）
    if pd.notna(row.iloc[0]) and str(row.iloc[0]).isdigit():
        item_name = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ""
        unit_price = float(row.iloc[2]) if pd.notna(row.iloc[2]) else 0
        unit = str(row.iloc[3]) if pd.notna(row.iloc[3]) else ""
        qty = float(row.iloc[4]) if pd.notna(row.iloc[4]) else 0
        amount = float(row.iloc[5]) if pd.notna(row.iloc[5]) else 0
        material_desc = str(row.iloc[6]) if pd.notna(row.iloc[6]) else ""
        craft_desc = str(row.iloc[7]) if pd.notna(row.iloc[7]) else ""
        
        if item_name and unit_price > 0:
            construction_items.append({
                "name": item_name,
                "unit_price": unit_price,
                "unit": unit,
                "material_desc": material_desc,
                "craft_desc": craft_desc
            })

# 去重
unique_items = []
seen_names = set()
for item in construction_items:
    if item['name'] not in seen_names:
        seen_names.add(item['name'])
        unique_items.append(item)

print(f"\n提取到 {len(unique_items)} 个施工项目：")
for i, item in enumerate(unique_items[:20], 1):
    print(f"{i}. {item['name']} ({item['unit_price']}元/{item['unit']})")

# 保存到JSON
import json
with open("模板施工项目.json", "w", encoding="utf-8") as f:
    json.dump(unique_items, f, ensure_ascii=False, indent=2)

print("\n已保存到 模板施工项目.json")

# 读取主材模板
print("\n读取主材模板...")
df_material = pd.read_excel("主材报价模板.xlsx", sheet_name="Sheet1")

material_items = []
for idx, row in df_material.iterrows():
    cell_0 = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
    
    if pd.notna(row.iloc[0]) and str(row.iloc[0]).isdigit():
        item_name = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ""
        qty = float(row.iloc[2]) if pd.notna(row.iloc[2]) else 0
        unit = str(row.iloc[3]) if pd.notna(row.iloc[3]) else ""
        unit_price = float(row.iloc[4]) if pd.notna(row.iloc[4]) else 0
        amount = float(row.iloc[5]) if pd.notna(row.iloc[5]) else 0
        remark = str(row.iloc[6]) if pd.notna(row.iloc[6]) else ""
        brand = str(row.iloc[7]) if pd.notna(row.iloc[7]) else ""
        
        if item_name and unit_price > 0:
            material_items.append({
                "name": item_name,
                "unit_price": unit_price,
                "unit": unit,
                "remark": remark,
                "brand": brand
            })

# 去重
unique_materials = []
seen_materials = set()
for item in material_items:
    if item['name'] not in seen_materials:
        seen_materials.add(item['name'])
        unique_materials.append(item)

print(f"\n提取到 {len(unique_materials)} 个主材项目：")
for i, item in enumerate(unique_materials[:20], 1):
    print(f"{i}. {item['name']} ({item['unit_price']}元/{item['unit']})")

with open("模板主材项目.json", "w", encoding="utf-8") as f:
    json.dump(unique_materials, f, ensure_ascii=False, indent=2)

print("\n已保存到 模板主材项目.json")

