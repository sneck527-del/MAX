"""飞书多维表格初始化脚本：一键创建Base中的表结构和字段

用法: python -m scripts.init_bitable
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from max_system.config.settings import get_settings
from max_system.integrations.feishu.api_client import FeishuApiClient


# ============ 表结构定义 ============

TABLES = [
    {
        "name": "客户信息表",
        "description": "客户全生命周期信息管理",
        "fields": [
            {"field_name": "客户姓名", "type": 1},
            {"field_name": "联系电话", "type": 1},
            {"field_name": "城市", "type": 1},
            {"field_name": "户型面积", "type": 1},
            {"field_name": "预算", "type": 1},
            {"field_name": "来源渠道", "type": 1},
            {"field_name": "意向等级", "type": 1},
            {"field_name": "客户状态", "type": 1},
            {"field_name": "标签", "type": 1},
            {"field_name": "跟进人", "type": 1},
            {"field_name": "创建时间", "type": 1},
            {"field_name": "更新时间", "type": 1},
            {"field_name": "备注", "type": 1},
        ],
    },
    {
        "name": "项目台账表",
        "description": "项目全流程信息台账",
        "fields": [
            {"field_name": "项目名称", "type": 1},
            {"field_name": "客户姓名", "type": 1},
            {"field_name": "项目地址", "type": 1},
            {"field_name": "面积", "type": 1},
            {"field_name": "风格", "type": 1},
            {"field_name": "合同金额", "type": 1},
            {"field_name": "已收款", "type": 1},
            {"field_name": "未收款", "type": 1},
            {"field_name": "项目状态", "type": 1},
            {"field_name": "设计师", "type": 1},
            {"field_name": "施工班组", "type": 1},
            {"field_name": "开工日期", "type": 1},
            {"field_name": "预计完工日", "type": 1},
            {"field_name": "实际完工日", "type": 1},
            {"field_name": "备注", "type": 1},
        ],
    },
    {
        "name": "售后维保台账",
        "description": "售后问题处理与维保记录",
        "fields": [
            {"field_name": "项目名称", "type": 1},
            {"field_name": "客户姓名", "type": 1},
            {"field_name": "问题类型", "type": 1},
            {"field_name": "问题描述", "type": 1},
            {"field_name": "处理状态", "type": 1},
            {"field_name": "优先级", "type": 1},
            {"field_name": "提报人", "type": 1},
            {"field_name": "处理人", "type": 1},
            {"field_name": "提报日期", "type": 1},
            {"field_name": "处理完成日期", "type": 1},
            {"field_name": "客户满意度", "type": 1},
            {"field_name": "备注", "type": 1},
        ],
    },
    {
        "name": "合同管理表",
        "description": "合同信息管理与进度跟踪",
        "fields": [
            {"field_name": "合同编号", "type": 1},
            {"field_name": "客户姓名", "type": 1},
            {"field_name": "合同类型", "type": 1},
            {"field_name": "合同金额", "type": 1},
            {"field_name": "已付金额", "type": 1},
            {"field_name": "付款进度", "type": 1},
            {"field_name": "签订日期", "type": 1},
            {"field_name": "合同状态", "type": 1},
            {"field_name": "备注", "type": 1},
        ],
    },
    {
        "name": "供应商表",
        "description": "供应商信息与合作管理",
        "fields": [
            {"field_name": "供应商名称", "type": 1},
            {"field_name": "联系人", "type": 1},
            {"field_name": "联系电话", "type": 1},
            {"field_name": "供应品类", "type": 1},
            {"field_name": "等级", "type": 1},
            {"field_name": "合作状态", "type": 1},
            {"field_name": "备注", "type": 1},
        ],
    },
    {
        "name": "回访记录表",
        "description": "售后回访与客户关怀记录",
        "fields": [
            {"field_name": "客户姓名", "type": 1},
            {"field_name": "项目名称", "type": 1},
            {"field_name": "回访日期", "type": 1},
            {"field_name": "回访人", "type": 1},
            {"field_name": "回访方式", "type": 1},
            {"field_name": "客户反馈", "type": 1},
            {"field_name": "满意度", "type": 1},
            {"field_name": "跟进事项", "type": 1},
            {"field_name": "下次回访日期", "type": 1},
        ],
    },
    {
        "name": "跟进记录表",
        "description": "客户跟进过程记录",
        "fields": [
            {"field_name": "客户姓名", "type": 1},
            {"field_name": "项目名称", "type": 1},
            {"field_name": "跟进时间", "type": 1},
            {"field_name": "跟进人", "type": 1},
            {"field_name": "跟进方式", "type": 1},
            {"field_name": "跟进内容", "type": 1},
            {"field_name": "客户反馈", "type": 1},
            {"field_name": "下次跟进时间", "type": 1},
            {"field_name": "状态", "type": 1},
        ],
    },
    {
        "name": "谈单账目表",
        "description": "谈单收款付款进程账目",
        "fields": [
            {"field_name": "客户姓名", "type": 1},
            {"field_name": "项目名称", "type": 1},
            {"field_name": "付款节点", "type": 1},
            {"field_name": "应收金额", "type": 1},
            {"field_name": "实收金额", "type": 1},
            {"field_name": "收款日期", "type": 1},
            {"field_name": "付款方", "type": 1},
            {"field_name": "付款方式", "type": 1},
            {"field_name": "状态", "type": 1},
            {"field_name": "备注", "type": 1},
        ],
    },
]


async def main():
    settings = get_settings()
    if not settings.feishu_bitable_app_token:
        print("[错误] 请先设置 FEISHU_BITABLE_APP_TOKEN 环境变量")
        sys.exit(1)

    client = FeishuApiClient(settings)
    print(f"[API] 已连接飞书 API")
    print(f"[Base] Token: {settings.feishu_bitable_app_token}")
    print()

    # Step 1: 检查现有表
    print("[检查] 正在检查现有表...")
    try:
        existing = await client.list_bitable_tables()
        existing_names = {t["name"]: t["table_id"] for t in existing}
        if existing_names:
            print(f"   已存在 {len(existing_names)} 个表: {', '.join(existing_names.keys())}")
        else:
            print("   当前Base为空")
    except Exception as e:
        print(f"   [警告] 获取现有表失败: {e}")
        existing_names = {}

    print()

    # Step 2: 创建表
    created_tables = {}
    for table_def in TABLES:
        name = table_def["name"]
        if name in existing_names:
            print(f"[跳过] '{name}'（已存在）")
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

        # Step 3: 创建字段（检查现有字段，避免重复）
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

    # Step 4: 输出汇总
    print("=" * 60)
    print("  初始化完成!")
    print("=" * 60)
    print()
    if created_tables:
        print("表的映射关系（table_id）：")
        print()
        for name, tid in created_tables.items():
            print(f"  {name}: {tid}")
        print()
        print("请将这些 table_id 记录到各 Agent 的 system prompt 中。")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
