"""知识库索引器：将文档索引到ChromaDB"""

import hashlib
import logging
from datetime import datetime

from max_system.config.settings import MaxSettings
from max_system.integrations.knowledge.vector_store import VectorStore
from max_system.integrations.knowledge.data_loader import load_all_sources

logger = logging.getLogger(__name__)


class KnowledgeIndexer:
    """知识库索引器

    扫描所有知识来源，将文档向量化存入ChromaDB。
    支持增量索引（只处理新增/变更的文档）。
    """

    # ChromaDB集合名称
    COLLECTION_MAIN = "max_knowledge"

    def __init__(self, settings: MaxSettings):
        self.settings = settings
        self.vector_store = VectorStore(settings)

    def index_all(self, force: bool = False) -> dict:
        """索引所有知识来源

        Args:
            force: 是否强制重新索引（忽略增量检测）

        Returns:
            索引统计 {"indexed": N, "skipped": N, "errors": N}
        """
        self.vector_store.initialize()

        if force:
            self.vector_store.reset_collection(self.COLLECTION_MAIN)

        stats = {"indexed": 0, "skipped": 0, "errors": 0}

        # 获取已有文档ID
        existing_ids = set()
        collection = self.vector_store.get_collection(self.COLLECTION_MAIN)
        if collection.count() > 0 and not force:
            all_ids = collection.get()["ids"]
            existing_ids = set(all_ids)

        # 加载并索引
        ids, documents, metadatas = [], [], []

        for doc_id, content, metadata in load_all_sources(self.settings):
            # 用内容hash检测变更
            content_hash = hashlib.md5(content.encode()).hexdigest()[:12]
            full_id = f"{doc_id}_{content_hash}"

            if not force and doc_id in existing_ids:
                stats["skipped"] += 1
                continue

            ids.append(full_id)
            documents.append(content[:8000])  # 限制单文档长度
            metadata["indexed_at"] = datetime.now().isoformat()
            metadata["base_id"] = doc_id
            metadatas.append(metadata)
            stats["indexed"] += 1

        if ids:
            self.vector_store.add_documents(
                collection_name=self.COLLECTION_MAIN,
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )

        logger.info(
            "知识库索引完成: 新增 %d, 跳过 %d, 错误 %d",
            stats["indexed"], stats["skipped"], stats["errors"],
        )
        return stats

    def get_stats(self) -> dict:
        """获取索引统计信息"""
        self.vector_store.initialize()
        collections = self.vector_store.list_collections()

        stats = {}
        for name in collections:
            count = self.vector_store.count(name)
            stats[name] = {"document_count": count}

        return stats
