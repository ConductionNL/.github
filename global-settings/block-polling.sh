#!/usr/bin/env bash
# PreToolUse(Bash) guard: block hand-rolled waiting.
#
# Why: the 2026-09-12 velocity diagnosis counted 2,043 `echo idle`, 929 `true`,
# 453 `cd … && echo waiting`, 395 streaks of five or more consecutive CI polls
# and 35.7 hours of sleep loops in twelve days of sessions. A session that waits
# by hand burns turns and context; a session that pushes and moves on does not.
#
# Blocks, per command segment:
#   - `gh run watch`, `gh pr checks --watch`      (CI is the arbiter, not the loop)
#   - `while|until … sleep`                        (a poll loop in one command)
#   - `sleep N` with N >= 60                       (a long wait)
#   - `echo idle`, `echo waiting`, `tail -f /dev/null`, `timeout N tail -f`
# Allows: short `sleep` (< 60 s) for a service to come up, `gh run view`,
#         `gh pr checks` without --watch (one read is fine), everything else.
#
# What to do instead: push and continue with the next task; use the Monitor
# tool or a background command with an `until` condition when a later event
# genuinely matters; read CI once, at the end, if at all.
set -uo pipefail
input="$(cat 2>/dev/null || true)"
cmd="$(printf '%s' "$input" | python3 -c 'import sys,json
try: print(json.load(sys.stdin).get("tool_input",{}).get("command",""))
except Exception: print("")' 2>/dev/null || true)"
[ -z "$cmd" ] && exit 0
deny() { printf 'BLOCKED by the no-polling guard: %s\nPush and move on. For a later event use the Monitor tool or a background command with an until-condition. Read CI once, at the end.\n' "$1" >&2; exit 2; }

# whole-command shapes first (a loop spans segments)
if printf '%s' "$cmd" | grep -qE '(^|[[:space:];&|(])(while|until)[[:space:]].*sleep[[:space:]]'; then
  deny "a while/until … sleep loop is a poll loop."
fi

segments="$(printf '%s' "$cmd" | sed -E 's/(\|\||&&|[;&|])/\n/g')"
while IFS= read -r seg; do
  [ -z "$seg" ] && continue
  if printf '%s' "$seg" | grep -qE '(^|[[:space:]])gh[[:space:]]+run[[:space:]]+watch([[:space:]]|$)'; then
    deny "gh run watch waits on the CI queue (96% of CI wall-clock is queueing)."
  fi
  if printf '%s' "$seg" | grep -qE '(^|[[:space:]])gh[[:space:]]+pr[[:space:]]+checks[^|;&]*--watch'; then
    deny "gh pr checks --watch waits on the CI queue."
  fi
  if printf '%s' "$seg" | grep -qE '(^|[[:space:]])sleep[[:space:]]+([6-9][0-9]|[1-9][0-9]{2,})([[:space:]]|$)'; then
    deny "sleep of 60 s or more is a hand-rolled wait."
  fi
  if printf '%s' "$seg" | grep -qE '(^|[[:space:]])echo[[:space:]]+"?(idle|waiting)"?([[:space:]]|$)'; then
    deny "echo idle / echo waiting is a heartbeat for a wait loop."
  fi
  if printf '%s' "$seg" | grep -qE 'tail[[:space:]]+-f[[:space:]]+/dev/null'; then
    deny "tail -f /dev/null is a sleep in disguise."
  fi
done <<EOF
$segments
EOF
exit 0
