#!/usr/bin/env python3
"""Agent CLI that calls an LLM and returns a structured JSON answer.

Usage:
    uv run agent.py "What does REST stand for?"

Output:
    {"answer": "...", "tool_calls": []}
"""

import json
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI


def load_config() -> dict:
    """Load LLM configuration from .env.agent.secret.
    
    Returns:
        dict with api_key, api_base, and model.
    
    Exits:
        1 if required environment variables are missing.
    """
    # Load from .env.agent.secret in project root
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


def call_llm(question: str, config: dict) -> str:
    """Call the LLM API with the user's question.
    
    Args:
        question: The user's question string.
        config: Configuration dict with api_key, api_base, model.
    
    Returns:
        The LLM's text response.
    
    Raises:
        Exception: If the API call fails.
    """
    client = OpenAI(
        api_key=config["api_key"],
        base_url=config["api_base"],
    )
    
    response = client.chat.completions.create(
        model=config["model"],
        messages=[
            {"role": "system", "content": "You are a helpful assistant. Answer concisely."},
            {"role": "user", "content": question},
        ],
        temperature=0.7,
        max_tokens=500,
    )
    
    return response.choices[0].message.content


def main():
    """Main entry point."""
    # Parse command-line argument
    if len(sys.argv) != 2:
        print("Usage: uv run agent.py \"<question>\"", file=sys.stderr)
        sys.exit(1)
    
    question = sys.argv[1]
    
    # Load configuration
    config = load_config()
    
    # Call LLM
    try:
        answer = call_llm(question, config)
    except Exception as e:
        print(f"Error calling LLM: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Build output structure
    output = {
        "answer": answer,
        "tool_calls": [],
    }
    
    # Output JSON to stdout
    print(json.dumps(output))


if __name__ == "__main__":
    main()
