# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Max 多Agent室内设计AI助手系统** — A multi-agent AI assistant for "斑马精装" interior design company. Max orchestrates 4 sub-agents (Talker, AfterPro, MediaPro, Helper) via LLM function calling (DeepSeek/Ollama), integrating with Feishu (Lark), Obsidian, and a knowledge base.

## Commands

- **Run all tests**: `pytest`
- **Run single test**: `pytest max_system/tests/test_file.py::TestClass::test_method -v`
- **Run tests with coverage**: `pytest --cov=max_system`
- **Lint**: `ruff check max_system/`
- **Format check**: `ruff format --check max_system/`
- **Format**: `ruff format max_system/`
- **Run CLI mode**: `python -m max_system cli`
- **Run Webhook mode**: `python -m max_system webhook`
- **Run Feishu mode** (default): `python -m max_system feishu`
- **Init Feishu Bitable**: `python scripts/init_bitable.py`

## Architecture

```
User → CLI / Feishu WS (long_conn) / Feishu Webhook (FastAPI)
         │                    │
    SessionManager        FeishuBot
         │                    │
    MaxOrchestrator ──────────┘
         │
    Max LLM (function calling) + ApprovalGate (risk check)
         │
    dispatch_talker / dispatch_afterpro / dispatch_mediapro / dispatch_helper
         │
    Sub-agent LLM loop (≤10 iterations, scoped tool permissions)
         │
    35+ MCP Tools: Feishu · Knowledge · Quote · ClientMgr · Obsidian · Agent-specific
         │
    AuditStore (SQLite) · VectorStore (ChromaDB)
```

### Multi-Agent Dispatch

1. User message arrives → SessionManager maintains per-chat history (20-turn max, 1h idle cleanup)
2. `MaxOrchestrator.dispatch()` sends to LLM with Max system prompt + all tool definitions
3. Max LLM decides: reply directly, call a tool, or `dispatch_{agent}` to a sub-agent
4. `_dispatch_to_agent()` loads agent prompt + skill appendix → `_run_agent_loop()` (≤10 iterations, agent-scoped tools only)
5. Result returns to Max for final response

### Agent Registry & Tool Permissions

Agent specs and tool permissions are defined statically in `max_system/config/agent_registry.py`. Each agent can only call its allowed tools:

| Agent | Skills | Tools | Key Restriction |
|-------|--------|-------|-----------------|
| Talker | 6 (LeadCatch→DataStat) | 17 | Full bitable write |
| AfterPro | 5 (ReturnVisit→ComplaintPro) | 15 | Full bitable write |
| MediaPro | 5 (ContentGen→DataReview) | 12 | No bitable write |
| Helper | 5 (DocGen→ObsidianSync) | 20 | Most permissive |

### Risk Control

`ApprovalGate` classifies tool calls as LOW/MEDIUM/HIGH risk. 8 tools are `HIGH_RISK_TOOLS` (contracts, pricing, customer data). CLI mode prompts y/N; Feishu mode creates an approval instance.

### Agent Prompts

Each agent's system prompt lives in `config/system_prompt.md` within its numbered directory. Skills are `skill_0X_*/config/system_prompt.md` files, loaded and appended by `build_skill_appendix()` at initialization. The 5 agent directories: `01_Max总控`, `02_Talker谈单官`, `03_AfterPro售后官`, `04_MediaPro自媒体`, `05_Helper执行助手`.

## Key Design Decisions

- **LLM**: DeepSeek or Ollama via OpenAI-compatible API (`AsyncOpenAI` in `llm_client.py`), not Anthropic Claude SDK
- **Feishu long-connection** (default mode): `lark-oapi` WebSocket in daemon thread, bridges to main async loop via `run_coroutine_threadsafe` — no public IP needed
- **3 startup modes** share the same orchestrator, differ only in message source (CLI stdin, FastAPI webhook, Feishu WebSocket)
- **Tool registration**: Each `*_tools.py` module has `register_tools(settings) → [(name, callable, tool_def)]`, called by orchestrator at init
- **Knowledge search**: Dual mode — keyword grep (`knowledge_tools.py`) for production, ChromaDB semantic search (`integrations/knowledge/`) for future use
- **ClientMgr**: In-memory cache + bidirectional Feishu Bitable sync with field name mapping (internal English keys ↔ Chinese field names)
- **Quote data**: JSON files in `Quote/` directory; `quote_tools.py` queries `材料库.json` and `施工库.json`
- **Audit**: All dispatches, tool calls, and approvals logged to SQLite via `AuditStore` (aiosqlite)
- **Messages >4000 chars**: Split into segments with 0.5s delay when sending to Feishu

## Configuration

Copy `.env.example` to `.env`. Required settings (see `max_system/config/settings.py`):

- **LLM**: `LLM_PROVIDER` (deepseek/ollama), `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL`
- **Feishu**: `FEISHU_APP_ID`, `FEISHU_APP_SECRET`, `FEISHU_VERIFICATION_TOKEN`, `FEISHU_ENCRYPT_KEY`, `FEISHU_BITABLE_APP_TOKEN`, plus 8 `FEISHU_TABLE_*_ID` values
- **Paths**: `OBSIDIAN_VAULT_PATH`, `KNOWLEDGE_BASE_PATH`, `QUOTE_DATA_PATH`
- See `需要你提供的配置说明.md` for the full setup checklist
