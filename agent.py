#!/usr/bin/env python3
"""Agent CLI with tools and agentic loop.

Usage:
    uv run agent.py "How do you resolve a merge conflict?"

Output:
    {
      "answer": "...",
      "source": "wiki/git-workflow.md#resolving-merge-conflicts",
      "tool_calls": [...]
    }
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


# Project root for path security
PROJECT_ROOT = Path(__file__).parent


def load_config() -> dict:
    """Load LLM configuration from .env.agent.secret."""
    env_file = os.path.join(os.path.dirname(__file__), ".env.agent.secret")
    load_dotenv(env_file)
    
    api_key = os.getenv("LLM_API_KEY")
    api_base = os.getenv("LLM_API_BASE")
    model = os.getenv("LLM_MODEL")
    
    if not api_key:
        print("Error: LLM_API_KEY not found in .env.agent.secret", file=sys.stderr)
        sys.exit(1)
    if not api_base:
        print("Error: LLM_API_BASE not found in .env.agent.secret", file=sys.stderr)
        sys.exit(1)
    if not model:
        print("Error: LLM_MODEL not found in .env.agent.secret", file=sys.stderr)
        sys.exit(1)
    
    return {
        "api_key": api_key,
        "api_base": api_base,
        "model": model,
    }


def safe_path(relative_path: str) -> Path:
    """Resolve path and ensure it's within project root.
    
    Args:
        relative_path: Path relative to project root.
    
    Returns:
        Absolute path within project root.
    
    Raises:
        ValueError: If path traversal is detected.
    """
    # Normalize the relative path to prevent traversal
    # Remove leading slashes and resolve
    clean_path = relative_path.lstrip("/")
    full_path = (PROJECT_ROOT / clean_path).resolve()
    
    # Ensure the resolved path is within project root
    if not str(full_path).startswith(str(PROJECT_ROOT.resolve())):
        raise ValueError(f"Path traversal detected: {relative_path}")
    
    return full_path


def read_file(path: str) -> str:
    """Read contents of a file from the project repository.
    
    Args:
        path: Relative path from project root.
    
    Returns:
        File contents as string, or error message.
    """
    try:
        safe = safe_path(path)
        if not safe.exists():
            return f"Error: File not found: {path}"
        if not safe.is_file():
            return f"Error: Not a file: {path}"
        return safe.read_text()
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error reading file: {e}"


def list_files(path: str) -> str:
    """List files and directories at a given path.
    
    Args:
        path: Relative directory path from project root.
    
    Returns:
        Newline-separated listing, or error message.
    """
    try:
        safe = safe_path(path)
        if not safe.exists():
            return f"Error: Path not found: {path}"
        if not safe.is_dir():
            return f"Error: Not a directory: {path}"
        
        entries = []
        for entry in sorted(safe.iterdir()):
            suffix = "/" if entry.is_dir() else ""
            entries.append(entry.name + suffix)
        return "\n".join(entries)
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error listing directory: {e}"


# Tool schemas for OpenAI function calling
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read contents of a file from the project repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g., 'wiki/git-workflow.md')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given path",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root (e.g., 'wiki')"
                    }
                },
                "required": ["path"]
            }
        }
    },
]

# Map tool names to implementation functions
TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_files": list_files,
}

# System prompt instructs the LLM on how to use tools
SYSTEM_PROMPT = """You are a helpful assistant that answers questions using the project documentation.

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
Only call tools when you need information. When you have enough information, provide the final answer."""


def call_llm(messages: list, config: dict, tools: list = None) -> dict:
    """Call the LLM API with messages and optional tools.
    
    Args:
        messages: List of message dicts (role, content, etc.)
        config: Configuration dict with api_key, api_base, model
        tools: Optional list of tool schemas
    
    Returns:
        The full response object from the API.
    """
    client = OpenAI(
        api_key=config["api_key"],
        base_url=config["api_base"],
    )
    
    kwargs = {
        "model": config["model"],
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000,
    }
    
    if tools:
        kwargs["tools"] = tools
    
    response = client.chat.completions.create(**kwargs)
    return response


def execute_tool_call(tool_call: dict) -> dict:
    """Execute a single tool call and return the result.
    
    Args:
        tool_call: Tool call object from LLM response
    
    Returns:
        Dict with tool name, args, and result
    """
    func = tool_call["function"]
    tool_name = func["name"]
    
    # Parse arguments
    try:
        args = json.loads(func["arguments"])
    except json.JSONDecodeError:
        args = {}
    
    # Execute the tool
    if tool_name in TOOL_FUNCTIONS:
        result = TOOL_FUNCTIONS[tool_name](**args)
    else:
        result = f"Error: Unknown tool: {tool_name}"
    
    return {
        "tool": tool_name,
        "args": args,
        "result": result,
    }


def main():
    """Main entry point with agentic loop."""
    # Parse command-line argument
    if len(sys.argv) != 2:
        print("Usage: uv run agent.py \"<question>\"", file=sys.stderr)
        sys.exit(1)
    
    question = sys.argv[1]
    
    # Load configuration
    config = load_config()
    
    # Initialize conversation
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    
    # Track all tool calls for output
    tool_calls_log = []
    
    # Agentic loop - max 10 iterations
    max_iterations = 10
    
    for iteration in range(max_iterations):
        # Call LLM with tools
        response = call_llm(messages, config, tools=TOOL_SCHEMAS)
        assistant_message = response.choices[0].message
        
        # Check if LLM wants to call tools
        if hasattr(assistant_message, "tool_calls") and assistant_message.tool_calls:
            # Add assistant message with tool calls to conversation
            messages.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in assistant_message.tool_calls
                ],
            })
            
            # Execute each tool call
            for tool_call in assistant_message.tool_calls:
                # Execute and log
                result = execute_tool_call({
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    }
                })
                tool_calls_log.append(result)
                
                # Add tool result to conversation
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result["result"],
                })
            
            # Continue loop - LLM will process tool results
            continue
        else:
            # LLM provided final answer (no tool calls)
            final_answer = assistant_message.content
            break
    else:
        # Max iterations reached
        final_answer = "I reached the maximum number of tool calls (10) without finding a complete answer."
    
    # Extract source from answer
    source = ""
    answer_text = final_answer
    
    # Look for "Source: " pattern
    import re
    source_match = re.search(r"Source:\s*(\S+)", final_answer)
    if source_match:
        source = source_match.group(1)
        # Remove the source line from the answer
        answer_text = re.sub(r"\n?Source:\s*\S+", "", final_answer).strip()
    
    # Build output structure
    output = {
        "answer": answer_text,
        "source": source,
        "tool_calls": tool_calls_log,
    }
    
    # Output JSON to stdout
    print(json.dumps(output))


if __name__ == "__main__":
    main()
