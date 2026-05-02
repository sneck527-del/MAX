
import pandas as pd
import json

print("开始解析报价库...\n")

# 解析主材数据库
print("1. 解析主材数据库...")
df_material = pd.read_excel('报价库.xlsx', sheet_name='主材数据库')
df_material.columns = ['col0', '分类', '部品', '项目_主材名称', '内容_图片', '单位', 'col6', 'col7', '单价', '人工技术服务费', '材料采购价格', '费率计算', '费率报价', '供货商', '联系方式', '采购链接', '发货地', '供货周期', '服务费计算方式', '服务流程']
df_material = df_material[4:].reset_index(drop=True)
df_material = df_material.dropna(subset=['分类', '项目_主材名称'], how='all')

material_data = {}
for _, row in df_material.iterrows():
    category = row['分类']
    if pd.isna(category):
        continue
    if category not in material_data:
        material_data[category] = {}
    
    sub_category = row['部品']
    if pd.isna(sub_category):
        sub_category = '其他'
    if sub_category not in material_data[category]:
        material_data[category][sub_category] = []
    
    item = {
        '名称': row['项目_主材名称'],
        '单位': row['单位'],
        '单价': row['单价'],
        '人工技术服务费': row['人工技术服务费'],
        '材料采购价格': row['材料采购价格'],
        '供货商': row['供货商'],
        '联系方式': row['联系方式']
    }
    material_data[category][sub_category].append(item)

with open('主材库_解析.json', 'w', encoding='utf-8') as f:
    json.dump(material_data, f, ensure_ascii=False, indent=2)
print(f"   已解析 {len(df_material)} 条主材数据，保存到 主材库_解析.json")

# 解析预算库（轻工辅料库）
print("\n2. 解析预算库（轻工辅料库）...")
df_budget = pd.read_excel('报价库.xlsx', sheet_name='Sheet4')
df_budget.columns = ['col0', '分类', '工种', '项目', '单位', '材料费', '人工费', '综合报价', '材料成本_单价', '人工成本_单价', '发包成本_单价', '毛利', '毛利率', '计算方式', '工艺要求与标准']
df_budget = df_budget[3:].reset_index(drop=True)
df_budget = df_budget.dropna(subset=['分类', '项目'], how='all')

budget_data = {}
for _, row in df_budget.iterrows():
    category = row['分类']
    if pd.isna(category):
        continue
    if category not in budget_data:
        budget_data[category] = []
    
    item = {
        '项目': row['项目'],
        '工种': row['工种'],
        '单位': row['单位'],
        '材料费': row['材料费'],
        '人工费': row['人工费'],
        '综合报价': row['综合报价'],
        '工艺要求与标准': row['工艺要求与标准']
    }
    budget_data[category].append(item)

with open('施工库_解析.json', 'w', encoding='utf-8') as f:
    json.dump(budget_data, f, ensure_ascii=False, indent=2)
print(f"   已解析 {len(df_budget)} 条施工数据，保存到 施工库_解析.json")

# 打印分类预览
print("\n3. 数据预览：")
print("   主材库分类:")
for cat in material_data.keys():
    sub_cats = list(material_data[cat].keys())
    print(f"     - {cat} ({len(sub_cats)} 个子分类)")

print("\n   施工库分类:")
for cat in budget_data.keys():
    print(f"     - {cat} ({len(budget_data[cat])} 个项目)")

print("\n解析完成！")

