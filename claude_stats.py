import json
from pathlib import Path


def extract_project_name(dir_name: str, home: Path) -> tuple[str, str]:
    """Convert '-home-albert-GitHub-noxtcore' -> ('GitHub/noxtcore', 'noxtcore')."""
    # Build the home prefix as it appears in the dir name: /home/albert -> -home-albert
    home_prefix = str(home).replace("/", "-")
    name = dir_name.lstrip("-")
    home_key = home_prefix.lstrip("-")
    if name.startswith(home_key):
        name = name[len(home_key):].lstrip("-")
    if not name:
        return "", ""
    full_path = name.replace("-", "/")
    short_name = name.split("-")[-1]
    return full_path, short_name


def parse_session_file(session_file: Path) -> tuple[list, int]:
    """Parse a session JSONL file.

    Returns (results, skipped) where results is a list of (timestamp_str, usage_dict)
    for complete assistant messages (those with output_tokens present).
    """
    results = []
    skipped = 0
    try:
        with open(session_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = entry.get("message", {})
                if msg.get("role") != "assistant":
                    continue
                usage = msg.get("usage", {})
                if not usage.get("output_tokens"):
                    continue
                timestamp = entry.get("timestamp")
                if timestamp:
                    results.append((timestamp, usage))
                else:
                    skipped += 1
    except (IOError, OSError):
        pass
    return results, skipped


# Cost per million tokens (update when Anthropic changes pricing)
COST_PER_MTOK = {
    "input": 3.00,
    "output": 15.00,
    "cache_creation": 3.75,
    "cache_read": 0.30,
}


def calc_cost(usage: dict) -> float:
    """Calculate USD cost for a usage dict with keys: input, output, cache_creation, cache_read."""
    return (
        usage["input"] / 1e6 * COST_PER_MTOK["input"]
        + usage["output"] / 1e6 * COST_PER_MTOK["output"]
        + usage["cache_creation"] / 1e6 * COST_PER_MTOK["cache_creation"]
        + usage["cache_read"] / 1e6 * COST_PER_MTOK["cache_read"]
    )


def total_tokens(usage: dict) -> int:
    return usage["input"] + usage["output"] + usage["cache_creation"] + usage["cache_read"]


def fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1e6:.1f}M"
    if n >= 1_000:
        return f"{n / 1e3:.0f}K"
    return str(n)


def fmt_cost(c: float) -> str:
    return f"${c:.2f}"
