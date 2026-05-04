# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Max 室内设计AI助手** — A single-agent AI assistant for interior design companies. Max directly calls 38 tools via LLM function calling (DeepSeek/Ollama), integrating with Feishu (Lark) and a knowledge base. Designed for solo designers (超级个体).

## Commands

- **Run all tests**: `pytest` (asyncio_mode=auto, no `@pytest.mark.asyncio` needed on `async def` tests)
- **Run single test**: `pytest max_system/tests/test_file.py::TestClass::test_method -v`
- **Run tests with coverage**: `pytest --cov=max_system --cov-report=term-missing`
- **Lint**: `ruff check max_system/`
- **Run CLI mode**: `python -m max_system cli`
- **Run Feishu mode** (default): `python -m max_system`
- **Init system**: `python -m max_system init`

## Architecture

```
User → CLI / Feishu Long-Conn (WebSocket)
         │
    SessionManager (20-turn, 1h idle)
         │
    MaxOrchestrator
         │
    LLM (function calling) → 38 MCP Tools
         │
    ProfileManager · AuditStore · JobStore → data/max.db
```

### Single-Agent Design

1. User message arrives → SessionManager gets/creates session
2. `MaxOrchestrator.dispatch()` sends to LLM with Max system prompt + all 38 tool definitions
3. LLM decides: reply directly or call tool(s)
4. Tools execute → results return to LLM → LLM generates final response
5. All tool calls logged to AuditStore (SQLite)

### Tool Groups (38 total)

| Group | Tools | Description |
|-------|-------|-------------|
| feishu | 10 | Message send, Bitable read/write, Approval create, Calendar create/list/delete, Task create/list/complete |
| knowledge | 3 | Keyword search, compliance check, catalog |
| quote | 3 | Material query, construction query, fee summary calculation (Module 4) |
| clientmgr | 4 | Client CRUD, tag & report |
| sales | 4 | Lead classify, need analysis, contract draft, data stats |
| service | 5 | Return visit, issue tracking, after-sales log, client care, complaint handling |
| marketing | 3 | Lead transfer, case packaging, data review |
| profile | 3 | Get/update/reset designer company info (Chinese key aliases supported) |
| schedule | 3 | Create/list/cancel scheduled jobs |

### Profile System

Designer company info stored in `data/max.db` → `designer_profile` table. Modified via conversation (e.g., "把我们公司名改成XX"). Supports 23 Chinese→English key aliases. Injected into system prompt each turn. First-run detection: if profile is empty, Max proactively asks onboarding questions.

### Fee Summary Calculation (Module 4)

Ported from DESIGN project's `calculator.js`. Computes: subtotal → management fee (%) → tax (%) → garbage fee → protection fee → grand total. Fee rates stored in Profile with industry defaults (8%, 3.41%, 800, 500).

## Key Design Decisions

- **LLM**: DeepSeek or Ollama via OpenAI-compatible API (`AsyncOpenAI` in `llm_client.py`)
- **Feishu long-connection** (default mode): WebSocket in daemon thread → main async loop via `run_coroutine_threadsafe` — no public IP needed
- **2 startup modes**: `feishu` (default) and `cli` (terminal testing). Webhook mode deleted.
- **Tool registration**: Each `*_tools.py` module has `register_tools(settings) → [(name, callable, tool_def)]`
- **Single SQLite DB**: `data/max.db` with tables: `designer_profile`, `scheduled_jobs`, `audit_log`, `task_log`
- **Knowledge search**: Keyword grep (`knowledge_tools.py`) for production
- **Quote data**: JSON files in `quotes/` directory; `材料库.json` and `施工库.json`
- **Bitable schema**: Defined in `max_system/config/bitable_schema.py` (9 tables, ~100 fields). System prompt lists table names only; LLM queries field details on demand.
- **Messages >4000 chars**: Split into segments with 0.5s delay

## Configuration

Copy `.env.example` to `.env`. 4 required fields (see `max_system/config/settings.py`):

- `LLM_API_KEY` — DeepSeek API key
- `FEISHU_APP_ID`, `FEISHU_APP_SECRET` — Feishu app credentials
- `FEISHU_BITABLE_APP_TOKEN` — Feishu Bitable base token

Optional: set `LLM_PROVIDER=ollama` to use a local Ollama instance (default model: `qwen3.5` at `http://localhost:11434/v1`).

Run `python -m max_system init` to auto-create Bitable tables, write table IDs to `.env`, and initialize the database.

## CLI Mode

In CLI mode (`python -m max_system cli`), these slash commands are available:

| Command | Description |
|---------|-------------|
| `/model` | Switch LLM provider (deepseek/ollama) at runtime |
| `/status` | Show current LLM, tool count, and registered tool names |
| `/clear` | Clear conversation history |
| `/help` | Show help text |
| `/quit` | Exit |

## Tool Output Convention

All tools return results in MCP-compatible format: `{"content": [{"type": "text", "text": "..."}]}`. When writing new tools, follow this pattern so the orchestrator can extract text correctly in `_execute_tool` ([orchestrator.py:211-215](max_system/core/orchestrator.py#L211-L215)).

## Dependency Note

Despite `anthropic` appearing in `pyproject.toml`, the actual LLM client uses the `openai` package (OpenAI-compatible API). `lark-oapi` is the Feishu SDK package (imported as `lark_oapi`).
