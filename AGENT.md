# Agent Architecture

## Overview

This agent is a Python CLI that answers questions by calling an LLM API with tool support. It implements an agentic loop that can discover and read wiki files to find answers, then returns a structured JSON response with the answer, source reference, and tool call history.

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
                        └─────────────┘
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

## Tools

Two tools are implemented and registered as function-calling schemas:

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

### Path Security

Both tools validate paths to prevent directory traversal attacks:

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

The system prompt instructs the LLM to:

1. Use `list_files` to discover files in the `wiki/` directory
2. Use `read_file` to read relevant wiki files
3. Include a source reference in the format `Source: wiki/filename.md#section-anchor`
4. Only call tools when needed; provide final answer when confident

**Full system prompt:**
```
You are a helpful assistant that answers questions using the project documentation.

You have access to two tools:
1. list_files - List files in a directory
2. read_file - Read the contents of a file

Strategy:
1. Use list_files to discover what files exist in the wiki/ directory
2. Use read_file to read relevant wiki files and find the answer
3. When you find the answer, provide it with a source reference

Source format:
Include the source at the end of your answer like this:
Source: wiki/filename.md#section-anchor

The section anchor should be the heading ID (lowercase, hyphens instead of spaces).

If you're not sure which file to read, start by listing the wiki/ directory.
Only call tools when you need information. When you have enough information, provide the final answer.
```

## Output Format

The agent outputs a single JSON object to stdout:

```json
{
  "answer": "Edit the conflicting file, choose which changes to keep, then stage and commit.",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git-workflow.md\n..."
    },
    {
      "tool": "read_file",
      "args": {"path": "wiki/git-workflow.md"},
      "result": "# Git Workflow\n\n..."
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | The final answer (source line removed) |
| `source` | string | Wiki file reference with section anchor |
| `tool_calls` | array | All tool calls made during the loop |

Each tool call entry has:
- `tool`: tool name
- `args`: arguments passed to the tool
- `result`: the tool's return value

All debug/error output goes to stderr.

## Usage

```bash
# Run with a question
uv run agent.py "How do you resolve a merge conflict?"

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
| Timeout (>60s) | Subprocess timeout, exit 1 |
| Max iterations (10) | Return partial answer with tool calls made |

## Dependencies

- `openai` — LLM API client (OpenAI-compatible)
- `python-dotenv` — Load environment from `.env.agent.secret`
- Standard library: `json`, `os`, `sys`, `re`, `pathlib`

## Testing

Run the regression tests:

```bash
uv run pytest tests/test_task1.py tests/test_task2.py -v
```

Tests verify:
- Basic JSON structure (Task 1)
- Tool usage for documentation questions (Task 2)
- Source reference extraction

## Extension Plan (Task 3)

- Add more tools (e.g., `query_api` to query the backend LMS)
- Improve source extraction with better parsing
- Handle edge cases (empty wiki, ambiguous questions)
