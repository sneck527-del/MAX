"""文档生成MCP工具：模板填充 + 报价文档生成"""

import json
import logging
import re
from datetime import date
from pathlib import Path

from max_system.config.settings import MaxSettings

logger = logging.getLogger(__name__)

# ============ 模块级状态 ============

_templates_root: Path | None = None
_settings: MaxSettings | None = None

# ============ 模板管理 ============


def _get_templates_root() -> Path:
    """获取模板根目录"""
    if _templates_root is not None:
        return _templates_root
    # 默认使用项目根目录下的 templates/
    root = _settings.get_project_root() if _settings else Path(__file__).resolve().parent.parent.parent
    return root / "templates"


def _scan_templates() -> list[dict]:
    """扫描 templates/ 目录，返回所有模板文件信息，按阶段分组"""
    root = _get_templates_root()
    if not root.exists():
        return []

    phases: dict[str, dict] = {}
    for entry in sorted(root.iterdir()):
        if entry.is_dir():
            phase_name = entry.name
            # 解析阶段编号和名称: 如 "01_前期对接与需求确认"
            parts = phase_name.split("_", 1)
            phase_num = parts[0] if parts else ""
            phase_label = parts[1] if len(parts) > 1 else phase_name

            files = []
            for md_file in sorted(entry.glob("*.md")):
                if md_file.name == "README.md":
                    continue
                template_info = _parse_template_frontmatter(md_file)
                template_info["filename"] = md_file.name
                template_info["template_name"] = md_file.stem
                template_info["relative_path"] = str(md_file.relative_to(root))
                files.append(template_info)

            if files:
                phases[phase_name] = {
                    "phase_number": phase_num,
                    "phase_label": phase_label,
                    "path": phase_name,
                    "templates": files,
                }

    # 按阶段编号排序
    result = []
    for key in sorted(phases.keys()):
        result.append(phases[key])
    return result


def _parse_template_frontmatter(filepath: Path) -> dict:
    """解析模板文件的 YAML frontmatter（简单解析，不依赖 pyyaml）"""
    info = {"description": "", "category": "", "responsible": ""}
    try:
        content = filepath.read_text(encoding="utf-8")
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                frontmatter = content[3:end]
                for line in frontmatter.strip().split("\n"):
                    line = line.strip()
                    if ":" in line:
                        key, _, value = line.partition(":")
                        key = key.strip()
                        value = value.strip()
                        if key in info:
                            info[key] = value
    except Exception:
        pass
    return info


def _find_template(template_name: str) -> Path | None:
    """在模板目录中查找匹配的模板文件"""
    root = _get_templates_root()
    if not root.exists():
        return None

    # 精确匹配：文件名（不含扩展名）完全相等
    for md_file in root.rglob("*.md"):
        if md_file.name == "README.md":
            continue
        if md_file.stem == template_name:
            return md_file

    # 模糊匹配：文件名包含 template_name 或 template_name 包含文件名
    for md_file in root.rglob("*.md"):
        if md_file.name == "README.md":
            continue
        if template_name in md_file.stem or md_file.stem in template_name:
            return md_file

    return None


def _render_template(template_content: str, variables: dict) -> str:
    """替换模板中的 {{变量}} 占位符，未匹配的保留原样并附加提示"""
    rendered_lines = []
    unresolved = set()

    for line in template_content.split("\n"):
        def replace_var(match):
            var_name = match.group(1)
            if var_name in variables:
                val = variables[var_name]
                return str(val) if val is not None else f"{{{{{var_name}}}}}"
            unresolved.add(var_name)
            return f"{{{{{var_name}}}}}"  # 保持原样
        rendered = re.sub(r"\{\{(.+?)\}\}", replace_var, line)
        rendered_lines.append(rendered)

    result = "\n".join(rendered_lines)

    if unresolved:
        note = "\n\n---\n> 以下变量未提供数据，已保留原占位符：\n"
        for v in sorted(unresolved):
            note += f"> - `{{{{{v}}}}}`\n"
        result += note

    return result


# ============ 工具实现 ============


