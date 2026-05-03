"""从磁盘加载 system_prompt.md 文件，带内存缓存"""

from pathlib import Path

_cache: dict[str, str] = {}


def load_prompt(path: Path) -> str:
    """加载 prompt 文件，缓存结果避免重复磁盘IO"""
    key = str(path.resolve())
    if key not in _cache:
        if not path.exists():
            raise FileNotFoundError(f"Prompt文件不存在: {path}")
        _cache[key] = path.read_text(encoding="utf-8").strip()
    return _cache[key]


def clear_cache() -> None:
    _cache.clear()
