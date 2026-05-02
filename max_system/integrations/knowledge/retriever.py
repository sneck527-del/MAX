"""知识库检索引擎：语义搜索 + 关键词混合搜索"""

import json
import logging
from typing import Any

from max_system.config.settings import MaxSettings
from max_system.integrations.knowledge.vector_store import VectorStore

logger = logging.getLogger(__name__)


class KnowledgeRetriever:
    """知识库检索引擎

    优先使用ChromaDB向量搜索（语义匹配），
    降级到文件系统关键词搜索（当向量库为空时）。
    """

    COLLECTION_MAIN = "max_knowledge"

    def __init__(self, settings: MaxSettings):
        self.settings = settings
        self.vector_store = VectorStore(settings)
        self._initialized = False

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            try:
                self.vector_store.initialize()
            except Exception as e:
                logger.warning("向量存储初始化失败，将使用关键词搜索: %s", e)
            self._initialized = True

    async def search(
        self,
        query: str,
        category: str = "",
        top_k: int = 5,
    ) -> list[dict]:
        """搜索知识库

        Args:
            query: 搜索查询
            category: 可选类别筛选
            top_k: 返回结果数量

        Returns:
            [{id, document, metadata, distance}]
        """
        self._ensure_initialized()

        # 尝试向量搜索
        try:
            count = self.vector_store.count(self.COLLECTION_MAIN)
            if count > 0:
                where = {"source": category} if category else None
                results = self.vector_store.search(
                    self.COLLECTION_MAIN, query, n_results=top_k, where=where
                )
                if results:
                    return results
        except Exception as e:
            logger.warning("向量搜索失败，降级到关键词搜索: %s", e)

        # 降级到文件系统搜索
        return self._keyword_search(query, category, top_k)

    def _keyword_search(
        self,
        query: str,
        category: str,
        top_k: int,
    ) -> list[dict]:
        """文件系统关键词搜索（降级方案）"""
        kb_path = self.settings.knowledge_base_path
        if not kb_path.exists():
            return []

        query_lower = query.lower()
        results = []

        search_dirs = [kb_path / category] if category and (kb_path / category).exists() else [
            kb_path / "company_standards", kb_path / "case_database",
            kb_path / "material_database", kb_path / "customer_service",
            kb_path / "media_materials",
        ]

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            for f in search_dir.rglob("*"):
                if not f.is_file():
                    continue
                if f.suffix not in (".md", ".json", ".txt"):
                    continue

                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue

                if query_lower in content.lower():
                    idx = content.lower().find(query_lower)
                    snippet = content[max(0, idx - 100):min(len(content), idx + len(query_lower) + 200)]
                    results.append({
                        "id": str(f.relative_to(kb_path)),
                        "document": snippet,
                        "metadata": {
                            "source": search_dir.name,
                            "path": str(f.relative_to(kb_path)),
                        },
                        "distance": 0,
                    })
                    if len(results) >= top_k:
                        break
            if len(results) >= top_k:
                break

        return results
