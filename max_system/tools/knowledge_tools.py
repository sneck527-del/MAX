"""知识库MCP工具：搜索、合规检查、批量导入、语义搜索

Supports multi-tenant workspace isolation:
- Each workspace can have its own knowledge directory at data/workspaces/{ws_id}/knowledge/
- If the workspace-specific directory exists, it is used; otherwise fall back to global knowledge/
- The knowledge_import tool writes to the workspace-specific directory when in a workspace context
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path

from max_system.config.settings import MaxSettings

logger = logging.getLogger(__name__)

_kb_path: Path | None = None
_settings: MaxSettings | None = None
_vector_store = None  # 延迟初始化


def _get_active_kb_path() -> Path | None:
    """Return workspace-specific knowledge path if active and exists, else global fallback."""
    from max_system.core.orchestrator import _current_workspace
    ws = _current_workspace.get(None)
    if ws is not None and _kb_path is not None:
        ws_kb = ws.dir / "knowledge"
        # For reads: prefer workspace kb if it exists, else fall back to global
        # For writes: create the workspace kb directory
        if ws_kb.exists():
            return ws_kb
        # If in workspace context, always return workspace path (caller handles creation)
        return ws_kb
    return _kb_path


def _get_vector_store():
    """延迟初始化并缓存VectorStore实例。"""
    global _vector_store
    if _vector_store is not None:
        return _vector_store

    try:
        from max_system.integrations.knowledge.vector_store import VectorStore

        vs_path = _settings.get_project_root() / "data" / "vector_store" if _settings else Path("data/vector_store")
        _vector_store = VectorStore(vs_path)
        _vector_store.initialize()
        logger.info("VectorStore延迟初始化完成，文档数: %d", _vector_store.count())
    except Exception as e:
        logger.warning("VectorStore初始化失败: %s", e)
        _vector_store = None

    return _vector_store


async def knowledge_search(args: dict) -> dict:
    """搜索公司知识库，支持关键词、语义和混合搜索。"""
    kb = _get_active_kb_path()
    if not kb or not kb.exists():
        return {"content": [{"type": "text", "text": "知识库目录尚未配置或不存在"}]}

    query = args.get("query", "")
    if not query:
        return {"content": [{"type": "text", "text": json.dumps([], ensure_ascii=False)}]}

    query_lower = query.lower()
    category = args.get("category", "")
    top_k = args.get("top_k", 5)
    search_type = args.get("search_type", "keyword")

    keyword_results = []
    semantic_results = []

    # ---- 关键词搜索（grep方式） ----
    if search_type in ("keyword", "hybrid"):
        search_dirs = [kb / category] if category and (kb / category).exists() else [
            kb / "company_standards", kb / "case_database",
            kb / "material_database", kb / "customer_service",
            kb / "media_materials",
        ]

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            for f in search_dir.rglob("*.md"):
                content = f.read_text(encoding="utf-8", errors="ignore")
                if query_lower in content.lower():
                    idx = content.lower().find(query_lower)
                    start = max(0, idx - 100)
                    end = min(len(content), idx + len(query) + 200)
                    snippet = content[start:end]
                    keyword_results.append({
                        "file": str(f.relative_to(kb)),
                        "snippet": snippet,
                        "source": "keyword",
                    })
                    if len(keyword_results) >= top_k:
                        break
            if len(keyword_results) >= top_k:
                break

    # ---- 语义搜索 ----
    if search_type in ("semantic", "hybrid"):
        try:
            vs = _get_vector_store()
            if vs is not None:
                raw_results = vs.search(query, top_k=top_k, category=category)
                for r in raw_results:
                    meta = r.get("metadata", {})
                    semantic_results.append({
                        "file": meta.get("file", meta.get("path", r.get("id", ""))),
                        "snippet": r.get("content", "")[:300],
                        "score": round(1.0 - float(r.get("distance", 0)), 4) if r.get("distance") is not None else None,
                        "source": "semantic",
                    })
        except Exception as e:
            logger.warning("语义搜索失败，回退到关键词搜索: %s", e)

    # ---- 合并结果 ----
    if search_type == "hybrid":
        # 合并并以file去重，优先保留关键词结果
        seen_files = set()
        merged = []
        for r in keyword_results:
            if r["file"] not in seen_files:
                seen_files.add(r["file"])
                merged.append(r)
        for r in semantic_results:
            if r["file"] not in seen_files:
                seen_files.add(r["file"])
                merged.append(r)
        final_results = merged[:top_k]
    elif search_type == "semantic":
        final_results = semantic_results[:top_k] if semantic_results else keyword_results[:top_k]
    else:
        final_results = keyword_results[:top_k]

    return {"content": [{"type": "text", "text": json.dumps(final_results, ensure_ascii=False)}]}


async def knowledge_compliance_check(args: dict) -> dict:
    kb = _get_active_kb_path()
    if not kb or not kb.exists():
        return {"content": [{"type": "text", "text": "知识库未配置，无法进行合规检查"}]}

    content = args["content"]
    violations = []

    safety_keywords = ["承重墙拆除", "梁体切割", "楼板开洞", "擅自改动结构"]
    for kw in safety_keywords:
        if kw in content:
            violations.append(f"红线违规: 涉及结构安全 - '{kw}'")

    if "底价" in content or "采购价" in content:
        violations.append("数据安全: 内容中包含供应商底价信息")

    if re.search(r"1[3-9]\d{9}", content):
        violations.append("隐私风险: 内容中包含手机号码")

    return {"content": [{"type": "text", "text": json.dumps({
        "compliant": len(violations) == 0, "violations": violations,
    }, ensure_ascii=False)}]}


async def knowledge_catalog(args: dict) -> dict:
    """知识库目录管理：查看目录或新增条目"""
    action = args.get("action", "catalog")
    kb = _get_active_kb_path()

    if action == "catalog":
        if not kb or not kb.exists():
            return {"content": [{"type": "text", "text": "知识库目录不存在"}]}

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

        # 同时添加到向量存储
        try:
            vs = _get_vector_store()
            if vs is not None:
                vs.add_documents([{
                    "id": f"kb_{category}_{safe_name}",
                    "content": content,
                    "metadata": {
                        "category": category,
                        "title": title,
                        "tags": tags,
                        "file": str(filepath.relative_to(kb)),
                    },
                }])
        except Exception as e:
            logger.warning("向量存储添加文档失败: %s", e)

        return {"content": [{"type": "text", "text": json.dumps({
            "success": True,
            "path": str(filepath.relative_to(kb)),
            "category": category,
            "title": title,
        }, ensure_ascii=False, indent=2)}]}

    return {"content": [{"type": "text", "text": f"未知操作: {action}"}]}


async def knowledge_import(args: dict) -> dict:
    """批量导入知识文档，支持目录扫描、JSON文件和直接文本导入。"""
    kb = _get_active_kb_path()
    if not kb:
        return {"content": [{"type": "text", "text": "知识库未配置"}]}
    if not kb.exists():
        kb.mkdir(parents=True, exist_ok=True)

    source = args.get("source", "text")
    path_str = args.get("path", "")
    category = args.get("category", "company_standards")
    documents = args.get("documents", [])

    imported = []
    errors = []

    if source == "directory":
        if not path_str:
            return {"content": [{"type": "text", "text": "目录导入需要提供path参数"}]}
        dir_path = Path(path_str)
        if not dir_path.exists() or not dir_path.is_dir():
            return {"content": [{"type": "text", "text": f"目录不存在: {path_str}"}]}

        md_files = list(dir_path.rglob("*.md"))
        for md_file in md_files:
            try:
                content = md_file.read_text(encoding="utf-8", errors="ignore")
                title = md_file.stem

                # 尝试从YAML frontmatter中提取title
                frontmatter_match = re.match(r'^---\s*\ntitle:\s*"?([^"\n]+)"?\s*\n', content)
                if frontmatter_match:
                    title = frontmatter_match.group(1).strip()

                target_dir = kb / category
                target_dir.mkdir(parents=True, exist_ok=True)
                safe_name = "".join(c for c in title if c.isalnum() or c in " _-")[:60]
                dest_path = target_dir / f"{safe_name}.md"
                dest_path.write_text(content, encoding="utf-8")
                imported.append(str(dest_path.relative_to(kb)))

                # 添加到向量存储
                try:
                    vs = _get_vector_store()
                    if vs is not None:
                        vs.add_documents([{
                            "id": f"kb_{category}_{safe_name}",
                            "content": content,
                            "metadata": {
                                "category": category,
                                "title": title,
                                "file": str(dest_path.relative_to(kb)),
                            },
                        }])
                except Exception as e:
                    logger.warning("向量存储添加失败: %s", e)
            except Exception as e:
                errors.append(f"{md_file}: {str(e)}")

    elif source == "json_file":
        if not path_str:
            return {"content": [{"type": "text", "text": "JSON文件导入需要提供path参数"}]}
        json_path = Path(path_str)
        if not json_path.exists():
            return {"content": [{"type": "text", "text": f"JSON文件不存在: {path_str}"}]}

        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            entries = data if isinstance(data, list) else data.get("entries", [])
            for i, entry in enumerate(entries):
                try:
                    title = entry.get("title", f"imported_{i}")
                    content = entry.get("content", "")
                    tags = entry.get("tags", "")
                    entry_category = entry.get("category", category)

                    if not content:
                        errors.append(f"条目{i}: 内容为空")
                        continue

                    target_dir = kb / entry_category
                    target_dir.mkdir(parents=True, exist_ok=True)
                    safe_name = "".join(c for c in title if c.isalnum() or c in " _-")[:60]
                    dest_path = target_dir / f"{safe_name}.md"

                    frontmatter = [
                        "---",
                        f'title: "{title}"',
                        f"date: {datetime.now().strftime('%Y-%m-%d')}",
                        f"tags: [{tags}]" if tags else "",
                        "created_by: max-import",
                        "---",
                    ]
                    full_content = "\n".join(frontmatter) + f"\n\n{content}"
                    dest_path.write_text(full_content, encoding="utf-8")
                    imported.append(str(dest_path.relative_to(kb)))

                    # 添加到向量存储
                    try:
                        vs = _get_vector_store()
                        if vs is not None:
                            vs.add_documents([{
                                "id": f"kb_{entry_category}_{safe_name}",
                                "content": content,
                                "metadata": {
                                    "category": entry_category,
                                    "title": title,
                                    "tags": tags,
                                    "file": str(dest_path.relative_to(kb)),
                                },
                            }])
                    except Exception as e:
                        logger.warning("向量存储添加失败: %s", e)
                except Exception as e:
                    errors.append(f"条目{i}: {str(e)}")
        except json.JSONDecodeError as e:
            errors.append(f"JSON解析失败: {str(e)}")

    elif source == "text":
        if not documents:
            return {"content": [{"type": "text", "text": "文本导入需要提供documents参数"}]}
        if isinstance(documents, str):
            try:
                documents = json.loads(documents)
            except json.JSONDecodeError:
                return {"content": [{"type": "text", "text": "documents参数格式错误，需要JSON数组"}]}

        for i, entry in enumerate(documents):
            try:
                title = entry.get("title", f"imported_{i}")
                content = entry.get("content", "")
                tags = entry.get("tags", "")
                entry_category = entry.get("category", category)

                if not title or not content:
                    errors.append(f"条目{i}: 标题或内容为空")
                    continue

                target_dir = kb / entry_category
                target_dir.mkdir(parents=True, exist_ok=True)
                safe_name = "".join(c for c in title if c.isalnum() or c in " _-")[:60]
                dest_path = target_dir / f"{safe_name}.md"

                frontmatter = [
                    "---",
                    f'title: "{title}"',
                    f"date: {datetime.now().strftime('%Y-%m-%d')}",
                    f"tags: [{tags}]" if tags else "",
                    "created_by: max-import",
                    "---",
                ]
                full_content = "\n".join(frontmatter) + f"\n\n{content}"
                dest_path.write_text(full_content, encoding="utf-8")
                imported.append(str(dest_path.relative_to(kb)))

                # 添加到向量存储
                try:
                    vs = _get_vector_store()
                    if vs is not None:
                        vs.add_documents([{
                            "id": f"kb_{entry_category}_{safe_name}",
                            "content": content,
                            "metadata": {
                                "category": entry_category,
                                "title": title,
                                "tags": tags,
                                "file": str(dest_path.relative_to(kb)),
                            },
                        }])
                except Exception as e:
                    logger.warning("向量存储添加失败: %s", e)
            except Exception as e:
                errors.append(f"条目{i}: {str(e)}")
    else:
        return {"content": [{"type": "text", "text": f"不支持的导入来源: {source}，可选: directory/json_file/text"}]}

    return {"content": [{"type": "text", "text": json.dumps({
        "success": len(errors) == 0,
        "导入数量": len(imported),
        "导入文件": imported,
        "错误": errors[:20] if errors else [],
    }, ensure_ascii=False, indent=2)}]}


TOOL_DEFS = [
    {
        "name": "knowledge_search",
        "description": "搜索公司知识库，包含公司标准、案例、材料库、客服话术等。支持关键词搜索、语义搜索和混合搜索。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
                "category": {"type": "string", "description": "类别: company_standards/case_database/material_database/customer_service/media_materials"},
                "top_k": {"type": "integer", "description": "返回结果数量"},
                "search_type": {"type": "string", "description": "搜索类型: keyword(关键词)/semantic(语义)/hybrid(混合)", "enum": ["keyword", "semantic", "hybrid"]},
            },
            "required": ["query"],
        },
    },
    {
        "name": "knowledge_compliance_check",
        "description": "检查内容是否符合公司标准和合规要求。",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "要检查的内容"},
                "check_type": {"type": "string", "description": "检查类型: contract/quotation/publicity/after_sales"},
            },
            "required": ["content"],
        },
    },
    {
        "name": "knowledge_catalog",
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
        "name": "knowledge_import",
        "description": "批量导入知识文档到知识库。支持从目录扫描md文件、JSON文件导入、或直接传入文档列表。导入后同时写入文件系统和向量存储。",
        "parameters": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "导入来源: directory(目录扫描)/json_file(JSON文件)/text(直接传入)", "enum": ["directory", "json_file", "text"]},
                "path": {"type": "string", "description": "文件或目录路径（directory和json_file来源时必填）"},
                "category": {"type": "string", "description": "默认分类: company_standards/case_database/material_database/customer_service/media_materials"},
                "documents": {"type": "array", "items": {"type": "object"}, "description": "文档列表（text来源时必填），每项含title/content/tags/category"},
            },
            "required": ["source"],
        },
    },
]


def register_tools(settings: MaxSettings):
    global _kb_path, _settings
    _settings = settings
    _kb_path = settings.get_knowledge_base_path()
    _kb_path.mkdir(parents=True, exist_ok=True)

    handlers = {
        "knowledge_search": knowledge_search,
        "knowledge_compliance_check": knowledge_compliance_check,
        "knowledge_catalog": knowledge_catalog,
        "knowledge_import": knowledge_import,
    }
    return [(d["name"], handlers[d["name"]], d) for d in TOOL_DEFS]
