"""字段名映射缓存：field_id → field_name 带TTL缓存"""

import time
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class FieldMappingCache:
    """field_id → field_name 映射缓存，按 table_id 隔离，带 TTL"""

    def __init__(self, ttl_seconds: int = 300):
        self._cache: Dict[str, Dict[str, str]] = {}  # table_id -> {field_id: field_name}
        self._timestamps: Dict[str, float] = {}       # table_id -> last_fetch_time
        self._ttl = ttl_seconds

    def get(self, table_id: str) -> Optional[Dict[str, str]]:
        """返回缓存的映射，过期或不存在返回 None"""
        ts = self._timestamps.get(table_id)
        if ts is None or (time.time() - ts) > self._ttl:
            return None
        return self._cache.get(table_id)

    def set(self, table_id: str, mapping: Dict[str, str]) -> None:
        """写入缓存"""
        self._cache[table_id] = mapping
        self._timestamps[table_id] = time.time()

    def invalidate(self, table_id: str) -> None:
        """使某个表的缓存失效"""
        self._cache.pop(table_id, None)
        self._timestamps.pop(table_id, None)

    def clear(self) -> None:
        """清空全部缓存"""
        self._cache.clear()
        self._timestamps.clear()
