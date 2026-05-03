"""数据加载器：从各种来源加载文档到知识库"""

import json
import logging
from pathlib import Path
from typing import Generator

from max_system.config.settings import MaxSettings

logger = logging.getLogger(__name__)


def load_all_sources(settings: MaxSettings) -> Generator[tuple[str, str, dict], None, None]:
    """加载所有知识来源，yield (doc_id, content, metadata)

    数据来源：
    1. 06_知识库/ 下的所有md和json文件
    2. Quote/材料库.json 和 施工库.json
    3. 各Agent的system_prompt.md（作为规范知识）
    """

    # 1. 加载知识库目录
    yield from _load_directory(settings.get_knowledge_base_path(), "knowledge_base")

    # 2. 加载报价数据
    yield from _load_quote_data(settings.get_quote_data_path())

    # 3. 加载Agent规范
    yield from _load_agent_prompts(settings.get_prompts_root())


def _load_directory(dir_path: Path, source: str) -> Generator[tuple[str, str, dict], None, None]:
    """递归加载目录下的文档"""
    if not dir_path.exists():
        return

    for f in sorted(dir_path.rglob("*")):
        if f.is_dir():
            continue
        if f.suffix == ".md":
            content = f.read_text(encoding="utf-8", errors="ignore")
            if content.strip():
                doc_id = f"{source}_{f.relative_to(dir_path).as_posix()}"
                metadata = {
                    "source": source,
                    "file_type": "markdown",
                    "path": str(f.relative_to(dir_path)),
                }
                yield doc_id, content, metadata
        elif f.suffix == ".json":
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                # 将JSON转为可搜索的文本
                flat_text = _flatten_json(data)
                if flat_text.strip():
                    doc_id = f"{source}_{f.relative_to(dir_path).as_posix()}"
                    metadata = {
                        "source": source,
                        "file_type": "json",
                        "path": str(f.relative_to(dir_path)),
                    }
                    yield doc_id, flat_text, metadata
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass


def _load_quote_data(quote_path: Path) -> Generator[tuple[str, str, dict], None, None]:
    """加载报价系统数据"""
    if not quote_path.exists():
        return

    # 材料库
    materials_file = quote_path / "材料库.json"
    if materials_file.exists():
        try:
            data = json.loads(materials_file.read_text(encoding="utf-8"))
            for category, items in data.items():
                if isinstance(items, dict):
                    for sub_cat, sub_items in items.items():
                        content = f"材料类别: {category} > {sub_cat}\n"
                        if isinstance(sub_items, list):
                            for item in sub_items:
                                content += _format_material_item(item) + "\n"
                        doc_id = f"quote_material_{category}_{sub_cat}"
                        metadata = {
                            "source": "quote_materials",
                            "category": category,
                            "subcategory": sub_cat,
                        }
                        yield doc_id, content, metadata
                elif isinstance(items, list):
                    content = f"材料类别: {category}\n"
                    for item in items:
                        content += _format_material_item(item) + "\n"
                    doc_id = f"quote_material_{category}"
                    metadata = {"source": "quote_materials", "category": category}
                    yield doc_id, content, metadata
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning("加载材料库失败: %s", e)

    # 施工库
    construction_file = quote_path / "施工库.json"
    if construction_file.exists():
        try:
            data = json.loads(construction_file.read_text(encoding="utf-8"))
            for trade, items in data.items():
                content = f"施工工种: {trade}\n"
                if isinstance(items, list):
                    for item in items:
                        content += _format_construction_item(item) + "\n"
                doc_id = f"quote_construction_{trade}"
                metadata = {"source": "quote_construction", "trade": trade}
                yield doc_id, content, metadata
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning("加载施工库失败: %s", e)


def _load_agent_prompts(prompts_root: Path) -> Generator[tuple[str, str, dict], None, None]:
    """加载Agent的system_prompt作为规范知识"""
    agent_dirs = [
        "01_Max总控",
    ]

    for agent_dir in agent_dirs:
        prompt_path = prompts_root / agent_dir / "config" / "system_prompt.md"
        if prompt_path.exists():
            content = prompt_path.read_text(encoding="utf-8")
            if content.strip():
                doc_id = f"agent_prompt_{agent_dir}"
                metadata = {
                    "source": "agent_prompt",
                    "agent": agent_dir,
                    "file_type": "markdown",
                }
                yield doc_id, content, metadata

        # 也加载各技能的prompt
        agent_path = prompts_root / agent_dir
        if agent_path.exists():
            for skill_dir in sorted(agent_path.iterdir()):
                if skill_dir.is_dir() and skill_dir.name.startswith("skill_"):
                    skill_prompt = skill_dir / "config" / "system_prompt.md"
                    if skill_prompt.exists():
                        content = skill_prompt.read_text(encoding="utf-8")
                        if content.strip():
                            doc_id = f"agent_prompt_{agent_dir}_{skill_dir.name}"
                            metadata = {
                                "source": "agent_prompt",
                                "agent": agent_dir,
                                "skill": skill_dir.name,
                                "file_type": "markdown",
                            }
                            yield doc_id, content, metadata


def _flatten_json(data, prefix="") -> str:
    """将JSON数据展平为可搜索的文本"""
    if isinstance(data, dict):
        parts = []
        for k, v in data.items():
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, (dict, list)):
                parts.append(_flatten_json(v, key))
            else:
                parts.append(f"{key}: {v}")
        return "\n".join(parts)
    elif isinstance(data, list):
        parts = []
        for i, item in enumerate(data):
            parts.append(_flatten_json(item, f"{prefix}[{i}]"))
        return "\n".join(parts)
    else:
        return f"{prefix}: {data}"


def _format_material_item(item) -> str:
    """格式化材料条目"""
    if isinstance(item, dict):
        name = item.get("name", item.get("名称", ""))
        unit = item.get("unit", item.get("单位", ""))
        price = item.get("unit_price", item.get("单价", ""))
        return f"  - {name} | 单位: {unit} | 单价: {price}"
    return str(item)


def _format_construction_item(item) -> str:
    """格式化施工条目"""
    if isinstance(item, dict):
        name = item.get("project", item.get("项目", ""))
        unit = item.get("unit", item.get("单位", ""))
        price = item.get("comprehensive_price", item.get("综合单价", ""))
        standard = item.get("process_requirements_and_standards", item.get("工艺标准", ""))
        return f"  - {name} | 单位: {unit} | 综合单价: {price} | 工艺: {standard[:100]}"
    return str(item)
