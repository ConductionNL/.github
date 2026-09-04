#!/bin/bash
# user-hooks-dispatch.sh — dispatch per-user custom hooks.
#
# This wrapper is registered ONCE in the shared settings.json for every hook
# event (PreToolUse, PostToolUse, UserPromptSubmit, SessionStart,
# PermissionRequest, Stop, SubagentStop, PreCompact, Notification). At runtime
# it reads a user-owned config file (~/.claude/user-hooks.json) and executes
# every entry registered for the current event, piping stdin through and
# forwarding stdout back to Claude Code.
#
# Why: the shared settings.json is copy-overwritten on every version update,
# so any per-user hook entry added there is lost the next time the user runs
# "update my global settings". This wrapper decouples the two — the shared
# settings.json only ever holds the dispatcher registration; the actual list
# of per-user hooks lives in ~/.claude/user-hooks.json, which is NEVER
# touched by an update and is explicitly locked from Claude in settings.json's
# deny list (users edit it by hand).
#
# Contract with Claude Code:
#   - Argument: $1 is the event name (PreToolUse / UserPromptSubmit / …).
#   - Stdin   : the standard hook JSON payload — passed through verbatim to
#               every registered user hook.
#   - Stdout  : concatenated stdout of every registered user hook.
#   - Exit    : 0 in the normal case. Propagates exit 2 (hard-deny for
#               PreToolUse) from any user hook that emits it. All other
#               non-zero user-hook exits are swallowed so that a broken
#               personal hook can never freeze a Claude session.
#
# Schema of ~/.claude/user-hooks.json:
#   {
#     "PreToolUse": [
#       { "matcher": "Bash",           "command": "bash ~/mypath/hook.sh" }
#     ],
#     "UserPromptSubmit": [
#       { "command": "bash ~/…/plan-context.sh" }
#     ],
#     "PostToolUse": [], "PermissionRequest": [], "Stop": [],
#     "SubagentStop": [], "SessionStart": [], "PreCompact": [],
#     "Notification": []
#   }
#
# The "matcher" field is an ERE (Extended Regular Expression) matched
# anchored against the tool_name in the stdin payload. It is honoured for
# events that carry a tool_name (PreToolUse, PostToolUse). For every other
# event the matcher is ignored; every entry is executed unconditionally.
# Omit "matcher" (or set it to "" / ".*") to fire on every tool.

set -u

EVENT="${1:-}"
[ -z "$EVENT" ] && exit 0

USER_HOOKS="$HOME/.claude/user-hooks.json"
[ -f "$USER_HOOKS" ] || exit 0

# jq is required — it is already listed as a hard dependency for the shared
# settings (check-settings-version.sh, block-config-tool-writes.sh). If it is
# absent for any reason, fail silent so we don't take Claude down with us.
command -v jq >/dev/null 2>&1 || exit 0

# Read stdin once so we can pass the identical payload to each user hook and
# still parse tool_name out of it for matcher-filtering.
input=$(cat)
tool_name=$(printf '%s' "$input" | jq -r '.tool_name // ""' 2>/dev/null)

# Materialise the array of entries for this event. If the key is absent or
# the file is malformed, jq returns nothing and we exit clean.
mapfile -t entries < <(
    jq -c --arg e "$EVENT" '(.[$e] // []) | .[]?' "$USER_HOOKS" 2>/dev/null
)
[ "${#entries[@]}" -eq 0 ] && exit 0

for entry in "${entries[@]}"; do
    matcher=$(printf '%s' "$entry" | jq -r '.matcher // ""')
    command_line=$(printf '%s' "$entry" | jq -r '.command // ""')

    # Skip entries that don't declare a command — treat them as inert.
    [ -z "$command_line" ] && continue

    # Matcher only applies to tool-carrying events. Empty matcher = fire on
    # every tool. Non-empty = anchored ERE against tool_name.
    if [ -n "$matcher" ] && [ -n "$tool_name" ]; then
        if ! [[ "$tool_name" =~ ^(${matcher})$ ]]; then
            continue
        fi
    fi

    # Execute the user hook with the shared payload on stdin. We forward
    # stdout (some events, notably UserPromptSubmit, use hook stdout as
    # additional context) and let stderr fall through to the terminal.
    if out=$(printf '%s' "$input" | bash -c "$command_line"); then
        rc=0
    else
        rc=$?
    fi
    # $(…) strips the trailing newline; re-add one so the outputs of
    # consecutive hooks don't run together in the forwarded context.
    [ -n "$out" ] && printf '%s\n' "$out"

    # Exit 2 = hard deny (PreToolUse). Propagate immediately so a user hook
    # can still block a tool call — that is a valid, intentional use.
    if [ "$rc" -eq 2 ]; then
        exit 2
    fi
    # All other non-zero exits are logged to stderr and swallowed. A broken
    # personal hook must never wedge Claude Code.
    if [ "$rc" -ne 0 ]; then
        printf 'user-hooks-dispatch: hook exited %d (event=%s, command=%s)\n' \
            "$rc" "$EVENT" "$command_line" >&2
    fi
done

exit 0
