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
Limits are loaded from limits.json next to this script; edit that file when
your plan changes. Falls back to built-in defaults with an "(estimate)" label.
"""

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess

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
    Load limits from limits.json next to this script.
    Returns (limits_dict, configured=True/False).
    configured=True means limits.json was found and used.
    """
    limits_file = Path(__file__).parent / "limits.json"
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
    except Exception:
        return DEFAULT_LIMITS, False


class ClaudeUsageTracker:

    def __init__(self, projects_dir=None, model="sonnet"):
        self.limits, self.limits_configured = load_limits()
        self.projects_dir = Path(projects_dir) if projects_dir else self._find_projects_dir()
        self.model = model.lower() if model in ALL_MODELS else "sonnet"
        self.model_config = self.limits[self.model]
        self.log_file = Path(__file__).parent / "logs" / "session.json"
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
        state_file = Path(__file__).parent / "logs" / "session-state.json"
        if not state_file.exists():
            return None
        try:
            data = json.loads(state_file.read_text())
            reset_at = datetime.fromisoformat(data["session_reset_at"])
            if reset_at > datetime.now(timezone.utc):
                return reset_at
        except Exception:
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
        state_file = Path(__file__).parent / "logs" / "session-state.json"
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
                            except Exception:
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
            except Exception:
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
                        except Exception:
                            pass
            except Exception:
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
        print("⚠️  Limits are estimates unless limits.json is configured.")
        print("   Actual limits: 5h rolling session + 7-day weekly (varies by plan).")
        print("   Check claude.ai/settings/usage for live percentages.")
        print("   Edit limits.json with your own estimates when your plan changes.")
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
                # Reload limits and model config in case limits.json changed
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
        except Exception:
            pass

    def _save_session_data(self, usages):
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        data = {u["model"]: u for u in usages}
        data["timestamp"] = datetime.now(timezone.utc).isoformat()
        with open(self.log_file, "w") as f:
            json.dump(data, f, indent=2)

    def _interruptible_sleep(self, interval):
        """Sleep for `interval` seconds, waking early if limits.json or session-state.json change."""
        script_dir = Path(__file__).parent
        watch = [script_dir / "limits.json", script_dir / "logs" / "session-state.json"]
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
        limits_file = Path(__file__).parent / "limits.json"
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
            print(f"\n  ⚠️  Using default estimates. Edit {limits_file} to set your real limits.")
        print()


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

    args = parser.parse_args()

    tracker = ClaudeUsageTracker(projects_dir=args.projects_dir, model=args.model)

    if args.mark_session_start:
        tracker.set_session_reset("5h")
    elif args.set_session_reset:
        tracker.set_session_reset(args.set_session_reset)
    elif args.limits:
        tracker.print_limits()
    elif args.status_bar:
        tracker.print_status_bar(all_models=args.all_models, active_only=args.active_only)
    elif args.monitor:
        tracker.monitor_continuous(interval=args.interval, all_models=args.all_models, active_only=args.active_only)
    else:
        tracker.print_report(all_models=args.all_models)


if __name__ == "__main__":
    main()
