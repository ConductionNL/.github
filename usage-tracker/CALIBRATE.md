# Calibrating the Usage Tracker

## For Claude (AI Assistant) — Quick Reference

When a user shares a screenshot of `claude.ai/settings/usage`, follow these steps:

### Step 1: Run the tracker to get current token counts

```bash
python3 usage-tracker/claude-usage-tracker.py --json --all-models
```

This outputs the current token counts. Note `all_models.session_tokens` and `all_models.weekly_tokens`.

### Step 2: Run the calibrate command

```bash
python3 usage-tracker/claude-usage-tracker.py --calibrate \
  --session-pct <SESSION_%> \
  --weekly-all-pct <WEEKLY_ALL_%> \
  --weekly-sonnet-pct <WEEKLY_SONNET_%> \
  --session-reset "<TIME_REMAINING>" \
  --weekly-all-reset "<DAY>:<HOUR_UTC>" \
  --weekly-sonnet-reset "<DAY>:<HOUR_UTC>"
```

**Example** (from a screenshot showing session 27%, weekly all 3%, sonnet 0%, session resets in 1h 48m, weekly resets Fri 10:00 AM CEST):

```bash
python3 usage-tracker/claude-usage-tracker.py --calibrate \
  --session-pct 27 \
  --weekly-all-pct 3 \
  --session-reset "1h 48m" \
  --weekly-all-reset "fri:08"
```

Notes on the reset time: convert local time to UTC. CEST = UTC+2, CET = UTC+1.
Example: "Fri 10:00 AM" CEST → `fri:08` (10 - 2 = 08 UTC).

### Step 3: Verify

The `--calibrate` command prints verification output automatically. Check that:
- Weekly percentage matches the screenshot (±0.5%)
- Session percentage is close (may differ by 1-3% due to tokens consumed during calibration)

### What each screenshot field maps to

| Screenshot field | CLI flag | Notes |
|-----------------|----------|-------|
| "Current session: X% used" | `--session-pct X` | |
| "Resets in Xh Ym" | `--session-reset "Xh Ym"` | Session rolling window |
| "All models: X% used" | `--weekly-all-pct X` | |
| "Resets Day HH:MM AM/PM" | `--weekly-all-reset "day:HH"` | Convert to UTC! |
| "Sonnet only: X% used" | `--weekly-sonnet-pct X` | Only if > 0% |
| Sonnet reset time | `--weekly-sonnet-reset "day:HH"` | Often different from All Models |

### When percentages are 0%

If weekly shows 0%, you **cannot** calibrate that limit (division by zero). Skip that flag — the tracker will keep the existing value or use defaults. Re-calibrate when usage builds up to ≥1%.

### Cache token note

JSONL files count ALL input tokens including `cache_read` tokens. Anthropic discounts cached tokens for quota tracking. This means:
- Calibrated limits will be **higher** than the real Anthropic quota (in raw token terms)
- This is correct behavior — both numerator and denominator use the same inflated unit
- Limits may drift as cache hit rates change — **re-calibrate weekly**

---

## For Humans — Manual Calibration

If you prefer to calibrate manually:

1. Open [claude.ai/settings/usage](https://claude.ai/settings/usage)
2. Run: `python3 usage-tracker/claude-usage-tracker.py --status-bar --all-models`
3. Calculate: `limit = tracker_token_count ÷ (observed_percentage / 100)`
4. Edit `~/.claude/usage-tracker/limits.json` with the calculated values
5. Verify: `python3 usage-tracker/claude-usage-tracker.py --limits`

## Data Location

All calibration data is stored centrally in `~/.claude/usage-tracker/`:

```
~/.claude/usage-tracker/
├── limits.json          ← Calibrated limits + config (written by --calibrate)
├── session-state.json   ← Session reset calibration (auto-written)
├── session.json         ← Last session snapshot (auto-written)
└── usage-api-cache.json ← Cached API response (if fetch_usage enabled)
```

This is shared across all project instances of the tracker.

## Optional: API-Based Usage Fetching (Experimental)

The tracker can attempt to fetch real-time usage percentages from an undocumented Anthropic API endpoint. This is experimental and may break at any time.

To enable, add `"fetch_usage": true` to `~/.claude/usage-tracker/limits.json`:
```json
{
  "all_models": { ... },
  "fetch_usage": true
}
```
Then run: `python3 usage-tracker/claude-usage-tracker.py --fetch-usage`

Requires `~/.claude/.credentials.json` (auto-created when you log in to Claude Code).
