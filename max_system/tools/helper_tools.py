"""Helper执行助手专用工具：文档批量生成、客户管理、知识库维护、飞书通知、归档同步"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from max_system.config.settings import MaxSettings

logger = logging.getLogger(__name__)

# 共享引用（由register_tools初始化）
_clients_db_ref: dict | None = None
_vault_path: Path | None = None
_kb_path: Path | None = None


# ============ 1. DocGen - 批量文档生成与校验 ============

async def helper_batch_generate(args: dict) -> dict:
    """批量生成文档，包含合规校验报告"""
    doc_type = args.get("doc_type", "量房单")
    projects = json.loads(args["projects"]) if isinstance(args.get("projects"), str) else args.get("projects", [])
    validate = args.get("validate", True)

    templates = {
        "量房单": "📐 量房确认单",
        "需求分析表": "📋 客户需求分析表",
        "设计说明": "🎨 设计方案说明",
        "施工交底": "🔨 施工技术交底",
        "验收单": "✅ 验收确认单",
        "竣工报告": "🏠 竣工验收报告",
    }
    header = templates.get(doc_type, f"📄 {doc_type}")

    generated = []
    validation_issues = []

    for proj in projects:
        name = proj.get("name", "未知项目")
        client = proj.get("client", "")
        items = proj.get("items", {})

        content = [
            f"{header}",
            f"━━━━━━━━━━━━━━━━━━━━━━━━",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"项目: {name}",
            f"客户: {client}",
            "",
        ]
        for key, val in items.items():
            if isinstance(val, list):
                content.append(f"\n{key}:")
                for v in val:
                    content.append(f"  - {v}")
            elif isinstance(val, dict):
                content.append(f"\n{key}:")
                for k, v in val.items():
                    content.append(f"  {k}: {v}")
            else:
                content.append(f"{key}: {val}")

        content.append(f"\n⚠️ 此文档由Max系统自动生成，需设计师审核确认后方可使用")
        doc_text = "\n".join(content)
        generated.append({"项目": name, "客户": client, "内容": doc_text})

        if validate:
            issues = []
            if not client:
                issues.append("缺少客户姓名")
            if not items:
                issues.append("文档内容为空")
            if any(kw in doc_text for kw in ["拆除承重墙", "梁体切割", "楼板开洞"]):
                issues.append("存在结构安全风险内容")
            if issues:
                validation_issues.append({"项目": name, "问题": issues})

    result = {
        "文档类型": doc_type,
        "批量生成": len(generated),
        "文档列表": generated,
    }

    if validate:
        result["校验报告"] = {
            "检查项数": len(generated),
            "问题数": len(validation_issues),
            "问题详情": validation_issues or ["无"],
            "结论": "全部通过" if not validation_issues else f"发现 {len(validation_issues)} 个文档存在问题",
        }

    result["生成时间"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}


# ============ 2. ClientMgr - 客户标签与报表 ============

async def helper_client_tag_and_report(args: dict) -> dict:
    """客户标签化管理 + 跟进报表 + 逾期预警"""
    action = args.get("action", "report")  # report / tag / overdue
    tag_client_id = args.get("client_id", "")
    tag_labels = args.get("labels", "")

    db = _clients_db_ref or {}

    if action == "tag" and tag_client_id and tag_labels:
        if tag_client_id in db:
            labels = [l.strip() for l in tag_labels.split(",") if l.strip()]
            db[tag_client_id]["tags"] = labels
            db[tag_client_id]["updated_at"] = datetime.now().isoformat()
            return {"content": [{"type": "text", "text": json.dumps({
                "success": True, "client_id": tag_client_id, "labels": labels,
            }, ensure_ascii=False)}]}
        return {"content": [{"type": "text", "text": f"客户 {tag_client_id} 不存在"}]}

    # 标签体系定义
    tag_system = {
        "意向标签": ["高意向-急跟", "中意向-培育", "低意向-长线"],
        "来源标签": ["小红书", "抖音", "老客户介绍", "门店", "朋友圈"],
        "阶段标签": ["初次接触", "方案沟通", "报价谈判", "已签约", "施工中", "已竣工"],
        "户型标签": ["别墅", "大平层", "普通住宅", "小户型"],
        "风格标签": ["现代简约", "新中式", "轻奢", "北欧", "日式"],
    }

    # 从db自动推断标签
    auto_tags = {}
    for cid, c in db.items():
        tags = []
        intent = c.get("intent", "")
        if intent == "高":
            tags.append("高意向-急跟")
        elif intent == "中":
            tags.append("中意向-培育")
        else:
            tags.append("低意向-长线")

        unit = c.get("unit_type", "")
        if "别墅" in unit:
            tags.append("别墅")
        elif "大平层" in unit:
            tags.append("大平层")

        source = c.get("source", "")
        for s in ["小红书", "抖音", "朋友", "门店"]:
            if s in source:
                tags.append({"小红书": "小红书", "抖音": "抖音", "朋友": "老客户介绍", "门店": "门店"}.get(s, s))

        status = c.get("status", "")
        status_map = {"新建": "初次接触", "跟进中": "方案沟通", "已签约": "已签约"}
        if status in status_map:
            tags.append(status_map[status])

        auto_tags[cid] = tags

    if action == "overdue":
        now = datetime.now()
        overdue = []
        for cid, c in db.items():
            updated = c.get("updated_at", "")
            if updated and c.get("status") in ("新建", "跟进中"):
                try:
                    updated_dt = datetime.fromisoformat(updated)
                    if (now - updated_dt) > timedelta(days=7):
                        overdue.append({
                            "client_id": cid,
                            "name": c.get("name", ""),
                            "intent": c.get("intent", ""),
                            "last_contact": updated,
                            "days_since": (now - updated_dt).days,
                        })
                except ValueError:
                    pass
        overdue.sort(key=lambda x: x["days_since"], reverse=True)

        return {"content": [{"type": "text", "text": json.dumps({
            "逾期未跟进客户": len(overdue),
            "列表": overdue[:20],
            "建议动作": "逐一联系客户，更新跟进状态",
        }, ensure_ascii=False, indent=2)}]}

    # 默认: 报表
    total = len(db)
    by_intent = {"高": 0, "中": 0, "低": 0, "待评估": 0}
    by_status = {}
    for c in db.values():
        i = c.get("intent", "待评估")
        by_intent[i] = by_intent.get(i, 0) + 1
        s = c.get("status", "未知")
        by_status[s] = by_status.get(s, 0) + 1

    report = {
        "客户标签体系": tag_system,
        "客户统计": {
            "总客户数": total,
            "意向分布": by_intent,
            "状态分布": by_status,
        },
        "自动标签": auto_tags,
        "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    return {"content": [{"type": "text", "text": json.dumps(report, ensure_ascii=False, indent=2)}]}


# ============ 3. Knowledge - 知识库目录与新增 ============

async def helper_knowledge_catalog(args: dict) -> dict:
    """生成知识库目录/索引/新增条目"""
    action = args.get("action", "catalog")  # catalog / add
    kb = _kb_path

    if action == "catalog":
        if not kb or not kb.exists():
            return {"content": [{"type": "text", "text": json.dumps({
                "知识库目录": "知识库目录不存在",
                "建议": "请先配置知识库路径或在 06_知识库 目录下创建内容",
            }, ensure_ascii=False, indent=2)}]}

        catalog = {}
        total_files = 0
        for sub_dir in sorted(kb.iterdir()):
            if sub_dir.is_dir():
                md_files = list(sub_dir.rglob("*.md"))
                total_files += len(md_files)
                catalog[sub_dir.name] = {
                    "文件数": len(md_files),
                    "文件列表": [str(f.relative_to(kb)) for f in md_files[:30]],
                }

        return {"content": [{"type": "text", "text": json.dumps({
            "知识库根目录": str(kb),
            "总文件数": total_files,
            "目录结构": catalog,
            "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }, ensure_ascii=False, indent=2)}]}

    if action == "add":
        if not kb or not kb.exists():
            return {"content": [{"type": "text", "text": "知识库目录不存在，无法新增"}]}

        category = args.get("category", "company_standards")
        title = args.get("title", "")
        content = args.get("content", "")
        tags = args.get("tags", "")

        if not title or not content:
            return {"content": [{"type": "text", "text": "标题和内容不能为空"}]}

        target_dir = kb / category
        target_dir.mkdir(parents=True, exist_ok=True)

        safe_name = "".join(c for c in title if c.isalnum() or c in " _-")[:60]
        filepath = target_dir / f"{safe_name}.md"

        frontmatter = [
            "---",
            f'title: "{title}"',
            f"date: {datetime.now().strftime('%Y-%m-%d')}",
            f"tags: [{tags}]" if tags else "",
            "created_by: max-system",
            "---",
        ]
        full_content = "\n".join(frontmatter) + f"\n\n{content}"
        filepath.write_text(full_content, encoding="utf-8")

        return {"content": [{"type": "text", "text": json.dumps({
            "success": True,
            "path": str(filepath.relative_to(kb)),
            "category": category,
            "title": title,
            "message": f"已新增知识库文档: {filepath.relative_to(kb)}",
        }, ensure_ascii=False, indent=2)}]}

    return {"content": [{"type": "text", "text": f"未知操作: {action}"}]}


# ============ 4. FeishuLink - 飞书通知与预警 ============

async def helper_feishu_sync_alert(args: dict) -> dict:
    """发送飞书通知/预警/提醒消息"""
    alert_type = args.get("alert_type", "reminder")  # reminder / warning / notification
    title = args.get("title", "")
    content = args.get("content", "")
    target = args.get("target", "设计师")  # 设计师 / 项目群 / 部门群
    urgency = args.get("urgency", "normal")  # normal / urgent

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 构建结构化消息
    level_icon = {"normal": "📌", "urgent": "🚨"}
    type_icon = {"reminder": "⏰", "warning": "⚠️", "notification": "📢"}
    icon = level_icon.get(urgency, "📌") + type_icon.get(alert_type, "📌")

    msg_block = [
        f"{icon} 【{title}】",
        f"━━━━━━━━━━━━━━━━━━━━━━━━",
        f"时间: {now}",
        f"发送至: {target}",
        f"",
        content,
        "",
    ]

    if urgency == "urgent":
        msg_block.append("🔴 请立即处理")
    elif alert_type == "warning":
        msg_block.append("🟡 请关注并安排处理")

    msg_block.append(f"\n—— Max系统自动通知")

    msg_text = "\n".join(msg_block)

    result = {
        "alert_type": alert_type,
        "title": title,
        "target": target,
        "urgency": urgency,
        "formatted_message": msg_text,
        "generated_at": now,
        "note": "此消息内容可通过 feishu_send_message 工具发送到飞书",
    }

    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}


# ============ 5. ObsidianSync - 完整项目归档 ============

async def helper_obsidian_full_archive(args: dict) -> dict:
    """全项目归档到Obsidian，含目录结构、索引页"""
    project_name = args.get("project_name", "")
    client_name = args.get("client_name", "")
    category = args.get("category", "projects")  # projects / clients / knowledge
    documents = json.loads(args["documents"]) if isinstance(args.get("documents"), str) else args.get("documents", [])

    vault = _vault_path
    if not vault or not vault.exists():
        return {"content": [{"type": "text", "text": "Obsidian Vault 路径未配置或不存在"}]}

    # 确定目录
    if category == "projects":
        target_dir = vault / "项目" / project_name
    elif category == "clients":
        target_dir = vault / "客户" / client_name
    else:
        target_dir = vault / "知识库" / category

    target_dir.mkdir(parents=True, exist_ok=True)

    archived_files = []
    for doc in documents:
        title = doc.get("title", "")
        content = doc.get("content", "")
        tags = doc.get("tags", [])
        links = doc.get("links", [])
        folder = doc.get("folder", "")

        if not title or not content:
            continue

        doc_dir = target_dir / folder if folder else target_dir
        doc_dir.mkdir(parents=True, exist_ok=True)

        safe_title = "".join(c for c in title if c.isalnum() or c in " _-")[:60]
        filepath = doc_dir / f"{safe_title}.md"

        # YAML frontmatter
        fm_lines = [
            "---",
            f'title: "{title}"',
            f"date: {datetime.now().strftime('%Y-%m-%d')}",
        ]
        if tags:
            fm_lines.append("tags:")
            for t in tags:
                fm_lines.append(f"  - {t}")
        if links:
            fm_lines.append("links:")
            for link in links:
                fm_lines.append(f'  - "{link}"')
        fm_lines.append("created_by: max-system")
        fm_lines.append("---")

        full = "\n".join(fm_lines) + f"\n\n{content}"
        filepath.write_text(full, encoding="utf-8")
        archived_files.append(str(filepath.relative_to(vault)))

    # 索引文件
    index_content = [
        "---",
        f'title: "{project_name or client_name or category} 归档索引"',
        f"date: {datetime.now().strftime('%Y-%m-%d')}",
        "tags: [归档, max-system]",
        "---",
        "",
        f"## {project_name or client_name or category} 归档概览",
        "",
        f"归档时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"文件数量: {len(archived_files)}",
        "",
        "### 文件列表",
    ]
    for f in archived_files:
        index_content.append(f"- [[{Path(f).stem}]] — `{f}`")

    index_path = target_dir / "归档索引.md"
    index_path.write_text("\n".join(index_content), encoding="utf-8")

    result = {
        "project": project_name,
        "client": client_name,
        "category": category,
        "归档目录": str(target_dir.relative_to(vault)),
        "归档文件数": len(archived_files),
        "文件列表": archived_files,
        "索引文件": str(index_path.relative_to(vault)),
        "归档时间": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}


# ============ 工具定义和注册 ============

TOOL_DEFS = [
    {
        "name": "helper_batch_generate",
        "description": "批量生成标准化文档，支持量房单/需求分析表/设计说明/施工交底/验收单/竣工报告，自动生成校验报告。",
        "parameters": {
            "type": "object",
            "properties": {
                "doc_type": {"type": "string", "description": "文档类型: 量房单/需求分析表/设计说明/施工交底/验收单/竣工报告"},
                "projects": {"type": "string", "description": "项目列表JSON字符串，每项包含 {name, client, items}"},
                "validate": {"type": "boolean", "description": "是否进行合规校验"},
            },
            "required": ["doc_type", "projects"],
        },
    },
    {
        "name": "helper_client_tag_and_report",
        "description": "客户标签化管理、统计报表与逾期预警。支持report/tag/overdue三种操作。",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "操作: report(报表)/tag(打标签)/overdue(逾期预警)", "enum": ["report", "tag", "overdue"]},
                "client_id": {"type": "string", "description": "客户编号（tag操作时需要）"},
                "labels": {"type": "string", "description": "标签，逗号分隔（tag操作时需要）"},
            },
            "required": [],
        },
    },
    {
        "name": "helper_knowledge_catalog",
        "description": "知识库目录管理。支持catalog(查看目录)/add(新增知识条目)操作。",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "操作: catalog/add", "enum": ["catalog", "add"]},
                "category": {"type": "string", "description": "分类: company_standards/case_database/material_database/customer_service/media_materials"},
                "title": {"type": "string", "description": "文档标题（add操作时需要）"},
                "content": {"type": "string", "description": "文档内容（add操作时需要）"},
                "tags": {"type": "string", "description": "标签，逗号分隔"},
            },
            "required": [],
        },
    },
    {
        "name": "helper_feishu_sync_alert",
        "description": "生成飞书通知/预警/提醒消息模板，可指定类型、紧急程度和发送目标。",
        "parameters": {
            "type": "object",
            "properties": {
                "alert_type": {"type": "string", "description": "通知类型: reminder(提醒)/warning(预警)/notification(通知)", "enum": ["reminder", "warning", "notification"]},
                "title": {"type": "string", "description": "通知标题"},
                "content": {"type": "string", "description": "通知内容"},
                "target": {"type": "string", "description": "发送目标: 设计师/项目群/部门群"},
                "urgency": {"type": "string", "description": "紧急程度: normal(普通)/urgent(紧急)", "enum": ["normal", "urgent"]},
            },
            "required": ["title", "content"],
        },
    },
    {
        "name": "helper_obsidian_full_archive",
        "description": "全项目归档到Obsidian，创建结构化目录和索引页，自动添加YAML frontmatter和双向链接。",
        "parameters": {
            "type": "object",
            "properties": {
                "project_name": {"type": "string", "description": "项目名称"},
                "client_name": {"type": "string", "description": "客户姓名"},
                "category": {"type": "string", "description": "归档分类: projects/clients/knowledge", "enum": ["projects", "clients", "knowledge"]},
                "documents": {"type": "string", "description": "文档列表JSON字符串，每项包含 {title, content, tags, links, folder}"},
            },
            "required": ["project_name", "documents"],
        },
    },
]


def register_tools(settings: MaxSettings):
    """注册Helper工具，返回 [(name, callable, tool_def), ...]"""
    global _vault_path, _kb_path, _clients_db_ref

    _vault_path = settings.obsidian_vault_path
    _kb_path = settings.knowledge_base_path

    # 尝试引用clientmgr的客户数据库
    try:
        from max_system.tools.clientmgr_tools import _clients_db
        _clients_db_ref = _clients_db
    except ImportError:
        _clients_db_ref = {}

    handlers = {
        "helper_batch_generate": helper_batch_generate,
        "helper_client_tag_and_report": helper_client_tag_and_report,
        "helper_knowledge_catalog": helper_knowledge_catalog,
        "helper_feishu_sync_alert": helper_feishu_sync_alert,
        "helper_obsidian_full_archive": helper_obsidian_full_archive,
    }

    return [(d["name"], handlers[d["name"]], d) for d in TOOL_DEFS]
