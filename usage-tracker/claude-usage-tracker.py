#!/usr/bin/env python3
"""
Claude Usage Tracker for VS Code + Claude Code
Reads token usage from ~/.claude/projects/ JSONL files.
Supports Claude Haiku, Sonnet, and Opus — session and weekly totals.

Anthropic's actual limit structure (Claude Pro/Max subscriptions):
  - Session limit  : 5-hour rolling window, shared across all models
  - Weekly limit   : resets every 7 days from your plan start (not necessarily Monday)
  - Sonnet weekly  : separate weekly limit for Sonnet only

This tracker approximates the session window as "last 5 hours" (rolling) and
the weekly window as "since Monday UTC" — both are approximations since the
exact boundaries are not stored in the JSONL files.

Works with VS Code (Claude Code extension) and Cursor (Claude Code CLI).
All variable data (limits.json, session state) is stored centrally in
~/.claude/usage-tracker/ so all project instances share the same calibration.
Falls back to built-in defaults with an "(estimate)" label.
"""

import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import urllib.request
import urllib.error

# Centralized data directory — all variable/user data lives here (not per-project)
DATA_DIR = Path.home() / ".claude" / "usage-tracker"

# ---------------------------------------------------------------------------
# Built-in fallback limits (used when limits.json is absent or incomplete)
# ---------------------------------------------------------------------------
DEFAULT_LIMITS = {
    "haiku":      {"session": 1200000, "weekly": 6000000,  "model_name": "Claude Haiku"},
    "sonnet":     {"session": 400000,  "weekly": 2860000,  "model_name": "Claude Sonnet"},
    "opus":       {"session": 200000,  "weekly": 1000000,  "model_name": "Claude Opus"},
    "all_models": {"session": 836000,  "weekly": 22400000, "model_name": "All Models"},
}

ALL_MODELS = ["haiku", "sonnet", "opus"]
COMBINED_KEY = "all_models"


def load_limits():
    """
    Load limits from ~/.claude/usage-tracker/limits.json.
    Returns (limits_dict, configured=True/False).
    configured=True means limits.json was found and used.
    """
    limits_file = DATA_DIR / "limits.json"
    if not limits_file.exists():
        return DEFAULT_LIMITS, False

    try:
        data = json.loads(limits_file.read_text())
        limits = {}

        def _load_entry(key, defaults):
            entry = data.get(key, {})
            d = {
                "session":    entry.get("session",    defaults["session"]),
                "weekly":     entry.get("weekly",     defaults["weekly"]),
                "model_name": defaults["model_name"],
            }
            if "weekly_reset_day" in entry:
                d["weekly_reset_day"] = int(entry["weekly_reset_day"])
            if "weekly_reset_hour_utc" in entry:
                d["weekly_reset_hour_utc"] = int(entry["weekly_reset_hour_utc"])
            return d

        for model in ALL_MODELS:
            if model in data:
                limits[model] = _load_entry(model, DEFAULT_LIMITS[model])
            else:
                limits[model] = DEFAULT_LIMITS[model]

        limits[COMBINED_KEY] = (
            _load_entry(COMBINED_KEY, DEFAULT_LIMITS[COMBINED_KEY])
            if COMBINED_KEY in data
            else DEFAULT_LIMITS[COMBINED_KEY]
        )
        return limits, True
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return DEFAULT_LIMITS, False


