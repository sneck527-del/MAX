"""Obsidian MCP工具：归档、搜索、读取"""

import json
import logging
from pathlib import Path
from datetime import datetime

from max_system.config.settings import MaxSettings

logger = logging.getLogger(__name__)

_vault_path: Path | None = None


def _get_vault_path() -> Path:
    if _vault_path is None:
        raise RuntimeError("Obsidian Vault路径未初始化")
    return _vault_path


def _build_frontmatter(title: str, tags: list[str], links: list[str]) -> str:
    lines = ["---"]
    lines.append(f'title: "{title}"')
    lines.append(f"date: {datetime.now().strftime('%Y-%m-%d')}")
    if tags:
        lines.append("tags:")
        for tag in tags:
            lines.append(f"  - {tag}")
    if links:
        lines.append("links:")
        for link in links:
            lines.append(f'  - "{link}"')
    lines.append("created_by: max-system")
    lines.append("---")
    return "\n".join(lines)


async def obsidian_archive_note(args: dict) -> dict:
    vault = _get_vault_path()
    folder = Path(args.get("folder", "归档"))
    tags = json.loads(args["tags"]) if isinstance(args.get("tags"), str) and args.get("tags") else args.get("tags", [])
    links = json.loads(args["links"]) if isinstance(args.get("links"), str) and args.get("links") else args.get("links", [])

    target_dir = vault / folder
    target_dir.mkdir(parents=True, exist_ok=True)

    safe_title = "".join(c for c in args["title"] if c.isalnum() or c in " _-")[:50]
    filepath = target_dir / f"{safe_title}.md"

    frontmatter = _build_frontmatter(args["title"], tags, links)
    filepath.write_text(f"{frontmatter}\n\n{args['content']}", encoding="utf-8")

    return {"content": [{"type": "text", "text": f"已归档到 Vault: {filepath.relative_to(vault)}"}]}


async def obsidian_search_vault(args: dict) -> dict:
    vault = _get_vault_path()
    query = args["query"]
    search_type = args.get("search_type", "keyword")

    results = []
    for md_file in vault.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8", errors="ignore")
        if search_type == "tag":
            if f"- {query}" in content:
                results.append(str(md_file.relative_to(vault)))
        else:
            if query.lower() in content.lower():
                results.append(str(md_file.relative_to(vault)))
        if len(results) >= 20:
            break

    return {"content": [{"type": "text", "text": json.dumps(results, ensure_ascii=False)}]}


async def obsidian_read_note(args: dict) -> dict:
    vault = _get_vault_path()
    filepath = vault / args["path"]
    if not filepath.exists():
        return {"content": [{"type": "text", "text": f"文件不存在: {args['path']}"}], "is_error": True}
    content = filepath.read_text(encoding="utf-8")
    return {"content": [{"type": "text", "text": content}]}


TOOL_DEFS = [
    {
        "name": "obsidian_archive_note",
        "description": "归档文档到Obsidian Vault，自动添加YAML frontmatter、标签和双向链接。",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "笔记标题"},
                "content": {"type": "string", "description": "笔记内容"},
                "folder": {"type": "string", "description": "Vault内相对目录路径"},
                "tags": {"type": "string", "description": "标签列表JSON字符串"},
                "links": {"type": "string", "description": "双向链接列表JSON字符串"},
            },
            "required": ["title", "content"],
        },
    },
    {
        "name": "obsidian_search_vault",
        "description": "搜索Obsidian Vault中的笔记，支持关键词和标签搜索。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
                "search_type": {"type": "string", "description": "搜索类型: keyword/tag", "enum": ["keyword", "tag"]},
            },
            "required": ["query"],
        },
    },
    {
        "name": "obsidian_read_note",
        "description": "读取Obsidian Vault中指定路径的笔记内容。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "笔记在Vault中的相对路径"},
            },
            "required": ["path"],
        },
    },
]


def register_tools(settings: MaxSettings):
    global _vault_path
    _vault_path = settings.obsidian_vault_path
    _vault_path.mkdir(parents=True, exist_ok=True)

    handlers = {
        "obsidian_archive_note": obsidian_archive_note,
        "obsidian_search_vault": obsidian_search_vault,
        "obsidian_read_note": obsidian_read_note,
    }
    return [(d["name"], handlers[d["name"]], d) for d in TOOL_DEFS]
