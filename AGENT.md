# Agent Architecture

## Overview

This agent is a Python CLI that answers questions using project documentation, source code, and the live backend API. It implements an agentic loop with three tools (`list_files`, `read_file`, `query_api`) and returns a structured JSON response with the answer, optional source reference, and tool call history.

## LLM Provider

- **Provider**: OpenRouter
- **Model**: `qwen/qwen3-coder:free`
- **API Base**: `https://openrouter.ai/api/v1`
- **API Key**: Stored in `.env.agent.secret` (LLM_API_KEY)

> **Note**: OpenRouter free tier has a 50 requests/day limit and may be rate-limited. For more reliable access, set up Qwen Code API on your VM (see wiki/qwen.md).

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  Command Line   │ ──> │  agent.py    │ ──> │  LLM API    │
│  (question)     │     │  (CLI)       │     │  (OpenRouter)│
└─────────────────┘     └──────┬────────┘     └─────────────┘
                               │
                               ▼
                        ┌─────────────┐
                        │  Tools      │
                        │  - list_files│
                        │  - read_file │
                        │  - query_api │
                        └──────┬──────┘
                               │
                               ▼
                        ┌──────────────┐
                        │  JSON Output │
                        │  - answer    │
                        │  - source    │
                        │  - tool_calls│
                        └──────────────┘
```

## Agentic Loop

The agent implements a loop that continues until the LLM provides a final answer:

1. **Send question** — Initial user question + system prompt sent to LLM with tool schemas
2. **LLM decides** — LLM either:
   - Returns tool calls → execute tools, append results, go to step 1
   - Returns final answer → extract answer and source, output JSON, exit
3. **Limit** — Maximum 10 tool call iterations to prevent infinite loops

```python
messages = [system_prompt, user_question]
tool_calls_log = []

for i in range(10):
    response = call_llm(messages, tools)
    
    if response has tool_calls:
        execute each tool
        append tool results to messages
        continue
    else:
        final_answer = response.content
        break

