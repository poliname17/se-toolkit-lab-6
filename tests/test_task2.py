#!/usr/bin/env python3
"""Regression tests for Task 2: Agentic Loop with Tools.

Tests verify that the agent:
- Uses list_files to discover wiki files
- Uses read_file to read documentation
- Includes source references in the answer
"""

import json
import subprocess
import sys
from pathlib import Path


def test_merge_conflict_question():
    """Test that agent uses read_file and includes wiki/git-workflow.md in source.
    
    Question: "How do you resolve a merge conflict?"
    Expected:
    - tool_calls should include read_file
    - source should contain wiki/git-workflow.md
    """
    agent_path = Path(__file__).parent.parent / "agent.py"
    result = subprocess.run(
        [sys.executable, str(agent_path), "How do you resolve a merge conflict?"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    
    # Check exit code
    assert result.returncode == 0, f"Agent exited with code {result.returncode}: {result.stderr}"
    
    # Parse JSON
    data = json.loads(result.stdout)
    
    # Check required fields
    assert "answer" in data, "Missing 'answer' field"
    assert "source" in data, "Missing 'source' field"
    assert "tool_calls" in data, "Missing 'tool_calls' field"
    
    # Check answer is non-empty
    assert len(data["answer"].strip()) > 0, "'answer' should not be empty"
    
    # Check source contains wiki/git-workflow.md
    assert "wiki/git-workflow.md" in data["source"], (
        f"Source should reference wiki/git-workflow.md, got: {data['source']}"
    )
    
    # Check tool_calls includes read_file
    tools_used = [tc.get("tool") for tc in data["tool_calls"]]
    assert "read_file" in tools_used, (
        f"Expected read_file in tool_calls, got: {tools_used}"
    )


def test_list_files_question():
    """Test that agent uses list_files for directory listing questions.
    
    Question: "What files are in the wiki?"
    Expected:
    - tool_calls should include list_files with path="wiki"
    """
    agent_path = Path(__file__).parent.parent / "agent.py"
    result = subprocess.run(
        [sys.executable, str(agent_path), "What files are in the wiki?"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    
    # Check exit code
    assert result.returncode == 0, f"Agent exited with code {result.returncode}: {result.stderr}"
    
    # Parse JSON
    data = json.loads(result.stdout)
    
    # Check required fields
    assert "answer" in data, "Missing 'answer' field"
    assert "tool_calls" in data, "Missing 'tool_calls' field"
    
    # Check answer is non-empty
    assert len(data["answer"].strip()) > 0, "'answer' should not be empty"
    
    # Check tool_calls includes list_files
    tools_used = [tc.get("tool") for tc in data["tool_calls"]]
    assert "list_files" in tools_used, (
        f"Expected list_files in tool_calls, got: {tools_used}"
    )
    
    # Check list_files was called with path="wiki" or similar
    list_files_calls = [
        tc for tc in data["tool_calls"]
        if tc.get("tool") == "list_files"
    ]
    assert len(list_files_calls) > 0, "list_files was not called"
    
    # At least one list_files call should have wiki in the path
    wiki_paths = [
        tc for tc in list_files_calls
        if "wiki" in tc.get("args", {}).get("path", "")
    ]
    assert len(wiki_paths) > 0, (
        f"Expected list_files to be called with wiki path, got: {list_files_calls}"
    )


if __name__ == "__main__":
    print("Running test_merge_conflict_question...")
    test_merge_conflict_question()
    print("  PASSED")
    
    print("Running test_list_files_question...")
    test_list_files_question()
    print("  PASSED")
    
    print("\nAll Task 2 tests passed!")
