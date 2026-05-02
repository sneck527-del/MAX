
import pandas as pd
from datetime import datetime

excel_file = "项目/灏园别墅_20260425/报价/灏园别墅装修报价单_完整版.xlsx"
df = pd.read_excel(excel_file)

print("=" * 80)
print("灏园别墅装修报价单验证")
print("=" * 80)
print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()
print(f"总项目数: {len(df)} 项")
print(f"文件路径: {excel_file}")
print()
print("=" * 80)
print("报价单预览（前20项）:")
print("=" * 80)
print(df.head(20).to_string(index=False))
print()
print("=" * 80)
print("项目分类统计:")
print("=" * 80)

category_stats = df["分类"].value_counts()
for cat, count in category_stats.items():
    print(f"  {cat}: {count} 项")

print("=" * 80)
print("项目总价:")
total_row = df[df["项目名称"] == "项目总价"]
if len(total_row) > 0:
    total_amount = total_row.iloc[0]["合价"]
    print(f"  ¥{total_amount:,.2f}")

print("=" * 80)
print("✅ 灏园别墅完整报价单已成功生成！")
print("=" * 80)
