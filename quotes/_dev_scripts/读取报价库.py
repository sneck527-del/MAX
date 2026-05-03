
import pandas as pd
import json
import os

try:
    excel_file = pd.ExcelFile('报价库.xlsx')
    
    print("工作表列表:")
    for i, sheet_name in enumerate(excel_file.sheet_names):
        print(f"  {i+1}. {sheet_name}")
    
    print("\n开始读取所有工作表...")
    
    for sheet_name in excel_file.sheet_names:
        print(f"\n读取: {sheet_name}")
        df = pd.read_excel('报价库.xlsx', sheet_name=sheet_name)
        
        json_filename = f"{sheet_name}.json"
        df.to_json(json_filename, force_ascii=False, orient='records')
        print(f"  已保存为: {json_filename}")
        print(f"  列名: {list(df.columns)}")
        print(f"  行数: {len(df)}")
        
        if len(df) > 0:
            print("  前10行数据:")
            print(df.head(10).to_string())
    
    print("\n完成！")
    
except FileNotFoundError:
    print("找不到报价库.xlsx文件")
except Exception as e:
    print(f"读取文件时出错: {e}")
    import traceback
    traceback.print_exc()

