# Agent Architecture

## Overview

This agent is a Python CLI that answers questions by calling an LLM API. It forms the foundation for the agentic system that will be extended with tools in Tasks 2–3.

## LLM Provider

- **Provider**: OpenRouter
- **Model**: `qwen/qwen3-coder:free`
- **API Base**: `https://openrouter.ai/api/v1`
- **API Key**: Stored in `.env.agent.secret` (LLM_API_KEY)

> **Note**: OpenRouter free tier has a 50 requests/day limit and may be rate-limited. For more reliable access, set up Qwen Code API on your VM (see wiki/qwen.md).

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│  Command Line   │ ──> │  agent.py    │ ──> │  LLM API    │ ──> │  JSON Output │
│  (question)     │     │  (CLI)       │     │  (OpenRouter)│     │  (stdout)    │
└─────────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
```

## Components

### 1. CLI Entry Point (`agent.py`)

The agent is a single Python file with three main functions:

- **`load_config()`** — Loads LLM configuration from `.env.agent.secret` using `python-dotenv`. Validates that `LLM_API_KEY`, `LLM_API_BASE`, and `LLM_MODEL` are present.

- **`call_llm(question, config)`** — Creates an OpenAI-compatible client and sends a chat completion request. Returns the LLM's text response.

- **`main()`** — Parses command-line arguments, orchestrates the flow, and outputs JSON.

### 2. Configuration (`.env.agent.secret`)

Environment variables loaded at runtime:

| Variable | Description |
|----------|-------------|
| `LLM_API_KEY` | API key for authentication |
| `LLM_API_BASE` | Base URL of the LLM API endpoint |
| `LLM_MODEL` | Model name to use for completions |

### 3. Output Format

The agent outputs a single JSON line to stdout:

```json
{"answer": "Representational State Transfer.", "tool_calls": []}
```

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | The LLM's response to the question |
| `tool_calls` | array | Empty for Task 1 (populated in Task 2) |

All debug/error output goes to stderr.

## Usage

```bash
# Run with a question
uv run agent.py "What does REST stand for?"

# Expected output (single JSON line to stdout)
{"answer": "...", "tool_calls": []}
```

## Error Handling

| Error | Behavior |
|-------|----------|
| Missing command-line argument | Print usage to stderr, exit 1 |
| Missing environment variables | Print error to stderr, exit 1 |
| API request failure | Print error to stderr, exit 1 |
| Timeout (>60s) | Subprocess timeout, exit 1 |

## Dependencies

- `openai` — LLM API client (OpenAI-compatible)
- `python-dotenv` — Load environment from `.env.agent.secret`
- Standard library: `json`, `os`, `sys`

## Testing

Run the regression test:

```bash
uv run pytest tests/test_task1.py -v
```

The test verifies:
- Agent exits with code 0
- Output is valid JSON
- `answer` field exists and is non-empty
- `tool_calls` field exists and is an empty list

## Extension Plan (Tasks 2–3)

- **Task 2**: Add tools (e.g., `read_file`, `list_files`, `query_api`) and populate `tool_calls` in the output.
- **Task 3**: Implement the agentic loop — parse tool results, make follow-up calls, and synthesize a final answer.
