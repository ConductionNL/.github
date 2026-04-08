#!/bin/bash
# check-settings-version.sh
# Fires on UserPromptSubmit. At the start of each Claude session, shows a status
# panel with the installed, local-branch, and online (origin/main) versions of
# the global Claude settings. Warns clearly when an update is available online.
#
# Required setup in ~/.claude/:
#   settings-version      — installed semver (e.g. "1.0.0")
#   settings-repo-path    — absolute path to the .claude/ directory of the
#                           canonical repo (e.g. /path/to/apps-extra/.claude)

# ── ANSI colors ───────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

REPO_PATH_FILE="$HOME/.claude/settings-repo-path"
VERSION_FILE="$HOME/.claude/settings-version"

# ── Session-once guard ────────────────────────────────────────────────────────
input=$(cat)
transcript_path=$(echo "$input" | jq -r '.transcript_path // ""' 2>/dev/null)
if [ -z "$transcript_path" ]; then
    exit 0
fi
session_key=$(echo "$transcript_path" | md5sum | cut -c1-12)
flag_file="/tmp/claude-version-warned-${session_key}"
[ -f "$flag_file" ] && exit 0
touch "$flag_file"

# ── Semver helpers ────────────────────────────────────────────────────────────
semver_gt() {
    [ "$1" = "$2" ] && return 1
    local IFS=.
    local i ver1=($1) ver2=($2)
    for ((i = 0; i < ${#ver1[@]}; i++)); do
        local a=${ver1[i]:-0} b=${ver2[i]:-0}
        if ((10#$a > 10#$b)); then return 0; fi
        if ((10#$a < 10#$b)); then return 1; fi
    done
    return 1
}
semver_eq() { [ "$1" = "$2" ]; }

# ── Installed version ─────────────────────────────────────────────────────────
installed_version="(not set)"
installed_ok=false
if [ -f "$VERSION_FILE" ]; then
    installed_version=$(cat "$VERSION_FILE" | tr -d '[:space:]')
    [ -n "$installed_version" ] && installed_ok=true
fi

# ── Repo dir resolution ───────────────────────────────────────────────────────
config_warnings=()
REPO_DIR=""
if [ ! -f "$REPO_PATH_FILE" ]; then
    config_warnings+=("~/.claude/settings-repo-path is missing — cannot check for updates. Your global settings may be outdated.")
else
    REPO_DIR=$(cat "$REPO_PATH_FILE" | tr -d '[:space:]')
    if [ ! -d "$REPO_DIR" ]; then
        config_warnings+=("Repo directory '${REPO_DIR}' from ~/.claude/settings-repo-path does not exist — cannot check for updates. Your global settings may be outdated.")
        REPO_DIR=""
    fi
fi

# ── Local branch + version ────────────────────────────────────────────────────
local_branch="(unknown)"
local_version="(unknown)"
git_root=""

if [ -n "$REPO_DIR" ]; then
    git_root=$(git -C "$REPO_DIR" rev-parse --show-toplevel 2>/dev/null)
    local_branch=$(git -C "$REPO_DIR" branch --show-current 2>/dev/null)
    [ -z "$local_branch" ] && local_branch="(detached HEAD)"

    REPO_VERSION_FILE="$REPO_DIR/global-settings/VERSION"
    if [ -f "$REPO_VERSION_FILE" ]; then
        local_version=$(cat "$REPO_VERSION_FILE" | tr -d '[:space:]')
    else
        local_version="(missing)"
        config_warnings+=("global-settings/VERSION not found at '${REPO_DIR}/global-settings/VERSION'. Your global settings may be outdated.")
    fi
fi

# ── Online version (origin/main) ──────────────────────────────────────────────
online_version="(unknown)"
online_fetch_ok=false

if [ -n "$REPO_DIR" ] && [ -n "$git_root" ]; then
    # Relative path from git root to the VERSION file (works regardless of repo depth)
    rel_path=$(realpath --relative-to="$git_root" "$REPO_DIR/global-settings/VERSION" 2>/dev/null)

    _do_fetch() {
        if timeout 5 git -C "$git_root" fetch origin main --quiet --depth=1 2>/dev/null; then
            fetched=$(git -C "$git_root" show "origin/main:${rel_path}" 2>/dev/null | tr -d '[:space:]')
            if [ -n "$fetched" ]; then
                online_version="$fetched"
                online_fetch_ok=true
                return 0
            else
                online_version="(not on remote)"
                config_warnings+=("global-settings/VERSION not found on origin/main (path: ${rel_path}). The canonical global settings may not be committed to this remote — your settings may be outdated.")
                return 1
            fi
        fi
        return 1
    }

    if ! _do_fetch; then
        if [ "$online_version" != "(not on remote)" ]; then
            # First attempt failed — wait briefly and retry once
            sleep 3
            if ! _do_fetch; then
                online_version="(fetch failed)"
                config_warnings+=("Could not reach origin to check online version — your global settings may be outdated. Run /verify-global-settings-version to retry.")
            fi
        fi
    fi
fi

# ── Color: installed ──────────────────────────────────────────────────────────
if ! $installed_ok; then
    ic="${RED}" ii="✗"
elif $online_fetch_ok && semver_gt "$online_version" "$installed_version"; then
    ic="${RED}" ii="⚠"
elif $online_fetch_ok && semver_eq "$online_version" "$installed_version"; then
    ic="${GREEN}" ii="✓"
else
    ic="${YELLOW}" ii="?"
fi

# ── Color: local ──────────────────────────────────────────────────────────────
if semver_eq "$local_version" "$installed_version" 2>/dev/null; then
    lc="${GREEN}"
elif semver_gt "$local_version" "$installed_version" 2>/dev/null; then
    lc="${YELLOW}"
else
    lc="${DIM}"
fi

# ── Color: online ─────────────────────────────────────────────────────────────
if ! $online_fetch_ok; then
    oc="${DIM}"
elif semver_eq "$online_version" "$installed_version"; then
    oc="${GREEN}"
elif semver_gt "$online_version" "$installed_version" 2>/dev/null; then
    oc="${RED}"
else
    oc="${DIM}"
fi

# ── Status panel → stderr (displayed directly in the UI) ─────────────────────
{
    echo -e "${CYAN}${BOLD}┌──────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}${BOLD}│     Global Claude Settings Status            │${NC}"
    echo -e "${CYAN}${BOLD}└──────────────────────────────────────────────┘${NC}"
    printf  "  ${BOLD}%-11s${NC}: ${ic}${BOLD}v%-20s${NC}${ic}%s${NC}\n" \
            "Installed" "$installed_version" "$ii"
    printf  "  ${BOLD}%-11s${NC}: ${DIM}%-20s${NC}@ ${lc}v%s${NC}\n" \
            "Local repo" "${local_branch}" "$local_version"
    printf  "  ${BOLD}%-11s${NC}: ${oc}v%s${NC}\n" \
            "Online" "$online_version"

    if [ ${#config_warnings[@]} -gt 0 ]; then
        echo ""
        for w in "${config_warnings[@]}"; do
            echo -e "  ${RED}${BOLD}⚠${NC}  ${RED}${w}${NC}"
        done
    fi
    echo ""
} >&2

# ── Stdout context injected into Claude's prompt ──────────────────────────────

# Config problems — must be very prominent in chat
if [ ${#config_warnings[@]} -gt 0 ]; then
    echo "=========================================="
    echo "🚨 NEW SESSION — GLOBAL CLAUDE SETTINGS: CONFIGURATION ERROR"
    echo "=========================================="
    echo ""
    echo "One or more configuration issues were found. The settings version check could not complete."
    echo ""
    for w in "${config_warnings[@]}"; do
        echo "  ❌ ${w}"
    done
    echo ""
    echo "INSTRUCTION FOR CLAUDE: At the very start of your response, mention that a new session has"
    echo "started and that you checked the Global Claude Settings. Then immediately display the error"
    echo "block prominently — use bold text and/or a code block so the user cannot overlook it."
    echo "Suggest they check ~/.claude/settings-repo-path and ~/.claude/settings-version."
    echo "=========================================="
    echo ""
fi

# Online update available — must be very prominent in chat
if $online_fetch_ok && semver_gt "$online_version" "$installed_version"; then
    echo "=========================================="
    echo "⚠️  NEW SESSION — GLOBAL CLAUDE SETTINGS: UPDATE REQUIRED"
    echo "=========================================="
    echo ""
    echo "  Installed : v${installed_version}  ❌ (outdated)"
    echo "  Latest    : v${online_version}  ✅ (on origin/main)"
    echo ""
    echo "  To apply the update:"
    echo "  1. First, in your own terminal (not through Claude), unlock the config files:"
    echo "       chmod 644 \$HOME/.claude/settings-version \$HOME/.claude/settings-repo-path \$HOME/.claude/hooks/*.sh"
    echo "  2. Then say: \"update my global settings to ${online_version}\""
    echo "  When they do, run the following to pull all files directly from origin/main (not the local branch):"
    echo "    git_root=\$(git -C \"${REPO_DIR}\" rev-parse --show-toplevel)"
    echo "    rel_base=\$(realpath --relative-to=\"\$git_root\" \"${REPO_DIR}/global-settings\")"
    echo "    mkdir -p ~/.claude/hooks"
    echo "    git -C \"\$git_root\" ls-tree --name-only \"origin/main:\${rel_base}/\" | while read f; do"
    echo "      src=\"origin/main:\${rel_base}/\${f}\""
    echo "      case \"\$f\" in"
    echo "        *.sh) dest=\"\$HOME/.claude/hooks/\$f\" ;;"
    echo "        VERSION) dest=\"\$HOME/.claude/settings-version\" ;;"
    echo "        *) dest=\"\$HOME/.claude/\$f\" ;;"
    echo "      esac"
    echo "      git -C \"\$git_root\" show \"\$src\" > \"\$dest\""
    echo "      if [[ \"\$f\" == *.sh ]]; then chmod 555 \"\$dest\"; elif [[ \"\$f\" == \"settings.json\" ]]; then chmod 644 \"\$dest\"; else chmod 444 \"\$dest\"; fi"
    echo "    done"
    echo "  Do NOT copy from the local repo directory — always use origin/main to get the correct version."
    echo ""
    echo "INSTRUCTION FOR CLAUDE: At the very start of your response, mention that a new session has"
    echo "started and that you checked the Global Claude Settings. Then immediately display the update"
    echo "notice as a clearly visible warning block — bold, a header, or a highlighted quote block."
    echo "The user must not be able to overlook it. Do not bury it in the middle of your response."
    echo "Also remind the user that they must first run the chmod 644 unlock command in their own terminal before asking Claude to update (settings.json does not need unlocking as it is already writable)."
    echo "=========================================="
    echo ""

# Settings up to date — brief session-start acknowledgement
elif $online_fetch_ok && semver_eq "$online_version" "$installed_version"; then
    echo "NEW SESSION — Global Claude Settings checked. ✅ Settings are up to date (v${installed_version})."
    echo "Briefly mention at the start of your response that a new session has started and the global Claude settings are up to date."
    echo ""

# Online version unknown but no other warning — still note session start
else
    echo "NEW SESSION — Global Claude Settings checked. Version comparison unavailable (could not reach origin/main)."
    echo "Briefly mention this at the start of your response, and suggest the user run /verify-global-settings-version to retry the check."
    echo ""
fi

exit 0
