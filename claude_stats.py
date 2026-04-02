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
