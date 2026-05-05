"""项目总览MCP工具：跨数据源整合项目全景视图"""

import logging

from max_system.config.settings import MaxSettings

logger = logging.getLogger(__name__)

_settings: MaxSettings | None = None


def _find_client(args: dict) -> tuple[dict | None, str]:
    """从参数中查找客户，返回 (client_dict, lookup_key)"""
    client_id = args.get("client_id", "")
    client_name = args.get("client_name", "")
    project_name = args.get("project_name", "")

    try:
        from max_system.tools.clientmgr_tools import _clients_db

        if client_id and client_id in _clients_db:
            return _clients_db[client_id], client_id

        if client_name:
            name_lower = client_name.lower()
            for c in _clients_db.values():
                if name_lower in c.get("name", "").lower():
                    return c, c.get("name", client_name)

        if project_name:
            name_lower = project_name.lower()
            for c in _clients_db.values():
                if name_lower in c.get("city", "").lower():
                    return c, c.get("city", project_name)

    except Exception as e:
        logger.warning("查找客户数据失败: %s", e)

    return None, ""


def _build_api_client():
    """构建 FeishuApiClient"""
    if not _settings or not _settings.feishu_bitable_app_token:
        return None
    try:
        from max_system.integrations.feishu.api_client import FeishuApiClient
        return FeishuApiClient(_settings)
    except Exception as e:
        logger.warning("构建 FeishuApiClient 失败: %s", e)
        return None


async def _read_bitable_records(api_client, table_id: str) -> list[dict]:
    """读取多维表格全部记录"""
    if not api_client or not table_id:
        return []
    try:
        all_records = []
        page_token = ""
        while True:
            result = await api_client.read_bitable(
                table_id=table_id, page_size=500, page_token=page_token
            )
            items = result.get("data", {}).get("items", [])
            all_records.extend(items)
            if not result.get("data", {}).get("has_more"):
                break
            page_token = result.get("data", {}).get("page_token", "")
        return all_records
    except Exception as e:
        logger.warning("读取多维表格失败 (table_id=%s): %s", table_id, e)
        return []


