"""Max编排器：多Agent调度引擎

基于DeepSeek/Ollama API的多Agent系统，替代Claude Agent SDK。
Max作为主控Agent，通过function calling调度4个子Agent，
子Agent调用MCP工具执行具体任务。
"""

import json
import logging
import uuid
from typing import AsyncIterator

from max_system.config.settings import MaxSettings
from max_system.config.agent_registry import AGENT_SPECS, AGENT_TOOLS
from max_system.core.llm_client import LLMClient
from max_system.utils.prompt_loader import load_prompt, build_skill_appendix
from max_system.audit import logger as audit_logger
from max_system.config.schema import NormalizedCommand, IntentCategory

logger = logging.getLogger(__name__)


class MaxOrchestrator:
    """Max总控编排器

    核心职责：
    1. 管理LLM客户端（DeepSeek/Ollama）
    2. 加载Max系统提示和子Agent定义
    3. 接收用户消息，Max决策调度
    4. 执行子Agent，收集结果
    5. 管理对话上下文
    """

    def __init__(self, settings: MaxSettings):
        self.settings = settings
        self.llm = LLMClient(settings)
        self.max_prompt = ""
        self.agent_prompts: dict[str, str] = {}
        self.agent_descriptions: dict[str, str] = {}
        self._initialized = False

        # 工具注册表：name -> callable
        self._tools: dict[str, callable] = {}
        self._tool_defs: list[dict] = []

        # 审批门
        self.approval_gate = None

    async def initialize(self) -> None:
        """初始化编排器"""
        if self._initialized:
            return

        # 加载Max主prompt
        self.max_prompt = load_prompt(
            self.settings.prompts_root / "01_Max总控" / "config" / "system_prompt.md"
        )

        # 加载子Agent prompts
        for name, (agent_dir, skill_dirs, description) in AGENT_SPECS.items():
            prompt_path = self.settings.prompts_root / agent_dir / "config" / "system_prompt.md"
            prompt = load_prompt(prompt_path)
            skill_appendix = build_skill_appendix(
                self.settings.prompts_root, agent_dir, skill_dirs
            )
            if skill_appendix:
                prompt = f"{prompt}\n\n---\n\n# 技能详细规范\n\n{skill_appendix}"

            self.agent_prompts[name] = prompt
            self.agent_descriptions[name] = description

        # 注册MCP工具
        self._register_all_tools()

        # 初始化审批门
        from max_system.core.approval_gate import ApprovalGate
        self.approval_gate = ApprovalGate(self.settings)

        self._initialized = True
        logger.info(
            "Max编排器初始化完成: provider=%s, model=%s, agents=%d, tools=%d",
            self.llm.provider_name, self.llm.model,
            len(self.agent_prompts), len(self._tools),
        )

    def _register_all_tools(self) -> None:
        """注册所有MCP工具"""
        from max_system.tools.feishu_tools import register_tools as reg_feishu
        from max_system.tools.obsidian_tools import register_tools as reg_obsidian
        from max_system.tools.knowledge_tools import register_tools as reg_knowledge
        from max_system.tools.quote_tools import register_tools as reg_quote
        from max_system.tools.docgen_tools import register_tools as reg_docgen
        from max_system.tools.clientmgr_tools import register_tools as reg_clientmgr
        from max_system.tools.talker_tools import register_tools as reg_talker
        from max_system.tools.afterpro_tools import register_tools as reg_afterpro
        from max_system.tools.mediapro_tools import register_tools as reg_mediapro
        from max_system.tools.helper_tools import register_tools as reg_helper

        for reg_fn in [reg_feishu, reg_obsidian, reg_knowledge, reg_quote, reg_docgen, reg_clientmgr, reg_talker, reg_afterpro, reg_mediapro, reg_helper]:
            for tool_name, tool_func, tool_def in reg_fn(self.settings):
                self._tools[tool_name] = tool_func
                self._tool_defs.append(tool_def)

        # 注册Agent调度工具
        for name, desc in self.agent_descriptions.items():
            self._tools[f"dispatch_{name}"] = None  # 特殊处理
            self._tool_defs.append({
                "name": f"dispatch_{name}",
                "description": f"调度{desc}。当用户需求属于该Agent职责范围时调用。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": f"要交给{name}处理的任务描述",
                        },
                    },
                    "required": ["task"],
                },
            })

    async def dispatch(
        self,
        message: str,
        session_id: str = "cli",
        user_id: str = "designer",
        history: list[dict] | None = None,
    ) -> str:
        """处理用户消息，返回Max响应

        Args:
            message: 用户消息
            session_id: 会话ID
            user_id: 用户ID
            history: 对话历史（不含system），跨消息保持上下文
        """
        if not self._initialized:
            await self.initialize()

        # 构建Max的对话消息：system + 历史 + 当前消息
        messages = [{"role": "system", "content": self._build_max_system_prompt()}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": message})

        # 调用Max
        max_tools = LLMClient.build_tool_definitions(self._tool_defs)
        response = await self.llm.chat(messages, tools=max_tools)

        # 处理Max的响应（可能包含工具调用）
        return await self._process_max_response(response, messages, session_id, user_id)

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

        messages = [{"role": "system", "content": self._build_max_system_prompt()}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": message})

        max_tools = LLMClient.build_tool_definitions(self._tool_defs)
        full_response = ""

        async for chunk in self.llm.chat_stream(messages, tools=max_tools):
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta is None:
                continue

            # 文本内容
            if delta.content:
                full_response += delta.content
                yield {"type": "text", "content": delta.content}

            # 工具调用
            if delta.tool_calls:
                # 流式工具调用需要等完整收集后再执行
                pass

        # 如果有工具调用，需要在流式结束后处理
        # 当前简化实现：流式模式不处理工具调用，用非流式模式

    async def _process_max_response(
        self,
        response,
        messages: list[dict],
        session_id: str,
        user_id: str,
        depth: int = 0,
    ) -> str:
        """处理Max响应，递归处理工具调用"""
        if depth > 5:
            return "调度深度超限，请简化需求"

        choice = response.choices[0]
        assistant_msg = choice.message

        # 如果Max直接回复文本
        if assistant_msg.content and not assistant_msg.tool_calls:
            return assistant_msg.content

        # 如果Max调用了工具
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

                # 执行工具
                result = await self._execute_tool(
                    func_name, func_args, session_id, user_id
                )

                # 将结果添加到消息
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

            # 继续对话，让Max看到工具结果
            max_tools = LLMClient.build_tool_definitions(self._tool_defs)
            next_response = await self.llm.chat(messages, tools=max_tools)
            return await self._process_max_response(
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
        # Agent调度工具：特殊处理
        if tool_name.startswith("dispatch_"):
            agent_name = tool_name.replace("dispatch_", "")
            task = args.get("task", "")
            return await self._dispatch_to_agent(agent_name, task, session_id, user_id)

        # 审批门检查
        if self.approval_gate:
            risk_level, reason = self.approval_gate.check_risk(tool_name, args)
            if risk_level == "high":
                approved = await self.approval_gate.request_approval(
                    tool_name, args, risk_level, reason
                )
                if not approved:
                    return f"审批未通过: {reason}。需要设计师确认后才能执行此操作。"

        # MCP工具：直接调用
        if tool_name in self._tools and self._tools[tool_name] is not None:
            try:
                result = await self._tools[tool_name](args)
                # 审计日志
                await audit_logger.log_tool_call(
                    session_id=session_id,
                    user_id=user_id,
                    agent="max",
                    tool_name=tool_name,
                    tool_input=args,
                    tool_output=result if isinstance(result, dict) else None,
                )
                # 提取content文本
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
                return f"工具执行失败: {str(e)}"

        return f"未知工具: {tool_name}"

    async def _dispatch_to_agent(
        self,
        agent_name: str,
        task: str,
        session_id: str,
        user_id: str,
    ) -> str:
        """调度任务到子Agent"""
        if agent_name not in self.agent_prompts:
            return f"未知Agent: {agent_name}"

        logger.info("调度到 %s: %s", agent_name, task[:100])

        await audit_logger.log_dispatch(
            NormalizedCommand(
                chat_id=session_id, user_id=user_id, user_name="",
                message_type="text", text=task,
                is_group=False, is_mentioned=False, should_respond=True,
                intent=IntentCategory(agent_name) if agent_name in [e.value for e in IntentCategory] else None,
            ),
            agent=agent_name,
        )

        # 构建子Agent对话
        agent_prompt = self.agent_prompts[agent_name]

        # 子Agent可用的工具（只包含该Agent权限内的MCP工具）
        agent_tool_names = AGENT_TOOLS.get(agent_name, [])
        agent_tool_defs = [
            t for t in self._tool_defs
            if t["name"] in agent_tool_names
        ]
        agent_tools = LLMClient.build_tool_definitions(agent_tool_defs) if agent_tool_defs else None

        messages = [
            {"role": "system", "content": agent_prompt},
            {"role": "user", "content": task},
        ]

        # 调用子Agent
        return await self._run_agent_loop(
            agent_name, messages, agent_tools, agent_tool_names,
            session_id, user_id,
        )

    async def _run_agent_loop(
        self,
        agent_name: str,
        messages: list[dict],
        tools: list[dict] | None,
        allowed_tool_names: list[str],
        session_id: str,
        user_id: str,
        max_iterations: int = 10,
    ) -> str:
        """运行子Agent的循环（调用LLM -> 执行工具 -> 再调用LLM -> ...）"""
        for iteration in range(max_iterations):
            response = await self.llm.chat(messages, tools=tools)
            choice = response.choices[0]
            assistant_msg = choice.message

            # 如果没有工具调用，返回文本
            if not assistant_msg.tool_calls:
                return assistant_msg.content or ""

            # 处理工具调用
            messages.append(assistant_msg.model_dump())

            for tool_call in assistant_msg.tool_calls:
                func_name = tool_call.function.name
                func_args_str = tool_call.function.arguments

                try:
                    func_args = json.loads(func_args_str) if func_args_str else {}
                except json.JSONDecodeError:
                    func_args = {}

                # 权限检查
                if func_name not in allowed_tool_names:
                    result = f"权限不足: {agent_name} 无权调用 {func_name}"
                elif func_name in self._tools and self._tools[func_name] is not None:
                    try:
                        result_obj = await self._tools[func_name](func_args)
                        if isinstance(result_obj, dict) and "content" in result_obj:
                            contents = result_obj["content"]
                            if isinstance(contents, list):
                                result = " ".join(
                                    c.get("text", "") for c in contents if c.get("text")
                                )
                            else:
                                result = str(contents)
                        else:
                            result = json.dumps(result_obj, ensure_ascii=False)
                    except Exception as e:
                        result = f"工具执行失败: {str(e)}"
                else:
                    result = f"未知工具: {func_name}"

                # 审计
                await audit_logger.log_tool_call(
                    session_id=session_id,
                    user_id=user_id,
                    agent=agent_name,
                    tool_name=func_name,
                    tool_input=func_args,
                )

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

        return "Agent执行轮次超限"

    def _build_max_system_prompt(self) -> str:
        """构建Max的系统提示（含Agent调度说明）"""
        agent_info = []
        for name, desc in self.agent_descriptions.items():
            agent_info.append(f"- dispatch_{name}: {desc}")

        tools_info = []
        for t in self._tool_defs:
            if not t["name"].startswith("dispatch_"):
                tools_info.append(f"- {t['name']}: {t['description']}")

        # 多维表格映射表
        s = self.settings
        bitable_info = f"""
## 飞书多维表格结构

当前使用的 Base Token: {s.feishu_bitable_app_token}

使用 feishu_read_bitable / feishu_write_bitable 时，fields 请使用中文 field_name。

### 客户信息表 (`{s.bitable_table_clients}`)
字段: 客户编号, 客户姓名, 性别, 联系方式, 客户类型, 客户来源, 项目地址, 类型, 户型, 面积, 报价, 设计费, 录入人, 部门, 分派设计师, 录入时间, 跟进时间, 落单进度, 服务阶段, 备注

### 合同管理表 (`{s.bitable_table_contracts}`)
字段: 合同编号, 签订日期, 客户姓名, 项目地址, 轻辅合同, 主材合同额, 直接费, 产值, 预估利润, 盈余, 支出, 设计费, 付款比例, 已付款, 剩余款, 首期款, 中期款, 尾期款, 主材款, 增减项, 设计师, 备注

### 合作商表 (`{s.bitable_table_suppliers}`)
字段: 姓名, 联系电话, 邮箱地址, 合作类型, 品牌/工种, 供应产品, 报价清单, 合作评分, 合作等级

### 支出明细表 (`{s.bitable_table_expense}`)
字段: 日期, 合同编号, 项目地址, 支出明细, 往来单位, 联系方式, 客户姓名, 支出, 备注, 附件

### 收入明细表 (`{s.bitable_table_income}`)
字段: 编号, 合同编号, 项目地址, 首期款, 中期款, 尾期款, 主材款, 设计费, 增减项, 收入总和, 客户姓名, 联系方式, 备注, 附件

### 施工管理表 (`{s.bitable_table_construction}`)
字段: 施工节点, 文本2, 执行人, 完结, 任务, 任务2, 日期, 日期2

### 任务表 (`{s.bitable_table_tasks}`)
字段: 施工节点, 分类, 工种, 预埋, 采购, 污染, J298进度

### 售后维保台账 (`{s.bitable_table_after_sales}`)
字段: 提报日期, 合同编号(关联合同表), 客户姓名(Lookup自动), 问题类型(单选:水电/墙面/防水/门窗/柜体/其他), 问题描述, 处理状态(单选:待处理/处理中/已完成/已关闭), 优先级(单选:紧急/高/中/低), 提报人, 处理人, 处理完成日期, 客户满意度(单选:非常满意/满意/一般/不满意), 备注

### 跟进记录表 (`{s.bitable_table_followups}`)
字段: 跟进时间, 合同编号(关联合同表), 客户姓名(Lookup自动), 记录类型(单选:日常跟进/售后回访/关怀回访/投诉跟进), 跟进人, 跟进方式(单选:微信/电话/面访/飞书), 跟进内容, 客户反馈, 满意度(单选:非常满意/满意/一般/不满意), 跟进事项, 下次跟进时间, 状态(单选:待跟进/跟进中/已完成)
"""

        return f"""{self.max_prompt}{bitable_info}

---

## 可用工具

### Agent调度工具
你可以通过以下工具调度搭档执行任务。每个任务必须包含清晰的任务描述。

{chr(10).join(agent_info)}

### 直接可用工具
你也可以直接调用以下工具（通常用于简单操作或协调任务）：

{chr(10).join(tools_info[:20])}

---

## 运行模式
- 你正在通过飞书与设计师对话
- 当需要搭档处理时，调用对应的dispatch_xxx工具
- 搭档执行完返回结果后，你来终审和整合
- 直接用自然对话的方式回复设计师，不要发"收到"之类的中间状态消息
- 处理完直接给结果，干净利落
"""
