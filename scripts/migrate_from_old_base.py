"""从旧飞书Base迁移数据到新Base

旧Base: Tckwby7qqaUlPWskr16crFR5nqc
新Base: 当前 settings.feishu_bitable_app_token 指向的Base

用法: python -m scripts.migrate_from_old_base
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from max_system.config.settings import get_settings
from max_system.integrations.feishu.api_client import FeishuApiClient

OLD_APP_TOKEN = "Tckwby7qqaUlPWskr16crFR5nqc"

# 表名映射: 旧表名 → 新表名（模糊匹配，包含即可）
TABLE_MAPPING = {
    "客户": "客户信息表",
    "项目": "项目台账表",
    "售后": "售后维保台账",
    "合同": "合同管理表",
    "供应商": "供应商表",
    "回访": "回访记录表",
    "跟进": "跟进记录表",
    "账目": "谈单账目表",
}


async def main():
    settings = get_settings()
    if not settings.feishu_bitable_app_token:
        print("[错误] 请先设置新Base的 FEISHU_BITABLE_APP_TOKEN")
        sys.exit(1)

    # 初始化新旧两个客户端
    old_client = FeishuApiClient(settings)
    new_client = FeishuApiClient(settings)

    # 重写old_client的app_token
    old_client.settings.feishu_bitable_app_token = OLD_APP_TOKEN

    print(f"[旧Base] Token: {OLD_APP_TOKEN}")
    print(f"[新Base] Token: {settings.feishu_bitable_app_token}")
    print()

    # 获取两边的表列表
    print("=== 扫描旧Base表结构 ===")
    old_tables = await old_client.list_bitable_tables()
    print(f"  旧Base有 {len(old_tables)} 个表:")
    for t in old_tables:
        fields = await old_client.list_bitable_fields(t["table_id"])
        field_names = [f["field_name"] for f in fields]
        print(f"    - {t['name']} ({t['table_id']}): {', '.join(field_names[:8])}...")

    print()

    print("=== 扫描新Base表结构 ===")
    new_tables = await new_client.list_bitable_tables()
    new_tables_dict = {t["name"]: t["table_id"] for t in new_tables}
    print(f"  新Base有 {len(new_tables)} 个表:")
    for t in new_tables:
        print(f"    - {t['name']} ({t['table_id']})")

    print()

    # 匹配表并迁移
    total_migrated = 0
    for old_table in old_tables:
        old_name = old_table["name"]
        old_id = old_table["table_id"]

        # 找到匹配的新表
        new_name = None
        for keyword, target in TABLE_MAPPING.items():
            if keyword in old_name:
                new_name = target
                break
        if not new_name or new_name not in new_tables_dict:
            print(f"[跳过] 旧表 '{old_name}' 未找到匹配的新表")
            continue

        new_id = new_tables_dict[new_name]
        print(f"[迁移] {old_name} → {new_name}")

        # 获取字段映射
        try:
            old_fields = await old_client.list_bitable_fields(old_id)
            new_fields = await new_client.list_bitable_fields(new_id)

            old_field_map = {f["field_name"]: f["field_id"] for f in old_fields}
            new_field_names = {f["field_name"] for f in new_fields}

            # 读取旧表所有记录
            page_token = ""
            records = []
            while True:
                result = await old_client.read_bitable(
                    table_id=old_id, page_size=500, page_token=page_token
                )
                items = result.get("data", {}).get("items", [])
                records.extend(items)
                if not result.get("data", {}).get("has_more"):
                    break
                page_token = result.get("data", {}).get("page_token", "")

            if not records:
                print(f"  旧表为空，无需迁移")
                continue

            # 转换字段：用中文field_name作为key
            transformed = []
            for record in records:
                fields = record.get("fields", {})
                new_record = {}
                for fid, val in fields.items():
                    # 找到对应的field_name（用旧表的field_map反向查找）
                    fname = None
                    for fn, fi in old_field_map.items():
                        if fi == fid:
                            fname = fn
                            break
                    if fname and fname in new_field_names:
                        new_record[fname] = val

                if new_record:
                    transformed.append(new_record)

            # 分批写入新表（每批最多500条）
            if transformed:
                batch_size = 500
                for i in range(0, len(transformed), batch_size):
                    batch = transformed[i:i + batch_size]
                    try:
                        await new_client.write_bitable(new_id, batch)
                        print(f"  已迁移 {len(batch)} 条 ({i + len(batch)}/{len(transformed)})")
                    except Exception as e:
                        print(f"  写入失败 (批次 {i}): {e}")

                total_migrated += len(transformed)
                print(f"  ✅ {old_name}: 迁移完成 {len(transformed)} 条记录")
            else:
                print(f"  无有效记录可迁移")

        except Exception as e:
            print(f"  ❌ 迁移失败: {e}")

        print()

    print("=" * 60)
    print(f"  迁移完成! 共迁移 {total_migrated} 条记录")
    print("=" * 60)

    await old_client.close()
    await new_client.close()


if __name__ == "__main__":
    asyncio.run(main())