async def project_overview(args: dict) -> dict:
    """获取项目全景视图：客户信息 + 合同 + 施工进度 + 售后问题"""
    client, lookup_key = _find_client(args)

    if not client:
        search_info = args.get("client_name") or args.get("client_id") or args.get("project_name") or "未知"
        return {"content": [{"type": "text", "text": f"未找到相关客户: {search_info}。请先创建客户记录或检查客户姓名/编号。"}]}

    # ============ 1. 客户信息 ============
    lines = []
    lines.append("# 项目全景视图")
    lines.append("")

    lines.append("## 客户信息")
    lines.append("")
    lines.append("| 字段 | 内容 |")
    lines.append("|------|------|")
    lines.append(f"| 客户编号 | {client.get('client_id', '-')} |")
    lines.append(f"| 客户姓名 | {client.get('name', '-')} |")
    lines.append(f"| 联系方式 | {client.get('phone', '-')} |")
    lines.append(f"| 项目地址 | {client.get('city', '-')} |")
    lines.append(f"| 户型 | {client.get('unit_type', '-')} |")
    lines.append(f"| 预算 | {client.get('budget', '-')} |")
    lines.append(f"| 设计费 | {client.get('design_fee', '-')} |")
    lines.append(f"| 客户来源 | {client.get('source', '-')} |")
    lines.append(f"| 客户类型 | {client.get('client_type', '-')} |")
    lines.append(f"| 服务阶段 | {client.get('status', '-')} |")
    lines.append(f"| 落单进度 | {client.get('intent', '-')} |")
    lines.append(f"| 分派设计师 | {client.get('follower', '-')} |")
    lines.append(f"| 备注 | {client.get('remark', '-')} |")
    lines.append(f"| 录入时间 | {client.get('created_at', '-')} |")
    lines.append("")

    client_name = client.get("name", "")

    # ============ 2. 合同与财务 ============
    lines.append("## 合同与财务")
    lines.append("")

    api_client = _build_api_client()
    bitable_available = api_client is not None and bool(
        _settings.feishu_bitable_app_token if _settings else ""
    )

    if not bitable_available:
        lines.append("> 飞书多维表格未连接，无法获取合同、施工、售后数据。以下仅展示本地客户信息。")
        lines.append("")
        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    contracts_found = []
    try:
        contracts_table_id = _settings.bitable_table_contracts
        if contracts_table_id and client_name:
            all_records = await _read_bitable_records(api_client, contracts_table_id)
            # 获取字段映射
            field_map = await api_client.get_field_mapping(contracts_table_id)

            for record in all_records:
                fields = record.get("fields", {})
                # 查找客户姓名字段
                rec_client_name = ""
                for fid, fname in field_map.items():
                    if fname == "客户姓名":
                        rec_client_name = str(fields.get(fid, ""))
                        break
                if client_name in rec_client_name or rec_client_name in client_name:
                    contracts_found.append(_translate_record(fields, field_map))
    except Exception as e:
        logger.warning("读取合同表失败: %s", e)

    if contracts_found:
        for idx, contract in enumerate(contracts_found, 1):
            lines.append(f"### 合同 {idx}")
            lines.append("")
            lines.append("| 字段 | 内容 |")
            lines.append("|------|------|")
            for k, v in contract.items():
                if v is not None and v != "":
                    lines.append(f"| {k} | {v} |")
            lines.append("")
    else:
        lines.append("> 未找到相关合同记录。")
        lines.append("")

    # ============ 3. 施工进度 ============
    lines.append("## 施工进度")
    lines.append("")

    construction_found = []
    try:
        construction_table_id = _settings.bitable_table_construction
        if construction_table_id:
            all_records = await _read_bitable_records(api_client, construction_table_id)
            field_map = await api_client.get_field_mapping(construction_table_id)
            for record in all_records:
                fields = record.get("fields", {})
                construction_found.append(_translate_record(fields, field_map))
    except Exception as e:
        logger.warning("读取施工管理表失败: %s", e)

    if construction_found:
        lines.append("| 施工节点 | 说明 | 执行人 | 状态 | 计划日期 | 实际日期 |")
        lines.append("|---------|------|--------|------|---------|---------|")
        for item in construction_found:
            lines.append(
                f"| {item.get('施工节点', '-')} | {item.get('节点说明', '-')} | "
                f"{item.get('执行人', '-')} | {item.get('完结', '-')} | "
                f"{item.get('计划日期', '-')} | {item.get('实际日期', '-')} |"
            )
        lines.append("")
    else:
        lines.append("> 未找到施工进度记录。")
        lines.append("")

    # ============ 4. 任务 ============
    lines.append("## 任务")
    lines.append("")

    tasks_found = []
    try:
        tasks_table_id = _settings.bitable_table_tasks
        if tasks_table_id:
            all_records = await _read_bitable_records(api_client, tasks_table_id)
            field_map = await api_client.get_field_mapping(tasks_table_id)
            for record in all_records:
                fields = record.get("fields", {})
                tasks_found.append(_translate_record(fields, field_map))
    except Exception as e:
        logger.warning("读取任务表失败: %s", e)

    if tasks_found:
        lines.append("| 施工节点 | 分类 | 工种 | 预埋 | 采购 | 污染 | 进度 |")
        lines.append("|---------|------|------|------|------|------|------|")
        for item in tasks_found:
            lines.append(
                f"| {item.get('施工节点', '-')} | {item.get('分类', '-')} | "
                f"{item.get('工种', '-')} | {item.get('预埋', '-')} | "
                f"{item.get('采购', '-')} | {item.get('污染', '-')} | "
                f"{item.get('进度', '-')} |"
            )
        lines.append("")
    else:
        lines.append("> 未找到任务记录。")
        lines.append("")

    # ============ 5. 售后 / 问题 ============
    lines.append("## 售后与问题")
    lines.append("")

    after_sales_found = []
    try:
        after_sales_table_id = _settings.bitable_table_after_sales
        if after_sales_table_id and client_name:
            all_records = await _read_bitable_records(api_client, after_sales_table_id)
            field_map = await api_client.get_field_mapping(after_sales_table_id)

            for record in all_records:
                fields = record.get("fields", {})
                rec_client_name = ""
                for fid, fname in field_map.items():
                    if fname == "客户姓名":
                        rec_client_name = str(fields.get(fid, ""))
                        break
                if client_name in rec_client_name or rec_client_name in client_name:
                    after_sales_found.append(_translate_record(fields, field_map))
    except Exception as e:
        logger.warning("读取售后维保台账失败: %s", e)

    if after_sales_found:
        lines.append("| 提报日期 | 问题类型 | 问题描述 | 处理状态 | 优先级 | 处理人 | 满意度 |")
        lines.append("|---------|---------|---------|---------|--------|--------|--------|")
        for item in after_sales_found:
            lines.append(
                f"| {item.get('提报日期', '-')} | {item.get('问题类型', '-')} | "
                f"{item.get('问题描述', '-')} | {item.get('处理状态', '-')} | "
                f"{item.get('优先级', '-')} | {item.get('处理人', '-')} | "
                f"{item.get('客户满意度', '-')} |"
            )
        lines.append("")
    else:
        lines.append("> 未找到售后/问题记录。")
        lines.append("")

    # ============ 清理 API 客户端 ============
    try:
        if api_client:
            await api_client.close()
    except Exception:
        pass

    # 追加生成时间
    from datetime import datetime
    lines.append("")
    lines.append(f"---")
    lines.append(f"> 项目全景视图生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("> 此文档为AI生成，请设计师审核确认后使用")

    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


def _translate_record(fields: dict, field_map: dict[str, str]) -> dict:
    """将 field_id→value 的记录转为 field_name→value"""
    result = {}
    for fid, fname in field_map.items():
        val = fields.get(fid)
        if val is not None:
            # 处理列表类型字段（如单选返回的 list）
            if isinstance(val, list):
                val = ", ".join(str(v) for v in val)
            result[fname] = str(val) if not isinstance(val, str) else val
    return result


# ============ 工具定义 ============

TOOL_DEFS = [
    {
        "name": "project_overview",
        "description": (
            "查看项目全景视图：整合客户信息、合同财务、施工进度、任务清单、售后问题等所有信息。"
            "设计师说'看看这个项目的情况'或'XX客户现在什么阶段了'时使用。"
            "自动从本地数据库和飞书多维表格拉取数据，汇总为结构化概览。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "client_name": {
                    "type": "string",
                    "description": "客户姓名，用于查找关联的项目数据。",
                },
                "project_name": {
                    "type": "string",
                    "description": "项目名称/地址关键词，用于查找关联数据。",
                },
                "client_id": {
                    "type": "string",
                    "description": "客户编号，用于精确查找。与client_name二选一。",
                },
            },
            "required": [],
        },
    },
]


def register_tools(settings: MaxSettings):
    global _settings
    _settings = settings

    handlers = {
        "project_overview": project_overview,
    }
    return [(d["name"], handlers[d["name"]], d) for d in TOOL_DEFS]
