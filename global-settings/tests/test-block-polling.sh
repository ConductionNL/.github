#!/usr/bin/env bash
# test-block-polling.sh — synthetic test harness for block-polling.sh.
#
# Feeds PreToolUse envelopes to the hook and asserts exit 2 (deny) or 0 (allow).
# Target: the hook must block the hand-rolled waiting shapes the 2026-09-12
# velocity diagnosis counted, and must NOT block a short sleep, a one-shot CI
# read, a push, or a grep that merely mentions the words.
#
# Usage:
#   ./tests/test-block-polling.sh            # run all
#   ./tests/test-block-polling.sh -v         # verbose
#   HOOK=/path/to/hook.sh ./tests/test-block-polling.sh
#
# Exit code: 0 if all tests pass, 1 if any fail. The harness carries its own
# positive control: it first proves the hook denies a known-bad command, so an
# unreadable or empty hook cannot read as green.

set -u
HOOK="${HOOK:-$(cd "$(dirname "$0")/.." && pwd)/block-polling.sh}"
VERBOSE=0; [[ "${1:-}" == "-v" ]] && VERBOSE=1

if [[ ! -r "$HOOK" ]]; then
    echo "ERROR: hook not found or unreadable: $HOOK" >&2
    exit 1
fi

run_hook() {  # $1 = command; returns the hook's exit code
    local env
    env=$(python3 -c 'import json,sys; print(json.dumps({"tool_input":{"command":sys.argv[1]}}))' "$1")
    printf '%s' "$env" | bash "$HOOK" >/dev/null 2>&1
}

pass=0; fail=0; details=()
expect() {  # $1 = deny|allow, $2 = command
    run_hook "$2"; local rc=$?
    local want=0; [[ "$1" == deny ]] && want=2
    if [[ $rc -eq $want ]]; then
        pass=$((pass+1)); [[ $VERBOSE -eq 1 ]] && echo "ok   $1  $2"
    else
        fail=$((fail+1)); details+=("want $1 (exit $want), got exit $rc: $2")
    fi
}

# positive control: a hook that denies nothing must fail this harness
run_hook 'gh run watch 1'; [[ $? -eq 2 ]] || { echo "POSITIVE CONTROL FAILED: hook did not deny 'gh run watch 1'" >&2; exit 1; }

# ── deny: waiting by hand ────────────────────────────────────────────────────
expect deny 'gh run watch 34676564600'
expect deny 'gh run watch 34676564600 --repo ConductionNL/dossiq --exit-status'
expect deny 'gh pr checks 2547 -R ConductionNL/dossiq --watch'
expect deny 'while true; do gh pr checks 5; sleep 30; done'
expect deny 'until gh pr checks 5 | grep -q pass; do sleep 20; done'
expect deny 'for i in 1 2 3; do sleep 1; done; while [ ! -f x ]; do sleep 5; done'
expect deny 'sleep 60'
expect deny 'sleep 120 && gh pr view 5'
expect deny 'cd /tmp && sleep 600'
expect deny 'echo idle'
expect deny 'cd /home/x/memcap-work/eslint-part-2 && echo waiting'
expect deny 'echo "idle"'
expect deny 'timeout 115 tail -f /dev/null; date'
expect deny 'tail -f /dev/null'

# ── allow: legitimate short waits, one-shot reads, everything else ───────────
expect allow 'sleep 5 && curl -s localhost:8080/status.php'
expect allow 'sleep 30'
expect allow 'sleep 59'
expect allow 'gh pr checks 5 -R ConductionNL/dossiq'
expect allow 'gh run view 34676564600 --json jobs'
expect allow 'gh run list --limit 5'
expect allow 'git push origin HEAD'
expect allow 'grep -n "echo idle" transcript.jsonl'
expect allow 'grep -c "gh run watch" file.txt'
expect allow 'echo idle-timeout=30 >> config.ini'
expect allow 'echo waiting-room >> names.txt'
expect allow 'tail -f /var/log/app.log | grep --line-buffered ERROR'
expect allow 'until_date=2026-09-12; echo $until_date'
expect allow 'composer check:strict'
expect allow ''

echo "block-polling: $pass passed, $fail failed"
if [[ $fail -gt 0 ]]; then
    printf '  %s\n' "${details[@]}" >&2
    exit 1
fi
exit 0
