# Quick Start Guide - Claude Usage Tracker

## 30-Second Setup

Run from the project root:

```bash
# 1. Run installer
bash usage-tracker/install.sh

# 2. Test it
python3 usage-tracker/claude-usage-tracker.py --status-bar
```

That's it. No verbose logging to enable — the tracker reads Claude Code's session files in `~/.claude/projects/` directly.

---

## Quick Commands

All commands run from the project root:

### Status (one-line)
```bash
python3 usage-tracker/claude-usage-tracker.py --status-bar             # Sonnet only
python3 usage-tracker/claude-usage-tracker.py --status-bar --all-models # All three models
python3 usage-tracker/claude-usage-tracker.py --model haiku --status-bar # Haiku only
```

### Full Report
```bash
python3 usage-tracker/claude-usage-tracker.py                # Sonnet
python3 usage-tracker/claude-usage-tracker.py --all-models   # All models
```

### Continuous Monitoring
```bash
python3 usage-tracker/claude-usage-tracker.py --monitor                                        # Sonnet, 5 min
python3 usage-tracker/claude-usage-tracker.py --monitor --all-models                           # All models
python3 usage-tracker/claude-usage-tracker.py --monitor --interval 300                         # 5 min refresh (default)
python3 usage-tracker/claude-usage-tracker.py --monitor --interval 30                          # 30s refresh
python3 usage-tracker/claude-usage-tracker.py --monitor --all-models --interval 300
python3 usage-tracker/claude-usage-tracker.py --monitor --all-models --active-only             # Hide idle models
```

### Calibrate Limits
```bash
python3 usage-tracker/claude-usage-tracker.py --limits   # show current limits

# Calibrate from claude.ai/settings/usage screenshot:
python3 usage-tracker/claude-usage-tracker.py --calibrate \
  --session-pct 27 --weekly-all-pct 3 --session-reset "1h 48m" --weekly-all-reset "fri:08"

# JSON output (for scripts / AI assistants):
python3 usage-tracker/claude-usage-tracker.py --json --all-models
```

Data is stored in `~/.claude/usage-tracker/` (shared across all projects). See [CALIBRATE.md](CALIBRATE.md) for details.

### Calibrate Session Reset Time
```bash
# When you start a fresh session:
python3 usage-tracker/claude-usage-tracker.py --mark-session-start

# When claude.ai/settings/usage shows a known "Resets in X" time, store it:
python3 usage-tracker/claude-usage-tracker.py --set-session-reset "4h 50m"
# Accepts: "4h 50m", "4:50", or plain minutes ("290")
# Header shows (calibrated) vs (approx) — running monitor picks up changes within 1 second
```

### Via Makefile
```bash
make -C usage-tracker report           # View report
make -C usage-tracker status           # Check status
make -C usage-tracker monitor          # Monitor (60s)
make -C usage-tracker monitor-fast     # Monitor (10s)
```

---

## VS Code Task Integration

Run the monitor automatically every time you open the workspace.

**Step 1** — `Ctrl + Shift + P` → type `Tasks: Open User Tasks` → press Enter

**Step 2** — A **"Select a Task Template"** dropdown appears → click **Others**

**Step 3** — If you already have tasks, add the task entries below to your existing `tasks` array. If the file is empty or new, use this content:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Claude Usage Monitor",
      "type": "shell",
      "command": "python3",
      "args": [
        "${workspaceFolder}/usage-tracker/claude-usage-tracker.py",
        "--monitor",
        "--all-models",
        "--interval",
        "300"
      ],
      "isBackground": true,
      "runOptions": { "runOn": "folderOpen" },
      "presentation": {
        "echo": true,
        "reveal": "always",
        "focus": false,
        "panel": "dedicated"
      },
      "problemMatcher": []
    }
  ]
}
```

**Step 4** — Save (`Ctrl + S`), then run it:
`Ctrl + Shift + P` → `Tasks: Run Task` → **Claude Usage Monitor**

**Optional keyboard shortcut** — add to `keybindings.json`:
```json
{
  "key": "ctrl+shift+u",
  "command": "workbench.action.tasks.runTask",
  "args": "Claude Usage Monitor"
}
```

---

## Understanding the Output

### Status Bar
```
─── 16:42:17 UTC ─── Session: 1h 33m elapsed  ·  3h 27m until reset  ·  5h (calibrated)
🟢🟢  All Models    │   83.6K ss │   2.34M wk │ Sess~:  10.0% │ Week~:  10.4% (cfg)
🟢🟢  Claude Haiku  │   18.6K ss │  278.8K wk │ Sess~:   1.6% │ Week~:   4.6% (cfg)
🟢🟡  Claude Sonnet │   65.0K ss │   2.06M wk │ Sess~:   5.8% │ Week~:  28.2% (cfg)
🔵🔵  Claude Opus   │  (no usage this period)
   Weekly resets: All Models in 16h 25m · Sonnet in 165h 25m
```

| Part | Meaning |
|------|---------|
| 1st circle | Session usage: 🔵 0% · 🟢 >0–50% · 🟡 50–75% · 🟠 75–90% · 🔴 90–99% · ⚫ 99%+ |
| 2nd circle | Weekly usage: same color scale |
| `83.6K ss` | Tokens used in last ~5h (session window) |
| `2.34M wk` | Tokens used this week |
| `Sess~: 10.0%` | % of **shared** session pool used (all models combined) |
| `Week~: 10.4%` | % of weekly limit used |
| `(X left)` | Remaining tokens — shown only at 🟠 75%+ for session (All Models row) and weekly |
| `(calibrated)` / `(approx)` | Session reset: stored via `--set-session-reset` vs. estimated as now − 5h |
| Weekly resets footer | Countdown to next reset for All Models and Sonnet weekly windows |
| `(cfg)` / `(est)` | `limits.json` loaded vs. using built-in defaults |

---

## Troubleshooting

### "Session: 0.0%"
Normal if no Claude Code API calls have been made in the current session (~5h rolling window). Use any slash command or run a task from the agent, then re-check.

### No `~/.claude/projects/` directory
Claude Code CLI is not installed or hasn't been run yet. Install it from [claude.ai/code](https://claude.ai/code).

---

## Real Limits Reference

**Note on limits:** Usage counts are accurate (read directly from JSONL files). The limits are estimates — Anthropic does not publish exact token budgets. Check [claude.ai/settings/usage](https://claude.ai/settings/usage) for live percentages to help calibrate your `limits.json`.

Limits vary by plan and are not published by Anthropic. Calibrate your personal limits in `limits.json` using the live percentages at [claude.ai/settings/usage](https://claude.ai/settings/usage). See [SETUP.md](SETUP.md) for calibration instructions.

---

## Full Documentation

For complete setup and advanced options, see [`SETUP.md`](SETUP.md).
