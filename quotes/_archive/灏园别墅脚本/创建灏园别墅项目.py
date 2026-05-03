
import os
import shutil
from datetime import datetime

print("=" * 60)
print("创建灏园别墅项目")
print("=" * 60)

# 创建项目文件夹
date_str = datetime.now().strftime("%Y%m%d")
project_name = "灏园别墅"
project_folder = f"{project_name}_{date_str}"
project_path = os.path.join("项目", project_folder)

print(f"\n创建项目文件夹: {project_path}")
os.makedirs(project_path, exist_ok=True)
os.makedirs(os.path.join(project_path, "图纸"), exist_ok=True)
os.makedirs(os.path.join(project_path, "报价"), exist_ok=True)
os.makedirs(os.path.join(project_path, "数据"), exist_ok=True)

# 复制报价模板
print("\n复制报价模板文件...")
shutil.copy2("完整装修报价模板.xlsx", os.path.join(project_path, "报价", "完整装修报价模板.xlsx"))
print("  完整装修报价模板.xlsx")

shutil.copy2("主材报价模板.xlsx", os.path.join(project_path, "报价", "主材报价模板.xlsx"))
print("  主材报价模板.xlsx")

shutil.copy2("轻工辅料模板.xlsx", os.path.join(project_path, "报价", "轻工辅料模板.xlsx"))
print("  轻工辅料模板.xlsx")

# 复制数据文件
print("\n复制数据文件...")
shutil.copy2("房间信息.json", os.path.join(project_path, "数据", "房间信息.json"))
print("  房间信息.json")

shutil.copy2("材料库.json", os.path.join(project_path, "数据", "材料库.json"))
print("  材料库.json")

shutil.copy2("施工库.json", os.path.join(project_path, "数据", "施工库.json"))
print("  施工库.json")

# 查找并复制截图文件
print("\n查找截图文件...")
screenshot_files = []
for filename in os.listdir("."):
    if filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")):
        screenshot_files.append(filename)

if screenshot_files:
    print(f"  找到 {len(screenshot_files)} 个截图文件:")
    for img_file in screenshot_files:
        shutil.copy2(img_file, os.path.join(project_path, "图纸", img_file))
        print(f"    {img_file}")
else:
    print("  未找到截图文件，请手动将CAD图纸截图放入'图纸'文件夹")

# 创建项目说明
print("\n创建项目说明文件...")
project_info = f"""
# 灏园别墅 - 装修项目

## 项目信息
- 项目名称: 灏园别墅
- 创建日期: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")
- 项目文件夹: {project_folder}

## 层高信息
- 一层: 3.07米
- 二层: 3.07米  
- 三层: 3.07米
- 地下室: 2.5米

## 文件结构
```
{project_folder}/
├── 图纸/
│   └── (在此放置CAD图纸截图)
├── 报价/
│   ├── 完整装修报价模板.xlsx   # 合并后的完整模板
│   ├── 主材报价模板.xlsx
│   └── 轻工辅料模板.xlsx
└── 数据/
    ├── 房间信息.json
    ├── 材料库.json
    └── 施工库.json
```
"""

with open(os.path.join(project_path, "项目说明.txt"), "w", encoding="utf-8"))
print("  项目说明.txt")

print("\n" + "=" * 60)
print("项目创建完成！")
print(f"   项目路径: {os.path.abspath(project_path)")
print("=" * 60)

# 显示项目结构
print("\n项目结构:")
for root, dirs, files in os.walk(project_path):
    level = root.replace(project_path, '').count(os.sep)
    indent = ' ' * 2 * level
    print(f'{indent}{os.path.basename(root)}/')
    subindent = ' ' * 2 * (level + 1)
    for file in files:
        print(f'{subindent}{file}')


