#!/bin/bash
# check-settings-version.sh
# Fires on UserPromptSubmit. At the start of each Claude session, shows a status
# panel with the installed, local-branch, and online (origin/main) versions of
# the global Claude settings. Warns clearly when an update is available online.
#
# The set of managed files is not a hand-maintained list (v2.7.0): it is derived
# from the hook scripts the canonical settings.json registers, plus settings.json
# itself and VERSION. When the installed version already matches the online one,
# every managed file is also compared with its canonical copy, so a hook that is
# missing or has drifted is reported and repaired instead of passing as
# "up to date" on the strength of the version number alone.
#
# Required setup in ~/.claude/:
#   settings-version      — installed semver (e.g. "1.0.0")
#   settings-repo-url     — (optional) GitHub repo slug for online version check
#                           (e.g. "ConductionNL/.github")
#                           If present, checks VERSION via GitHub raw URL first.
#   settings-repo-ref     — (optional) Git ref to track. Defaults to "main"
#                           when absent. The GitHub raw URL path uses the
#                           literal branch name; for tag/SHA tracking, configure
#                           settings-repo-path and rely on the git-fetch fallback.
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
# Hook basenames end up inside commands Claude runs: a plain name, no leading dot.
validate_hook_name() { [[ "$1" =~ ^[a-zA-Z0-9_][a-zA-Z0-9_.-]*\.sh$ ]]; }

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
            config_warnings+=("$HOME/.claude/settings-version contains invalid value '$_iv' — expected semver (e.g. 1.2.3).")
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
rel_base="global-settings"   # global-settings/ relative to the repo root (git show needs it)
has_local_repo=false

if [ -n "$REPO_DIR" ]; then
    has_local_repo=true
    git_root=$(git -C "$REPO_DIR" rev-parse --show-toplevel 2>/dev/null)
    local_branch=$(git -C "$REPO_DIR" branch --show-current 2>/dev/null)
    [ -z "$local_branch" ] && local_branch="(detached HEAD)"
    if [ -n "$git_root" ]; then
        _rb=$(realpath --relative-to="$git_root" "$REPO_DIR/global-settings" 2>/dev/null)
        [ -n "$_rb" ] && rel_base="$_rb"
    fi

    REPO_VERSION_FILE="$REPO_DIR/global-settings/VERSION"
    if [ -f "$REPO_VERSION_FILE" ]; then
        local_version=$(tr -d '[:space:]' < "$REPO_VERSION_FILE")
    else
        local_version="(missing)"
        config_warnings+=("global-settings/VERSION not found at '${REPO_DIR}/global-settings/VERSION'.")
    fi
fi

# ── Online version (GitHub raw URL — primary method) ────────────────────────
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
            config_warnings+=("$HOME/.claude/settings-repo-url contains invalid value '$_slug' — expected owner/repo format.")
        fi
    fi
fi

if [ -n "$online_repo_slug" ]; then
    if command -v curl >/dev/null 2>&1; then
        _raw_url="https://raw.githubusercontent.com/${online_repo_slug}/${tracking_ref}/global-settings/VERSION"
        _curl_result=$(run_with_timeout 5 curl -fsSL --max-time 5 "$_raw_url" 2>/dev/null | tr -d '[:space:]')
        if [ -n "$_curl_result" ] && echo "$_curl_result" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
            online_version="$_curl_result"
            online_fetch_ok=true
            online_source="github-raw"
        else
            config_warnings+=("GitHub raw URL fetch failed for '${online_repo_slug}' at branch '${tracking_ref}' — falling back to local repo method.")
        fi
    else
        config_warnings+=("settings-repo-url is configured but 'curl' is not installed — falling back to local repo method.")
    fi
fi

