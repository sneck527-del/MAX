"""ARK Design 桥接 MCP 工具：AI 概念设计提案生成

通过调用 ARK Design 子进程（Node.js），自动完成：
1. 客户数据 →  project.json 映射
2. 4 Agent 设计辩论
3. PPT HTML 生成
4. 飞书文件上传发送
"""

import asyncio
import json
import logging
import os
from pathlib import Path

from max_system.config.settings import MaxSettings
from max_system.integrations.ark_bridge import (
    build_project_json,
    collect_ark_results,
    run_ark,
)
from max_system.integrations.pptx_generator import generate_pptx
from max_system.tools.clientmgr_tools import (
    _ensure_api_client,
    _get_clients_db,
    _load_from_bitable,
)

logger = logging.getLogger(__name__)

TOOL_DEFS = [
    {
        "name": "ark_generate_proposal",
        "description": (
            "为客户生成AI概念设计提案（30页PPT）。调用ARK Design多Agent设计辩论引擎，"
            "4个AI角色（审美专家、硬核执行官、精算专家、虚拟客户）辩论后由叙事架构师总结，"
            "生成proposal.html。需要提供客户姓名或编号。整个过程需要3-5分钟，完成后自动发送HTML文件到飞书聊天。"
            "仅当设计师明确要求「生成提案」「做概念设计」「出PPT提案」时才使用。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "chat_id": {
                    "type": "string",
                    "description": "当前飞书聊天ID，用于发送进度和结果文件",
                },
                "client_name": {
                    "type": "string",
                    "description": "客户姓名（与client_id二选一）",
                },
                "client_id": {
                    "type": "string",
                    "description": "客户编号（与client_name二选一）",
                },
                "space_type": {
                    "type": "string",
                    "enum": ["residential", "restaurant", "hotel", "exhibition", "retail"],
                    "description": "项目类型（可选，默认自动从客户数据推断）",
                },
            },
            "required": ["chat_id"],
        },
    },
]


async def ark_generate_proposal(args: dict) -> dict:
    """为客户生成 AI 概念设计提案。

    启动 ARK Design 子进程在后台运行，通过飞书发送进度和结果。
    """
    chat_id = args.get("chat_id", "")
    client_name = args.get("client_name", "")
    client_id = args.get("client_id", "")

    # 加载客户数据
    await _load_from_bitable()
    db = _get_clients_db()

    client_data = None
    if client_id and client_id in db:
        client_data = db[client_id]
    elif client_name:
        for c in db.values():
            if c.get("name", "").lower() == client_name.lower():
                client_data = c
                client_id = c.get("client_id", "")
                break

    if client_data is None:
        identifier = client_id or client_name or "(未指定)"
        return {
            "content": [{
                "type": "text",
                "text": f"未找到客户: {identifier}。请先用 clientmgr_query_clients 确认客户姓名或编号。",
            }],
        }

    # 加载设计师 Profile
    profile = {}
    try:
        from max_system.tools.profile_tools import _get_active_profile_mgr
        mgr = _get_active_profile_mgr()
        if mgr is not None:
            profile = await mgr.get_all()
    except Exception as e:
        logger.warning("读取 Profile 失败，使用空配置: %s", e)

    # 构建 project.json
    space_type_override = args.get("space_type", "")
    project_data = build_project_json(client_data, profile)
    if space_type_override:
        project_data["spaceType"] = space_type_override

    client_display = client_data.get("name", client_id)

    # 检查 node 是否可用
    import shutil
    if not shutil.which("node"):
        return {
            "content": [{
                "type": "text",
                "text": "Node.js 未安装或不在系统 PATH 中，无法运行 ARK Design 引擎。请安装 Node.js 后再试。",
            }],
        }

    # 启动后台任务运行 ARK
    asyncio.create_task(
        _run_ark_background(
            chat_id=chat_id,
            project_data=project_data,
            client_display=client_display,
        )
    )

    space_label = {"residential": "私宅", "restaurant": "餐饮", "hotel": "酒店民宿",
                   "exhibition": "展厅", "retail": "服务门店"}.get(
        project_data.get("spaceType", "residential"), "项目")

    return {
        "content": [{
            "type": "text",
            "text": (
                f"已启动「{client_display}」的概念设计提案生成。\n"
                f"项目类型：{space_label}，预算：{project_data.get('budget', 0):,}元\n"
                f"ARK Design 4 Agent 辩论引擎已启动，预计3-5分钟完成，"
                f"完成后会自动发送 proposal.html 到当前聊天。"
            ),
        }],
    }


