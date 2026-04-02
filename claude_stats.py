import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
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


def aggregate_data(
    claude_dir: Path,
    home: Path | None = None,
    days: int | None = None,
) -> tuple[dict, dict, int]:
    """Scan all session JSONL files and aggregate tokens by project and by date.

    Returns:
        projects: dict[dir_name -> usage_dict with keys input/output/cache_creation/cache_read/full_path/short_name]
        daily:    dict[date_str -> usage_dict with keys input/output/cache_creation/cache_read]
        skipped:  total count of messages that had no timestamp
    """
    if home is None:
        home = Path.home()

    cutoff = None
    if days is not None:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)

    projects: dict = defaultdict(lambda: {
        "input": 0, "output": 0, "cache_creation": 0, "cache_read": 0,
        "full_path": "", "short_name": "",
    })
    daily: dict = defaultdict(lambda: {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0})
    total_skipped = 0

    projects_dir = claude_dir / "projects"
    if not projects_dir.exists():
        return {}, {}, 0

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        full_path, short_name = extract_project_name(project_dir.name, home)
        for session_file in project_dir.glob("*.jsonl"):
            entries, skipped = parse_session_file(session_file)
            total_skipped += skipped
            for timestamp_str, usage in entries:
                try:
                    ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                except ValueError:
                    total_skipped += 1
                    continue
                if cutoff and ts < cutoff:
                    continue
                date_key = ts.strftime("%Y-%m-%d")
                input_tok = usage.get("input_tokens", 0) or 0
                output_tok = usage.get("output_tokens", 0) or 0
                cache_create = usage.get("cache_creation_input_tokens", 0) or 0
                cache_read = usage.get("cache_read_input_tokens", 0) or 0
                projects[project_dir.name]["input"] += input_tok
                projects[project_dir.name]["output"] += output_tok
                projects[project_dir.name]["cache_creation"] += cache_create
                projects[project_dir.name]["cache_read"] += cache_read
                projects[project_dir.name]["full_path"] = full_path
                projects[project_dir.name]["short_name"] = short_name
                daily[date_key]["input"] += input_tok
                daily[date_key]["output"] += output_tok
                daily[date_key]["cache_creation"] += cache_create
                daily[date_key]["cache_read"] += cache_read

    # Filter out projects with zero tokens
    projects = {k: v for k, v in projects.items() if total_tokens(v) > 0}
    return dict(projects), dict(daily), total_skipped


def render_summary(projects: dict, daily: dict, skipped: int, days: int = 30) -> str:
    lines = []
    lines.append("━" * 52)
    lines.append(f"  Claude Code Usage  ·  last {days} days")
    lines.append("━" * 52)
    lines.append("")

    # Timeline
    lines.append("  Daily Activity")
    if daily:
        sorted_days = sorted(daily.keys())[-days:]
        max_tok = max(total_tokens(daily[d]) for d in sorted_days) or 1
        bar_width = 20
        for d in sorted_days:
            tok = total_tokens(daily[d])
            bars = round(tok / max_tok * bar_width)
            bar = "█" * bars + "░" * (bar_width - bars)
            lines.append(f"  {d}  {bar}  {fmt_tokens(tok)}")
    else:
        lines.append("  (no data)")
    lines.append("")

    # Top projects
    lines.append("  Top Projects")
    col_w = 24
    sorted_projects = sorted(projects.values(), key=calc_cost, reverse=True)
    top5 = sorted_projects[:5]
    others = sorted_projects[5:]

    lines.append(f"  {'Project':<{col_w}} {'Tokens':>8}  {'Cost':>7}")
    lines.append(f"  {'─' * col_w} {'─' * 8}  {'─' * 7}")

    for p in top5:
        tok = total_tokens(p)
        cost = calc_cost(p)
        name = p["short_name"] or p["full_path"] or "(unknown)"
        lines.append(f"  {name:<{col_w}} {fmt_tokens(tok):>8}  {fmt_cost(cost):>7}")

    if others:
        other_tok = sum(total_tokens(p) for p in others)
        other_cost = sum(calc_cost(p) for p in others)
        label = f"··· {len(others)} others"
        lines.append(f"  {label:<{col_w}} {fmt_tokens(other_tok):>8}  {fmt_cost(other_cost):>7}")

    lines.append(f"  {'─' * col_w} {'─' * 8}  {'─' * 7}")
    all_tok = sum(total_tokens(p) for p in sorted_projects)
    all_cost = sum(calc_cost(p) for p in sorted_projects)
    lines.append(f"  {'Total':<{col_w}} {fmt_tokens(all_tok):>8}  {fmt_cost(all_cost):>7}")

    if skipped:
        lines.append(f"\n  ({skipped} messages skipped — no usage data)")

    return "\n".join(lines)
