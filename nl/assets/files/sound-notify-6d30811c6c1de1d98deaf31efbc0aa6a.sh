#!/bin/bash
# sound-notify.sh
# Optional notification-sound wrapper. Wired to three Claude Code events:
#   PreToolUse:AskUserQuestion → sound-notify.sh question
#   PermissionRequest         → sound-notify.sh permission
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

# Detach the player from the hook's process group so short sounds (<~500ms)
# survive Claude Code tearing down the hook after we exit. Without setsid /
# nohup, a bare `&` + `disown` still leaves the child in the same process
# group; a group-wide SIGTERM/SIGHUP on hook cleanup then kills PulseAudio
# playback mid-stream. Symptoms (v2.2.0): long sounds like complete.oga (~1s)
# played fine, short sounds like dialog-information.oga (~200ms) were silent.
detach_run() {
    if command -v setsid >/dev/null 2>&1; then
        setsid "$@" </dev/null >/dev/null 2>&1 &
    else
        nohup "$@" </dev/null >/dev/null 2>&1 &
    fi
    disown 2>/dev/null || true
}

if command -v paplay >/dev/null 2>&1; then
    detach_run paplay -- "$file"
elif command -v afplay >/dev/null 2>&1; then
    detach_run afplay "$file"
elif command -v aplay >/dev/null 2>&1; then
    detach_run aplay -q -- "$file"
elif command -v powershell.exe >/dev/null 2>&1; then
    # WSL path — convert if wslpath is available, otherwise use as-is.
    win_path="$file"
    if command -v wslpath >/dev/null 2>&1 && [ "${file#/}" != "$file" ]; then
        win_path=$(wslpath -w "$file" 2>/dev/null || printf '%s' "$file")
    fi
    detach_run powershell.exe -NoProfile -Command "(New-Object Media.SoundPlayer '${win_path//\'/\'\'}').PlaySync()"
fi

exit 0
