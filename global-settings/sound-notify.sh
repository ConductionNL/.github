#!/bin/bash
# sound-notify.sh
# Optional notification-sound wrapper. Wired to three Claude Code events:
#   PreToolUse:AskUserQuestion → sound-notify.sh question
#   Notification              → sound-notify.sh permission
#   Stop                      → sound-notify.sh stop
#
# Opt-in: sounds are silent by default. To enable, copy
# sound-config.sh.example to ~/.claude/sound-config.sh and set SOUND_ENABLED=1.
# The config file is NOT chattr-locked and is user-editable.
#
# Contract: this hook MUST always exit 0. A broken sound must never block
# Claude's turn.

event="${1:-}"

case "$event" in
    question|permission|stop) ;;
    *) exit 0 ;;
esac

config="$HOME/.claude/sound-config.sh"
[ -f "$config" ] || exit 0

# Whitelisted variables sourced from the config. We do NOT eval user-supplied
# command strings — the config exposes file paths, and this wrapper picks the
# player. That way tampering with the config cannot produce shell injection.
SOUND_ENABLED=0
SOUND_QUESTION_FILE=""
SOUND_PERMISSION_FILE=""
SOUND_STOP_FILE=""
# shellcheck disable=SC1090
. "$config" 2>/dev/null || exit 0

[ "$SOUND_ENABLED" = "1" ] || exit 0

case "$event" in
    question)   file="$SOUND_QUESTION_FILE" ;;
    permission) file="$SOUND_PERMISSION_FILE" ;;
    stop)       file="$SOUND_STOP_FILE" ;;
esac

[ -n "$file" ] && [ -r "$file" ] || exit 0

# Background the player so the hook never blocks Claude's turn.
play() {
    if command -v paplay >/dev/null 2>&1; then
        paplay -- "$1" >/dev/null 2>&1
    elif command -v afplay >/dev/null 2>&1; then
        afplay "$1" >/dev/null 2>&1
    elif command -v aplay >/dev/null 2>&1; then
        aplay -q -- "$1" >/dev/null 2>&1
    elif command -v powershell.exe >/dev/null 2>&1; then
        # WSL path — convert if wslpath is available, otherwise use as-is.
        local win_path="$1"
        if command -v wslpath >/dev/null 2>&1 && [ "${1#/}" != "$1" ]; then
            win_path=$(wslpath -w "$1" 2>/dev/null || printf '%s' "$1")
        fi
        powershell.exe -NoProfile -Command "(New-Object Media.SoundPlayer '${win_path//\'/\'\'}').PlaySync()" >/dev/null 2>&1
    fi
}

(play "$file") >/dev/null 2>&1 &
disown 2>/dev/null || true

exit 0
