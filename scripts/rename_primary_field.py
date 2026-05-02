"""将飞书多维表格的"多行文本"主字段重命名为业务字段

飞书新建表时自动生成"多行文本"作为主字段（Primary Field），无法删除。
此脚本将其重命名为该表最合适的业务字段名，同时清理可能重复的字段。

用法: python -m scripts.rename_primary_field
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from max_system.config.settings import get_settings
from max_system.integrations.feishu.api_client import FeishuApiClient

# 每个表的主字段应重命名的目标名称
PRIMARY_FIELD_NAMES = {
    "客户信息表": "客户姓名",
    "项目台账表": "项目名称",
    "售后维保台账": "项目名称",
    "合同管理表": "合同编号",
    "供应商表": "供应商名称",
    "回访记录表": "客户姓名",
    "跟进记录表": "客户姓名",
    "谈单账目表": "客户姓名",
}

TABLE_INFOS = [
    ("tblIxjtaLphlbCnq", "客户信息表"),
    ("tblMq9dKmxqok7Yd", "项目台账表"),
    ("tbliy6uD9WeHBjY5", "售后维保台账"),
    ("tblYK0k9DL4rS8HX", "合同管理表"),
    ("tblj0ggjNAUSnM6q", "供应商表"),
    ("tblGKolCVrikc94G", "回访记录表"),
    ("tbljvs4iKtp6GJMA", "跟进记录表"),
    ("tblavuqWrGIY6JUr", "谈单账目表"),
]


async def main():
    settings = get_settings()
    client = FeishuApiClient(settings)

    for table_id, table_name in TABLE_INFOS:
        fields = await client.list_bitable_fields(table_id)
        target_name = PRIMARY_FIELD_NAMES[table_name]

        # 找到多行文本字段（即主字段）
        multi_fields = [f for f in fields if f.get("field_name") == "多行文本"]
        if not multi_fields:
            print(f"[跳过] {table_name}: 没有多行文本字段")
            continue

        primary_field = multi_fields[0]
        primary_id = primary_field["field_id"]

        # 检查目标字段名是否已存在（且不是主字段本身）
        dup_fields = [
            f for f in fields
            if f.get("field_name") == target_name and f["field_id"] != primary_id
        ]

        # 如果有重复字段，先删除它
        for dup in dup_fields:
            dup_id = dup["field_id"]
            try:
                resp = await client.delete_bitable_field(table_id, dup_id)
                code = resp.get("code", -1)
                if code == 0:
                    print(f"[删除重复字段] {table_name}: 删除已有的'{target_name}'({dup_id})")
                else:
                    print(f"[警告] {table_name}: 删除重复字段失败 code={code} msg={resp.get('msg', '')}")
            except Exception as e:
                print(f"[警告] {table_name}: 删除重复字段异常 - {e}")

        # 重命名主字段
        try:
            resp = await client.update_bitable_field(
                table_id, primary_id, field_name=target_name
            )
            code = resp.get("code", -1)
            if code == 0:
                print(f"[重命名] {table_name}: 多行文本 -> {target_name}")
            else:
                print(f"[失败] {table_name}: 重命名失败 code={code} msg={resp.get('msg', '')}")
        except Exception as e:
            print(f"[失败] {table_name}: 重命名异常 - {e}")

    await client.close()
    print()
    print("完成！请在飞书UI中查看效果。")


if __name__ == "__main__":
    asyncio.run(main())
