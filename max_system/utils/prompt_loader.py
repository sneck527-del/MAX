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


def build_skill_appendix(prompts_root: Path, agent_dir: str, skill_dirs: list[str]) -> str:
    """构建技能描述附录，追加到Agent主prompt后面"""
    parts = []
    for skill_dir in skill_dirs:
        prompt_path = prompts_root / agent_dir / skill_dir / "config" / "system_prompt.md"
        if prompt_path.exists():
            skill_name = skill_dir.replace("skill_0X_", "").replace("skill_0", "")
            content = load_prompt(prompt_path)
            parts.append(f"## 技能: {skill_dir}\n{content}")
    return "\n\n---\n\n".join(parts) if parts else ""