async def _run_ark_background(
    chat_id: str,
    project_data: dict,
    client_display: str,
) -> None:
    """后台运行 ARK 并发送飞书进度消息（带超时、并发、文件大小保护）"""
    from max_system.tools.feishu_tools import _get_api_client
    from max_system.integrations.ark_bridge import (
        _ark_lock,
        _ark_running,
        ARK_TIMEOUT_SECONDS,
        FEISHU_FILE_MAX_BYTES,
    )

    try:
        client = _get_api_client()
    except RuntimeError as e:
        logger.error("无法获取飞书API客户端: %s", e)
        return

    # ── 并发控制 ──────────────────────────────────
    if _ark_running:
        await client.send_message(
            chat_id,
            "当前有一个提案正在生成中，请等待上一个完成后再试。",
        )
        return

    async with _ark_lock:
        _ark_running = True
        try:
            await _do_run_ark(
                client, chat_id, project_data, client_display,
            )
        finally:
            _ark_running = False


async def _do_run_ark(
    client,
    chat_id: str,
    project_data: dict,
    client_display: str,
) -> None:
    """实际执行 ARK 流程（在锁保护下运行）"""
    from max_system.integrations.ark_bridge import (
        ARK_TIMEOUT_SECONDS,
        FEISHU_FILE_MAX_BYTES,
    )

    # ── 发送初始进度卡片 ──────────────────────────
    await _send_progress_card(client, chat_id, client_display, 0, "启动中")

    output_dir = None
    line_buffer = []
    current_phase = 0
    phase_names = ["审美专家", "硬核执行官", "精算专家", "虚拟客户", "叙事架构师"]
    start_time = asyncio.get_event_loop().time()

    try:
        run_iter = run_ark(project_data)
        while True:
            try:
                line = await asyncio.wait_for(
                    run_iter.__anext__(), timeout=ARK_TIMEOUT_SECONDS
                )
            except asyncio.TimeoutError:
                logger.error("ARK 超时 (>%ds)", ARK_TIMEOUT_SECONDS)
                await client.send_message(
                    chat_id,
                    f"提案生成超时，已终止。请简化项目信息后重试。",
                )
                return
            except StopAsyncIteration:
                break

            line_buffer.append(line)

            # 检测阶段切换
            for i, name in enumerate(phase_names):
                if name in line and current_phase <= i:
                    current_phase = i + 1
                    elapsed = int(asyncio.get_event_loop().time() - start_time)
                    await _send_progress_card(
                        client, chat_id, client_display,
                        current_phase, phase_names[i], elapsed,
                    )
                    break

            if line.startswith("[ERROR]"):
                await client.send_message(
                    chat_id,
                    f"ARK 错误: {line.replace('[ERROR] ', '')}",
                )

            if line.startswith("[DONE]"):
                for l in line_buffer:
                    if l.startswith("[RESULT_DIR]"):
                        output_dir = l.split("] ", 1)[1].strip()
                line_buffer = []
                break
    except Exception as e:
        logger.error("ARK 运行异常: %s", e)
        await client.send_message(chat_id, f"提案生成失败: {e}")
        return

    # 收集结果
    if not output_dir:
        await client.send_message(chat_id, "ARK 未返回输出目录，生成可能失败")
        return

    results = collect_ark_results(output_dir)

    # ── 上传 HTML ─────────────────────────────────
    if not results.get("proposal_html"):
        await client.send_message(
            chat_id,
            f"提案生成完成但未找到 proposal.html。\n"
            f"输出目录: {output_dir}\n"
            f"请检查 ARK Design 是否正确安装和配置。",
        )
        return

    html_path = Path(output_dir) / "proposal.html"
    html_size = html_path.stat().st_size if html_path.exists() else 0

    if html_size > FEISHU_FILE_MAX_BYTES:
        await client.send_message(
            chat_id,
            f"提案 HTML 文件过大（{html_size / 1024 / 1024:.1f}MB），"
            f"超过飞书文件大小限制（{FEISHU_FILE_MAX_BYTES // 1024 // 1024}MB）。"
            f"\n请缩减提案页数后重试。\n文件: {html_path}",
        )
        return

    try:
        file_key = await client.upload_file(str(html_path), file_type="stream")
        if file_key:
            await client.send_message(
                chat_id,
                json.dumps({"file_key": file_key}),
                msg_type="file",
            )
            await client.send_message(
                chat_id,
                f"「{client_display}」的概念设计提案已生成，请查收上方 HTML 文件。",
            )
        else:
            await client.send_message(
                chat_id,
                f"提案 HTML 已生成（{html_path}），但上传飞书失败，请检查文件大小和权限。",
            )
            return
    except Exception as e:
        logger.error("上传提案文件失败: %s", e)
        await client.send_message(
            chat_id,
            f"提案已生成（{html_path}），但上传飞书失败: {e}",
        )
        return

    # ── 生成并上传 PPTX ───────────────────────────
    result_json = results.get("result_json", {})
    pages = result_json.get("pages", []) if result_json else []
    if not pages:
        return

    try:
        company_name = project_data.get("_profile", {}).get(
            "company_name", "ARK Design"
        )
        pptx_path = Path(output_dir) / "proposal.pptx"
        generate_pptx(
            pages=pages,
            project_name=project_data.get("name", ""),
            space_type=project_data.get("spaceType", "residential"),
            company_name=company_name,
            output_path=pptx_path,
        )
        pptx_file_key = await client.upload_file(
            str(pptx_path), file_type="stream"
        )
        if pptx_file_key:
            await client.send_message(
                chat_id,
                json.dumps({"file_key": pptx_file_key}),
                msg_type="file",
            )
            await client.send_message(
                chat_id,
                f"同时生成了可编辑的 PPTX 文件（{len(pages)}页），请查收。",
            )
    except Exception as e:
        logger.warning("PPTX 生成/上传失败: %s", e)

    # ── 记录提案历史 ──────────────────────────────
    try:
        _log_proposal_history(
            client_name=client_display,
            project_name=project_data.get("name", ""),
            space_type=project_data.get("spaceType", "residential"),
            pages_count=len(pages) if pages else 0,
            output_dir=output_dir,
        )
    except Exception as e:
        logger.warning("记录提案历史失败: %s", e)


