# claude-stats

A Claude Code skill that shows your token usage and estimated API cost, broken down by project and over time.

## Install

```bash
git clone https://github.com/Albschu/claude-stats.git ~/.claude/plugins/claude-stats
ln -sf ~/.claude/plugins/claude-stats/skills/claude-stats/SKILL.md ~/.claude/commands/claude-stats.md
```

Restart Claude Code after installing.

## Usage

```
/claude-stats                  # last 30 days summary + timeline
/claude-stats detailed         # full per-project breakdown, all time
/claude-stats --days 7         # last 7 days
/claude-stats detailed --days 7
```

## Update pricing

Edit `COST_PER_MTOK` in `claude_stats.py` when Anthropic changes rates.

## Requirements

Python 3.9+ (stdlib only, no pip install needed).
