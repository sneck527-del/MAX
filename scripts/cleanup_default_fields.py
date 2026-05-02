"""清理飞书多维表格自动创建的"多行文本"首列

飞书新建表时自动生成一个"多行文本"字段作为第一列，
此脚本遍历所有8个表，将其删除，使第一个业务字段（如客户姓名）成为首列。

用法: python -m scripts.cleanup_default_fields
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from max_system.config.settings import get_settings
from max_system.integrations.feishu.api_client import FeishuApiClient


async def main():
    settings = get_settings()
    if not settings.feishu_bitable_app_token:
        print("[错误] 请先设置 FEISHU_BITABLE_APP_TOKEN")
        sys.exit(1)

    client = FeishuApiClient(settings)

    # 所有8个表的 ID 和名称
    table_infos = [
        (settings.bitable_table_clients, "客户信息表"),
        (settings.bitable_table_projects, "项目台账表"),
        (settings.bitable_table_after_sales, "售后维保台账"),
        (settings.bitable_table_contracts, "合同管理表"),
        (settings.bitable_table_suppliers, "供应商表"),
        (settings.bitable_table_visits, "回访记录表"),
        (settings.bitable_table_followups, "跟进记录表"),
        (settings.bitable_table_accounting, "谈单账目表"),
    ]

    total_deleted = 0
    for table_id, table_name in table_infos:
        try:
            fields = await client.list_bitable_fields(table_id)
        except Exception as e:
            print(f"[失败] {table_name}: 获取字段列表失败 - {e}")
            continue

        multi_text_fields = [f for f in fields if f.get("field_name") == "多行文本"]
        if not multi_text_fields:
            print(f"[跳过] {table_name}: 没有多行文本字段")
            continue

        for field in multi_text_fields:
            fid = field["field_id"]
            try:
                await client.delete_bitable_field(table_id, fid)
                print(f"[删除] {table_name}: 多行文本 ({fid})")
                total_deleted += 1
            except Exception as e:
                print(f"[失败] {table_name}: 删除多行文本失败 - {e}")

    print()
    print(f"完成! 共删除 {total_deleted} 个多行文本字段")
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
