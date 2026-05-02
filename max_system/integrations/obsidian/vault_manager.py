"""Obsidian Vault管理器：目录结构、文件读写、YAML frontmatter"""

import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Any

from max_system.config.settings import MaxSettings

logger = logging.getLogger(__name__)

# Vault标准目录结构
VAULT_FOLDERS = [
    "项目",           # 按项目归档的所有文档
    "客户",           # 客户档案
    "知识库",         # 公司标准、模板、规范
    "日报",           # 每日执行日志
    "素材",           # 案例素材、文案素材
]


class VaultManager:
    """Obsidian Vault管理器

    负责：
    - 初始化Vault目录结构
    - 创建/读取/搜索笔记
    - 管理YAML frontmatter
    - 维护项目知识图谱
    """

    def __init__(self, settings: MaxSettings):
        self.vault_path = settings.obsidian_vault_path
        self._ensure_structure()

    def _ensure_structure(self) -> None:
        """确保Vault目录结构存在"""
        self.vault_path.mkdir(parents=True, exist_ok=True)
        for folder in VAULT_FOLDERS:
            (self.vault_path / folder).mkdir(exist_ok=True)

    def write_note(
        self,
        relative_path: str,
        content: str,
        title: str = "",
        tags: list[str] | None = None,
        links: list[str] | None = None,
        extra_frontmatter: dict[str, Any] | None = None,
    ) -> Path:
        """写入笔记，自动添加YAML frontmatter"""
        filepath = self.vault_path / relative_path
        filepath.parent.mkdir(parents=True, exist_ok=True)

        frontmatter = self._build_frontmatter(
            title=title or filepath.stem,
            tags=tags or [],
            links=links or [],
            extra=extra_frontmatter,
        )

        full_content = f"{frontmatter}\n{content}"
        filepath.write_text(full_content, encoding="utf-8")
        logger.info("写入笔记: %s", relative_path)
        return filepath

    def read_note(self, relative_path: str) -> dict | None:
        """读取笔记，分离frontmatter和正文"""
        filepath = self.vault_path / relative_path
        if not filepath.exists():
            return None

        raw = filepath.read_text(encoding="utf-8")
        frontmatter, body = self._parse_frontmatter(raw)

        return {
            "path": relative_path,
            "frontmatter": frontmatter,
            "body": body,
        }

    def search(self, query: str, search_type: str = "keyword", limit: int = 20) -> list[dict]:
        """搜索Vault笔记"""
        results = []
        query_lower = query.lower()

        for md_file in self.vault_path.rglob("*.md"):
            content = md_file.read_text(encoding="utf-8", errors="ignore")

            if search_type == "tag":
                if not self._match_tag(content, query):
                    continue
            else:
                if query_lower not in content.lower():
                    continue

            frontmatter, body = self._parse_frontmatter(content)
            rel_path = str(md_file.relative_to(self.vault_path))

            # 找到匹配位置，截取上下文片段
            snippet = self._extract_snippet(body, query, context_len=150)

            results.append({
                "path": rel_path,
                "title": frontmatter.get("title", md_file.stem),
                "tags": frontmatter.get("tags", []),
                "snippet": snippet,
            })

            if len(results) >= limit:
                break

        return results

    def create_project_note(
        self,
        project_name: str,
        doc_type: str,
        content: str,
        tags: list[str] | None = None,
    ) -> Path:
        """创建项目归档笔记

        按规范路径: 项目/{项目名}/{文档类型}.md
        """
        safe_name = "".join(c for c in project_name if c.isalnum() or c in " _-")[:50]
        relative_path = f"项目/{safe_name}/{doc_type}.md"

        project_tags = (tags or []) + [f"项目/{safe_name}", doc_type]
        return self.write_note(
            relative_path=relative_path,
            content=content,
            title=f"{safe_name} - {doc_type}",
            tags=project_tags,
            links=[f"[[项目/{safe_name}/项目总览]]"],
        )

    def create_client_note(
        self,
        client_name: str,
        content: str,
        tags: list[str] | None = None,
    ) -> Path:
        """创建客户档案笔记

        路径: 客户/{客户名}.md
        """
        safe_name = "".join(c for c in client_name if c.isalnum() or c in " _-")[:30]
        relative_path = f"客户/{safe_name}.md"

        client_tags = (tags or []) + [f"客户/{safe_name}"]
        return self.write_note(
            relative_path=relative_path,
            content=content,
            title=f"客户档案 - {safe_name}",
            tags=client_tags,
        )

    def _build_frontmatter(
        self,
        title: str,
        tags: list[str],
        links: list[str],
        extra: dict[str, Any] | None = None,
    ) -> str:
        lines = ["---"]
        lines.append(f'title: "{title}"')
        lines.append(f"date: {datetime.now().strftime('%Y-%m-%d')}")
        lines.append(f"created: {datetime.now().isoformat()}")
        lines.append("created_by: max-system")

        if tags:
            lines.append("tags:")
            for tag in tags:
                lines.append(f"  - {tag}")

        if links:
            lines.append("links:")
            for link in links:
                lines.append(f'  - "{link}"')

        if extra:
            for key, value in extra.items():
                if isinstance(value, list):
                    lines.append(f"{key}:")
                    for item in value:
                        lines.append(f"  - {item}")
                elif isinstance(value, str):
                    lines.append(f'{key}: "{value}"')
                else:
                    lines.append(f"{key}: {value}")

        lines.append("---")
        return "\n".join(lines)

    @staticmethod
    def _parse_frontmatter(content: str) -> tuple[dict, str]:
        """解析YAML frontmatter，返回(metadata, body)"""
        if not content.startswith("---"):
            return {}, content

        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
        if not match:
            return {}, content

        yaml_text = match.group(1)
        body = match.group(2)

        # 简易YAML解析（不引入pyyaml依赖）
        metadata: dict[str, Any] = {}
        current_key = None
        current_list: list | None = None

        for line in yaml_text.split("\n"):
            stripped = line.strip()

            if not stripped or stripped.startswith("#"):
                continue

            # 列表项
            if stripped.startswith("- ") and current_key is not None:
                if current_list is None:
                    current_list = []
                    metadata[current_key] = current_list
                current_list.append(stripped[2:].strip('"').strip("'"))
                continue

            # 键值对
            if ":" in stripped and not stripped.startswith(" "):
                # 保存之前的list
                current_list = None

                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip().strip('"').strip("'")

                if value:
                    metadata[key] = value
                else:
                    current_key = key
                    metadata[key] = []

        return metadata, body

    @staticmethod
    def _match_tag(content: str, tag: str) -> bool:
        """检查笔记是否包含指定标签"""
        return f"- {tag}" in content or f"# {tag}" in content

    @staticmethod
    def _extract_snippet(body: str, query: str, context_len: int = 150) -> str:
        """提取匹配关键词附近的文本片段"""
        idx = body.lower().find(query.lower())
        if idx == -1:
            return body[:context_len]

        start = max(0, idx - context_len // 2)
        end = min(len(body), idx + len(query) + context_len // 2)
        snippet = body[start:end].strip()

        if start > 0:
            snippet = "..." + snippet
        if end < len(body):
            snippet = snippet + "..."

        return snippet
