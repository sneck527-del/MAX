"""ARK Design 桥接模块：MAX 客户数据 → ARK project.json → 子进程调用"""

import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, AsyncIterator

logger = logging.getLogger(__name__)

# ARK 项目路径（相对于 MAX 仓库根目录）
ARK_PROJECT_PATH = Path(__file__).resolve().parent.parent.parent / "ark_design"
ARK_CLI = ARK_PROJECT_PATH / "ark.js"
ARK_CONFIG_PATH = Path.home() / ".arkconfig.json"

# 生产保护参数
ARK_TIMEOUT_SECONDS = 600       # 10 分钟超时
FEISHU_FILE_MAX_BYTES = 20 * 1024 * 1024  # 飞书文件上限 20MB
HTML_SPLIT_THRESHOLD = 15 * 1024 * 1024   # 超过 15MB 自动压缩

# 并发控制：同一时间只允许一个 ARK 子进程运行
_ark_lock = asyncio.Lock()
_ark_running = False

# MAX spaceType 推断映射
# MAX "type" 字段值 → ARK spaceType
MAX_TYPE_TO_SPACE_TYPE = {
    "住宅": "residential",
    "商业": "restaurant",
    "办公": "office",
    "酒店": "hotel",
    "展厅": "exhibition",
    "零售": "retail",
    "餐饮": "restaurant",
    "民宿": "hotel",
    "店铺": "retail",
}


