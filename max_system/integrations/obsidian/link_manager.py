"""Obsidian双向链接和标签管理器"""

import re
import logging
from pathlib import Path
from typing import Any

from max_system.config.settings import MaxSettings

logger = logging.getLogger(__name__)


class LinkManager:
    """双向链接和标签管理

    负责：
    - 自动插入 [[双向链接]]
    - 维护链接关系（谁引用了谁）
    - 标签去重和规范化
    - 反向链接查询
    """

    def __init__(self, settings: MaxSettings):
        self.vault_path = settings.obsidian_vault_path

    def insert_links(self, content: str, link_targets: list[str]) -> str:
        """在内容中自动插入双向链接

        将提到的项目名、客户名、文档等自动转为 [[链接]]
        """
        for target in link_targets:
            # 避免重复链接（已经是 [[...]] 格式的不处理）
            pattern = re.compile(
                rf'(?<!\[\[)({re.escape(target)})(?!\]\])',
                re.IGNORECASE
            )
            # 只替换第一次出现（避免全文都是链接）
            content = pattern.sub(f'[[{target}]]', content, count=1)

        return content

    def find_backlinks(self, note_path: str) -> list[dict]:
        """查找所有引用了指定笔记的其他笔记（反向链接）"""
        note_name = Path(note_path).stem
        backlinks = []

        for md_file in self.vault_path.rglob("*.md"):
            if md_file.name == Path(note_path).name:
                continue

            content = md_file.read_text(encoding="utf-8", errors="ignore")
            # 查找 [[note_name]] 或 [[path/note_name]]
            link_pattern = rf'\[\[.*{re.escape(note_name)}.*\]\]'
            if re.search(link_pattern, content):
                backlinks.append({
                    "path": str(md_file.relative_to(self.vault_path)),
                    "title": md_file.stem,
                })

        return backlinks

    def normalize_tags(self, tags: list[str]) -> list[str]:
        """标签规范化：去重、去空、统一格式"""
        seen = set()
        result = []
        for tag in tags:
            tag = tag.strip().strip("#")
            if not tag:
                continue
            if tag.lower() not in seen:
                seen.add(tag.lower())
                result.append(tag)
        return result

    def extract_tags_from_content(self, content: str) -> list[str]:
        """从内容中提取所有 #标签"""
        # 匹配行内标签（排除标题的#）
        tags = re.findall(r'(?:^|\s)#([一-鿿\w/]+)', content)
        return list(set(tags))

    def build_link_map(self) -> dict[str, list[str]]:
        """构建全Vault的链接图谱

        Returns:
            {笔记名: [它引用的所有笔记名]}
        """
        link_map: dict[str, list[str]] = {}

        for md_file in self.vault_path.rglob("*.md"):
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            note_name = md_file.stem

            # 提取所有 [[链接]]
            links = re.findall(r'\[\[([^\]|]+?)(?:\|.*)?\]\]', content)
            link_map[note_name] = links

        return link_map