output JSON with answer, source, tool_calls
```

**Important:** Handle `content: null` from LLM — use `(msg.get("content") or "")` instead of `msg.get("content", "")`.

## Tools

Three tools are implemented and registered as function-calling schemas:

### `list_files`

List files and directories at a given path.

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | string | Relative directory path from project root |

**Example:**
```json
{"tool": "list_files", "args": {"path": "wiki"}, "result": "git-workflow.md\nllm.md\n..."}
```

### `read_file`

Read contents of a file from the project repository.

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | string | Relative path from project root |

**Example:**
```json
{"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, "result": "# Git Workflow\n\n..."}
```

### `query_api`

Call the deployed backend API and return the response.

| Parameter | Type | Description |
|-----------|------|-------------|
| `method` | string | HTTP method (GET, POST, PUT, DELETE) |
| `path` | string | API path (e.g., `/items/`, `/analytics/completion-rate?lab=lab-01`) |
| `body` | string | Optional JSON request body for POST/PUT requests |

**Example:**
```json
{"tool": "query_api", "args": {"method": "GET", "path": "/items/"}, "result": "{\"status_code\": 200, \"body\": \"[...]\"}"}
```

**Authentication:** Uses `LMS_API_KEY` from `.env.docker.secret` in the `X-API-Key` header.

**Base URL:** Uses `AGENT_API_BASE_URL` from environment (default: `http://localhost:42002`).

### Path Security

`read_file` and `list_files` validate paths to prevent directory traversal attacks:

```python
def safe_path(relative_path: str) -> Path:
    clean_path = relative_path.lstrip("/")
    full_path = (PROJECT_ROOT / clean_path).resolve()
    
    # Ensure path is within project root
    if not str(full_path).startswith(str(PROJECT_ROOT.resolve())):
        raise ValueError(f"Path traversal detected: {relative_path}")
    
    return full_path
```

This prevents access to files outside the project directory (e.g., `../../../etc/passwd`).

## System Prompt Strategy

The system prompt guides the LLM on **when to use which tool**:

| Question Type | Tool Strategy |
|---------------|---------------|
| Wiki/documentation | `list_files` → `read_file` |
| Source code | `list_files` → `read_file` |
| Live data (counts, scores) | `query_api` (GET) |
| Status codes | `query_api` (omit auth for 401/403) |
| Bug diagnosis | `query_api` → `read_file` |
| Configuration (ports, services) | `read_file` (docker-compose.yml) |

**Full system prompt:**
```
You are a helpful assistant that answers questions using project documentation, 
source code, and the live backend API.

You have access to three tools:
1. list_files - List files in a directory (use to discover what files exist)
2. read_file - Read contents of a file (use for wiki documentation, source code, config files)
3. query_api - Call the deployed backend API (use for live data, status codes, testing endpoints)

Tool selection strategy:
- For wiki/documentation questions → use list_files to find wiki files, then read_file
- For source code questions → use list_files to find files, then read_file
- For live data questions → use query_api with GET
- For status code questions → use query_api (omit auth header to see 401/403 if needed)
- For bug diagnosis → use query_api to reproduce the error, then read_file to find the buggy code
- For configuration questions → read docker-compose.yml or config files

Source format:
When answering from wiki or source code, include the source at the end:
Source: path/to/file.md#section-anchor

The section anchor should be the heading ID (lowercase, hyphens instead of spaces).
For API responses, you don't need a source reference.

Think step by step. Only call tools when you need information. When you have 
enough information, provide the final answer.
```

## Output Format

The agent outputs a single JSON object to stdout:

```json
{
  "answer": "There are 120 items in the database.",
  "source": "",
  "tool_calls": [
    {
      "tool": "query_api",
      "args": {"method": "GET", "path": "/items/"},
      "result": "{\"status_code\": 200, \"body\": \"[...]\"}"
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | The final answer (source line removed) |
| `source` | string | Wiki/source file reference with section anchor (optional for API questions) |
| `tool_calls` | array | All tool calls made during the loop |

Each tool call entry has:
- `tool`: tool name
- `args`: arguments passed to the tool
- `result`: the tool's return value

All debug/error output goes to stderr.

## Configuration

The agent reads configuration from two environment files:

### `.env.agent.secret` (LLM configuration)

| Variable | Purpose |
|----------|---------|
| `LLM_API_KEY` | LLM provider API key |
| `LLM_API_BASE` | LLM API endpoint URL |
| `LLM_MODEL` | Model name |

### `.env.docker.secret` (LMS configuration)

| Variable | Purpose |
|----------|---------|
| `LMS_API_KEY` | Backend API key for query_api authentication |
| `AGENT_API_BASE_URL` | Base URL for query_api (default: http://localhost:42002) |

**Important:** The autochecker injects its own values at runtime. Never hardcode URLs or keys.

## Usage

```bash
# Run with a question
uv run agent.py "How many items are in the database?"

# Expected output (JSON with answer, source, tool_calls)
```

## Error Handling

| Error | Behavior |
|-------|----------|
| Missing command-line argument | Print usage to stderr, exit 1 |
| Missing environment variables | Print error to stderr, exit 1 |
| API request failure | Print error to stderr, exit 1 |
| Path traversal attempt | Return error message as tool result |
| File not found | Return error message as tool result |
| API connection error | Return error message as tool result |
| Timeout (>60s) | Subprocess timeout, exit 1 |
| Max iterations (10) | Return partial answer with tool calls made |

## Dependencies

- `openai` — LLM API client (OpenAI-compatible)
- `httpx` — HTTP client for query_api
- `python-dotenv` — Load environment from `.env.*` files
- Standard library: `json`, `os`, `sys`, `re`, `pathlib`

## Testing

Run the benchmark evaluation:

```bash
uv run run_eval.py
```

This runs 10 questions across all categories:
- Wiki lookup (questions 0–1)
- Source code reading (questions 2–3)
- Live API queries (questions 4–5)
- Bug diagnosis (questions 6–7)
- Reasoning with LLM judge (questions 8–9)

## Debugging Workflow

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Agent doesn't use a tool | Tool description too vague | Improve schema description |
| Tool returns error | Bug in tool implementation | Fix tool code, test in isolation |
| Wrong tool arguments | LLM misunderstands schema | Clarify parameter descriptions |
| Agent times out | Too many tool calls | Reduce max iterations |
| AttributeError: NoneType | LLM returns `content: null` | Use `(msg.get("content") or "")` |
| Answer doesn't match | Wrong phrasing | Adjust system prompt |

## Lessons Learned from Benchmark

### 1. Tool Selection Matters

The LLM needs clear guidance on **when** to use each tool. Initially, the agent would sometimes try to answer data-dependent questions (like "how many items") from memory instead of calling `query_api`. The fix was to make the system prompt more explicit:

> "For live data questions (e.g., 'how many items', 'what's the score') → use query_api with GET"

This simple addition dramatically improved tool selection accuracy.

### 2. Authentication Details Are Critical

The `query_api` tool initially failed because I used `X-API-Key` header, but the backend expects `Authorization: Bearer <token>`. This took time to debug because the error message was generic. Lesson: always check the actual authentication mechanism in the backend code, not just assume a standard.

### 3. Handle `content: null` Gracefully

OpenAI-compatible APIs return `content: null` (not missing) when the LLM makes tool calls. Using `msg.get("content", "")` returns `None` instead of `""`, causing `AttributeError` later. The fix: `msg.get("content") or ""`.

### 4. Rate Limiting Affects Reliability

OpenRouter's free tier (50 requests/day) is convenient for development but unreliable for evaluation. The agent would pass a question one minute and fail the next due to rate limiting. For serious evaluation, Qwen Code API (1000 requests/day) or a paid key is essential.

### 5. Source Extraction Is Tricky

The regex-based source extraction (`Source: \S+`) works well when the LLM follows instructions. However, some LLMs format sources differently. A more robust approach would be to ask the LLM to include source in a structured field or use a separate tool call to report the source.

### 6. Token Limits Matter

Long file contents can exceed the LLM's context window or cause truncated responses. The `read_file` tool should ideally limit the content returned or implement pagination for large files.

## Final Evaluation Score

**Local benchmark results (with Qwen Code API):**

| Question | Topic | Expected Tool | Status |
|----------|-------|---------------|--------|
| 0 | Branch protection (wiki) | read_file | ✅ PASSED |
| 1 | SSH connection (wiki) | read_file | ✅ PASSED |
| 2 | Backend framework | read_file | ✅ PASSED |
| 3 | API router modules | list_files + read_file | ⚠️ Iteration limit |
| 4 | Item count | query_api | ⏳ Not reached |
| 5 | Status code without auth | query_api | ⏳ Not reached |
| 6 | Bug diagnosis (ZeroDivisionError) | query_api + read_file | ⏳ Not reached |
| 7 | Bug diagnosis (TypeError) | query_api + read_file | ⏳ Not reached |
| 8 | Request lifecycle (reasoning) | read_file | ⏳ Not reached |
| 9 | ETL idempotency (reasoning) | read_file | ⏳ Not reached |

**Score: 3/10 passed**

**Analysis:**
- Questions 0-2 pass consistently - the agent effectively uses `list_files` and `read_file` for wiki and source code questions
- Question 3 fails due to iteration limits - reading 5 router files requires more than 15 iterations when the LLM calls one tool per iteration
- Questions 4-9 are not reached because the benchmark stops at the first failure

**Limitations:**
1. **Single tool per iteration**: Qwen calls one tool at a time, not batching multiple tool calls
2. **Iteration limit**: 15 iterations is insufficient for multi-file analysis questions
3. **Path confusion**: The LLM sometimes constructs wrong paths despite hints in tool results

**Potential fixes:**
- Increase max_iterations to 25-30 for complex questions
- Modify tool schemas to encourage batching (e.g., "read multiple files in one call")
- Use a more efficient LLM model (Qwen3-Coder-Flash instead of Plus)
- Implement a "read multiple files" tool that batches file reads

## Extension Plan

Future improvements:
- Add more tools (e.g., `search_code` for grep-like search)
- Improve source extraction with better parsing
- Handle multi-step reasoning more explicitly
- Add caching for repeated file reads
- Implement content truncation for large files
