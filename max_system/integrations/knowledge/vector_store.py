"""ChromaDB向量存储管理"""

import logging
from pathlib import Path
from typing import Any

from max_system.config.settings import MaxSettings

logger = logging.getLogger(__name__)


class VectorStore:
    """ChromaDB向量存储管理

    使用本地ChromaDB存储文档向量，支持语义搜索。
    """

    def __init__(self, settings: MaxSettings):
        self.settings = settings
        self._client = None
        self._collections: dict[str, Any] = {}

    def initialize(self) -> None:
        """初始化ChromaDB客户端"""
        import chromadb

        persist_dir = str(self.settings.vector_store_path)
        self.settings.vector_store_path.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(path=persist_dir)
        logger.info("ChromaDB初始化完成: %s", persist_dir)

    def get_collection(self, name: str) -> Any:
        """获取或创建集合"""
        if self._client is None:
            self.initialize()

        if name not in self._collections:
            self._collections[name] = self._client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[name]

    def add_documents(
        self,
        collection_name: str,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict] | None = None,
    ) -> int:
        """添加文档到集合"""
        collection = self.get_collection(collection_name)

        # 分批添加，每批最多100条
        batch_size = 100
        added = 0
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_docs = documents[i:i + batch_size]
            batch_meta = metadatas[i:i + batch_size] if metadatas else None

            collection.upsert(
                ids=batch_ids,
                documents=batch_docs,
                metadatas=batch_meta,
            )
            added += len(batch_ids)

        logger.info("向 %s 添加了 %d 条文档", collection_name, added)
        return added

    def search(
        self,
        collection_name: str,
        query: str,
        n_results: int = 5,
        where: dict | None = None,
    ) -> list[dict]:
        """语义搜索"""
        collection = self.get_collection(collection_name)

        # 如果集合为空，返回空结果
        if collection.count() == 0:
            return []

        kwargs = {"query_texts": [query], "n_results": n_results}
        if where:
            kwargs["where"] = where

        results = collection.query(**kwargs)

        items = []
        for i in range(len(results["ids"][0])):
            item = {
                "id": results["ids"][0][i],
                "document": results["documents"][0][i] if results["documents"] else "",
                "distance": results["distances"][0][i] if results["distances"] else 0,
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
            }
            items.append(item)

        return items

    def count(self, collection_name: str) -> int:
        """获取集合中文档数量"""
        collection = self.get_collection(collection_name)
        return collection.count()

    def list_collections(self) -> list[str]:
        """列出所有集合"""
        if self._client is None:
            self.initialize()
        return [c.name for c in self._client.list_collections()]

    def reset_collection(self, collection_name: str) -> None:
        """重置集合（删除后重建）"""
        if self._client is None:
            self.initialize()
        try:
            self._client.delete_collection(collection_name)
        except Exception:
            pass
        self._collections.pop(collection_name, None)
        logger.info("集合 %s 已重置", collection_name)
