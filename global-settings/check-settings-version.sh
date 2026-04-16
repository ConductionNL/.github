#!/bin/bash
# check-settings-version.sh
# Fires on UserPromptSubmit. At the start of each Claude session, shows a status
# panel with the installed, local-branch, and online (origin/main) versions of
# the global Claude settings. Warns clearly when an update is available online.
#
# Required setup in ~/.claude/:
#   settings-version      — installed semver (e.g. "1.0.0")
#   settings-repo-url     — (optional) GitHub repo slug for online version check
#                           (e.g. "ConductionNL/.github")
#                           If present, checks VERSION via GitHub API first.
#   settings-repo-ref     — (optional) Git ref (branch/tag/sha) to track.
#                           Defaults to "main" when absent. Applies to both
#                           GitHub API and git-fetch lookup paths.
#   settings-repo-path    — absolute path to the root of the canonical repo
#                           (e.g. ~/path/to/.github)
#                           Used as fallback when settings-repo-url is absent or fails.

# ── ANSI colors ───────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

REPO_URL_FILE="$HOME/.claude/settings-repo-url"
REPO_PATH_FILE="$HOME/.claude/settings-repo-path"
REPO_REF_FILE="$HOME/.claude/settings-repo-ref"
VERSION_FILE="$HOME/.claude/settings-version"