class ClaudeUsageTracker:

    def __init__(self, projects_dir=None, model="sonnet"):
        self.limits, self.limits_configured = load_limits()
        self.projects_dir = Path(projects_dir) if projects_dir else self._find_projects_dir()
        self.model = model.lower() if model in ALL_MODELS else "sonnet"
        self.model_config = self.limits[self.model]
        self.log_file = DATA_DIR / "session.json"
        self.notify_state = {
            "last_notification": 0,
            "notification_percentages": [25, 50, 75, 90],
        }

    def _find_projects_dir(self):
        return Path.home() / ".claude" / "projects"

    # ------------------------------------------------------------------
    # Time helpers
    # ------------------------------------------------------------------

    def _load_session_reset(self):
        """Return stored session_reset_at datetime if present and still in the future, else None."""
        state_file = DATA_DIR / "session-state.json"
        if not state_file.exists():
            return None
        try:
            data = json.loads(state_file.read_text())
            reset_at = datetime.fromisoformat(data["session_reset_at"])
            if reset_at > datetime.now(timezone.utc):
                return reset_at
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
        return None

    def set_session_reset(self, time_str):
        """
        Parse a 'time remaining' string (e.g. '4h 50m', '4:50', '290') and store
        the calculated reset timestamp in logs/session-state.json.
        """
        import re
        h = re.search(r'(\d+)\s*h', time_str)
        m = re.search(r'(\d+)\s*m', time_str)
        c = re.match(r'^(\d+):(\d+)$', time_str.strip())
        if h or m:
            total = (int(h.group(1)) if h else 0) * 60 + (int(m.group(1)) if m else 0)
        elif c:
            total = int(c.group(1)) * 60 + int(c.group(2))
        else:
            try:
                total = int(time_str.strip())
            except ValueError:
                print(f"❌ Cannot parse: {time_str!r}  (expected '4h 50m', '4:50', or minutes)")
                return
        reset_at = datetime.now(timezone.utc) + timedelta(minutes=total)
        state_file = DATA_DIR / "session-state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps({
            "session_reset_at": reset_at.isoformat(),
            "set_at": datetime.now(timezone.utc).isoformat(),
        }, indent=2))
        h_part, m_part = divmod(total, 60)
        print(f"✅ Session reset stored: {reset_at.strftime('%H:%M:%S UTC')} "
              f"(in {h_part}h {m_part:02d}m)")

    def _session_start(self):
        """
        Start of the token-counting window (always at most 5h back).
        When calibrated, uses the known session start capped to now-5h so that
        pre-reset tokens from a previous session are excluded while current-session
        tokens are never lost. Falls back to now-5h when not calibrated.
        """
        rolling = datetime.now(timezone.utc) - timedelta(hours=5)
        reset_at = self._load_session_reset()
        if reset_at:
            return max(reset_at - timedelta(hours=5), rolling)
        return rolling

    @staticmethod
    def _week_start():
        """Monday 00:00 UTC — fallback when no reset time is configured."""
        n = datetime.now(timezone.utc)
        return (n - timedelta(days=n.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    def _week_start_for(self, model):
        """
        Return the start of the current weekly window for the given model.
        Uses weekly_reset_day (0=Mon..6=Sun) and weekly_reset_hour_utc from
        limits.json when configured; falls back to Monday 00:00 UTC.
        """
        cfg = self.limits.get(model, {})
        reset_day  = cfg.get("weekly_reset_day")
        reset_hour = cfg.get("weekly_reset_hour_utc", 0)
        now = datetime.now(timezone.utc)
        if reset_day is None:
            return self._week_start()
        days_back = (now.weekday() - reset_day) % 7
        candidate = (now - timedelta(days=days_back)).replace(
            hour=reset_hour, minute=0, second=0, microsecond=0
        )
        if candidate > now:
            candidate -= timedelta(days=7)
        return candidate

    # ------------------------------------------------------------------
    # JSONL parsing
    # ------------------------------------------------------------------

    def parse_jsonl_logs(self, since=None, model_filter=None):
        """
        Read all *.jsonl files under self.projects_dir and return a list of
        request dicts. Filters by model name and timestamp window if given.
        """
        if not self.projects_dir.exists():
            return []

        model_filter = (model_filter or self.model).lower()
        requests = []

        for jsonl_file in sorted(self.projects_dir.glob("**/*.jsonl")):
            try:
                for line in jsonl_file.read_text(errors="ignore").splitlines():
                    if not line.strip():
                        continue
                    d = json.loads(line)
                    msg = d.get("message", {})
                    usage = msg.get("usage", {})

                    if usage.get("output_tokens", 0) == 0:
                        continue

                    model_name = msg.get("model", "").lower()
                    if model_filter not in model_name:
                        continue

                    if since:
                        ts_str = d.get("timestamp", "")
                        if ts_str:
                            try:
                                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                                if ts < since:
                                    continue
                            except (ValueError, TypeError):
                                pass

                    requests.append({
                        "tokens":               usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                        "input_tokens":         usage.get("input_tokens", 0),
                        "output_tokens":        usage.get("output_tokens", 0),
                        "cache_creation_tokens":usage.get("cache_creation_input_tokens", 0),
                        "cache_read_tokens":    usage.get("cache_read_input_tokens", 0),
                        "timestamp":            d.get("timestamp", ""),
                        "model":                model_name,
                        "source":               jsonl_file.name,
                    })
            except (json.JSONDecodeError, OSError):
                pass

        return requests

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def get_usage(self, model=None):
        """
        Return a usage dict for the given model (defaults to self.model):
          session — last 5 hours (approximates Anthropic's 5h rolling session window)
          week    — since the configured weekly_reset_day/hour_utc, or Monday UTC if not set
        """
        m = (model or self.model).lower()
        cfg = self.limits[m]

        session_reqs = self.parse_jsonl_logs(since=self._session_start(),   model_filter=m)
        week_reqs    = self.parse_jsonl_logs(since=self._week_start_for(m), model_filter=m)

        def totals(reqs):
            return {
                "input":    sum(r["input_tokens"]  for r in reqs),
                "output":   sum(r["output_tokens"] for r in reqs),
                "total":    sum(r["tokens"]        for r in reqs),
                "requests": len(reqs),
            }

        sess = totals(session_reqs)
        wk   = totals(week_reqs)

        # Session is a shared pool across all models — use the combined pool limit
        # so per-model session % reflects each model's share of the real budget,
        # not a meaningless per-model estimate.
        session_pool = self.limits.get(COMBINED_KEY, {}).get("session") or cfg["session"]

        return {
            "model":             m,
            "model_name":        cfg["model_name"],
            "session_limit":     session_pool,
            "weekly_limit":      cfg["weekly"],
            "limits_configured": self.limits_configured,
            "session":           sess,
            "week":              wk,
            "session_pct":       (sess["total"] / session_pool * 100) if session_pool else 0,
            "week_pct":          (wk["total"]   / cfg["weekly"]  * 100) if cfg["weekly"]  else 0,
        }

    def get_combined_usage(self):
        """
        Return summed usage across all models, compared against all_models limits.
        Session: sum of per-model session totals.
        Weekly: all-model tokens since the all_models weekly_reset_day/hour_utc.
        Using a separate weekly window here so the combined bar reflects its own
        reset cycle, independent of per-model reset days.
        """
        cfg = self.limits[COMBINED_KEY]

        # Session: sum individual model sessions (shared 5h window)
        usages = [self.get_usage(m) for m in ALL_MODELS]
        sess = {
            "input":    sum(u["session"]["input"]    for u in usages),
            "output":   sum(u["session"]["output"]   for u in usages),
            "total":    sum(u["session"]["total"]    for u in usages),
            "requests": sum(u["session"]["requests"] for u in usages),
        }

        # Weekly: query all models from the all_models reset time
        week_start = self._week_start_for(COMBINED_KEY)
        week_reqs  = []
        for m in ALL_MODELS:
            week_reqs.extend(self.parse_jsonl_logs(since=week_start, model_filter=m))
        wk = {
            "input":    sum(r["input_tokens"]  for r in week_reqs),
            "output":   sum(r["output_tokens"] for r in week_reqs),
            "total":    sum(r["tokens"]        for r in week_reqs),
            "requests": len(week_reqs),
        }

        return {
            "model":             COMBINED_KEY,
            "model_name":        cfg["model_name"],
            "session_limit":     cfg["session"],
            "weekly_limit":      cfg["weekly"],
            "limits_configured": self.limits_configured,
            "session":           sess,
            "week":              wk,
            "session_pct":       (sess["total"] / cfg["session"] * 100) if cfg["session"] else 0,
            "week_pct":          (wk["total"]   / cfg["weekly"]  * 100) if cfg["weekly"]  else 0,
        }

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def fmt(n):
        if n >= 1_000_000:
            return f"{n/1_000_000:.2f}M"
        if n >= 1_000:
            return f"{n/1_000:.2f}K"
        return str(n)

    @staticmethod
    def indicator(pct):
        if pct >= 99: return "⚫"
        if pct >= 90: return "🔴"
        if pct >= 75: return "🟠"
        if pct >= 50: return "🟡"
        if pct >  0:  return "🟢"
        return "🔵"

    def limit_label(self):
        return "(configured)" if self.limits_configured else "(estimate ⚠️)"

    # ------------------------------------------------------------------
    # Session timing
    # ------------------------------------------------------------------

    def get_session_info(self):
        """
        Return elapsed and remaining time for the current session window.
        Uses calibrated reset time (session-state.json) when available for
        remaining; falls back to oldest-JSONL approximation.
        """
        since = self._session_start()
        oldest_ts = None

        for jsonl_file in sorted(self.projects_dir.glob("**/*.jsonl")):
            try:
                for line in jsonl_file.read_text(errors="ignore").splitlines():
                    if not line.strip():
                        continue
                    d = json.loads(line)
                    if d.get("message", {}).get("usage", {}).get("output_tokens", 0) == 0:
                        continue
                    ts_str = d.get("timestamp", "")
                    if ts_str:
                        try:
                            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                            if ts >= since and (oldest_ts is None or ts < oldest_ts):
                                oldest_ts = ts
                        except (ValueError, TypeError):
                            pass
            except (json.JSONDecodeError, OSError):
                pass

        def fmt_td(td):
            s = int(td.total_seconds())
            if s <= 0:
                return "0m"
            h, m = divmod(s // 60, 60)
            return f"{h}h {m:02d}m" if h else f"{m}m"

        now      = datetime.now(timezone.utc)
        reset_at = self._load_session_reset()

        if reset_at:
            calibrated = True
            remaining  = reset_at - now
            # Elapsed from known session start (not from oldest token)
            elapsed    = now - (reset_at - timedelta(hours=5))
            if oldest_ts is None:
                # Calibrated but no tokens yet in this session window
                rem_str = fmt_td(remaining) if remaining.total_seconds() > 0 else "< 1m"
                return {"has_activity": False, "elapsed_str": fmt_td(elapsed), "remaining_str": rem_str, "calibrated": True}
        elif oldest_ts is None:
            return {"has_activity": False, "elapsed_str": "—", "remaining_str": "—", "calibrated": False}
        else:
            calibrated = False
            elapsed    = now - oldest_ts
            remaining  = timedelta(hours=5) - elapsed

        return {
            "has_activity":   True,
            "elapsed_str":    fmt_td(elapsed),
            "remaining_str":  fmt_td(remaining) if remaining.total_seconds() > 0 else "< 1m",
            "calibrated":     calibrated,
        }

    def _weekly_reset_in(self, model):
        """Timedelta until the next weekly reset for the given model."""
        cfg = self.limits.get(model, {})
        reset_day  = cfg.get("weekly_reset_day", 0)
        reset_hour = cfg.get("weekly_reset_hour_utc", 0)
        now = datetime.now(timezone.utc)
        days_until = (reset_day - now.weekday()) % 7
        next_reset = (now + timedelta(days=days_until)).replace(
            hour=reset_hour, minute=0, second=0, microsecond=0
        )
        if next_reset <= now:
            next_reset += timedelta(days=7)
        return next_reset - now

    def _weekly_reset_footer(self, all_models):
        """One-line footer with time until the next weekly reset(s)."""
        def fmt_td(td):
            h = int(td.total_seconds()) // 3600
            m = (int(td.total_seconds()) % 3600) // 60
            return f"{h}h {m:02d}m"

        if all_models:
            parts = [
                f"All Models in {fmt_td(self._weekly_reset_in(COMBINED_KEY))}",
                f"Sonnet in {fmt_td(self._weekly_reset_in('sonnet'))}",
            ]
        else:
            parts = [f"{self.model_config['model_name']} in {fmt_td(self._weekly_reset_in(self.model))}"]
        return "   Weekly resets: " + " · ".join(parts)

    def _header_line(self, timestamp):
        """Single header line: timestamp + session elapsed/remaining, shown once per refresh."""
        info = self.get_session_info()
        tag  = "calibrated" if info.get("calibrated") else "approx"
        if info["elapsed_str"] != "—":
            sess = f"Session: {info['elapsed_str']} elapsed  ·  {info['remaining_str']} until reset  ·  5h ({tag})"
        else:
            sess = f"Session: no activity in last 5h  ({tag})"
        bar = "─" * max(0, 78 - len(timestamp) - len(sess) - 8)
        return f"─── {timestamp} ─── {sess} {bar}"

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _format_line(self, u):
        """
        Format a usage dict as a table row with two indicator circles.
        First circle = Session usage, second circle = Weekly usage.
        Zero-usage rows are de-emphasized with a condensed format.
        Session remaining shown only on the combined row (shared pool).
        Weekly remaining shown on all active rows.
        """
        s_ind = self.indicator(u["session_pct"])
        w_ind = self.indicator(u["week_pct"])
        lbl   = "(cfg)" if u["limits_configured"] else "(est)"

        # Zero-usage: condensed de-emphasized row
        if u["session"]["total"] == 0 and u["week"]["total"] == 0:
            return f"{s_ind}{w_ind}  {u['model_name']:<14}│  (no usage this period)"

        s_tok = self.fmt(u["session"]["total"])
        w_tok = self.fmt(u["week"]["total"])

        # Session remaining is only accurate on the combined row (shared pool)
        if u["model"] == COMBINED_KEY:
            sess_rem  = max(0, u["session_limit"] - u["session"]["total"])
            sess_suf  = f" ({self.fmt(sess_rem)} left)" if u["session_pct"] >= 75 else ""
        else:
            sess_suf  = ""

        week_rem = max(0, u["weekly_limit"] - u["week"]["total"])
        week_suf = f" ({self.fmt(week_rem)} left)" if u["week_pct"] >= 75 else ""

        return (
            f"{s_ind}{w_ind}  {u['model_name']:<14}"
            f"│ {s_tok:>8} ss "
            f"│ {w_tok:>8} wk "
            f"│ Sess~: {u['session_pct']:>5.1f}%{sess_suf} "
            f"│ Week~: {u['week_pct']:>5.1f}%{week_suf} {lbl}"
        )

    def status_bar_line(self, model=None):
        return self._format_line(self.get_usage(model))

    def combined_status_bar_line(self):
        return self._format_line(self.get_combined_usage())

    def print_status_bar(self, all_models=False, active_only=False):
        now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        print(self._header_line(now))
        if all_models:
            print(self._format_line(self.get_combined_usage()))
            for m in ALL_MODELS:
                u = self.get_usage(m)
                if active_only and u["session"]["total"] == 0 and u["week"]["total"] == 0:
                    continue
                print(self._format_line(u))
        else:
            print(self.status_bar_line(self.model))
        print(self._weekly_reset_footer(all_models))

    # ------------------------------------------------------------------
    # Full report
    # ------------------------------------------------------------------

    def print_report(self, all_models=False):
        models = ALL_MODELS if all_models else [self.model]
        for m in models:
            u = self.get_usage(m)
            lbl = "configured" if u["limits_configured"] else "estimate ⚠️"
            print()
            print("=" * 60)
            print(f"📊 CLAUDE USAGE REPORT  —  {u['model_name'].upper()}")
            print("=" * 60)
            print(f"\n⏰ Report time  : {datetime.now(timezone.utc).isoformat()[:19]} UTC")
            print(f"📁 Data source  : {self.projects_dir}")
            print(f"⚙️  Limits       : {lbl}  (edit limits.json to configure)")

            print(f"\n📈 THIS SESSION (last ~5h, approx rolling window):")
            sess = u["session"]
            print(f"   Requests      : {sess['requests']}")
            print(f"   Input tokens  : {self.fmt(sess['input'])}")
            print(f"   Output tokens : {self.fmt(sess['output'])}")
            if u["session_limit"]:
                print(f"   Total         : {self.fmt(sess['total'])} / {self.fmt(u['session_limit'])}")
                print(f"   Used          : {u['session_pct']:.1f}%  ({self.fmt(max(0, u['session_limit'] - sess['total']))} remaining)")
            else:
                print(f"   Total         : {self.fmt(sess['total'])}  (session limit combined — see all_models.weekly)")

            print(f"\n📊 THIS WEEK:")
            wk = u["week"]
            print(f"   Requests      : {wk['requests']}")
            print(f"   Total         : {self.fmt(wk['total'])} / {self.fmt(u['weekly_limit'])}")
            print(f"   Used          : {u['week_pct']:.1f}%  ({self.fmt(max(0, u['weekly_limit'] - wk['total']))} remaining)")

        print()
        print("=" * 60)
        print("⚠️  Limits are estimates unless calibrated.")
        print("   Run --calibrate with percentages from claude.ai/settings/usage.")
        print("   Or edit ~/.claude/usage-tracker/limits.json directly.")
        print("=" * 60)
        print()

    # ------------------------------------------------------------------
    # Continuous monitoring
    # ------------------------------------------------------------------

    def monitor_continuous(self, interval=300, all_models=False, active_only=False):
        models = ALL_MODELS if all_models else [self.model]
        label  = "all models" if all_models else self.model_config["model_name"]
        print(f"🔍 Monitoring {label} — refresh every {interval}s  |  Ctrl+C to stop")
        print(f"   Circles: 1st = Session  ·  2nd = Weekly  |  🔵 0% · 🟢 low · 🟡 50% · 🟠 75% · 🔴 90% · ⚫ 99%+\n")

        try:
            while True:
                now    = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
                usages = [self.get_usage(m) for m in models]

                print(self._header_line(now))

                if all_models:
                    print(self._format_line(self.get_combined_usage()))

                notifications = []
                for u in usages:
                    if active_only and u["session"]["total"] == 0 and u["week"]["total"] == 0:
                        continue
                    print(self._format_line(u))
                    should_notify, threshold = self._should_notify(u["week_pct"])
                    if should_notify:
                        notifications.append((u["model_name"], threshold, u["week"]["total"]))

                for model_name, threshold, total in notifications:
                    msg = (
                        f"{model_name} weekly usage at {threshold}% "
                        f"({self.fmt(total)} tokens this week)"
                    )
                    self._send_notification(msg)
                    print(f"   🔔 {msg}")

                print(self._weekly_reset_footer(all_models))
                print()  # blank line between refresh cycles

                self._save_session_data(usages)
                self._interruptible_sleep(interval)
                # Reload limits and model config in case limits.json changed.
                # Also reset the notification watermark when the weekly window rolls over
                # so the 25/50/75% thresholds fire again in the new week.
                new_week_start = self._week_start_for(COMBINED_KEY)
                if not hasattr(self, "_last_week_start") or new_week_start != self._last_week_start:
                    self.notify_state["last_notification"] = 0
                    self._last_week_start = new_week_start
                self.limits, self.limits_configured = load_limits()
                self.model_config = self.limits[self.model]

        except KeyboardInterrupt:
            print("\n✅ Monitoring stopped")

    def _should_notify(self, pct):
        thresholds = self.notify_state["notification_percentages"]
        for t in thresholds:
            if pct >= t and t > self.notify_state["last_notification"]:
                self.notify_state["last_notification"] = t
                return True, t
        return False, None

    def _send_notification(self, message):
        try:
            subprocess.run(["notify-send", "Claude Usage", message],
                           capture_output=True, timeout=3)
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass

    def _save_session_data(self, usages):
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        data = {u["model"]: u for u in usages}
        data["timestamp"] = datetime.now(timezone.utc).isoformat()
        with open(self.log_file, "w") as f:
            json.dump(data, f, indent=2)

    def _interruptible_sleep(self, interval):
        """Sleep for `interval` seconds, waking early if limits.json or session-state.json change."""
        watch = [DATA_DIR / "limits.json", DATA_DIR / "session-state.json"]
        mtimes = {f: (f.stat().st_mtime if f.exists() else 0) for f in watch}
        for _ in range(interval):
            time.sleep(1)
            if any((f.stat().st_mtime if f.exists() else 0) != mtimes[f] for f in watch):
                return

    # ------------------------------------------------------------------
    # Show current limit configuration
    # ------------------------------------------------------------------

    @staticmethod
    def _reset_label(cfg):
        """Human-readable weekly reset label from a limits config entry."""
        day  = cfg.get("weekly_reset_day")
        hour = cfg.get("weekly_reset_hour_utc", 0)
        if day is None:
            return "Mon 00:00 UTC (default)"
        names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        return f"{names[day]} {hour:02d}:00 UTC (configured)"

    def print_limits(self):
        limits_file = DATA_DIR / "limits.json"
        src = f"limits.json ({limits_file})" if self.limits_configured else "built-in defaults"
        print(f"\n⚙️  Current limits  [{src}]\n")
        print(f"  {'Model':<10}  {'Session (~5h)':>14}  {'Weekly':>10}  {'Weekly resets'}")
        print(f"  {'-'*10}  {'-'*14}  {'-'*10}  {'-'*28}")
        for m in ALL_MODELS:
            cfg = self.limits[m]
            print(f"  {m:<10}  {self.fmt(cfg['session']):>14}  {self.fmt(cfg['weekly']):>10}  {self._reset_label(cfg)}")
        cfg = self.limits[COMBINED_KEY]
        print(f"  {'all_models':<10}  {'—':>14}  {self.fmt(cfg['weekly']):>10}  {self._reset_label(cfg)}")
        print(f"\n  Session = last 5h rolling window (shared across all models).")
        print(f"  Weekly reset times from limits.json; defaults to Mon 00:00 UTC.")
        if not self.limits_configured:
            print(f"\n  ⚠️  Using default estimates. Run --calibrate or edit {limits_file}.")
        print()

    # ------------------------------------------------------------------
    # Calibrate from observed percentages
    # ------------------------------------------------------------------

    def calibrate(self, session_pct=None, weekly_all_pct=None, weekly_sonnet_pct=None,
                  session_reset=None, weekly_all_reset=None, weekly_sonnet_reset=None):
        """
        Back-calculate limits from observed claude.ai/settings/usage percentages.
        Formula: limit = tracker_token_count / (observed_pct / 100)
        Writes updated values to ~/.claude/usage-tracker/limits.json.
        """
        limits_file = DATA_DIR / "limits.json"
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Load existing limits.json or start fresh
        if limits_file.exists():
            try:
                data = json.loads(limits_file.read_text())
            except (json.JSONDecodeError, OSError):
                data = {}
        else:
            data = {}

        # Remove non-config keys
        data.pop("_calibrated", None)
        data.pop("_note", None)
        data.pop("_structure", None)

        combined = self.get_combined_usage()
        changes = []

        # --- Session limit (shared pool) ---
        if session_pct is not None and session_pct > 0:
            session_tokens = combined["session"]["total"]
            if session_tokens > 0:
                limit = int(session_tokens / (session_pct / 100))
                for key in ALL_MODELS + [COMBINED_KEY]:
                    data.setdefault(key, {})["session"] = limit
                changes.append(f"Session: {self.fmt(session_tokens)} tokens / {session_pct}% = {self.fmt(limit)} limit")
            else:
                print("⚠️  No session tokens found — cannot calibrate session limit. Use the tracker during an active session.")

        # --- Weekly All Models limit ---
        if weekly_all_pct is not None and weekly_all_pct > 0:
            weekly_tokens = combined["week"]["total"]
            if weekly_tokens > 0:
                limit = int(weekly_tokens / (weekly_all_pct / 100))
                data.setdefault(COMBINED_KEY, {})["weekly"] = limit
                changes.append(f"Weekly All Models: {self.fmt(weekly_tokens)} tokens / {weekly_all_pct}% = {self.fmt(limit)} limit")
            else:
                print("⚠️  No weekly tokens found — cannot calibrate weekly limit.")

        # --- Weekly Sonnet limit ---
        if weekly_sonnet_pct is not None and weekly_sonnet_pct > 0:
            sonnet_usage = self.get_usage("sonnet")
            sonnet_tokens = sonnet_usage["week"]["total"]
            if sonnet_tokens > 0:
                limit = int(sonnet_tokens / (weekly_sonnet_pct / 100))
                data.setdefault("sonnet", {})["weekly"] = limit
                changes.append(f"Weekly Sonnet: {self.fmt(sonnet_tokens)} tokens / {weekly_sonnet_pct}% = {self.fmt(limit)} limit")
            else:
                print("⚠️  No Sonnet weekly tokens found — cannot calibrate Sonnet weekly limit.")

        # --- Weekly reset times ---
        if weekly_all_reset:
            day, hour = weekly_all_reset
            data.setdefault(COMBINED_KEY, {})["weekly_reset_day"] = day
            data.setdefault(COMBINED_KEY, {})["weekly_reset_hour_utc"] = hour
            names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            changes.append(f"All Models weekly reset: {names[day]} {hour:02d}:00 UTC")

        if weekly_sonnet_reset:
            day, hour = weekly_sonnet_reset
            data.setdefault("sonnet", {})["weekly_reset_day"] = day
            data.setdefault("sonnet", {})["weekly_reset_hour_utc"] = hour
            names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            changes.append(f"Sonnet weekly reset: {names[day]} {hour:02d}:00 UTC")

        if not changes:
            print("⚠️  No calibration changes — provide at least one percentage flag.")
            return

        # Add calibration timestamp
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        pcts = []
        if session_pct is not None:
            pcts.append(f"session {session_pct}%")
        if weekly_all_pct is not None:
            pcts.append(f"weekly all_models {weekly_all_pct}%")
        if weekly_sonnet_pct is not None:
            pcts.append(f"weekly sonnet {weekly_sonnet_pct}%")
        data["_calibrated"] = f"{now_str} from claude.ai/settings/usage: {', '.join(pcts)}"

        # Write
        limits_file.write_text(json.dumps(data, indent=2) + "\n")

        # Set session reset if provided
        if session_reset:
            self.set_session_reset(session_reset)

        # Reload limits
        self.limits, self.limits_configured = load_limits()
        self.model_config = self.limits[self.model]

        # Print summary
        print(f"\n✅ Calibration saved to {limits_file}\n")
        for c in changes:
            print(f"   {c}")
        print()

        # Show verification
        self.print_status_bar(all_models=True)

    # ------------------------------------------------------------------
    # JSON output
    # ------------------------------------------------------------------

    def get_json_output(self, all_models=False):
        """Return structured dict suitable for JSON serialization."""
        session_info = self.get_session_info()
        combined = self.get_combined_usage()

        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session": {
                "elapsed": session_info.get("elapsed_str", "—"),
                "remaining": session_info.get("remaining_str", "—"),
                "calibrated": session_info.get("calibrated", False),
            },
            "limits_configured": self.limits_configured,
            "all_models": {
                "session_tokens": combined["session"]["total"],
                "session_pct": round(combined["session_pct"], 1),
                "session_limit": combined["session_limit"],
                "weekly_tokens": combined["week"]["total"],
                "weekly_pct": round(combined["week_pct"], 1),
                "weekly_limit": combined["weekly_limit"],
            },
        }

        if all_models:
            result["models"] = {}
            for m in ALL_MODELS:
                u = self.get_usage(m)
                result["models"][m] = {
                    "session_tokens": u["session"]["total"],
                    "session_pct": round(u["session_pct"], 1),
                    "weekly_tokens": u["week"]["total"],
                    "weekly_pct": round(u["week_pct"], 1),
                    "weekly_limit": u["weekly_limit"],
                }

        return result

    # ------------------------------------------------------------------
    # Fetch usage from Anthropic API (optional)
    # ------------------------------------------------------------------

    def fetch_usage(self):
        """
        Fetch real-time usage from the undocumented Anthropic OAuth usage endpoint.
        Requires ~/.claude/.credentials.json (auto-created on Claude Code login).
        Must be enabled in ~/.claude/usage-tracker/limits.json:
          "fetch_usage": true
        """
        limits_file = DATA_DIR / "limits.json"
        try:
            data = json.loads(limits_file.read_text()) if limits_file.exists() else {}
        except (json.JSONDecodeError, OSError):
            data = {}

        if not data.get("fetch_usage"):
            print("⚠️  API usage fetching is not enabled.")
            print(f"   Add '\"fetch_usage\": true' to {limits_file}")
            print(f"   Or run: --calibrate first, then edit the file.")
            return None

        creds_file = Path.home() / ".claude" / ".credentials.json"
        if not creds_file.exists():
            print("❌ ~/.claude/.credentials.json not found.")
            print("   Log in to Claude Code first (the extension creates this file).")
            return None

        try:
            creds = json.loads(creds_file.read_text())
            token = creds.get("claudeAiOauth", {}).get("accessToken")
            if not token:
                print("❌ No accessToken found in credentials file.")
                return None
        except Exception as e:
            print(f"❌ Cannot read credentials: {e}")
            return None

        org_uuid = creds.get("organizationUuid", "")
        # Try known endpoints — this API is undocumented and may change
        url = f"https://claude.ai/api/organizations/{org_uuid}/usage"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "claude-usage-tracker/1.0",
        }

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            # Cache the result — chmod 600 because the response contains
            # org-scoped account data fetched with the user's OAuth token.
            cache_file = DATA_DIR / "usage-api-cache.json"
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps({
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "data": data,
            }, indent=2))
            cache_file.chmod(0o600)

            print(f"✅ Usage fetched from Anthropic API")
            print(json.dumps(data, indent=2))
            return data

        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ""
            print(f"❌ API request failed: HTTP {e.code}")
            if body:
                print(f"   {body[:200]}")
            return None
        except Exception as e:
            print(f"❌ API request failed: {e}")
            return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Claude Usage Tracker — reads ~/.claude/projects/ JSONL files"
    )
    parser.add_argument(
        "--model", choices=ALL_MODELS, default="sonnet",
        help="Model to track (default: sonnet). Ignored when --all-models is set.",
    )
    parser.add_argument(
        "--all-models", action="store_true",
        help="Show usage for all models (haiku, sonnet, opus) at once.",
    )
    parser.add_argument(
        "--monitor", action="store_true",
        help="Continuous monitoring mode.",
    )
    parser.add_argument(
        "--interval", type=int, default=300,
        help="Monitoring refresh interval in seconds (default: 300 = 5 minutes).",
    )
    parser.add_argument(
        "--projects-dir", "--logs-dir", dest="projects_dir",
        help="Path to Claude CLI projects directory (default: ~/.claude/projects/).",
    )
    parser.add_argument(
        "--status-bar", action="store_true",
        help="Output one-line status bar format.",
    )
    parser.add_argument(
        "--limits", action="store_true",
        help="Show the currently configured limits and exit.",
    )
    parser.add_argument(
        "--active-only", action="store_true",
        help="Hide models with no usage in the current session or week.",
    )
    parser.add_argument(
        "--set-session-reset", metavar="TIME",
        help="Store calibrated session reset time. Format: '4h 50m', '4:50', or minutes. "
             "Run this when claude.ai/settings/usage shows a known time remaining.",
    )
    parser.add_argument(
        "--mark-session-start", action="store_true",
        help="Mark the start of a new session (sets reset time to 5h from now). "
             "Run this when you begin a fresh session.",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output in JSON format (works with --status-bar and default report).",
    )

    # --- Calibration flags ---
    cal = parser.add_argument_group("calibration",
        "Back-calculate limits from claude.ai/settings/usage percentages. "
        "Run the tracker first to get current token counts, then provide the "
        "observed percentages from the dashboard.")
    cal.add_argument(
        "--calibrate", action="store_true",
        help="Calibrate limits from observed percentages. Requires at least one --*-pct flag.",
    )
    cal.add_argument(
        "--session-pct", type=float, metavar="PCT",
        help="Observed session usage percentage from claude.ai (e.g. 27).",
    )
    cal.add_argument(
        "--weekly-all-pct", type=float, metavar="PCT",
        help="Observed 'All models' weekly percentage from claude.ai (e.g. 3).",
    )
    cal.add_argument(
        "--weekly-sonnet-pct", type=float, metavar="PCT",
        help="Observed 'Sonnet only' weekly percentage from claude.ai (e.g. 15).",
    )
    cal.add_argument(
        "--session-reset", metavar="TIME",
        help="Session time remaining (e.g. '1h 48m'). Used with --calibrate or standalone.",
    )
    cal.add_argument(
        "--weekly-all-reset", metavar="DAY:HOUR",
        help="All Models weekly reset as 'day:hour_utc' (e.g. 'fri:08'). "
             "Day: mon/tue/wed/thu/fri/sat/sun. Hour: UTC hour 0-23.",
    )
    cal.add_argument(
        "--weekly-sonnet-reset", metavar="DAY:HOUR",
        help="Sonnet weekly reset as 'day:hour_utc' (e.g. 'thu:08').",
    )

    # --- API fetch ---
    parser.add_argument(
        "--fetch-usage", action="store_true",
        help="Fetch real-time usage from Anthropic API (requires config). "
             "See SETUP.md for how to enable this.",
    )

    args = parser.parse_args()

    # --- Parse reset day:hour strings ---
    def parse_reset(s):
        """Parse 'fri:08' into (day_int, hour_int)."""
        if not s:
            return None
        days = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
        parts = s.lower().split(":")
        if len(parts) != 2 or parts[0] not in days:
            print(f"❌ Invalid reset format: {s!r}  (expected 'fri:08')")
            sys.exit(1)
        return (days[parts[0]], int(parts[1]))

    tracker = ClaudeUsageTracker(projects_dir=args.projects_dir, model=args.model)

    if args.calibrate:
        weekly_all_reset = parse_reset(args.weekly_all_reset)
        weekly_sonnet_reset = parse_reset(args.weekly_sonnet_reset)
        tracker.calibrate(
            session_pct=args.session_pct,
            weekly_all_pct=args.weekly_all_pct,
            weekly_sonnet_pct=args.weekly_sonnet_pct,
            session_reset=args.session_reset,
            weekly_all_reset=weekly_all_reset,
            weekly_sonnet_reset=weekly_sonnet_reset,
        )
    elif args.fetch_usage:
        tracker.fetch_usage()
    elif args.mark_session_start:
        tracker.set_session_reset("5h")
    elif args.set_session_reset:
        tracker.set_session_reset(args.set_session_reset)
    elif args.session_reset and not args.calibrate:
        # --session-reset used standalone (not with --calibrate)
        tracker.set_session_reset(args.session_reset)
    elif args.limits:
        tracker.print_limits()
    elif args.json:
        output = tracker.get_json_output(all_models=args.all_models)
        print(json.dumps(output, indent=2))
    elif args.status_bar:
        tracker.print_status_bar(all_models=args.all_models, active_only=args.active_only)
    elif args.monitor:
        tracker.monitor_continuous(interval=args.interval, all_models=args.all_models, active_only=args.active_only)
    else:
        tracker.print_report(all_models=args.all_models)


if __name__ == "__main__":
    main()
