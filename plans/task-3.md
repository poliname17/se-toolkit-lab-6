# Task 3 Plan: The System Agent with query_api Tool

## Overview

Extend the agent from Task 2 with a new `query_api` tool that can call the deployed backend API. This enables the agent to answer:
1. **Static system facts** — framework, ports, status codes (from source code)
2. **Data-dependent queries** — item count, scores, analytics (from live API)
3. **Bug diagnosis** — query API, get error, read source code to find bug

## Tool Schema: query_api

### Function Definition

```json
{
  "type": "function",
  "function": {
    "name": "query_api",
    "description": "Call the deployed backend API and return the response",
    "parameters": {
      "type": "object",
      "properties": {
        "method": {
          "type": "string",
          "description": "HTTP method (GET, POST, PUT, DELETE, etc.)"
        },
        "path": {
          "type": "string",
          "description": "API path (e.g., /items/, /analytics/completion-rate)"
        },
        "body": {
          "type": "string",
          "description": "Optional JSON request body for POST/PUT requests"
        }
      },
      "required": ["method", "path"]
    }
  }
}
```

### Implementation

```python
def query_api(method: str, path: str, body: str = None) -> str:
    """Call the deployed backend API.
    
    Uses LMS_API_KEY from .env.docker.secret for authentication.
    Uses AGENT_API_BASE_URL (default: http://localhost:42002) as base URL.
    
    Returns: JSON string with status_code and body.
    """
```

## Authentication

The `query_api` tool needs to authenticate with the backend using `LMS_API_KEY`.

**Important:** Two distinct keys:
- `LLM_API_KEY` (in `.env.agent.secret`) — authenticates with LLM provider
- `LMS_API_KEY` (in `.env.docker.secret`) — authenticates with backend API

The tool will:
1. Load `LMS_API_KEY` from `.env.docker.secret`
2. Load `AGENT_API_BASE_URL` (optional, defaults to `http://localhost:42002`)
3. Include the key in the `X-API-Key` header for all requests

## Environment Variables

The agent must read configuration from environment variables (not hardcoded):

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API key for query_api auth | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Base URL for query_api (optional) | `.env.docker.secret` or default |

**Critical:** The autochecker injects its own values. Never hardcode URLs or keys.

## System Prompt Update

The system prompt needs to guide the LLM on **when to use which tool**:

```
You have access to these tools:
1. list_files - List files in a directory (use to discover files)
2. read_file - Read file contents (use for wiki docs, source code)
3. query_api - Call the backend API (use for live data, status codes, analytics)

Strategy:
- For wiki/documentation questions → use list_files, then read_file
- For source code questions → use list_files to find files, then read_file
- For live data questions (how many items, what's the score) → use query_api
- For status code questions → use query_api without auth header to see 401/403
- For bug diagnosis → use query_api to see the error, then read_file to find the bug
```

## Agentic Loop

No changes needed — the loop remains the same. Just add `query_api` to the tool schemas and functions.

## Implementation Steps

1. Add `query_api` tool implementation in `agent.py`
2. Add `query_api` to `TOOL_SCHEMAS` and `TOOL_FUNCTIONS`
3. Update system prompt to guide tool selection
4. Load `LMS_API_KEY` and `AGENT_API_BASE_URL` from `.env.docker.secret`
5. Test with benchmark questions
6. Update `AGENT.md` documentation
7. Run `run_eval.py` and iterate until passing

## Expected Failures and Iterations

**Likely first failures:**
1. **Wrong tool for data questions** — LLM tries to read_file instead of query_api
   - Fix: Improve system prompt to emphasize query_api for live data
2. **Authentication errors** — Missing or wrong API key
   - Fix: Ensure LMS_API_KEY is loaded correctly (use Bearer token auth)
3. **Wrong API path** — Missing trailing slash or wrong endpoint
   - Fix: Improve tool description with examples
4. **NoneType errors** — LLM returns `content: null` with tool calls
   - Fix: Use `(msg.get("content") or "")` instead of `msg.get("content", "")`
5. **Rate limiting on OpenRouter** — Free tier (50 req/day) gets rate-limited
   - Fix: Use Qwen Code API on VM (1000 req/day) or add own OpenRouter key

## Initial Score and Iterations

**First run results:**
- Question 0 (branch protection): PASSED when LLM responds fully
- Issues: OpenRouter free tier rate limiting causes incomplete responses

**Iteration strategy:**
1. Set up Qwen Code API on VM for reliable access
2. Update `.env.agent.secret` with Qwen API credentials
3. Re-run benchmark and fix remaining failures

## Testing Strategy

Run the benchmark after each change:

```bash
uv run run_eval.py
```

Fix one failing question at a time, starting with the simplest (wiki lookup, then system facts, then data queries, then bug diagnosis).