async def generate_document(args: dict) -> dict:
    """填充模板生成格式化文档"""
    template_name = args.get("template_name", "")
    client_name = args.get("client_name", "")
    client_id = args.get("client_id", "")
    project_name = args.get("project_name", "")
    custom_data = args.get("custom_data", {})

    # 列出所有模板
    if template_name == "list":
        templates = _scan_templates()
        if not templates:
            return {"content": [{"type": "text", "text": "模板目录为空，请先在 templates/ 目录下添加模板文件。"}]}

        lines = ["## 可用文档模板", ""]
        lines.append(f"共 {sum(len(p['templates']) for p in templates)} 份模板，按 {len(templates)} 个阶段组织。")
        lines.append("")

        for phase in templates:
            lines.append(f"### {phase['phase_number']} — {phase['phase_label']}")
            lines.append("")
            for t in phase["templates"]:
                desc = f" — {t['description']}" if t["description"] else ""
                lines.append(f"- **{t['template_name']}**{desc}")
                lines.append(f"  `{t['relative_path']}`")
            lines.append("")

        lines.append("---")
        lines.append("使用 `generate_document` 并指定 `template_name` 即可生成文档。")
        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    # 查找模板文件
    if not template_name:
        return {"content": [{"type": "text", "text": "请指定 template_name，或使用 template_name=\"list\" 查看可用模板。"}]}

    template_path = _find_template(template_name)
    if template_path is None:
        return {"content": [{"type": "text", "text": f"未找到模板: {template_name}。使用 template_name=\"list\" 查看可用模板列表。"}]}

    try:
        template_content = template_path.read_text(encoding="utf-8")
    except Exception as e:
        return {"content": [{"type": "text", "text": f"读取模板文件失败: {e}"}]}

    # 查找客户数据
    client_data: dict = {}
    try:
        from max_system.tools.clientmgr_tools import _clients_db

        if client_id and client_id in _clients_db:
            client_data = _clients_db[client_id]
        elif client_name:
            name_lower = client_name.lower()
            for c in _clients_db.values():
                if name_lower in c.get("name", "").lower():
                    client_data = c
                    break
    except Exception as e:
        logger.warning("查找客户数据失败: %s", e)

    # 查找设计师信息
    company_name = ""
    try:
        from max_system.tools.profile_tools import get_profile_manager
        mgr = get_profile_manager()
        if mgr is not None:
            company_name = await mgr.get("company_name") or ""
    except Exception as e:
        logger.warning("获取Profile失败: %s", e)

    # 构建变量映射
    today_str = date.today().strftime("%Y-%m-%d")
    variables = {
        "客户姓名": client_data.get("name", client_name or ""),
        "项目地址": client_data.get("city", project_name or ""),
        "户型": client_data.get("unit_type", ""),
        "面积": _extract_area(client_data),
        "设计师": company_name,
        "日期": today_str,
        "报价": client_data.get("budget", ""),
        "合同额": client_data.get("design_fee", client_data.get("budget", "")),
        "电话": client_data.get("phone", ""),
    }

    # 合并自定义数据
    if isinstance(custom_data, dict):
        for k, v in custom_data.items():
            variables[k] = v

    # 渲染模板
    rendered = _render_template(template_content, variables)

    # 追加审核提醒
    rendered += "\n\n---\n> 此文档为AI生成草稿，请设计师审核确认后使用"

    return {"content": [{"type": "text", "text": rendered}]}


def _extract_area(client_data: dict) -> str:
    """从客户数据中提取面积信息"""
    # 尝试从 unit_type 中提取数字，如 "150㎡大平层"
    unit = client_data.get("unit_type", "")
    if unit:
        m = re.search(r"(\d+)\s*[㎡平米mM]", unit)
        if m:
            return m.group(1)
    # 尝试从设计费中推测（不可靠，仅fallback）
    design_fee = client_data.get("design_fee", "")
    if design_fee:
        return str(design_fee)
    return ""


