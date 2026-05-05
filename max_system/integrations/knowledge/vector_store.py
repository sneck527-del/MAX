"""基于ChromaDB的向量存储，提供语义搜索能力。"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# 尝试导入chromadb，如果不可用则优雅降级
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    _CHROMADB_AVAILABLE = True
except ImportError:
    _CHROMADB_AVAILABLE = False
    chromadb = None  # type: ignore
    ChromaSettings = None  # type: ignore


class VectorStore:
    """基于ChromaDB的轻量级向量存储，用于知识库语义搜索。

    如果chromadb未安装，所有操作均为空操作（no-op），
    并记录警告日志。
    """

    def __init__(self, persist_dir: Path):
        self._persist_dir = persist_dir
        self._client = None
        self._collection = None
        self._available = _CHROMADB_AVAILABLE

    def initialize(self):
        """初始化PersistentClient并获取或创建collection。"""
        if not self._available:
            logger.warning("chromadb未安装，VectorStore不可用。语义搜索将降级为关键词搜索。")
            return

        try:
            self._persist_dir.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=str(self._persist_dir),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name="knowledge_base",
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("VectorStore initialized at %s", self._persist_dir)
        except Exception as e:
            logger.warning("VectorStore初始化失败: %s，语义搜索将不可用", e)
            self._available = False
            self._client = None
            self._collection = None

    def add_documents(self, documents: list[dict]):
        """批量添加文档到向量存储。

        每个文档dict需包含:
            - id: 唯一标识符
            - content: 文档文本内容
            - metadata: 元数据字典（可选，用于过滤）
        """
        if not self._available or self._collection is None:
            logger.warning("VectorStore不可用，跳过add_documents")
            return

        if not documents:
            return

        ids = []
        contents = []
        metadatas = []

        for doc in documents:
            doc_id = str(doc.get("id", ""))
            content = str(doc.get("content", ""))
            metadata = doc.get("metadata", {}) or {}

            if not doc_id or not content:
                continue

            # Chromadb要求metadata值均为基本类型（str/int/float/bool）
            clean_metadata = {}
            for k, v in metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_metadata[k] = v
                else:
                    clean_metadata[k] = str(v)

            ids.append(doc_id)
            contents.append(content)
            metadatas.append(clean_metadata)

        if not ids:
            return

        try:
            self._collection.add(
                ids=ids,
                documents=contents,
                metadatas=metadatas,
            )
            logger.info("VectorStore: 添加 %d 篇文档", len(ids))
        except Exception as e:
            logger.warning("VectorStore添加文档失败: %s", e)

    def search(self, query: str, top_k: int = 5, category: str = "") -> list[dict]:
        """语义搜索。

        Args:
            query: 搜索查询
            top_k: 返回结果数量
            category: 可选，按metadata中的category字段过滤

        Returns:
            list[dict]: 每个结果包含 id, content, metadata, distance
        """
        if not self._available or self._collection is None:
            logger.warning("VectorStore不可用，返回空搜索结果")
            return []

        try:
            where_filter = None
            if category:
                where_filter = {"category": category}

            results = self._collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where_filter,
            )

            output = []
            if results and results.get("ids") and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    entry = {
                        "id": doc_id,
                        "content": results["documents"][0][i] if results.get("documents") else "",
                        "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                        "distance": results["distances"][0][i] if results.get("distances") else None,
                    }
                    output.append(entry)

            return output
        except Exception as e:
            logger.warning("VectorStore搜索失败: %s", e)
            return []

    def delete(self, doc_id: str):
        """删除指定文档。"""
        if not self._available or self._collection is None:
            return
        try:
            self._collection.delete(ids=[doc_id])
        except Exception as e:
            logger.warning("VectorStore删除文档失败: %s", e)

    def count(self) -> int:
        """返回已索引的文档数量。"""
        if not self._available or self._collection is None:
            return 0
        try:
            return self._collection.count()
        except Exception as e:
            logger.warning("VectorStore获取文档数失败: %s", e)
            return 0

    def close(self):
        """持久化并关闭（PersistentClient会自动持久化，此处为显式接口）。"""
        self._client = None
        self._collection = None
        logger.info("VectorStore closed")
