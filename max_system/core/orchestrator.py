"""Max编排器：单Agent + 多工具

Max作为唯一的AI入口，通过function calling直接调用所有工具。
没有子Agent、没有dispatch，一次LLM调用链搞定。
"""

import contextvars
import json
import logging
from typing import AsyncIterator

from max_system.config.settings import MaxSettings
from max_system.config.workspace import Workspace, WorkspaceManager
from max_system.core.llm_client import LLMClient
from max_system.utils.prompt_loader import load_prompt
from max_system.audit import logger as audit_logger

logger = logging.getLogger(__name__)

# Context variable for the current workspace during a dispatch cycle.
# Tools read this to determine which workspace DB / data to operate on.
_current_workspace: contextvars.ContextVar = contextvars.ContextVar(
    "workspace", default=None
)


class MaxOrchestrator:
    """Max编排器：单Agent直接调工具，扁平架构"""

    def __init__(self, settings: MaxSettings):
        self.settings = settings
        self.llm = LLMClient(settings)
        self.max_prompt = ""
        self._initialized = False

        # 工具注册表：name -> callable
        self._tools: dict[str, callable] = {}
        self._tool_defs: list[dict] = []

        # Profile管理器 (global fallback for CLI mode)
        self.profile_manager = None

        # Workspace manager (multi-tenant isolation)
        self.workspace_manager = WorkspaceManager(
            settings.get_project_root() / "data" / "workspaces"
        )

    async def initialize(self) -> None:
        """初始化编排器"""
        if self._initialized:
            return

        # 加载Max主prompt
        self.max_prompt = load_prompt(
            self.settings.get_prompts_root() / "config" / "system_prompt.md"
        )

        # 注册所有工具
        self._register_all_tools()

        # 初始化Profile管理器 (global fallback)
        from max_system.config.profile import ProfileManager
        from max_system.tools.profile_tools import set_profile_manager
        self.profile_manager = ProfileManager(self.settings.get_db_path())
        await self.profile_manager.initialize()
        set_profile_manager(self.profile_manager)

        # 初始化Workspace管理器
        await self.workspace_manager.initialize()

        self._initialized = True
        logger.info(
            "Max初始化完成: provider=%s, model=%s, tools=%d",
            self.llm.provider_name, self.llm.model, len(self._tools),
        )

    async def close(self) -> None:
        """关闭编排器，释放资源"""
        if self.profile_manager:
            await self.profile_manager.close()
        await self.workspace_manager.close()

    def _register_all_tools(self) -> None:
        """注册所有工具"""
        from max_system.config.agent_registry import register_all_tools
        for tool_name, tool_func, tool_def in register_all_tools(self.settings):
            self._tools[tool_name] = tool_func
            self._tool_defs.append(tool_def)

    async def dispatch(
        self,
        message: str,
        session_id: str = "cli",
        user_id: str = "designer",
        history: list[dict] | None = None,
    ) -> str:
        """处理用户消息，返回Max响应"""
        if not self._initialized:
            await self.initialize()

        # Set up workspace context if session_id is a non-default chat_id
        workspace: Workspace | None = None
        if session_id and session_id != "cli":
            workspace = await self.workspace_manager.get_workspace(session_id)
            _current_workspace.set(workspace)
            # Wire workspace profile into profile_tools
            from max_system.tools.profile_tools import set_profile_manager
            if workspace.profile:
                set_profile_manager(workspace.profile)

        try:
            # 首次使用引导：profile为空时注入引导指令
            profile_mgr = workspace.profile if workspace and workspace.profile else self.profile_manager
            is_first_run = False
            if profile_mgr:
                is_first_run = await profile_mgr.is_empty()

            system_prompt = await self._build_max_system_prompt(workspace)
            if is_first_run:
                system_prompt += (

                    "\n\n---\n"
                    "## 首次使用引导\n"
                    "这是一位新设计师。系统已经发送了飞书交互式卡片来收集公司信息"
                    "（公司名、设计风格、城市、客户群、品牌调性等）。"
                    "你只需要简单打招呼，介绍自己是谁、能做什么，然后提示设计师"
                    "查看并填写卡片即可。不要重复询问卡片上已有的问题。"
                )

            messages = [{"role": "system", "content": system_prompt}]
            if history:
                messages.extend(history)
            messages.append({"role": "user", "content": message})

            max_tools = LLMClient.build_tool_definitions(self._tool_defs)
            response = await self.llm.chat(messages, tools=max_tools)

            return await self._process_response(response, messages, session_id, user_id)
        finally:
            # Restore global profile_manager on exit (backward compat)
            if workspace:
                from max_system.tools.profile_tools import set_profile_manager
                set_profile_manager(self.profile_manager)

    async def dispatch_stream(
        self,
        message: str,
        session_id: str = "cli",
        user_id: str = "designer",
        history: list[dict] | None = None,
    ) -> AsyncIterator:
        """流式处理用户消息"""
        if not self._initialized:
            await self.initialize()

        # Set up workspace context
        workspace: Workspace | None = None
        if session_id and session_id != "cli":
            workspace = await self.workspace_manager.get_workspace(session_id)
            _current_workspace.set(workspace)
            from max_system.tools.profile_tools import set_profile_manager
            if workspace.profile:
                set_profile_manager(workspace.profile)

        try:
            messages = [{"role": "system", "content": await self._build_max_system_prompt(workspace)}]
            if history:
                messages.extend(history)
            messages.append({"role": "user", "content": message})

            max_tools = LLMClient.build_tool_definitions(self._tool_defs)

            async for chunk in self.llm.chat_stream(messages, tools=max_tools):
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue
                if delta.content:
                    yield {"type": "text", "content": delta.content}
        finally:
            if workspace:
                from max_system.tools.profile_tools import set_profile_manager
                set_profile_manager(self.profile_manager)

    async def _process_response(
        self,
        response,
        messages: list[dict],
        session_id: str,
        user_id: str,
        depth: int = 0,
    ) -> str:
        """处理LLM响应，递归处理工具调用"""
        if depth > 5:
            return "处理深度超限，请简化需求"

        choice = response.choices[0]
        assistant_msg = choice.message

        # 直接回复文本
        if assistant_msg.content and not assistant_msg.tool_calls:
            return assistant_msg.content

        # 有工具调用
        if assistant_msg.tool_calls:
            messages.append(assistant_msg.model_dump())

            for tool_call in assistant_msg.tool_calls:
                func_name = tool_call.function.name
                func_args_str = tool_call.function.arguments

                try:
                    func_args = json.loads(func_args_str) if func_args_str else {}
                except json.JSONDecodeError:
                    func_args = {}

                logger.info("Max调用工具: %s(%s)", func_name, func_args_str[:200])

                result = await self._execute_tool(
                    func_name, func_args, session_id, user_id
                )

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

            max_tools = LLMClient.build_tool_definitions(self._tool_defs)
            next_response = await self.llm.chat(messages, tools=max_tools)
            return await self._process_response(
                next_response, messages, session_id, user_id, depth + 1
            )

        return assistant_msg.content or ""

    async def _execute_tool(
        self,
        tool_name: str,
        args: dict,
        session_id: str,
        user_id: str,
    ) -> str:
        """执行工具调用"""
        if tool_name in self._tools and self._tools[tool_name] is not None:
            try:
                result = await self._tools[tool_name](args)
                await audit_logger.log_tool_call(
                    session_id=session_id,
                    user_id=user_id,
                    agent="max",
                    tool_name=tool_name,
                    tool_input=args,
                    tool_output=result if isinstance(result, dict) else None,
                )
                if isinstance(result, dict) and "content" in result:
                    contents = result["content"]
                    if isinstance(contents, list):
                        return " ".join(
                            c.get("text", "") for c in contents if c.get("text")
                        )
                    return str(contents)
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                logger.error("工具 %s 执行失败: %s", tool_name, e)
                await audit_logger.log_tool_call(
                    session_id=session_id,
                    user_id=user_id,
                    agent="max",
                    tool_name=tool_name,
                    tool_input=args,
                    result_status="error",
                )
                return f"工具执行失败: {str(e)}"

        return f"未知工具: {tool_name}"

    def _build_preference_summary(self) -> str:
        """构建客户偏好记忆摘要，注入系统提示中。

        只包含有非空preferences的客户，最多取最近更新的10个。
        """
        try:
            from max_system.tools.clientmgr_tools import _get_clients_db

            clients_db = _get_clients_db()
            clients_with_prefs = []
            for c in clients_db.values():
                prefs = c.get("preferences")
                if prefs and isinstance(prefs, dict) and len(prefs) > 0:
                    clients_with_prefs.append(c)

            if not clients_with_prefs:
                return ""

            clients_with_prefs.sort(
                key=lambda c: c.get("updated_at") or c.get("created_at") or "",
                reverse=True,
            )
            clients_with_prefs = clients_with_prefs[:10]

            lines = []
            for c in clients_with_prefs:
                name = c.get("name", "未知")
                prefs = c.get("preferences", {})
                prefs_str = ", ".join(f"{k}={v}" for k, v in prefs.items())
                lines.append(f"- {name}: {prefs_str}")

            if lines:
                return "\n## 客户偏好记忆\n" + "\n".join(lines)

        except Exception:
            pass

        return ""

    async def _build_max_system_prompt(self, workspace: Workspace | None = None) -> str:
        """构建Max的系统提示

        Args:
            workspace: If provided, use the workspace's ProfileManager.
                       Otherwise fall back to the global profile_manager (CLI mode).
        """
        # 注入Profile信息 (workspace first, then global fallback)
        profile_section = ""
        profile_mgr = (workspace.profile if workspace and workspace.profile
                       else self.profile_manager)
        if profile_mgr:
            try:
                profile = await profile_mgr.get_all()
                profile_section = profile_mgr.build_prompt_section(profile)
            except Exception:
                logger.warning("Profile注入失败，跳过")

        tools_info = []
        for t in self._tool_defs:
            tools_info.append(f"- {t['name']}: {t['description']}")

        s = self.settings
        bitable_info = f"""
## 飞书多维表格

Base Token: {s.feishu_bitable_app_token}

可用表: 客户信息、合同管理、合作商、支出明细、收入明细、施工管理、任务、售后维保台账、跟进记录
读写工具: feishu_read_bitable(table_id, fields) / feishu_write_bitable(table_id, records)
需要字段详情时，先调 feishu_read_bitable 查看表结构。
"""

        preference_summary = self._build_preference_summary()

        return f"""{self.max_prompt}{profile_section}{bitable_info}
{preference_summary}

---

## 可用工具

{chr(10).join(tools_info)}

---

## 运行模式
- 你正在通过飞书与设计师对话
- 需要数据时调用对应工具查询，需要写入时调用写入工具
- 内容由你自己生成，工具只提供数据和执行操作
- 处理完直接给结果，不要发"收到"之类的中间状态消息
- **你就是Max，设计师只和Max对话，回复中不要提工具名**
"""
