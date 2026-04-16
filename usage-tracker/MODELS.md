# Multi-Model Tracking Guide - Claude Usage Tracker

Track **Haiku, Sonnet, and Opus** simultaneously with separate usage monitoring.

**All commands run from the project root.**

---

## Model Limits Overview

> These are **subscription quota** limits (how many tokens you can use across all conversations before hitting your cap), NOT model context windows. Context windows are a separate, per-conversation limit. See [Two Kinds of Token Limits](../../.claude/docs/parallel-agents.md#two-kinds-of-token-limits) for the full explanation.

| Model | Session (~5h) | Weekly (~7d) | Best For |
|-------|--------------|-------------|----------|
| **Haiku** | ~1.2M tokens | ~6M tokens | ⚡ Quick tasks, high volume |
| **Sonnet** | ~400K tokens | ~2M tokens | 🎯 Balanced, most tasks |
| **Opus** | ~200K tokens | ~1M tokens | 🧠 Complex reasoning |

**Important:** The session limit is **shared across all models** — it's one combined 5-hour rolling window, not separate per-model buckets. The per-model session values above are estimates; only Anthropic knows the exact combined pool size for your plan.

**Note:** Anthropic does not publish exact token budgets, but [claude.ai/settings/usage](https://claude.ai/settings/usage) shows live usage percentages for your session, weekly "All models" combined, and weekly "Sonnet only" — useful for calibrating the values in `limits.json`.

---

## Quick Track One Model

```bash
# Track Sonnet (default)
python3 .claude/usage-tracker/claude-usage-tracker.py --status-bar

# Track Haiku (1.2M session / 6M weekly)
python3 .claude/usage-tracker/claude-usage-tracker.py --model haiku --status-bar

# Track Opus (200K session / 1M weekly)
python3 .claude/usage-tracker/claude-usage-tracker.py --model opus --status-bar
```

---

## Monitor Multiple Models Simultaneously

Open 3 VS Code terminal tabs and run one per tab:

```bash
# Tab 1: Sonnet
python3 .claude/usage-tracker/claude-usage-tracker.py --model sonnet --monitor --interval 300

# Tab 2: Haiku
python3 .claude/usage-tracker/claude-usage-tracker.py --model haiku --monitor --interval 300

# Tab 3: Opus
python3 .claude/usage-tracker/claude-usage-tracker.py --model opus --monitor --interval 300
```

---

## Full Reports for Each Model

```bash
python3 .claude/usage-tracker/claude-usage-tracker.py                  # Sonnet
python3 .claude/usage-tracker/claude-usage-tracker.py --model haiku    # Haiku
python3 .claude/usage-tracker/claude-usage-tracker.py --model opus     # Opus
```

---

## Session Planning

Check all models before starting work:

```bash
for model in haiku sonnet opus; do
  echo "$model:"
  python3 .claude/usage-tracker/claude-usage-tracker.py --model $model --status-bar
done
```

End-of-session summary across all models:

```bash
for model in haiku sonnet opus; do
  echo "=== $model ===" && python3 .claude/usage-tracker/claude-usage-tracker.py --model $model
done
```

---

## Understanding Multi-Model Colors

The color indicator (🟢 🟡 🟠 🔴) is **percentage-based**, so it's comparable across models:

```
🟡 Claude Usage: 600K | Session~: 50.0% | Week~: 10.0%    ← Haiku at 50%
🟡 Claude Usage: 200K | Session~: 50.0% | Week~: 10.0%    ← Sonnet at 50%
```

Both yellow = both at the same limit percentage, even though token counts differ.

---

## Shell Aliases for Quick Access

Add to `~/.bashrc` or `~/.zshrc`:

```bash
alias claude-haiku="python3 /path/to/project/.claude/usage-tracker/claude-usage-tracker.py --model haiku --status-bar"
alias claude-sonnet="python3 /path/to/project/.claude/usage-tracker/claude-usage-tracker.py --status-bar"
alias claude-opus="python3 /path/to/project/.claude/usage-tracker/claude-usage-tracker.py --model opus --status-bar"
```

---

## Troubleshooting Multi-Model

### Can I track across VS Code sessions?

Yes — session data per model is saved automatically (git-ignored):
- `.claude/usage-tracker/logs/session-sonnet.json`
- `.claude/usage-tracker/logs/session-haiku.json`
- `.claude/usage-tracker/logs/session-opus.json`

### Get total tokens across all models

Use the built-in combined view:

```bash
python3 .claude/usage-tracker/claude-usage-tracker.py --status-bar --all-models
```

Or for a full report across all models at once:

```bash
python3 .claude/usage-tracker/claude-usage-tracker.py --all-models
```
