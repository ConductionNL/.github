# Claude Usage Tracker Setup Guide

Monitor Claude token usage directly in VS Code with real-time status indicators and notifications. Supports **Haiku, Sonnet, and Opus** models.

**All commands run from the project root.**

## How It Works

The Claude Code extension writes full API responses (including token counts) to `~/.claude/projects/**/*.jsonl` as you work. The tracker reads those files directly — no verbose logging, no extra configuration.

**What gets tracked:** every Claude Code API call made through VS Code (slash commands like `/opsx-apply`, agent tasks, inline chat). The tracker shows the last ~5 hours (approximating Anthropic's 5h rolling session window) and this week's running total.

---

## Prerequisites

- **Python 3.8+**
- **Claude Code** extension installed in VS Code and signed in

Verify Claude Code is working:
```bash
ls ~/.claude/projects/    # should list project directories after first use
```

---

## Step 1: Install Tracker Script

```bash
bash .claude/usage-tracker/install.sh
```

This will:
- ✅ Create log storage directory (`.claude/usage-tracker/logs/`, git-ignored)
- ✅ Make scripts executable
- ✅ Create a symlink at `~/.local/bin/claude-usage-tracker`
- ✅ Self-test the configuration

---

## Step 2: Test It

```bash
# Quick one-line status (Sonnet)
python3 .claude/usage-tracker/claude-usage-tracker.py --status-bar

# All three models at once
python3 .claude/usage-tracker/claude-usage-tracker.py --status-bar --all-models

# Full report
python3 .claude/usage-tracker/claude-usage-tracker.py
```

If you see `Today: 0.0%`, that's normal until you make Claude Code API calls today. The weekly total should show data if you've used Claude Code this week.

Output shows `(cfg)` if your limits are configured, or `(est)` if using built-in defaults. `Session~` = last 5h; `Week~` = since Mon UTC — both are approximations.

---

## Step 2.5: Configure Your Plan Limits

```bash
# Copy the example file
cp .claude/usage-tracker/limits.example.json .claude/usage-tracker/limits.json

# Open and edit the values to match your actual plan
```

`limits.json` is git-ignored so it stays personal to your machine. The tracker shows `(cfg)` when it's loaded and `(est)` when falling back to defaults.

### Token limits

Open [claude.ai/settings/usage](https://claude.ai/settings/usage) and note the percentage next to each bar. Divide the tracker's current token count by that percentage (as a decimal) to get the real limit:

```
token count ÷ percentage = limit
Example: tracker shows 286K, page shows 24% → 286000 ÷ 0.24 = ~1.2M quota limit
```

The page shows three bars: **Current session**, **All models** (weekly combined), and **Sonnet only** (weekly). Use the matching percentage for each.

> **Tip:** Share a screenshot of [claude.ai/settings/usage](https://claude.ai/settings/usage) with Claude while the tracker is running — Claude can read the percentages and the tracker's output to calculate and update your `limits.json` automatically.

### Weekly reset times

This matters: the **"Sonnet only" bar resets on a different day than "All models"**, and neither necessarily resets on Monday. Without the correct reset times, the weekly percentages can be significantly off.

For each weekly bar, `claude.ai/settings/usage` shows either:
- A countdown: **"Resets in 17 hr 27 min"** — add that to the current UTC time to get the next reset, then subtract 7 days for the reset day/hour
- A day and time: **"Resets Thu 5:00 PM"** — use that day and convert the time to UTC

Set `weekly_reset_day` (0=Mon … 6=Sun) and `weekly_reset_hour_utc` for both `sonnet` and `all_models`:

```json
"sonnet": {
  "weekly": 8200000,
  "weekly_reset_day": 3,
  "weekly_reset_hour_utc": 16
},
"all_models": {
  "weekly": 18000000,
  "weekly_reset_day": 4,
  "weekly_reset_hour_utc": 11
}
```

**Converting local time to UTC:**
- CET (Central European, UTC+1): subtract 1 hour. "Thu 5:00 PM CET" → Thu 16:00 UTC → `"weekly_reset_day": 3, "weekly_reset_hour_utc": 16`
- CEST (Central European Summer, UTC+2): subtract 2 hours
- EST (UTC-5): add 5 hours

Omit `weekly_reset_day` / `weekly_reset_hour_utc` to fall back to Monday 00:00 UTC.

To verify your configuration:
```bash
python3 .claude/usage-tracker/claude-usage-tracker.py --limits
```

### Session reset calibration

The session window is a rolling 5-hour window — there's no fixed start time in the JSONL files, so the tracker approximates it as "now − 5h". You can calibrate this two ways:

**At the start of a new session:**
```bash
python3 .claude/usage-tracker/claude-usage-tracker.py --mark-session-start
```

**When [claude.ai/settings/usage](https://claude.ai/settings/usage) shows a known remaining time:**
```bash
python3 .claude/usage-tracker/claude-usage-tracker.py --set-session-reset "4h 50m"
# Also accepts: "4:50" or plain minutes ("290")
```

Both write `session-state.json` next to the script. The tracker uses it until the stored time passes, then falls back to `(approx)` automatically. The header shows `(calibrated)` when active.

A running monitor picks up changes to `session-state.json` and `limits.json` within 1 second — no restart needed.

---

## Step 3: Set Up Continuous Monitoring in VS Code

### A. Create a VS Code Task

This creates an always-on monitor that displays in a dedicated Terminal panel.

**Step 1 — Open the user tasks file:**

1. Press `Ctrl + Shift + P`
2. Type `Tasks: Open User Tasks` and press Enter
3. A **"Select a Task Template"** dropdown appears — click **"Others"**

> This creates (or opens) a global `tasks.json` file that applies to all your workspaces.

**Step 2 — Replace the entire file content** with this:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Claude Usage Monitor",
      "type": "shell",
      "command": "python3",
      "args": [
        "${workspaceFolder}/.claude/usage-tracker/claude-usage-tracker.py",
        "--monitor",
        "--all-models",
        "--interval",
        "300"
      ],
      "isBackground": true,
      "runOptions": {
        "runOn": "folderOpen"
      },
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

**Step 3 — Save the file** (`Ctrl + S`).

**Step 4 — Run it:**
- `Ctrl + Shift + P` → `Tasks: Run Task` → select **Claude Usage Monitor**
- A dedicated Terminal panel opens with live output

With `"runOn": "folderOpen"`, the monitor will start automatically every time you open this workspace.

### B. Add Keyboard Shortcut (Optional)

Open keyboard shortcuts (`Ctrl + K, Ctrl + S`) → click the `{}` icon to edit `keybindings.json`:

```json
{
  "key": "ctrl+shift+u",
  "command": "workbench.action.tasks.runTask",
  "args": "Claude Usage Monitor"
}
```

Press `Ctrl+Shift+U` to start the monitor at any time.

---

## Usage

### One-time Report

```bash
python3 .claude/usage-tracker/claude-usage-tracker.py                # Sonnet only
python3 .claude/usage-tracker/claude-usage-tracker.py --all-models   # All three models
```

### Status Bar (Compact, One Line per Model)

```bash
python3 .claude/usage-tracker/claude-usage-tracker.py --status-bar             # Sonnet
python3 .claude/usage-tracker/claude-usage-tracker.py --status-bar --all-models # All models
```

Output (all models):
```
─── 16:42:17 UTC ─── Session: 1h 33m elapsed  ·  3h 27m until reset  ·  5h (calibrated)
🟢🟢  All Models    │   83.6K ss │   2.34M wk │ Sess~:  10.0% │ Week~:  10.4% (cfg)
🟢🟢  Claude Haiku  │   18.6K ss │  278.8K wk │ Sess~:   1.6% │ Week~:   4.6% (cfg)
🟢🟡  Claude Sonnet │   65.0K ss │   2.06M wk │ Sess~:   5.8% │ Week~:  28.2% (cfg)
🔵🔵  Claude Opus   │  (no usage this period)
   Weekly resets: All Models in 16h 25m · Sonnet in 165h 25m
```
First circle = Session · Second circle = Weekly · `(cfg)` = limits.json loaded · `(est)` = using defaults

`(X left)` appears only at 🟠 75%+ · `(calibrated)` = reset time set via `--set-session-reset` · `(approx)` = estimated as now − 5h

### Continuous Monitoring

```bash
python3 .claude/usage-tracker/claude-usage-tracker.py --monitor                          # Sonnet, 5 min
python3 .claude/usage-tracker/claude-usage-tracker.py --monitor --all-models             # All models
python3 .claude/usage-tracker/claude-usage-tracker.py --monitor --all-models --interval 300
python3 .claude/usage-tracker/claude-usage-tracker.py --monitor --all-models --active-only  # Hide idle models
```

### Check Configured Limits

```bash
python3 .claude/usage-tracker/claude-usage-tracker.py --limits
```

### Calibrate Session Reset

```bash
python3 .claude/usage-tracker/claude-usage-tracker.py --mark-session-start          # new session
python3 .claude/usage-tracker/claude-usage-tracker.py --set-session-reset "4h 50m"  # known time remaining
```

---

## Customization

### Switch Between Models

```bash
# Sonnet (default)
python3 .claude/usage-tracker/claude-usage-tracker.py --monitor

# Haiku
python3 .claude/usage-tracker/claude-usage-tracker.py --model haiku --monitor

# Opus
python3 .claude/usage-tracker/claude-usage-tracker.py --model opus --monitor

# All three simultaneously
python3 .claude/usage-tracker/claude-usage-tracker.py --monitor --all-models
```

### Update Plan Limits

Default limits are approximate **subscription quota** estimates (not model context windows — see [Two Kinds of Token Limits](../../.claude/docs/parallel-agents.md#two-kinds-of-token-limits)). To set your real limits, edit `limits.json` (see Step 2.5). Default values:

| Model | Daily | Weekly |
|-------|-------|--------|
| **Haiku** | ~1.2M | ~6M |
| **Sonnet** | ~400K | ~2M |
| **Opus** | ~200K | ~1M |

### Custom Projects Directory

If your Claude Code data is in a non-default location:

```bash
python3 .claude/usage-tracker/claude-usage-tracker.py \
  --projects-dir /path/to/.claude/projects
```

---

## Troubleshooting

### "Today: 0.0%" when you've been working

Check if JSONL files exist:
```bash
ls ~/.claude/projects/
find ~/.claude/projects -name "*.jsonl" | head -5
```

If the directory is empty, Claude Code hasn't written any session data yet. Make at least one Claude Code API call (run any slash command or use the agent), then re-run the tracker.

### Python not found

```bash
python3 --version   # must be 3.8+
which python3
```

### Notifications not showing (Linux)

```bash
sudo apt install libnotify-bin   # installs notify-send
```

---

## What Gets Tracked

| Metric | Source | Accuracy |
|--------|--------|----------|
| **Session tokens** | JSONL entries in last 5h, `input_tokens` + `output_tokens` | ~100% |
| **Weekly tokens** | Same, filtered to Mon UTC–now | ~100% |
| **Cache tokens** | Not counted (cheaper tier) | — |

The only inaccuracy comes from the **limit numbers** — the defaults are estimates. Configure your limits in `limits.json` (see Step 2.5). Use [claude.ai/settings/usage](https://claude.ai/settings/usage) to see live percentages and calibrate your values. Note that Anthropic tracks a session limit + weekly limits (not daily), so "Today" in the tracker is an approximation based on UTC midnight.

---

## Advanced: Parse Logs Manually

To inspect the raw data the tracker reads:

```bash
# List all project JSONL files
find ~/.claude/projects -name "*.jsonl"

# Show recent API calls with token counts
python3 -c "
import json, pathlib
for f in sorted(pathlib.Path.home().glob('.claude/projects/**/*.jsonl'))[-3:]:
    for line in f.read_text(errors='ignore').splitlines()[-5:]:
        try:
            d = json.loads(line)
            usage = d.get('message', {}).get('usage', {})
            if usage.get('output_tokens', 0) > 0:
                print(d.get('timestamp','')[:19], usage)
        except: pass
"
```

---

## Recommended Daily Workflow

1. Open the workspace — monitor starts automatically (if task is configured)
2. Keep the dedicated Terminal panel visible while working
3. Check [claude.ai/settings/usage](https://claude.ai/settings/usage) for authoritative usage percentages


---

## Using in Cursor

The tracker works identically in Cursor. Cursor uses Claude Code CLI under the hood, which writes the same JSONL files to `~/.claude/projects/`.

**Setup is the same** — run `install.sh`, then set up a Cursor Task (same JSON format as the VS Code task above, Tasks: Open User Tasks → paste the same task definition).

**One difference:** Cursor's native chat window (the sidebar AI panel) runs on Cursor's own quota, separate from your Claude Code subscription. The tracker only counts usage from Claude Code API calls (slash commands, agent runs) — not from Cursor's sidebar chat.
