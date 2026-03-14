# Task 1 Plan: Call an LLM from Code

## LLM Provider and Model

- **Provider**: OpenRouter
- **Model**: `meta-llama/llama-3.3-70b-instruct:free`
- **API Base**: `https://openrouter.ai/api/v1`
- **API Key**: Stored in `.env.agent.secret` (LLM_API_KEY)

> Note: OpenRouter free tier has 50 requests/day limit. Testing should be done carefully.

## Agent Structure

### Components

1. **CLI Argument Parsing**
   - Use `sys.argv` to get the question from command line
   - Validate that exactly one argument is provided
   - Show usage message on stderr if invalid

2. **Environment Configuration**
   - Use `python-dotenv` to load `.env.agent.secret`
   - Read `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`

3. **LLM API Client**
   - Use `openai` Python package (OpenRouter supports OpenAI-compatible API)
   - Create `OpenAI` client with custom `base_url` and `api_key`
   - Send chat completion request with user question

4. **Response Formatting**
   - Extract answer from LLM response
   - Build JSON object: `{"answer": "...", "tool_calls": []}`
   - Output to stdout as single-line JSON

5. **Error Handling**
   - Missing argument → print usage to stderr, exit 1
   - Missing env vars → print error to stderr, exit 1
   - API request failure → print error to stderr, exit 1
   - Timeout (>60s) → let it fail naturally or add explicit timeout

### Data Flow

```
Command line → Parse argument → Load env → Call LLM API → Parse response → JSON to stdout
```

## Libraries

- `sys` — command-line arguments
- `json` — JSON output
- `os` — environment access
- `python-dotenv` — load `.env.agent.secret`
- `openai` — LLM API client (OpenAI-compatible)

## Testing Strategy

Create one regression test (`tests/test_task1.py`):
- Run `agent.py "test question"` as subprocess
- Parse stdout as JSON
- Assert `answer` field exists and is non-empty string
- Assert `tool_calls` field exists and is empty list
- Assert exit code is 0

## Implementation Steps

1. Create `.env.agent.secret` (already done)
2. Write `agent.py` with basic structure
3. Test manually with a sample question
4. Create `tests/test_task1.py`
5. Run test to verify
6. Create `AGENT.md` documentation
