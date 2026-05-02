# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Max 多Agent室内设计AI助手系统** — A multi-agent AI assistant system for "斑马精装" interior design company. Max orchestrates 4 sub-agents (Talker, AfterPro, MediaPro, Helper) using an LLM (DeepSeek/Ollama) with function calling, integrates with Feishu (Lark), Obsidian, and a knowledge base.

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

## Project Structure

```
max_system/                      # Main Python package
├── __main__.py                  # Entry point (3 modes: cli/webhook/feishu)
├── config/
│   ├── settings.py              # Pydantic-settings (.env file config)
│   ├── schema.py                # Shared data models (IntentCategory, NormalizedCommand, etc.)
│   └── agent_registry.py        # Agent directory mapping & tool access control
├── core/
│   ├── orchestrator.py          # MaxOrchestrator - multi-agent dispatch engine
│   ├── llm_client.py            # OpenAI-compatible LLM client (DeepSeek/Ollama)
│   ├── intent_router.py         # Keyword-based intent classification
│   ├── approval_gate.py         # Risk-based approval for high-stakes tool calls
│   └── session_manager.py       # Per-chat conversation history (idle cleanup)
├── tools/
│   ├── feishu_tools.py          # Feishu message/bitable/approval/calendar tools
│   ├── knowledge_tools.py       # Knowledge base search & compliance check
│   ├── quote_tools.py           # Materials/construction price query
│   ├── docgen_tools.py          # Document generation & validation
│   ├── obsidian_tools.py        # Obsidian vault operations
│   ├── clientmgr_tools.py       # Client CRM operations
│   ├── talker_tools.py          # Talker-specific tools
│   ├── afterpro_tools.py        # AfterPro-specific tools
│   ├── mediapro_tools.py        # MediaPro-specific tools
│   └── helper_tools.py          # Helper-specific tools
├── integrations/
│   ├── feishu/                  # Feishu (Lark) integration
│   │   ├── bot.py               # Webhook event handler & message dispatch
│   │   ├── long_conn.py         # WebSocket long-connection (no tunnel needed)
│   │   ├── api_client.py        # Feishu REST API client (httpx)
│   │   ├── adapter.py           # Event parsing & normalization
│   │   └── event_types.py       # Event type definitions
│   ├── obsidian/                # Obsidian vault integration
│   │   ├── vault_manager.py     # Vault CRUD operations
│   │   ├── link_manager.py      # Wiki link management
│   │   └── template_engine.py   # Note template rendering
│   └── knowledge/               # Knowledge base
│       ├── vector_store.py      # ChromaDB vector store
│       ├── data_loader.py       # File ingestion
│       ├── indexer.py           # Index building
│       └── retriever.py         # Semantic retrieval
├── api/                         # FastAPI webhook server
│   ├── app.py                   # FastAPI app factory
│   └── routes/
│       ├── health.py            # GET /health
│       ├── feishu_webhook.py    # POST /webhook/feishu
│       └── task_status.py       # GET /tasks/{task_id}
├── audit/                       # SQLite audit logging
│   ├── models.py                # AuditEntry / TaskLog dataclasses
│   ├── store.py                 # aiosqlite-backed storage
│   └── logger.py                # Convenience logging functions
├── utils/
│   ├── prompt_loader.py         # System prompt loading with caching
│   └── retry.py                 # Exponential backoff retry utility
└── tests/
    ├── test_config.py           # Agent registry & schema tests
    ├── test_intent_router.py    # Intent classification tests
    ├── test_session_manager.py  # Session lifecycle & history trim tests
    └── test_tools.py            # Tool function output tests

01_Max总控/       # Max orchestrator system prompt
02_Talker谈单官/   # Talker agent + 6 skills
03_AfterPro售后官/ # AfterPro agent + 5 skills
04_MediaPro自媒体/  # MediaPro agent + 5 skills
05_Helper执行助手/  # Helper agent + 5 skills
06_知识库/         # Knowledge base (company standards, cases, materials, etc.)
07_工具集成/       # (reserved)
08_测试文件/       # (reserved)
09_迭代记录/       # (reserved)
Quote/           # Excel quote templates
DESIGN-main/     # Design tool (Puppeteer-based, separate project)
```

## Architecture

### Multi-Agent Flow

1. **User message** arrives via CLI, Feishu Webhook, or Feishu WebSocket long-connection
2. **SessionManager** maintains per-chat conversation history (20-turn max, 1h idle cleanup)
3. **MaxOrchestrator.dispatch()** sends message to LLM with Max system prompt + tool definitions
4. **Max (main LLM)** decides: reply directly, call MCP tools, or dispatch to a sub-agent via `dispatch_{agent_name}`
5. **Sub-agents** run their own tool-calling loop (up to 10 iterations) with scoped tool permissions
6. **Max** receives agent results and produces final response

### Agent Dispatch Flow

`dispatch_{agent}` tool → `_dispatch_to_agent()` → loads agent prompt + skill appendix → calls LLM with agent-scoped tools → `_run_agent_loop()` handles tool call chain → returns result to Max

### Risk Control

`ApprovalGate` intercepts high-risk tool calls (contracts, pricing, customer data) before execution. CLI mode prompts for confirm; Feishu mode creates an approval instance.

### Running Modes

- **`feishu`** (default): WebSocket long-connection to Feishu, no public IP needed
- **`webhook`**: FastAPI server receiving Feishu webhook events
- **`cli`**: Interactive terminal REPL

## Key Design Decisions

- Uses **DeepSeek or Ollama** via OpenAI-compatible API (not Anthropic Claude SDK), despite the project name "Max"
- **Feishu long-connection** mode uses `lark-oapi` WebSocket — avoids need for ngrok/public URL
- **3 startup modes** share the same orchestrator but different message sources (CLI stdin, FastAPI webhook, Feishu WebSocket)
- **Tool permissions** per agent defined statically in `agent_registry.py` — each agent can only call its allowed tools
- **Knowledge base** supports both keyword search (file-based) and semantic search (ChromaDB vector store)
- **Quote data** sourced from JSON files in `Quote/` directory alongside Excel templates
- Each sub-agent has skills defined as `system_prompt.md` files in numbered `skill_0X_*` directories, loaded and appended at initialization
