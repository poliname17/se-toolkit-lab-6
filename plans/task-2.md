# Task 2 Plan: Implement an Agentic Loop with Tools

## Overview

Extend `agent.py` from Task 1 to support tool calls and an agentic loop. The agent will:
1. Send the user's question to the LLM with tool definitions
2. Execute tool calls returned by the LLM
3. Feed results back to the LLM
4. Repeat until the LLM provides a final answer (or 10 tool calls max)
5. Output JSON with `answer`, `source`, and `tool_calls`

## Tool Schemas

Define two tools using OpenAI function-calling format:

### `read_file`
```json
{
  "type": "function",
  "function": {
    "name": "read_file",
    "description": "Read contents of a file from the project repository",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {"type": "string", "description": "Relative path from project root"}
      },
      "required": ["path"]
    }
  }
}
```

### `list_files`
```json
{
  "type": "function",
  "function": {
    "name": "list_files",
    "description": "List files and directories at a given path",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {"type": "string", "description": "Relative directory path from project root"}
      },
      "required": ["path"]
    }
  }
}
```

## Agentic Loop Logic

```
messages = [system_prompt, user_question]
tool_calls_log = []
max_iterations = 10

for i in range(max_iterations):
    response = call_llm(messages, tools)
    
    if response has tool_calls:
        for each tool_call:
            execute tool
            append result to tool_calls_log
            add tool_call and result to messages
    else:
        # LLM provided final answer
        break

extract answer and source from final response
output JSON
```

**Tracking:**
- `messages` list accumulates the conversation (user, assistant, tool roles)
- `tool_calls_log` tracks all tool calls for the output JSON
- Counter limits to 10 iterations

## Path Security

Prevent directory traversal attacks:

```python
PROJECT_ROOT = Path(__file__).parent

def safe_path(relative_path: str) -> Path:
    """Resolve path and ensure it's within project root."""
    full_path = (PROJECT_ROOT / relative_path).resolve()
    if not str(full_path).startswith(str(PROJECT_ROOT)):
        raise ValueError(f"Path traversal detected: {relative_path}")
    return full_path
```

Both `read_file` and `list_files` will use this validation.

## System Prompt Strategy

The system prompt will instruct the LLM to:
1. Use `list_files` to discover files in the `wiki/` directory
2. Use `read_file` to read relevant wiki files
3. Include a source reference in the format `wiki/filename.md#section-anchor`
4. Only call tools when needed; provide final answer when confident

## Extracting Source

The system prompt will ask the LLM to include the source in a specific format. Options:
1. Ask LLM to include source in a structured way (e.g., "Source: wiki/file.md#section")
2. Parse the final answer to extract the source reference
3. Use a separate field in the response

**Approach:** Include instructions in the system prompt to format the source as `Source: <path>#<anchor>` at the end of the answer. Parse this from the final response.

## Implementation Steps

1. Add tool implementation functions (`read_file`, `list_files`)
2. Add tool schema definitions
3. Implement the agentic loop in `main()`
4. Update JSON output to include `source` and populated `tool_calls`
5. Update system prompt
6. Update `AGENT.md` documentation
7. Write 2 regression tests

## Dependencies

No new dependencies needed — uses standard library `pathlib` for path handling.