# ── Input validation ─────────────────────────────────────────────────────────
# All config values read from files are validated before use — prevents prompt
# injection via crafted config files and API endpoint abuse via repo slug.
validate_ref() { [[ "$1" =~ ^[a-zA-Z0-9._/-]+$ ]]; }
validate_repo_slug() { [[ "$1" =~ ^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$ ]]; }
validate_semver() { [[ "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; }

# ── timeout wrapper (falls back to direct execution if timeout is missing) ───
run_with_timeout() {
    local secs="$1"; shift
    if command -v timeout >/dev/null 2>&1; then
        timeout "$secs" "$@"
    else
        "$@"
    fi
}

# ── Tracking ref (branch/tag/sha) — defaults to "main" when unset ────────────
tracking_ref="main"
if [ -f "$REPO_REF_FILE" ]; then
    _ref=$(tr -d '[:space:]' < "$REPO_REF_FILE")
    if [ -n "$_ref" ]; then
        if validate_ref "$_ref"; then
            tracking_ref="$_ref"
        else
            echo "WARNING: ~/.claude/settings-repo-ref contains invalid characters — ignoring, using 'main'." >&2
        fi
    fi
fi

# ── Session-once guard ────────────────────────────────────────────────────────
input=$(cat)
transcript_path=$(echo "$input" | jq -r '.transcript_path // ""' 2>/dev/null)
if [ -z "$transcript_path" ]; then
    exit 0
fi
session_key=$(echo "$transcript_path" | md5sum | cut -c1-12)
_flag_dir="${XDG_RUNTIME_DIR:-$HOME/.claude}"
flag_file="${_flag_dir}/claude-version-warned-${session_key}"
[ -f "$flag_file" ] && exit 0
touch "$flag_file" && chmod 600 "$flag_file" 2>/dev/null

# ── Semver helpers ────────────────────────────────────────────────────────────
semver_gt() {
    [ "$1" = "$2" ] && return 1
    local IFS=. i
    local -a ver1 ver2
    read -ra ver1 <<< "$1"
    read -ra ver2 <<< "$2"
    for ((i = 0; i < ${#ver1[@]}; i++)); do
        local a=${ver1[i]:-0} b=${ver2[i]:-0}
        if ((10#$a > 10#$b)); then return 0; fi
        if ((10#$a < 10#$b)); then return 1; fi
    done
    return 1
}
semver_eq() { [ "$1" = "$2" ]; }

# ── Config warnings array (populated throughout, displayed at the end) ────────
config_warnings=()

# ── Installed version ─────────────────────────────────────────────────────────
installed_version="(not set)"
installed_ok=false
if [ -f "$VERSION_FILE" ]; then
    _iv=$(tr -d '[:space:]' < "$VERSION_FILE")
    if [ -n "$_iv" ]; then
        if validate_semver "$_iv"; then
            installed_version="$_iv"
            installed_ok=true
        else
            installed_version="(invalid: $_iv)"
            config_warnings+=("~/.claude/settings-version contains invalid value '$_iv' — expected semver (e.g. 1.2.3).")
        fi
    fi
fi

# ── Repo dir resolution ───────────────────────────────────────────────────────
REPO_DIR=""
if [ -f "$REPO_PATH_FILE" ]; then
    REPO_DIR=$(tr -d '[:space:]' < "$REPO_PATH_FILE")
    if [ ! -d "$REPO_DIR" ]; then
        config_warnings+=("Repo directory '${REPO_DIR}' from ~/.claude/settings-repo-path does not exist.")
        REPO_DIR=""
    fi
fi

# ── Local branch + version ────────────────────────────────────────────────────
local_branch="(unknown)"
local_version="(unknown)"
git_root=""
has_local_repo=false

if [ -n "$REPO_DIR" ]; then
    has_local_repo=true
    git_root=$(git -C "$REPO_DIR" rev-parse --show-toplevel 2>/dev/null)
    local_branch=$(git -C "$REPO_DIR" branch --show-current 2>/dev/null)
    [ -z "$local_branch" ] && local_branch="(detached HEAD)"

    REPO_VERSION_FILE="$REPO_DIR/global-settings/VERSION"
    if [ -f "$REPO_VERSION_FILE" ]; then
        local_version=$(tr -d '[:space:]' < "$REPO_VERSION_FILE")
    else
        local_version="(missing)"
        config_warnings+=("global-settings/VERSION not found at '${REPO_DIR}/global-settings/VERSION'.")
    fi
fi

# ── Online version (GitHub API — primary method) ─────────────────────────────
online_version="(unknown)"
online_fetch_ok=false
online_source=""
online_repo_slug=""

if [ -f "$REPO_URL_FILE" ]; then
    _slug=$(tr -d '[:space:]' < "$REPO_URL_FILE")
    if [ -n "$_slug" ]; then
        if validate_repo_slug "$_slug"; then
            online_repo_slug="$_slug"
        else
            config_warnings+=("~/.claude/settings-repo-url contains invalid value '$_slug' — expected owner/repo format.")
        fi
    fi
fi

if [ -n "$online_repo_slug" ]; then
    if command -v gh >/dev/null 2>&1; then
        _api_path="repos/${online_repo_slug}/contents/global-settings/VERSION?ref=${tracking_ref}"
        _gh_result=$(run_with_timeout 5 gh api "$_api_path" -H "Accept: application/vnd.github.raw+json" 2>/dev/null | tr -d '[:space:]')
        if [ -n "$_gh_result" ] && echo "$_gh_result" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
            online_version="$_gh_result"
            online_fetch_ok=true
            online_source="github-api"
        else
            config_warnings+=("GitHub API fetch failed for '${online_repo_slug}' — falling back to local repo method.")
        fi
    else
        config_warnings+=("settings-repo-url is configured but 'gh' CLI is not installed — falling back to local repo method.")
    fi
fi

# ── Online version (git fetch — fallback method) ─────────────────────────────
if ! $online_fetch_ok && [ -n "$REPO_DIR" ] && [ -n "$git_root" ]; then
    rel_path=$(realpath --relative-to="$git_root" "$REPO_DIR/global-settings/VERSION" 2>/dev/null)

    if run_with_timeout 5 git -C "$git_root" fetch origin "${tracking_ref}" --quiet --depth=1 2>/dev/null; then
        fetched=$(git -C "$git_root" show "origin/${tracking_ref}:${rel_path}" 2>/dev/null | tr -d '[:space:]')
        if [ -n "$fetched" ]; then
            online_version="$fetched"
            online_fetch_ok=true
            online_source="git-fetch"
        else
            online_version="(not on remote)"
            config_warnings+=("global-settings/VERSION not found on origin/${tracking_ref} (path: ${rel_path}). The canonical global settings may not be committed to this remote — your settings may be outdated.")
        fi
    else
        online_version="(fetch failed)"
        config_warnings+=("Could not reach origin to check online version — your global settings may be outdated.")
    fi
fi

# ── No method available at all ────────────────────────────────────────────────
if ! $online_fetch_ok && [ -z "$online_repo_slug" ] && [ -z "$REPO_DIR" ]; then
    config_warnings+=("Neither ~/.claude/settings-repo-url nor ~/.claude/settings-repo-path is configured — cannot check for updates. Your global settings may be outdated.")
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

# ── Online source label ──────────────────────────────────────────────────────
online_label=""
ref_suffix=""
[ "$tracking_ref" != "main" ] && ref_suffix=" @${tracking_ref}"
if [ "$online_source" = "github-api" ]; then
    online_label="  ${DIM}(via GitHub API${ref_suffix})${NC}"
elif [ "$online_source" = "git-fetch" ]; then
    online_label="  ${DIM}(via git fetch${ref_suffix})${NC}"
fi

# ── Status panel → stderr (displayed directly in the UI) ─────────────────────
{
    echo -e "${CYAN}${BOLD}┌──────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}${BOLD}│     Global Claude Settings Status            │${NC}"
    echo -e "${CYAN}${BOLD}└──────────────────────────────────────────────┘${NC}"
    printf  "  ${BOLD}%-11s${NC}: ${ic}${BOLD}v%-20s${NC}${ic}%s${NC}\n" \
            "Installed" "$installed_version" "$ii"
    if $has_local_repo; then
        printf  "  ${BOLD}%-11s${NC}: ${DIM}%-20s${NC}@ ${lc}v%s${NC}\n" \
                "Local repo" "${local_branch}" "$local_version"
    else
        printf  "  ${BOLD}%-11s${NC}: ${DIM}%s${NC}\n" \
                "Local repo" "(not configured)"
    fi
    printf  "  ${BOLD}%-11s${NC}: ${oc}v%s${NC}${online_label}\n" \
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
    echo "Suggest they check ~/.claude/settings-repo-url, ~/.claude/settings-repo-path, and ~/.claude/settings-version."
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
    echo "  Latest    : v${online_version}  ✅ (on origin/${tracking_ref})"
    echo ""
    echo "  To apply the update:"
    echo "  1. First, in your own terminal (not through Claude), unlock the config files:"
    echo "       chmod 644 \$HOME/.claude/settings-version \$HOME/.claude/settings-repo-path \$HOME/.claude/hooks/*.sh"
    echo "  2. Then say: \"update my global settings to ${online_version}\""

    if [ "$online_source" = "github-api" ]; then
        echo "  When they do, run the following to pull all files directly from GitHub (${online_repo_slug}, ref: ${tracking_ref}):"
        echo "    repo_slug=\"${online_repo_slug}\""
        echo "    ref=\"${tracking_ref}\""
        echo "    base_path=\"global-settings\""
        echo "    mkdir -p ~/.claude/hooks"
        echo "    for f in settings.json block-write-commands.sh check-settings-version.sh VERSION README.md; do"
        echo "      content=\$(gh api \"repos/\${repo_slug}/contents/\${base_path}/\${f}?ref=\${ref}\" -H \"Accept: application/vnd.github.raw+json\")"
        echo "      case \"\$f\" in"
        echo "        *.sh) dest=\"\$HOME/.claude/hooks/\$f\" ;;"
        echo "        VERSION) dest=\"\$HOME/.claude/settings-version\" ;;"
        echo "        README.md) continue ;;"
        echo "        *) dest=\"\$HOME/.claude/\$f\" ;;"
        echo "      esac"
        echo "      printf '%s\n' \"\$content\" > \"\$dest\""
        echo "      if [[ \"\$f\" == *.sh ]]; then chmod 555 \"\$dest\"; elif [[ \"\$f\" == \"settings.json\" ]]; then chmod 644 \"\$dest\"; else chmod 444 \"\$dest\"; fi"
        echo "    done"
        echo "  This pulls files directly from GitHub (ref: ${tracking_ref}) — no local repo clone needed."
    else
        echo "  When they do, run the following to pull all files directly from origin/${tracking_ref} (not the local branch):"
        echo "    ref=\"${tracking_ref}\""
        echo "    git_root=\$(git -C \"${REPO_DIR}\" rev-parse --show-toplevel)"
        echo "    rel_base=\$(realpath --relative-to=\"\$git_root\" \"${REPO_DIR}/global-settings\")"
        echo "    mkdir -p ~/.claude/hooks"
        echo "    git -C \"\$git_root\" fetch origin \"\$ref\" --depth=1"
        echo "    git -C \"\$git_root\" ls-tree --name-only \"origin/\${ref}:\${rel_base}/\" | while read f; do"
        echo "      src=\"origin/\${ref}:\${rel_base}/\${f}\""
        echo "      case \"\$f\" in"
        echo "        *.sh) dest=\"\$HOME/.claude/hooks/\$f\" ;;"
        echo "        VERSION) dest=\"\$HOME/.claude/settings-version\" ;;"
        echo "        *) dest=\"\$HOME/.claude/\$f\" ;;"
        echo "      esac"
        echo "      git -C \"\$git_root\" show \"\$src\" > \"\$dest\""
        echo "      if [[ \"\$f\" == *.sh ]]; then chmod 555 \"\$dest\"; elif [[ \"\$f\" == \"settings.json\" ]]; then chmod 644 \"\$dest\"; else chmod 444 \"\$dest\"; fi"
        echo "    done"
        echo "  Do NOT copy from the local repo directory — always use origin/${tracking_ref} to get the correct version."
    fi
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
    echo "NEW SESSION — Global Claude Settings checked. Version comparison unavailable (could not reach origin/${tracking_ref})."
    echo "Briefly mention this at the start of your response, and suggest the user run /verify-global-settings-version to retry the check."
    echo ""
fi

exit 0
