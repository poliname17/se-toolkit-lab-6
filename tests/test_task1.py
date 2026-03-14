#!/usr/bin/env python3
"""Regression test for Task 1: Call an LLM from Code.

Verifies that agent.py:
- Exits with code 0
- Outputs valid JSON
- Has 'answer' field (non-empty string)
- Has 'tool_calls' field (empty list)
"""

import json
import subprocess
import sys
from pathlib import Path


def test_agent_basic():
    """Test that agent.py returns valid JSON with required fields."""
    # Run agent.py with a simple question
    agent_path = Path(__file__).parent.parent / "agent.py"
    result = subprocess.run(
        [sys.executable, str(agent_path), "What is 2 + 2?"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    
    # Check exit code
    assert result.returncode == 0, f"Agent exited with code {result.returncode}: {result.stderr}"
    
    # Check stdout is not empty
    assert result.stdout.strip(), "Agent produced no output"
    
    # Check output is valid JSON
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Agent output is not valid JSON: {result.stdout[:200]}") from e
    
    # Check 'answer' field exists and is non-empty
    assert "answer" in data, "Missing 'answer' field in output"
    assert isinstance(data["answer"], str), "'answer' should be a string"
    assert len(data["answer"].strip()) > 0, "'answer' should not be empty"
    
    # Check 'tool_calls' field exists and is empty list
    assert "tool_calls" in data, "Missing 'tool_calls' field in output"
    assert isinstance(data["tool_calls"], list), "'tool_calls' should be a list"
    assert len(data["tool_calls"]) == 0, "'tool_calls' should be empty for Task 1"


if __name__ == "__main__":
    test_agent_basic()
    print("All tests passed!")
