
import pandas as pd
import json

with open("主材模板内容.txt", "w", encoding="utf-8") as f:
    f.write("=" * 60 + "\n")
    f.write("读取主材报价模板.xlsx\n")
    f.write("=" * 60 + "\n")
    
    try:
        excel_material = pd.ExcelFile("主材报价模板.xlsx")
        f.write(f"\n工作表列表: {excel_material.sheet_names}\n")
        
        for sheet_name in excel_material.sheet_names:
            f.write(f"\n--- {sheet_name} ---\n")
            df = pd.read_excel("主材报价模板.xlsx", sheet_name=sheet_name)
            f.write(f"列名: {list(df.columns)}\n")
            f.write(f"行数: {len(df)}\n")
            f.write(f"\n完整数据:\n")
            f.write(df.to_string())
            
    except Exception as e:
        f.write(f"错误: {e}\n")
        import traceback
        f.write(traceback.format_exc())

with open("轻工辅料模板内容.txt", "w", encoding="utf-8") as f:
    f.write("=" * 60 + "\n")
    f.write("读取轻工辅料模板.xlsx\n")
    f.write("=" * 60 + "\n")
    
    try:
        excel_construction = pd.ExcelFile("轻工辅料模板.xlsx")
        f.write(f"\n工作表列表: {excel_construction.sheet_names}\n")
        
        for sheet_name in excel_construction.sheet_names:
            f.write(f"\n--- {sheet_name} ---\n")
            df = pd.read_excel("轻工辅料模板.xlsx", sheet_name=sheet_name)
            f.write(f"列名: {list(df.columns)}\n")
            f.write(f"行数: {len(df)}\n")
            f.write(f"\n完整数据:\n")
            f.write(df.to_string())
            
    except Exception as e:
        f.write(f"错误: {e}\n")
        import traceback
        f.write(traceback.format_exc())

print("文件已保存: 主材模板内容.txt, 轻工辅料模板内容.txt")

