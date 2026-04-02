---
name: claude-stats
description: Show Claude Code token usage and estimated API cost broken down by project and timeline. Handles /claude-stats and /claude-stats detailed.
---

Run the following command and display the output **verbatim** — do not summarize, reformat, or add commentary unless the command fails.

Parse the user's invocation for flags:
- `detailed` anywhere in the message → add `--detailed`
- `--days N` or `last N days` → add `--days N`

**Default (last 30 days):**
```bash
python3 ~/.claude/plugins/claude-stats/claude_stats.py
```

**Detailed (all time):**
```bash
python3 ~/.claude/plugins/claude-stats/claude_stats.py --detailed
```

**With day filter:**
```bash
python3 ~/.claude/plugins/claude-stats/claude_stats.py [--detailed] --days N
```

If the command exits with an error, show the error message and suggest running:
```bash
ls ~/.claude/plugins/claude-stats/
```
to verify the plugin is installed correctly.