# ── Online version (git fetch — fallback method) ─────────────────────────────
if ! $online_fetch_ok && [ -n "$REPO_DIR" ] && [ -n "$git_root" ]; then
    if run_with_timeout 5 git -C "$git_root" fetch origin "${tracking_ref}" --quiet --depth=1 2>/dev/null; then
        fetched=$(git -C "$git_root" show "origin/${tracking_ref}:${rel_base}/VERSION" 2>/dev/null | tr -d '[:space:]')
        if [ -n "$fetched" ]; then
            online_version="$fetched"
            online_fetch_ok=true
            online_source="git-fetch"
        else
            online_version="(not on remote)"
            config_warnings+=("global-settings/VERSION not found on origin/${tracking_ref} (path: ${rel_base}/VERSION). The canonical global settings may not be committed to this remote — your settings may be outdated.")
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

# ── Canonical copies ─────────────────────────────────────────────────────────
# fetch_canonical <dest dir> <name>... — writes the canonical copy of each
# global-settings/<name> to <dest dir>/<name>, from the same source the version
# came from. A file that could not be fetched is left absent or empty; callers
# test each one with `-s`. The GitHub path fetches every name in one curl call
# (one connection, one timeout), so the check costs one round trip, not one per
# file.
fetch_canonical() {
    local dest="$1"; shift
    local name
    case "$online_source" in
        github-raw)
            local -a args=()
            for name in "$@"; do
                args+=(-o "${dest}/${name}" "https://raw.githubusercontent.com/${online_repo_slug}/${tracking_ref}/global-settings/${name}")
            done
            [ ${#args[@]} -gt 0 ] && run_with_timeout 20 curl -fsSL --max-time 20 "${args[@]}" 2>/dev/null
            ;;
        git-fetch)
            for name in "$@"; do
                git -C "$git_root" show "origin/${tracking_ref}:${rel_base}/${name}" > "${dest}/${name}" 2>/dev/null \
                    || rm -f "${dest}/${name}"
            done
            ;;
    esac
    return 0
}

canon_dir=""
if $online_fetch_ok; then
    canon_dir=$(mktemp -d "${TMPDIR:-/tmp}/claude-settings-canon.XXXXXX" 2>/dev/null) || canon_dir=""
    [ -n "$canon_dir" ] && trap 'rm -rf "$canon_dir"' EXIT
fi

# ── Managed files: derived from the canonical settings.json ──────────────────
# The update notice used to carry a hand-maintained file list, and it fell
# behind settings.json twice: v2.4.1 added two hooks it had missed, and
# block-polling.sh (registered since v2.5.0) was never on it. The list is now
# read from the hook registrations, so a hook that is wired is a hook that gets
# installed. settings.json itself and VERSION are always managed.
#
# hooks_from_settings <settings.json> — the basename of every ~/.claude/hooks/*.sh
# a hook command references, one per line, sorted and de-duplicated. Only the
# hook registrations are read, not the deny list.
hooks_from_settings() {
    jq -r '.hooks // {} | .[]? | .[]? | (.hooks // [])[]? | .command? // empty' "$1" 2>/dev/null \
        | grep -oE '\.claude/hooks/[a-zA-Z0-9_.-]+\.sh' \
        | sed 's#.*/##' | sort -u
}

