import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from claude_stats import extract_project_name

HOME = Path("/home/albert")

def test_github_project():
    full, short = extract_project_name("-home-albert-GitHub-noxtcore", HOME)
    assert short == "noxtcore"
    assert full == "GitHub/noxtcore"

def test_nested_project():
    full, short = extract_project_name("-home-albert-GitHub-bauteilversagen", HOME)
    assert short == "bauteilversagen"
    assert full == "GitHub/bauteilversagen"

def test_home_dir_only():
    full, short = extract_project_name("-home-albert", HOME)
    assert short == ""
    assert full == ""

def test_deeply_nested():
    full, short = extract_project_name("-home-albert-GitHub-bauteilversagen-sub", HOME)
    assert short == "sub"
    assert full == "GitHub/bauteilversagen/sub"


import json
from claude_stats import parse_session_file

def _write_jsonl(path, entries):
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n")

def test_parse_extracts_complete_messages(tmp_path):
    f = tmp_path / "session.jsonl"
    _write_jsonl(f, [{
        "type": "assistant",
        "timestamp": "2026-04-01T10:00:00.000Z",
        "message": {
            "role": "assistant",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_creation_input_tokens": 200,
                "cache_read_input_tokens": 10,
            }
        }
    }])
    results, skipped = parse_session_file(f)
    assert len(results) == 1
    ts, usage = results[0]
    assert ts == "2026-04-01T10:00:00.000Z"
    assert usage["input_tokens"] == 100
    assert usage["output_tokens"] == 50
    assert skipped == 0

def test_parse_skips_entries_without_output_tokens(tmp_path):
    f = tmp_path / "session.jsonl"
    _write_jsonl(f, [
        # streaming start event — no output_tokens
        {
            "type": "assistant",
            "timestamp": "2026-04-01T10:00:00.000Z",
            "message": {
                "role": "assistant",
                "usage": {"input_tokens": 100, "cache_creation_input_tokens": 500}
            }
        },
        # complete message — has output_tokens
        {
            "type": "assistant",
            "timestamp": "2026-04-01T10:00:01.000Z",
            "message": {
                "role": "assistant",
                "usage": {"input_tokens": 100, "output_tokens": 50, "cache_creation_input_tokens": 500}
            }
        }
    ])
    results, skipped = parse_session_file(f)
    assert len(results) == 1

def test_parse_skips_user_messages(tmp_path):
    f = tmp_path / "session.jsonl"
    _write_jsonl(f, [{
        "type": "user",
        "timestamp": "2026-04-01T10:00:00.000Z",
        "message": {"role": "user", "content": "hello"}
    }])
    results, skipped = parse_session_file(f)
    assert len(results) == 0

def test_parse_handles_missing_file():
    results, skipped = parse_session_file(Path("/nonexistent/file.jsonl"))
    assert results == []
    assert skipped == 0