# ════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════


async def _send_progress_card(
    client,
    chat_id: str,
    client_name: str,
    phase: int,
    phase_name: str,
    elapsed: int = 0,
) -> None:
    """发送飞书卡片显示生成进度"""
    phases = ["审美专家", "硬核执行官", "精算专家", "虚拟客户", "叙事架构师"]
    lines = []
    for i, name in enumerate(phases):
        if i < phase:
            lines.append(f"✅ {name} - 已完成")
        elif i == phase:
            elapsed_str = f" ({elapsed}s)" if elapsed else ""
            lines.append(f"🔄 {name} - 运行中{elapsed_str}")
        else:
            lines.append(f"⏳ {name} - 等待中")

    # 构建简单卡片
    card = {
        "header": {
            "title": {"tag": "plain_text", "content": f"AI 概念设计提案"},
            "template": "blue",
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**客户：**{client_name}\n**阶段：**{phase}/5\n\n" + "\n".join(lines),
                },
            },
        ],
    }
    try:
        await client.send_message(
            chat_id,
            json.dumps(card),
            msg_type="interactive",
        )
    except Exception:
        # 卡片发送失败时回退到纯文本
        await client.send_message(
            chat_id,
            f"[{phase}/5] {phase_name} — 「{client_name}」",
        )


PROPOSAL_HISTORY_PATH = Path("data/proposal_history.json")


def _log_proposal_history(
    client_name: str,
    project_name: str,
    space_type: str,
    pages_count: int,
    output_dir: str,
) -> None:
    """记录提案生成历史到本地 JSON 文件"""
    import datetime

    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "client_name": client_name,
        "project_name": project_name,
        "space_type": space_type,
        "pages_count": pages_count,
        "output_dir": output_dir,
    }

    history = []
    if PROPOSAL_HISTORY_PATH.exists():
        try:
            history = json.loads(PROPOSAL_HISTORY_PATH.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    history.append(entry)

    # 保留最近 50 条
    if len(history) > 50:
        history = history[-50:]

    PROPOSAL_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROPOSAL_HISTORY_PATH.write_text(
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def register_tools(settings: MaxSettings) -> list[tuple[str, callable, dict]]:
    handlers = {
        "ark_generate_proposal": ark_generate_proposal,
    }
    return [(d["name"], handlers[d["name"]], d) for d in TOOL_DEFS]