async def generate_quote_document(args: dict) -> dict:
    """生成格式化的报价文档"""
    items = args.get("items", [])
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except json.JSONDecodeError:
            return {"content": [{"type": "text", "text": "items 参数格式错误，需要 JSON 数组。"}]}

    client_name = args.get("client_name", "")
    project_name = args.get("project_name", "")

    if not items:
        return {"content": [{"type": "text", "text": "请提供报价项目列表 items。"}]}

    # 调用报价汇总计算
    try:
        from max_system.tools.quote_tools import quote_calculate_summary
        summary_result = await quote_calculate_summary({"items": items})
        summary_text = summary_result["content"][0]["text"]
        summary = json.loads(summary_text)
    except Exception as e:
        return {"content": [{"type": "text", "text": f"计算报价汇总失败: {e}"}]}

    # 获取公司名称
    company_name = ""
    try:
        from max_system.tools.profile_tools import get_profile_manager
        mgr = get_profile_manager()
        if mgr is not None:
            company_name = await mgr.get("company_name") or ""
    except Exception:
        pass

    today_str = date.today().strftime("%Y-%m-%d")

    # 构建格式化报价文档
    lines = []
    lines.append("# 装修工程报价单")
    lines.append("")

    # 头部信息
    if company_name:
        lines.append(f"**设计单位：** {company_name}")
    if client_name:
        lines.append(f"**客户姓名：** {client_name}")
    if project_name:
        lines.append(f"**项目名称：** {project_name}")
    lines.append(f"**报价日期：** {today_str}")
    lines.append("")

    # 分项明细表
    if summary.get("items"):
        lines.append("## 报价项目明细")
        lines.append("")
        lines.append("| 序号 | 项目名称 | 类型 | 数量 | 单价(元) | 金额(元) |")
        lines.append("|------|---------|------|------|---------|---------|")
        for idx, item in enumerate(summary["items"], 1):
            item_type = "施工" if item.get("type") == "engineering" else "主材"
            lines.append(
                f"| {idx} | {item.get('name', '-')} | {item_type} | "
                f"{item.get('quantity', 0)} | {item.get('unit_price', 0)} | "
                f"{item.get('amount', 0)} |"
            )
        lines.append("")

    # 费用汇总
    lines.append("## 费用汇总")
    lines.append("")
    lines.append("| 费用项目 | 金额(元) |")
    lines.append("|---------|---------|")
    lines.append(f"| 工程小计 | {summary.get('工程小计', 0)} |")
    lines.append(f"| 产品小计 | {summary.get('产品小计', 0)} |")
    lines.append(f"| **直接费用合计** | **{summary.get('直接费用合计', 0)}** |")
    lines.append(f"| 管理费（{summary.get('管理费比例', '8%')}） | {summary.get('管理费', 0)} |")
    lines.append(f"| 税金（{summary.get('税金比例', '3.41%')}） | {summary.get('税金', 0)} |")
    lines.append(f"| 垃圾清运费 | {summary.get('垃圾清运费', 0)} |")
    lines.append(f"| 成品保护费 | {summary.get('成品保护费', 0)} |")
    lines.append(f"| **报价总计** | **{summary.get('报价总计', 0)}** |")
    lines.append("")

    # 付款条款
    lines.append("## 付款方式")
    lines.append("")
    lines.append("| 付款节点 | 比例 | 应付金额(元) |")
    lines.append("|---------|------|-------------|")
    lines.append("| 签约首期款 | 待定 | — |")
    lines.append("| 中期款 | 待定 | — |")
    lines.append("| 竣工验收尾款 | 待定 | — |")
    lines.append("")

    # 有效期
    lines.append(f"**报价有效期：** 自报价日期起 30 天")
    lines.append("")
    lines.append("---")
    lines.append("> 此文档为AI生成草稿，请设计师审核确认后使用")

    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


# ============ 工具定义 ============

TOOL_DEFS = [
    {
        "name": "generate_document",
        "description": (
            "填充文档模板生成格式化文档。设计师说'生成XX文档'或'帮我填一下XX模板'时使用。"
            "先查可用模板列表，再填充指定模板的占位符（{{客户姓名}}、{{项目地址}}、{{日期}}等），自动代入客户数据和设计师信息。"
            "使用 template_name=\"list\" 可查看全部可用模板。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "template_name": {
                    "type": "string",
                    "description": "模板名称（不含.md扩展名），如'客户信息与装修需求登记表'。传'list'列出所有可用模板。",
                },
                "client_name": {
                    "type": "string",
                    "description": "客户姓名，用于自动填充模板中的客户相关占位符。",
                },
                "client_id": {
                    "type": "string",
                    "description": "客户编号，用于精确查找客户数据。与client_name二选一。",
                },
                "project_name": {
                    "type": "string",
                    "description": "项目名称，用于填充{{项目地址}}等占位符（如未提供客户数据）。",
                },
                "custom_data": {
                    "type": "object",
                    "description": "自定义变量，key-value形式，用于填充模板中额外的{{变量}}占位符。",
                },
            },
            "required": ["template_name"],
        },
    },
    {
        "name": "generate_quote_document",
        "description": (
            "生成格式化的装修工程报价单。设计师说'生成报价单'或'帮我出一个报价文档'时使用。"
            "自动计算管理费、税金、垃圾清运费、成品保护费，汇总报价总计，输出客户可查看的报价文档。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "description": "报价项目列表。每项需含 quantity（数量）和 unit_price（单价），可选 name（名称）和 type（engineering=施工/material=主材）",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "项目名称"},
                            "type": {
                                "type": "string",
                                "description": "类型: engineering(施工) 或 material(主材)",
                                "enum": ["engineering", "material"],
                            },
                            "quantity": {"type": "number", "description": "数量"},
                            "unit_price": {"type": "number", "description": "单价"},
                        },
                        "required": ["quantity", "unit_price"],
                    },
                },
                "client_name": {
                    "type": "string",
                    "description": "客户姓名（可选）",
                },
                "project_name": {
                    "type": "string",
                    "description": "项目名称（可选）",
                },
            },
            "required": ["items"],
        },
    },
]


def register_tools(settings: MaxSettings):
    global _settings, _templates_root
    _settings = settings
    _templates_root = settings.get_project_root() / "templates"

    handlers = {
        "generate_document": generate_document,
        "generate_quote_document": generate_quote_document,
    }
    return [(d["name"], handlers[d["name"]], d) for d in TOOL_DEFS]