managed_hooks=()
hooks_source=""            # "canonical" | "installed" | ""
if $online_fetch_ok && [ -n "$canon_dir" ]; then
    fetch_canonical "$canon_dir" settings.json
    if [ -s "$canon_dir/settings.json" ]; then
        while IFS= read -r _h; do
            [ -n "$_h" ] && managed_hooks+=("$_h")
        done < <(hooks_from_settings "$canon_dir/settings.json")
        [ ${#managed_hooks[@]} -gt 0 ] && hooks_source="canonical"
    fi
    if [ -z "$hooks_source" ]; then
        config_warnings+=("Could not read the canonical settings.json from origin/${tracking_ref} — the hook list is derived from the installed ~/.claude/settings.json instead and may be incomplete; the installed files were not verified.")
        if [ -f "$HOME/.claude/settings.json" ]; then
            while IFS= read -r _h; do
                [ -n "$_h" ] && managed_hooks+=("$_h")
            done < <(hooks_from_settings "$HOME/.claude/settings.json")
            [ ${#managed_hooks[@]} -gt 0 ] && hooks_source="installed"
        fi
    fi
fi
_valid_hooks=()
for _h in "${managed_hooks[@]}"; do
    if validate_hook_name "$_h"; then
        _valid_hooks+=("$_h")
    else
        config_warnings+=("Ignoring a hook with an unexpected name in settings.json: '${_h}'.")
    fi
done
managed_hooks=("${_valid_hooks[@]}")

# ── Integrity: do the installed files match the canonical ones? ──────────────
# Only when the installed version equals the online one: an outdated install
# gets the full update anyway, and without an online source there is nothing to
# compare against. VERSION is covered by the version compare itself.
integrity_ran=false
integrity_checked=0
files_missing=()
files_changed=()           # "name" or "name (detail)"
files_unverified=()

# norm_sha <file> — sha256 of the file with its trailing newlines stripped. The
# curl-based install writes `printf '%s\n' "$content"`, which collapses the
# trailing newlines of the canonical file to exactly one, while the git-based
# install copies the bytes verbatim. Neither may count as drift.
norm_sha() {
    if command -v sha256sum >/dev/null 2>&1; then
        printf '%s' "$(cat "$1")" | sha256sum | cut -d' ' -f1
    else
        printf '%s' "$(cat "$1")" | shasum -a 256 | cut -d' ' -f1
    fi
}

# Top-level keys Claude Code itself writes into ~/.claude/settings.json when the
# user picks a model or an effort level, which is exactly what relock option (B)
# allows. They are preferences, not policy (README → Updating, step 4):
#   model               the model picker and /model
#   modelSettings       /effort and the effort picker, saved per model as
#                       modelSettings.<model>.effortLevel
#   effortLevel         the same choice when it cannot be keyed by model
#   fastMode            /fast
#   advisorModel        /advisor
#   switchModelsOnFlag  the VSCode toggle that switches model when a safeguard
#                       flags a message
# Everything else in that file is policy.
CLIENT_MODEL_KEYS='["model","modelSettings","effortLevel","fastMode","advisorModel","switchModelsOnFlag"]'

# settings_diff <installed> <canonical> — empty when both settings.json files are
# the same document, otherwise the top-level keys that differ. Compared as parsed
# JSON (formatting is not drift) and without CLIENT_MODEL_KEYS.
settings_diff() {
    local a b keys
    a=$(jq -S --argjson k "$CLIENT_MODEL_KEYS" 'delpaths($k | map([.]))' "$1" 2>/dev/null) \
        || { echo "not valid JSON"; return; }
    b=$(jq -S --argjson k "$CLIENT_MODEL_KEYS" 'delpaths($k | map([.]))' "$2" 2>/dev/null) \
        || { echo "canonical copy not valid JSON"; return; }
    [ "$a" = "$b" ] && return
    keys=$(jq -n -r --argjson a "$a" --argjson b "$b" \
        '[($a | keys[]), ($b | keys[])] | unique | map(select($a[.] != $b[.])) | join(", ")' 2>/dev/null)
    echo "${keys:-content differs}"
}

if $online_fetch_ok && $installed_ok && semver_eq "$online_version" "$installed_version" \
   && [ "$hooks_source" = "canonical" ]; then
    integrity_ran=true
    fetch_canonical "$canon_dir" "${managed_hooks[@]}"

    integrity_checked=$((integrity_checked + 1))
    if [ ! -f "$HOME/.claude/settings.json" ]; then
        files_missing+=("settings.json")
    else
        _d=$(settings_diff "$HOME/.claude/settings.json" "$canon_dir/settings.json")
        [ -n "$_d" ] && files_changed+=("settings.json (top-level keys: ${_d})")
    fi

    for _h in "${managed_hooks[@]}"; do
        integrity_checked=$((integrity_checked + 1))
        if [ ! -s "$canon_dir/$_h" ]; then
            files_unverified+=("$_h")
        elif [ ! -f "$HOME/.claude/hooks/$_h" ]; then
            files_missing+=("$_h")
        elif [ "$(norm_sha "$HOME/.claude/hooks/$_h")" != "$(norm_sha "$canon_dir/$_h")" ]; then
            files_changed+=("$_h")
        fi
    done

    if [ ${#files_unverified[@]} -gt 0 ]; then
        config_warnings+=("Could not fetch the canonical copy of: ${files_unverified[*]} — these installed files were not verified.")
    fi
fi
integrity_issues=$(( ${#files_missing[@]} + ${#files_changed[@]} ))

# needs_repair <name> — is <name> in files_missing or files_changed?
needs_repair() {
    local e
    for e in "${files_missing[@]}" "${files_changed[@]}"; do
        [ "${e%% (*}" = "$1" ] && return 0
    done
    return 1
}

# ── What the update adds: one sentence per version from CHANGELOG.md ─────────
# Only for an outdated install. CHANGELOG.md is fetched from the same source as
# VERSION; it is not installed. Each "## X.Y.Z" heading is followed by one
# sentence, and the notice shows that sentence for every version after the
# installed one up to the online one, newest first. An install whose version is
# unreadable gets the online version's entry only. A version without an entry
# says so instead of being skipped, so the list never reads as complete when it
# is not.
CHANGES_MAX=5
changes_lines=()
changes_fetched=false
changes_more=0

# changelog_summary <CHANGELOG.md> <version> — the first non-empty line under
# "## <version>", control characters removed and capped at 300 characters.
changelog_summary() {
    awk -v v="$2" '
        /^## / { if (found) exit; found = ($2 == v); next }
        found && NF { print; exit }
    ' "$1" 2>/dev/null | tr -d '\000-\037\177' | cut -c1-300
}

if $online_fetch_ok && [ -n "$canon_dir" ] && semver_gt "$online_version" "$installed_version"; then
    fetch_canonical "$canon_dir" CHANGELOG.md
    _versions=("$online_version")
    if [ -s "$canon_dir/CHANGELOG.md" ]; then
        changes_fetched=true
        if $installed_ok; then
            _versions=()
            while IFS= read -r _v; do
                validate_semver "$_v" || continue
                semver_gt "$_v" "$installed_version" || continue
                semver_gt "$_v" "$online_version" && continue
                _versions+=("$_v")
            done < <(awk '/^## / { print $2 }' "$canon_dir/CHANGELOG.md" | sort -t. -k1,1nr -k2,2nr -k3,3nr -u)
            # The online version always leads, with or without an entry.
            [ "${_versions[0]:-}" = "$online_version" ] || _versions=("$online_version" "${_versions[@]}")
        fi
    fi
    for _v in "${_versions[@]}"; do
        if [ ${#changes_lines[@]} -ge "$CHANGES_MAX" ]; then
            changes_more=$((changes_more + 1))
            continue
        fi
        _s=""
        $changes_fetched && _s=$(changelog_summary "$canon_dir/CHANGELOG.md" "$_v")
        changes_lines+=("v${_v} — ${_s:-(no summary in CHANGELOG.md for this version)}")
    done
fi

# The repository the details are looked up in: the GitHub slug the version came
# from, or the GitHub origin of the local clone on the git-fetch path.
changes_slug="$online_repo_slug"
if [ -z "$changes_slug" ] && [ -n "$git_root" ]; then
    changes_slug=$(git -C "$git_root" remote get-url origin 2>/dev/null \
        | sed -nE 's#^(https://|git@|ssh://git@)github\.com[:/]([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)$#\2#p' \
        | sed 's#\.git$##')
    validate_repo_slug "$changes_slug" || changes_slug=""
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
if [ "$online_source" = "github-raw" ]; then
    online_label="  ${DIM}(via GitHub${ref_suffix})${NC}"
elif [ "$online_source" = "git-fetch" ]; then
    online_label="  ${DIM}(via git fetch${ref_suffix})${NC}"
fi

# ── Friendly source name (surfaced in the session-start message) ─────────────
# github-raw is always GitHub (hardcoded URL). For git-fetch we infer the
# host from the local repo's origin URL.
online_source_name=""
if [ "$online_source" = "github-raw" ]; then
    online_source_name="GitHub"
elif [ "$online_source" = "git-fetch" ] && [ -n "$git_root" ]; then
    _origin_url=$(git -C "$git_root" remote get-url origin 2>/dev/null)
    if echo "$_origin_url" | grep -qE 'codeberg\.org'; then
        online_source_name="Codeberg"
    elif echo "$_origin_url" | grep -qE 'github\.com'; then
        online_source_name="GitHub"
    elif echo "$_origin_url" | grep -qE 'gitlab\.com'; then
        online_source_name="GitLab"
    else
        online_source_name="git origin"
    fi
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
    if $integrity_ran; then
        if [ "$integrity_issues" -gt 0 ]; then
            printf  "  ${BOLD}%-11s${NC}: ${RED}%d missing, %d changed ✗${NC}\n" \
                    "Files" "${#files_missing[@]}" "${#files_changed[@]}"
        elif [ ${#files_unverified[@]} -gt 0 ]; then
            printf  "  ${BOLD}%-11s${NC}: ${YELLOW}%d/%d verified, %d not verified ?${NC}\n" \
                    "Files" "$((integrity_checked - ${#files_unverified[@]}))" "$integrity_checked" "${#files_unverified[@]}"
        else
            printf  "  ${BOLD}%-11s${NC}: ${GREEN}%d/%d verified ✓${NC}\n" \
                    "Files" "$integrity_checked" "$integrity_checked"
        fi
    fi

    if [ ${#config_warnings[@]} -gt 0 ]; then
        echo ""
        for w in "${config_warnings[@]}"; do
            echo -e "  ${RED}${BOLD}⚠${NC}  ${RED}${w}${NC}"
        done
    fi
    echo ""
} >&2

# ── Emitters for the stdout notices ──────────────────────────────────────────
# One notice for an outdated install (every managed file) and one for an install
# whose version matches but whose files do not (only the affected files). They
# share the unlock/relock steps, the contract and the per-file command shape.
# That shape is what block-write-commands.sh allows — the literal canonical URL
# or the literal 'origin/main:' path in the same command — so it lives in one
# place.

emit_unlock_steps() {   # $1 = "the update" | "the repair", $2 = the phrase the user says in step 3
    echo "  To apply $1 (v1.7.0+ — kernel-level chattr +i lock):"
    echo "  1. First, in your own terminal (not through Claude), unlock the files. TWO things need"
    echo "     clearing — the kernel immutable flag AND the read-only file mode the previous update"
    echo "     left behind (Claude installs the hooks as 555 and settings-version as 444, and is"
    echo "     hard-denied from making them writable again — it can only stop and ask you):"
    echo "       sudo chattr -i \$HOME/.claude/settings.json \$HOME/.claude/hooks/*.sh \$HOME/.claude/settings-version"
    echo "       chmod u+w \$HOME/.claude/settings.json \$HOME/.claude/hooks/*.sh \$HOME/.claude/settings-version"
    echo "     The chmod needs no sudo — you own the files. Skip it and every write in step 3 fails"
    echo "     with 'Permission denied' even though the chattr unlock itself succeeded."
    echo "  2. Verify BOTH cleared — no 'i' in the lsattr flags, and a 'w' in the owner bits:"
    echo "       lsattr \$HOME/.claude/settings.json \$HOME/.claude/hooks/*.sh \$HOME/.claude/settings-version"
    echo "       ls -l  \$HOME/.claude/settings.json \$HOME/.claude/hooks/*.sh \$HOME/.claude/settings-version"
    echo "  3. Then say: \"$2\""
    echo "  4. After Claude finishes, re-apply the immutable lock in your own terminal. Pick ONE:"
    echo "     (A) Full lock — every file, all four protection layers (strongest):"
    echo "       sudo chattr +i \$HOME/.claude/settings.json \$HOME/.claude/hooks/*.sh \$HOME/.claude/settings-version"
    echo "     (B) Lock without settings.json — keeps the VSCode model picker working:"
    echo "       sudo chattr +i \$HOME/.claude/hooks/*.sh \$HOME/.claude/settings-version"
    echo "     Why (B) exists: the VSCode extension rewrites ~/.claude/settings.json on every model"
    echo "     switch, and with (A) the picker fails with EPERM and does nothing. What (B) costs:"
    echo "     settings.json is the main file everything hangs off — it holds permissions.deny and"
    echo "     registers every guard hook — and (B) takes the kernel lock off exactly that file."
    echo "     What is left in front of it are the guard hooks. They stay kernel-locked, but they"
    echo "     are regex checks the README calls bypassable, they only police Claude (not other"
    echo "     processes running as you), and one write that slips past them can unregister them."
    echo "     A limited but real risk. (A) plus a project-local model pin keeps all four layers and"
    echo "     stays the recommendation: docs/claude/global-claude-settings.md#troubleshooting."
}

emit_contract() {
    echo "  CONTRACT (must be respected by every emitted command, or block-write-commands.sh will deny it):"
    echo "    (a) Every curl write must use the literal prefix 'https://raw.githubusercontent.com/ConductionNL/.github/'"
    echo "        in the same command (no variable indirection for the URL). Every git-show write"
    echo "        must use the 'origin/main:' path literally in the same command — no variable indirection."
    echo "    (b) Never run 'chmod 644', any write-enabling chmod, or 'chattr' on ~/.claude/ files —"
    echo "        block-write-commands.sh hard-denies all three. Only chmod 444 / 555 are permitted"
    echo "        (cosmetic defense in depth — chattr +i is the actual lock). If a write fails with"
    echo "        'Permission denied' the file is still 444/555 from an earlier update: STOP and ask"
    echo "        the user to run the step-1 'chmod u+w'. Do not route around it with rm/mv/cp/tee —"
    echo "        those are denied on protected paths too, and a half-removed hook is worse than a stale one."
    echo "    (c) Emit one file per command block (flat, no loops) so a single denial does not abort the"
    echo "        whole update and leave ~/.claude/ in a half-installed state."
    echo "    (d) The git-fetch fallback always pulls from 'origin/main:' regardless of the tracked ref"
    echo "        (the hook only allows that literal). If you are tracking a non-main branch, the update"
    echo "        you get via git-fetch reflects main — merge your branch to main first, or use the"
    echo "        GitHub raw path (which uses the branch ref directly) by ensuring"
    echo "        ~/.claude/settings-repo-url is set."
}

# emit_file_blocks <name>... — one command block per managed file, in the order
# given. settings.json goes to ~/.claude/settings.json, VERSION to
# ~/.claude/settings-version (444), anything else to ~/.claude/hooks/<name> (555).
# Callers put VERSION last so the version bump only lands if every other write
# succeeded.
emit_file_blocks() {
    local name target mode first_hook=true
    if [ "$online_source" = "github-raw" ]; then
        echo "  When they do, run each block below (one per file) to pull files directly from GitHub"
        echo "  (${online_repo_slug}, branch: ${tracking_ref}). URLs are inlined so the hook can verify the canonical source:"
    else
        echo "  When they do, run each block below (one per file) to pull files directly from origin/${tracking_ref}"
        echo "  (not the local branch). Paths are inlined so the hook can verify the canonical source:"
        echo ""
        echo "    # Refresh origin/${tracking_ref} once before the copies below"
        echo "    git -C '${REPO_DIR}' fetch origin '${tracking_ref}' --depth=1"
    fi
    for name in "$@"; do
        echo ""
        case "$name" in
            settings.json)
                target="\$HOME/.claude/settings.json"; mode=""
                echo "    # settings.json" ;;
            VERSION)
                target="\$HOME/.claude/settings-version"; mode="444"
                echo "    # VERSION → settings-version (write last, so the version bump only lands if all files succeeded)" ;;
            *)
                target="\$HOME/.claude/hooks/${name}"; mode="555"
                echo "    # ${name}"
                if $first_hook; then
                    echo "    mkdir -p ~/.claude/hooks"
                    first_hook=false
                fi ;;
        esac
        if [ "$online_source" = "github-raw" ]; then
            echo "    content=\$(curl -fsSL --max-time 10 'https://raw.githubusercontent.com/${online_repo_slug}/${tracking_ref}/global-settings/${name}')"
            printf '%s\n' "    printf '%s\\n' \"\$content\" > \"${target}\""
        else
            echo "    git -C '${REPO_DIR}' show 'origin/main:${rel_base}/${name}' > \"${target}\""
        fi
        [ -n "$mode" ] && echo "    chmod ${mode} \"${target}\""
    done
    echo ""
    if [ "$online_source" = "github-raw" ]; then
        echo "  This pulls files directly from GitHub (branch: ${tracking_ref}) — no local repo clone needed."
    else
        echo "  Note: the hook only accepts 'origin/main:' (not 'origin/${tracking_ref}:') for git-show writes."
        echo "  Do NOT copy from the local working tree — always use the origin/main: ref."
    fi
}

emit_claude_instruction() {   # $1 = "the update" | "the repair"
    echo "INSTRUCTION FOR CLAUDE: At the very start of your response, mention that a new session has"
    echo "started and that you checked the Global Claude Settings. Then immediately display the"
    echo "notice as a clearly visible warning block — bold, a header, or a highlighted quote block."
    echo "The user must not be able to overlook it. Do not bury it in the middle of your response."
    echo "Also remind the user that the unlock is TWO commands — 'sudo chattr -i' for the kernel flag"
    echo "and a plain 'chmod u+w' for the read-only mode a previous update left behind — and that they"
    echo "must run 'sudo chattr +i' afterward to re-apply the kernel-level lock. Without the relock the"
    echo "immutable protection is gone until next session. Show BOTH relock options from step 4 — (A)"
    echo "full lock and (B) lock without settings.json — each as its own fenced command block, and give"
    echo "the reason (B) exists (the VSCode model picker keeps working) together with its cost (the main"
    echo "file, settings.json, loses the kernel lock and is then guarded only by the regex hooks, which"
    echo "only police Claude — a limited but real risk). Do not call that risk small or negligible. Say"
    echo "that (A) plus a project-local model pin is the recommendation, then let the user choose; do not"
    echo "pick for them and do not shrink (B) to a side note. Claude can run neither 'sudo chattr' nor a"
    echo "write-enabling chmod on these files (both hard-blocked); when a write fails with 'Permission"
    echo "denied', stop and ask the user for the chmod rather than working around it."
    echo "When you proceed with $1, emit each file's command block as a separate Bash call, verbatim"
    echo "from the blocks above — do not introduce loops, variables for the repo slug or GitHub URL, or chmod 644/chattr."
}

# emit_changes — the "What this update adds" lines, under the version lines.
emit_changes() {
    echo "  What this update adds:"
    if ! $changes_fetched; then
        echo "    (CHANGELOG.md could not be fetched from origin/${tracking_ref} — ask Claude for the details)"
    fi
    local l
    for l in "${changes_lines[@]}"; do echo "    ${l}"; done
    [ "$changes_more" -gt 0 ] && echo "    … and ${changes_more} earlier version(s), listed in global-settings/CHANGELOG.md"
    echo "  Want to know more? Ask Claude for the details of these changes."
}

# emit_changes_instruction — how Claude relays the summary and, on request,
# digs into the commits and pull requests behind it.
emit_changes_instruction() {
    echo "WHAT THIS UPDATE ADDS: Show the 'What this update adds' lines from the notice word for word,"
    echo "directly under the Installed/Latest lines of your warning block, followed by one line telling"
    echo "the user they can ask you for more details about these changes. Do not look anything up yet."
    echo "If the user asks for more details, look deeper before answering — never expand on the summary"
    echo "sentence from memory. For each listed version, find the commit that set global-settings/VERSION"
    echo "to it (its subject ends in '(vX.Y.Z)'), read its full message and changed files, and find the"
    echo "pull request that merged it:"
    if [ -n "$changes_slug" ]; then
        echo "    gh api 'repos/${changes_slug}/commits?path=global-settings/VERSION&sha=${tracking_ref}&per_page=20' --jq '.[] | .sha[0:8] + \" \" + (.commit.message | split(\"\\n\")[0])'"
        echo "    gh api 'repos/${changes_slug}/commits/<sha>' --jq '.commit.message, (.files[] | .filename)'"
        echo "    gh api 'repos/${changes_slug}/commits/<sha>/pulls' --jq '.[] | .html_url + \" \" + .title'"
    fi
    if [ -n "$REPO_DIR" ]; then
        echo "    git -C '${REPO_DIR}' log 'origin/${tracking_ref}' --format='%h %s' -- '${rel_base}/VERSION'"
        echo "    git -C '${REPO_DIR}' show --stat <sha>"
    fi
    echo "Then explain per version what changed, why, and what it means for the user's daily work, and"
    if [ -n "$changes_slug" ]; then
        echo "link each pull request (https://github.com/${changes_slug}/pull/<n>), or the commit"
        echo "(https://github.com/${changes_slug}/commit/<sha>) when no pull request merged it."
    else
        echo "name each commit (short sha and subject); no GitHub repository is known to link to."
    fi
}

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
    emit_changes
    echo ""
    emit_unlock_steps "the update" "update my global settings to ${online_version}"
    echo ""
    emit_contract
    echo ""
    emit_file_blocks settings.json "${managed_hooks[@]}" VERSION
    echo ""
    emit_claude_instruction "the update"
    emit_changes_instruction
    echo "=========================================="
    echo ""

# Version matches, files do not — just as prominent, repairs only what differs
elif $integrity_ran && [ "$integrity_issues" -gt 0 ]; then
    echo "=========================================="
    echo "⚠️  NEW SESSION — GLOBAL CLAUDE SETTINGS: FILES OUT OF SYNC"
    echo "=========================================="
    echo ""
    echo "  Installed : v${installed_version}  ✅ (matches origin/${tracking_ref})"
    echo "  Files     : ${integrity_issues} of ${integrity_checked} installed files do not match the canonical v${installed_version} copies ❌"
    for f in "${files_missing[@]}"; do echo "    ❌ missing : ${f}"; done
    for f in "${files_changed[@]}"; do echo "    ❌ changed : ${f}"; done
    echo ""
    echo "  A hook that settings.json registers but that is missing never runs, so its guard is off;"
    echo "  a changed file is not the reviewed version. The version number alone does not show this,"
    echo "  which is why the files themselves are checked. Only the files listed above are rewritten."
    echo ""
    emit_unlock_steps "the repair" "repair my global settings"
    echo ""
    emit_contract
    echo ""
    _repair=()
    needs_repair settings.json && _repair+=(settings.json)
    for _h in "${managed_hooks[@]}"; do
        needs_repair "$_h" && _repair+=("$_h")
    done
    emit_file_blocks "${_repair[@]}"
    echo ""
    emit_claude_instruction "the repair"
    echo "=========================================="
    echo ""

# Settings up to date — brief session-start acknowledgement
elif $online_fetch_ok && semver_eq "$online_version" "$installed_version"; then
    _files_note=""
    if $integrity_ran; then
        if [ ${#files_unverified[@]} -eq 0 ]; then
            _files_note=" All ${integrity_checked} installed files match the canonical copies."
        else
            _files_note=" ${#files_unverified[@]} of ${integrity_checked} installed files could not be verified (see the configuration warning above)."
        fi
    fi
    if [ -n "$online_source_name" ]; then
        echo "NEW SESSION — Global Claude Settings checked. ✅ Settings are up to date (v${installed_version}, via ${online_source_name}).${_files_note}"
        echo "Briefly mention at the start of your response that a new session has started, that the global Claude settings are up to date, and name the source (${online_source_name})."
    else
        echo "NEW SESSION — Global Claude Settings checked. ✅ Settings are up to date (v${installed_version}).${_files_note}"
        echo "Briefly mention at the start of your response that a new session has started and the global Claude settings are up to date."
    fi
    echo ""

# Online version unknown but no other warning — still note session start
else
    echo "NEW SESSION — Global Claude Settings checked. Version comparison unavailable (could not reach origin/${tracking_ref})."
    echo "Briefly mention this at the start of your response, and suggest the user run /verify-global-settings-version to retry the check."
    echo ""
fi

exit 0