def load_ark_config() -> dict[str, str]:
    """读取 ARK 的 API 配置文件 ~/.arkconfig.json"""
    if ARK_CONFIG_PATH.exists():
        try:
            return json.loads(ARK_CONFIG_PATH.read_text("utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("读取 ARK 配置失败: %s", e)
    return {}


def infer_space_type(client_data: dict) -> str:
    """从客户数据推断 spaceType，默认 residential"""
    max_type = client_data.get("type", "")
    unit = client_data.get("unit_type", "")
    if max_type in MAX_TYPE_TO_SPACE_TYPE:
        return MAX_TYPE_TO_SPACE_TYPE[max_type]
    if "餐厅" in unit or "餐饮" in unit or "饭店" in unit:
        return "restaurant"
    if "酒店" in unit or "民宿" in unit:
        return "hotel"
    if "展厅" in unit or "展览" in unit:
        return "exhibition"
    if "商铺" in unit or "门店" in unit or "零售" in unit:
        return "retail"
    return "residential"


def build_project_json(
    client_data: dict,
    profile: dict | None = None,
) -> dict:
    """将 MAX 客户数据 + 设计师 Profile 转换为 ARK project.json 格式

    Args:
        client_data: MAX 客户记录（来自 clientmgr_query_clients 输出）
        profile: 设计师 Profile（来自 profile_get 输出），可选

    Returns:
        ARK project.json 格式的 dict
    """
    profile = profile or {}

    # 基础字段映射
    project: dict[str, Any] = {
        "name": client_data.get("name") or "未命名项目",
        "spaceType": infer_space_type(client_data),
        "budget": _parse_budget(client_data.get("budget")),
        "city": client_data.get("city", ""),
        "brief": client_data.get("remark", ""),
        "clientTags": [],
        "userHabits": [],
        "fundingPhases": [],
    }

    # 户型信息作为 regionFeatures
    unit_type = client_data.get("unit_type", "")
    if unit_type:
        area_parts = [unit_type]
        project["regionFeatures"] = "、".join(area_parts)
    else:
        project["regionFeatures"] = ""

    # 客户偏好 → clientTags
    prefs = client_data.get("preferences", {})
    if isinstance(prefs, dict):
        for key, value in prefs.items():
            project["clientTags"].append(f"{key}:{value}")
    elif isinstance(prefs, str):
        try:
            prefs_dict = json.loads(prefs)
            if isinstance(prefs_dict, dict):
                for key, value in prefs_dict.items():
                    project["clientTags"].append(f"{key}:{value}")
        except (json.JSONDecodeError, TypeError):
            pass

    # 设计师 Profile 注入到 brief 描述中
    company_name = profile.get("company_name", "")
    design_style = profile.get("design_style", "")
    if company_name:
        brief_prefix = f"由{company_name}设计的"
        if design_style:
            brief_prefix += f"（风格：{design_style}）"
        original_brief = project["brief"]
        project["brief"] = f"{brief_prefix}{original_brief}" if original_brief else f"{brief_prefix}项目"

    # 将 profile 作为 _profile 嵌入，供 Phase 2 使用
    project["_profile"] = profile

    return project


def _parse_budget(budget_val) -> int:
    """解析预算值为整数（元）"""
    if budget_val is None:
        return 0
    if isinstance(budget_val, (int, float)):
        return int(budget_val)
    budget_str = str(budget_val).strip()
    if not budget_str:
        return 0
    budget_str = budget_str.replace(",", "").replace("，", "")
    if "万" in budget_str:
        try:
            return int(float(budget_str.replace("万", "")) * 10000)
        except (ValueError, TypeError):
            pass
    if "k" in budget_str.lower():
        try:
            return int(float(budget_str.lower().replace("k", "")) * 1000)
        except (ValueError, TypeError):
            pass
    try:
        return int(float(budget_str))
    except (ValueError, TypeError):
        return 0


async def run_ark(
    project_data: dict,
    output_dir: str | None = None,
    theme: str | None = None,
) -> AsyncIterator[str]:
    """运行 ARK Design 子进程，实时产出进度行

    Args:
        project_data: ARK project.json 格式的 dict
        output_dir: 输出目录（None 则用临时目录）
        theme: PPT 主题名（可选）

    Yields:
        进度字符串，每行一个
    """
    # 检查 node 是否可用
    import shutil
    node_path = shutil.which("node")
    if not node_path:
        logger.warning("node 不可用，跳过 ARK 调用")
        yield "[ERROR] Node.js 未安装或不在 PATH 中"
        return

    # 构建 CLI 参数
    project_dir = output_dir or tempfile.mkdtemp(prefix="ark_project_")
    os.makedirs(project_dir, exist_ok=True)

    # 先写 project.json
    try:
        project_json_path = Path(project_dir) / "project.json"
        project_json_path.write_text(
            json.dumps(project_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as e:
        logger.error("写入 project.json 失败: %s", e)
        yield f"[ERROR] 无法写入 project.json: {e}"
        return

    # 构建命令行参数
    name = project_data.get("name", "未命名")
    space_type = project_data.get("spaceType", "residential")
    budget = project_data.get("budget", 0)
    city = project_data.get("city", "")
    brief = project_data.get("brief", "")
    area = project_data.get("area", 0)
    tags = project_data.get("clientTags", [])
    habits = project_data.get("userHabits", [])

    cmd = [
        str(node_path),
        str(ARK_CLI),
        "all",
        "--name", name,
        "--type", space_type,
        "--budget", str(budget),
        "--output", str(project_dir),
    ]
    if city:
        cmd.extend(["--city", city])
    if brief:
        cmd.extend(["--brief", brief])
    if area and area > 0:
        cmd.extend(["--area", str(area)])
    if tags:
        cmd.extend(["--tags", ",".join(str(t) for t in tags)])
    if habits:
        cmd.extend(["--habits", ",".join(str(h) for h in habits)])
    if theme:
        cmd.extend(["--theme", theme])
    if project_data.get("_profile"):
        cmd.extend(["--profile", str(project_json_path)])

    yield f"[CMD] node ark.js all --name '{name}' --type {space_type}"

    # 启动子进程
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(ARK_PROJECT_PATH),
        )
    except OSError as e:
        logger.error("启动 ARK 子进程失败: %s", e)
        yield f"[ERROR] 无法启动 ARK: {e}"
        return

    # 实时读取输出
    assert proc.stdout is not None
    line_count = 0
    try:
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            decoded = line.decode("utf-8", errors="replace").rstrip()
            if decoded:
                yield decoded
                line_count += 1
    except Exception as e:
        logger.error("读取 ARK 输出时出错: %s", e)
        yield f"[ERROR] 读取输出失败: {e}"

    await proc.wait()

    if proc.returncode != 0:
        yield f"[ERROR] ARK 进程退出码: {proc.returncode}"
    else:
        yield f"[DONE] ARK 完成，输出目录: {project_dir}"
        yield f"[RESULT_DIR] {project_dir}"


def collect_ark_results(project_dir: str) -> dict:
    """收集 ARK 输出的文件内容

    Returns:
        {
            "proposal_html": str | None,
            "speech_md": str | None,
            "debate_log": str | None,
            "result_json": dict | None,
            "project_dir": str,
        }
    """
    p = Path(project_dir)
    results: dict[str, Any] = {
        "proposal_html": None,
        "speech_md": None,
        "debate_log": None,
        "result_json": None,
        "project_dir": str(p),
    }

    for filename, key in [
        ("proposal.html", "proposal_html"),
        ("speech.md", "speech_md"),
        ("debate.log", "debate_log"),
    ]:
        filepath = p / filename
        if filepath.exists():
            try:
                results[key] = filepath.read_text("utf-8")
            except (OSError, UnicodeDecodeError) as e:
                logger.warning("读取 %s 失败: %s", filename, e)

    result_path = p / "result.json"
    if result_path.exists():
        try:
            results["result_json"] = json.loads(result_path.read_text("utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("读取 result.json 失败: %s", e)

    return results
