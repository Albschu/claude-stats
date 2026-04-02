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


import pytest
from claude_stats import calc_cost, total_tokens, fmt_tokens, fmt_cost

def test_calc_cost_input_only():
    usage = {"input": 1_000_000, "output": 0, "cache_creation": 0, "cache_read": 0}
    assert calc_cost(usage) == pytest.approx(3.00)

def test_calc_cost_output_only():
    usage = {"input": 0, "output": 1_000_000, "cache_creation": 0, "cache_read": 0}
    assert calc_cost(usage) == pytest.approx(15.00)

def test_calc_cost_cache_creation():
    usage = {"input": 0, "output": 0, "cache_creation": 1_000_000, "cache_read": 0}
    assert calc_cost(usage) == pytest.approx(3.75)

def test_calc_cost_cache_read():
    usage = {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 1_000_000}
    assert calc_cost(usage) == pytest.approx(0.30)

def test_total_tokens():
    usage = {"input": 100, "output": 50, "cache_creation": 200, "cache_read": 10}
    assert total_tokens(usage) == 360

def test_fmt_tokens_millions():
    assert fmt_tokens(1_500_000) == "1.5M"

def test_fmt_tokens_thousands():
    assert fmt_tokens(500_000) == "500K"

def test_fmt_tokens_small():
    assert fmt_tokens(999) == "999"

def test_fmt_tokens_zero():
    assert fmt_tokens(0) == "0"

def test_fmt_cost():
    assert fmt_cost(8.4) == "$8.40"

def test_fmt_cost_zero():
    assert fmt_cost(0.0) == "$0.00"


from claude_stats import aggregate_data

def _make_session(tmp_path, project_dir_name, filename, entries):
    proj_dir = tmp_path / "projects" / project_dir_name
    proj_dir.mkdir(parents=True, exist_ok=True)
    f = proj_dir / filename
    _write_jsonl(f, entries)
    return f

def _assistant_entry(timestamp, input_tok, output_tok, cache_create=0, cache_read=0):
    return {
        "type": "assistant",
        "timestamp": timestamp,
        "message": {
            "role": "assistant",
            "usage": {
                "input_tokens": input_tok,
                "output_tokens": output_tok,
                "cache_creation_input_tokens": cache_create,
                "cache_read_input_tokens": cache_read,
            }
        }
    }

def test_aggregate_sums_by_project(tmp_path):
    home = tmp_path / "home" / "user"
    home.mkdir(parents=True)
    claude_dir = tmp_path / ".claude"
    _make_session(claude_dir, "-home-user-proj-alpha", "s1.jsonl", [
        _assistant_entry("2026-04-01T10:00:00.000Z", 100, 50),
        _assistant_entry("2026-04-01T11:00:00.000Z", 200, 80),
    ])
    projects, daily, skipped = aggregate_data(claude_dir, home=home)
    assert "alpha" in [p["short_name"] for p in projects.values()]
    alpha = next(p for p in projects.values() if p["short_name"] == "alpha")
    assert alpha["input"] == 300
    assert alpha["output"] == 130
    assert skipped == 0

def test_aggregate_sums_by_date(tmp_path):
    home = tmp_path / "home" / "user"
    home.mkdir(parents=True)
    claude_dir = tmp_path / ".claude"
    _make_session(claude_dir, "-home-user-proj-beta", "s1.jsonl", [
        _assistant_entry("2026-04-01T10:00:00.000Z", 100, 50),
        _assistant_entry("2026-04-02T10:00:00.000Z", 200, 80),
    ])
    projects, daily, skipped = aggregate_data(claude_dir, home=home)
    assert "2026-04-01" in daily
    assert "2026-04-02" in daily
    assert daily["2026-04-01"]["input"] == 100
    assert daily["2026-04-02"]["input"] == 200

def test_aggregate_respects_days_cutoff(tmp_path):
    home = tmp_path / "home" / "user"
    home.mkdir(parents=True)
    claude_dir = tmp_path / ".claude"
    _make_session(claude_dir, "-home-user-proj-gamma", "s1.jsonl", [
        _assistant_entry("2020-01-01T10:00:00.000Z", 999, 999),  # very old, should be excluded
        _assistant_entry("2026-04-01T10:00:00.000Z", 100, 50),
    ])
    projects, daily, skipped = aggregate_data(claude_dir, home=home, days=30)
    gamma = next((p for p in projects.values() if p["short_name"] == "gamma"), None)
    assert gamma is not None
    assert gamma["input"] == 100  # only the recent entry

def test_aggregate_empty_dir(tmp_path):
    home = tmp_path / "home" / "user"
    home.mkdir(parents=True)
    claude_dir = tmp_path / ".claude"
    (claude_dir / "projects").mkdir(parents=True)
    projects, daily, skipped = aggregate_data(claude_dir, home=home)
    assert projects == {}
    assert daily == {}
    assert skipped == 0


from claude_stats import render_summary

def _make_projects(*names):
    """Helper: build a projects dict with synthetic data."""
    projects = {}
    for i, name in enumerate(names):
        projects[f"dir-{name}"] = {
            "input": (i + 1) * 100_000,
            "output": (i + 1) * 20_000,
            "cache_creation": 0,
            "cache_read": 0,
            "full_path": f"GitHub/{name}",
            "short_name": name,
        }
    return projects

def _make_daily(dates):
    """Helper: build a daily dict with 100K tokens each day."""
    return {d: {"input": 80_000, "output": 20_000, "cache_creation": 0, "cache_read": 0} for d in dates}

def test_render_summary_contains_project_names():
    projects = _make_projects("alpha", "beta")
    daily = _make_daily(["2026-04-01", "2026-04-02"])
    output = render_summary(projects, daily, skipped=0, days=30)
    assert "alpha" in output
    assert "beta" in output

def test_render_summary_contains_cost():
    projects = _make_projects("alpha")
    daily = _make_daily(["2026-04-01"])
    output = render_summary(projects, daily, skipped=0, days=30)
    assert "$" in output

def test_render_summary_collapses_others():
    # 7 projects — top 5 shown, 2 collapsed
    projects = _make_projects("a", "b", "c", "d", "e", "f", "g")
    daily = _make_daily(["2026-04-01"])
    output = render_summary(projects, daily, skipped=0, days=30)
    assert "others" in output

def test_render_summary_no_others_when_five_or_fewer():
    projects = _make_projects("a", "b", "c")
    daily = _make_daily(["2026-04-01"])
    output = render_summary(projects, daily, skipped=0, days=30)
    assert "others" not in output

def test_render_summary_shows_skipped_note():
    projects = _make_projects("a")
    daily = _make_daily(["2026-04-01"])
    output = render_summary(projects, daily, skipped=5, days=30)
    assert "5 messages skipped" in output

def test_render_summary_no_skipped_note_when_zero():
    projects = _make_projects("a")
    daily = _make_daily(["2026-04-01"])
    output = render_summary(projects, daily, skipped=0, days=30)
    assert "skipped" not in output
