"""飞书多维表格初始化脚本：在线上Base中新建缺失表、补建字段

用法: python -m scripts.init_bitable
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from max_system.config.settings import get_settings
from max_system.integrations.feishu.api_client import FeishuApiClient


# ============ 需要新建的表 ============

NEW_TABLES = [
    {
        "name": "售后维保台账",
        "description": "售后问题处理与维保记录",
        "fields": [
            {"field_name": "客户姓名", "type": 1},
            {"field_name": "项目编号", "type": 1},
            {"field_name": "问题类型", "type": 3, "type_name": "SingleSelect",
             "property": {"options": [
                 {"name": "水电"}, {"name": "墙面"}, {"name": "防水"},
                 {"name": "门窗"}, {"name": "柜体"}, {"name": "其他"},
             ]}},
            {"field_name": "问题描述", "type": 1},
            {"field_name": "处理状态", "type": 3, "type_name": "SingleSelect",
             "property": {"options": [
                 {"name": "待处理"}, {"name": "处理中"}, {"name": "已完成"}, {"name": "已关闭"},
             ]}},
            {"field_name": "优先级", "type": 3, "type_name": "SingleSelect",
             "property": {"options": [
                 {"name": "紧急"}, {"name": "高"}, {"name": "中"}, {"name": "低"},
             ]}},
            {"field_name": "提报人", "type": 1},
            {"field_name": "处理人", "type": 1},
            {"field_name": "提报日期", "type": 5},
            {"field_name": "处理完成日期", "type": 5},
            {"field_name": "客户满意度", "type": 3, "type_name": "SingleSelect",
             "property": {"options": [
                 {"name": "非常满意"}, {"name": "满意"}, {"name": "一般"}, {"name": "不满意"},
             ]}},
            {"field_name": "备注", "type": 1},
        ],
    },
    {
        "name": "跟进记录表",
        "description": "客户跟进与回访记录（合并原回访+跟进）",
        "fields": [
            {"field_name": "客户姓名", "type": 1},
            {"field_name": "项目编号", "type": 1},
            {"field_name": "记录类型", "type": 3, "type_name": "SingleSelect",
             "property": {"options": [
                 {"name": "日常跟进"}, {"name": "售后回访"}, {"name": "关怀回访"}, {"name": "投诉跟进"},
             ]}},
            {"field_name": "跟进时间", "type": 5},
            {"field_name": "跟进人", "type": 1},
            {"field_name": "跟进方式", "type": 3, "type_name": "SingleSelect",
             "property": {"options": [
                 {"name": "微信"}, {"name": "电话"}, {"name": "面访"}, {"name": "飞书"},
             ]}},
            {"field_name": "跟进内容", "type": 1},
            {"field_name": "客户反馈", "type": 1},
            {"field_name": "满意度", "type": 3, "type_name": "SingleSelect",
             "property": {"options": [
                 {"name": "非常满意"}, {"name": "满意"}, {"name": "一般"}, {"name": "不满意"},
             ]}},
            {"field_name": "跟进事项", "type": 1},
            {"field_name": "下次跟进时间", "type": 5},
            {"field_name": "状态", "type": 3, "type_name": "SingleSelect",
             "property": {"options": [
                 {"name": "待跟进"}, {"name": "跟进中"}, {"name": "已完成"},
             ]}},
        ],
    },
]

# ============ 线上已有表需要补建的字段 ============

EXTRA_FIELDS = {
    "客户信息": [
        {"field_name": "客户编号", "type": 1},
    ],
}


async def main():
    settings = get_settings()
    if not settings.feishu_bitable_app_token:
        print("[错误] 请先设置 FEISHU_BITABLE_APP_TOKEN 环境变量")
        sys.exit(1)

    client = FeishuApiClient(settings)
    print(f"[API] 已连接飞书 API")
    print(f"[Base] Token: {settings.feishu_bitable_app_token}")
    print()

    # Step 1: 获取现有表
    print("[检查] 正在获取现有表...")
    try:
        existing = await client.list_bitable_tables()
        existing_names = {t["name"]: t["table_id"] for t in existing}
        if existing_names:
            print(f"   已有 {len(existing_names)} 个表: {', '.join(existing_names.keys())}")
        else:
            print("   当前Base为空")
    except Exception as e:
        print(f"   [警告] 获取现有表失败: {e}")
        existing_names = {}

    print()

    # Step 2: 新建缺失表
    created_tables = {}
    for table_def in NEW_TABLES:
        name = table_def["name"]
        if name in existing_names:
            print(f"[跳过] '{name}'（已存在，ID: {existing_names[name]}）")
            created_tables[name] = existing_names[name]
        else:
            print(f"[创建] 表 '{name}' ...", end=" ", flush=True)
            try:
                resp = await client.create_bitable_table(name)
                table_id = resp.get("data", {}).get("table_id", "")
                if table_id:
                    print(f"成功 ID: {table_id}")
                    created_tables[name] = table_id
                else:
                    print(f"返回异常: {json.dumps(resp, ensure_ascii=False)[:200]}")
                    continue
            except Exception as e:
                print(f"失败: {e}")
                continue

        # Step 3: 创建字段
        table_id = created_tables[name]
        try:
            existing_fields = await client.list_bitable_fields(table_id)
            existing_field_names = {f["field_name"] for f in existing_fields}
        except Exception:
            existing_field_names = set()

        new_fields = [f for f in table_def["fields"] if f["field_name"] not in existing_field_names]
        if not new_fields:
            print(f"  [字段] 全部已存在，无需创建")
        else:
            print(f"  [字段] 需创建 {len(new_fields)} 个 ...", end=" ", flush=True)
            try:
                field_resp = await client.batch_create_fields(table_id, new_fields)
                fields_created = field_resp.get("data", {}).get("fields", [])
                print(f"成功创建 {len(fields_created)} 个字段")
            except Exception as e:
                print(f"失败: {e}")

        print()

    # Step 4: 在线上已有表中补建字段
    for table_name, fields in EXTRA_FIELDS.items():
        if table_name not in existing_names:
            print(f"[跳过] 补字段: '{table_name}' 不存在")
            continue
        table_id = existing_names[table_name]
        print(f"[补字段] '{table_name}' ...")
        try:
            existing_fields = await client.list_bitable_fields(table_id)
            existing_field_names = {f["field_name"] for f in existing_fields}
        except Exception:
            existing_field_names = set()

        new_fields = [f for f in fields if f["field_name"] not in existing_field_names]
        if not new_fields:
            print(f"  全部已存在，无需创建")
        else:
            print(f"  需创建 {len(new_fields)} 个字段 ...", end=" ", flush=True)
            try:
                field_resp = await client.batch_create_fields(table_id, new_fields)
                fields_created = field_resp.get("data", {}).get("fields", [])
                print(f"成功创建 {len(fields_created)} 个字段")
            except Exception as e:
                print(f"失败: {e}")
        print()

    # Step 5: 输出汇总
    print("=" * 60)
    print("  初始化完成!")
    print("=" * 60)
    print()
    if created_tables:
        print("新建表的 table_id（填入 settings.py 或 .env）：")
        print()
        mapping = {
            "售后维保台账": "BITABLE_TABLE_AFTER_SALES",
            "跟进记录表": "BITABLE_TABLE_FOLLOWUPS",
        }
        for name, tid in created_tables.items():
            env_key = mapping.get(name, "")
            print(f"  {name}: {tid}")
            if env_key:
                print(f"    → .env: {env_key}={tid}")
    print()
    print("线上已有表（无需改动）：")
    print("  客户信息:   BITABLE_TABLE_CLIENTS=tbl6IdYFBB8RDFiO")
    print("  合同管理:   BITABLE_TABLE_CONTRACTS=tblRS5zg0u5Hj6DN")
    print("  合作商:     BITABLE_TABLE_SUPPLIERS=tblnKdukg33OfUsN")
    print("  支出明细:   BITABLE_TABLE_EXPENSE=tbl2X6WH1RuCwBM3")
    print("  收入明细:   BITABLE_TABLE_INCOME=tbl6WFZYHS19JHKk")
    print("  施工管理:   BITABLE_TABLE_CONSTRUCTION=tblLBj0GQik63K9W")
    print("  任务:       BITABLE_TABLE_TASKS=tblZA6hpoSVUbfTm")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
