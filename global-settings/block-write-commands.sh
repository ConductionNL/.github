#!/bin/bash
# Guard write operations for: ~/.claude/ config files (HARD BLOCK with canonical-repo check),
# curl, gh api, gh pr/issue/repo/release/workflow/run write subcommands,
# git push, git -C, git branch, git remote, env, date, cat, find, sort, awk, hostname
# WSL boundary: all paths and executables that would escape the Linux filesystem are hard-blocked.
# Most other write operations prompt for approval.
# git push is allowed only when the last user message contains an authorized phrase.

# Read stdin once so we can extract multiple fields from the hook payload
input=$(cat)
cmd=$(echo "$input" | jq -r '.tool_input.command // ""')
transcript_path=$(echo "$input" | jq -r '.transcript_path // ""')

deny() {
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$1"
    exit 0
}

ask() {
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"%s"}}\n' "$1"
    exit 0
}

# Returns 0 (true) if the last user message in the transcript contains an authorized push phrase.
# Authorized phrases (case-insensitive, words must appear in this order):
#   "push for me" | "commit and push" | "please push" | "push my changes"
# The transcript is a JSONL file; content may be a string or an array of content blocks.
git_push_authorized() {
    [[ -z "$transcript_path" || ! -f "$transcript_path" ]] && return 1
    local last_msg
    last_msg=$(jq -r 'select(.type == "user") | [.message.content[] | select(.type == "text") | .text] | join(" ")' \
        "$transcript_path" 2>/dev/null | grep -v '^[[:space:]]*$' | tail -1)
    echo "$last_msg" | grep -qiE '(push for me|commit and push|please git push|push my changes)'
}

PUSH_DENY_MSG="Blocked: git push requires explicit authorization. Include one of these phrases in your message: 'push for me', 'commit and push', 'please git push', or 'push my changes'."

# ── Claude config guard (HARD BLOCK) ─────────────────────────────────────────
# Prevent writes to protected ~/.claude/ config files.
# Canonical update source: ConductionNL/.github — origin/main only.
#
# Detects writes via: output redirect, cp/mv, variable+redirect (same command),
# tee, eval, bash/sh -c, and inline scripting (python, perl, node).
# Also hard-blocks chmod that makes protected files writable.
_h=$(printf '%s' "$HOME" | sed 's/[.[\*^$()+?{}|]/\\&/g')
_prot="(~|\\\$HOME|${_h})/\.claude/(settings\.json|hooks/|settings-version|settings-repo-path|settings-repo-url|settings-repo-ref)"

# chmod guard: deny write-enabling permissions on protected files
if echo "$cmd" | grep -qE "^\s*chmod\b" && echo "$cmd" | grep -qE "${_prot}"; then
    if echo "$cmd" | grep -qE "^\s*chmod\s+(444|555|-w|\+x)(\s|$)"; then
        : # read-only or execute-only — allowed
    else
        deny "BLOCKED: Claude cannot make ~/.claude/ config files writable. Run chmod manually in your own terminal if an update requires it."
    fi
fi

# Write guard: detect content writes to protected files
_is_config_write=false

# 1. Literal output redirect to a protected file
if echo "$cmd" | grep -qE ">{1,2}[[:space:]]*${_prot}"; then
    _is_config_write=true
fi
# 2. cp/mv with a protected file as destination
if echo "$cmd" | grep -qE "^\s*(cp|mv)\b" && echo "$cmd" | grep -qE "[[:space:]]${_prot}"; then
    _is_config_write=true
fi
# 3. Variable assigned to a protected path and used as redirect target (same command)
if echo "$cmd" | grep -qE "[a-zA-Z_][a-zA-Z0-9_]*=[\"']?(~|\\\$HOME|${_h})/\.claude/(settings\.json|hooks|settings-version|settings-repo-path|settings-repo-url|settings-repo-ref)" \
&& echo "$cmd" | grep -qE ">[[:space:]]*[\"']?\\\$[a-zA-Z_][a-zA-Z0-9_]*"; then
    _is_config_write=true
fi
# 4. tee targeting a protected file (literal or via variable assigned in same command)
if echo "$cmd" | grep -qE "\btee\b.*${_prot}"; then
    _is_config_write=true
fi
if echo "$cmd" | grep -qE "[a-zA-Z_][a-zA-Z0-9_]*=[\"']?(~|\\\$HOME|${_h})/\.claude/(settings\.json|hooks|settings-version|settings-repo-path|settings-repo-url|settings-repo-ref)" \
&& echo "$cmd" | grep -qE "\btee\b[^|]*\\\$[a-zA-Z_][a-zA-Z0-9_]*"; then
    _is_config_write=true
fi
# 5. eval / bash -c / sh -c with a literal protected path
if echo "$cmd" | grep -qE "\b(eval|bash|sh)\b.*${_prot}"; then
    _is_config_write=true
fi
# 6. Inline scripting languages with a literal protected path
if echo "$cmd" | grep -qiE "\b(python3?|perl|ruby|node|nodejs)\b.*-[ce]\b.*${_prot}"; then
    _is_config_write=true
fi

if $_is_config_write; then
    if echo "$cmd" | grep -qE "\bgit\b.*\bshow\b.*\borigin/main:"; then
        # Method 1: git show origin/main — verify canonical repo
        _repo_path=$(cat "$HOME/.claude/settings-repo-path" 2>/dev/null | tr -d '[:space:]')
        _git_root=""
        [ -n "$_repo_path" ] && [ -d "$_repo_path" ] && \
            _git_root=$(git -C "$_repo_path" rev-parse --show-toplevel 2>/dev/null)
        if [ -n "$_git_root" ]; then
            _remote=$(git -C "$_git_root" remote get-url origin 2>/dev/null)
            if echo "$_remote" | grep -qE "ConductionNL/\.github(\.git|/|$)"; then
                : # canonical repo and main branch verified — allow
            else
                deny "BLOCKED: Config update rejected. Remote '${_remote:-unknown}' is not the canonical repo (ConductionNL/.github, main branch only)."
            fi
        else
            deny "BLOCKED: ~/.claude/settings-repo-path is missing or invalid. Cannot verify canonical repo."
        fi
    elif echo "$cmd" | grep -qE "\bgh\s+api\b.*ConductionNL/\.github.*contents/global-settings/"; then
        # Method 2: gh api — canonical repo verified by URL path
        : # canonical repo via GitHub API — allow
    else
        deny "BLOCKED: Claude cannot write to ~/.claude/ config files. Updates must use git show origin/main or gh api from ConductionNL/.github only."
    fi
fi

# ── curl ──────────────────────────────────────────────────────────────────────
if echo "$cmd" | grep -qE '^\s*curl\b'; then
    # Unambiguous write flags — check the full command string so that piped curl
    # invocations are also caught (e.g. curl url | curl -X POST url2).
    if echo "$cmd" | grep -qiE '(^|\s)(-[sviIkLSfnN]*X\s*(POST|PUT|DELETE|PATCH)|--request\s+(POST|PUT|DELETE|PATCH))' \
    || echo "$cmd" | grep -qiE '(^|\s)(--data|--data-raw|--data-binary|--data-urlencode|--data-ascii|--json|--upload-file|--form-string)(=|\s)' \
    || echo "$cmd" | grep -qiE '(^|\s)--form(=|\s)' \
    || echo "$cmd" | grep -qiE '(^|\s)--output(=|\s)'; then
        ask "curl write operation detected (non-GET method, data flags, or file output) — approve to proceed."
    fi
    # Ambiguous short flags (-o/-O, -d/-T/-F): these overlap with flags used by common
    # read-only commands (grep -o, awk -F). Check only within pipe segments that are
    # curl invocations so piped read tools do not cause false positives.
    _curl_write=false
    while IFS= read -r _seg; do
        if echo "$_seg" | grep -qE '^\s*curl\b'; then
            if echo "$_seg" | grep -qE '(^|\s)-[a-zA-Z]*[dTF](\s|=|$)' \
            || echo "$_seg" | grep -qE '(^|\s)-[a-zA-Z]*[oO](\s|=|[^a-zA-Z-])'; then
                _curl_write=true
                break
            fi
        fi
    done < <(echo "$cmd" | tr '|' '\n')
    if $_curl_write; then
        ask "curl write operation detected (data/upload/output short flags) — approve to proceed."
    fi
fi

# ── docker write operations ───────────────────────────────────────────────────
# Read-only docker commands are auto-approved via the allow list. This guard catches
# write/mutating subcommands anywhere in the command string — including when chained
# after an allowlisted read prefix (e.g. "docker network inspect X || docker network create Y").
if echo "$cmd" | grep -qE '\bdocker\b'; then
    if echo "$cmd" | grep -qE '\bdocker\s+(run|create|start|stop|restart|rm|kill|exec|build|pull|push|tag|rmi|commit|save|load|import|export|cp|rename|pause|unpause|update|wait|attach)\b' \
    || echo "$cmd" | grep -qE '\bdocker\s+container\s+(run|create|start|stop|restart|rm|kill|exec|rename|commit|cp|pause|unpause|update|wait|attach|prune)\b' \
    || echo "$cmd" | grep -qE '\bdocker\s+image\s+(build|pull|push|tag|rm|prune|import|load|save)\b' \
    || echo "$cmd" | grep -qE '\bdocker\s+network\s+(create|rm|connect|disconnect|prune)\b' \
    || echo "$cmd" | grep -qE '\bdocker\s+volume\s+(create|rm|prune)\b' \
    || echo "$cmd" | grep -qE '\bdocker\s+compose\s+(up|down|start|stop|restart|build|pull|push|rm|create|kill|run|exec)\b' \
    || echo "$cmd" | grep -qE '\bdocker\s+system\s+prune\b'; then
        ask "docker write/mutating operation detected — approve to proceed."
    fi
fi

# ── gh api ────────────────────────────────────────────────────────────────────
if echo "$cmd" | grep -qE '^\s*gh\s+api\b'; then
    if echo "$cmd" | grep -qiE '(^|\s)(--method\s+(POST|PUT|DELETE|PATCH)|-X\s*(POST|PUT|DELETE|PATCH))' \
    || echo "$cmd" | grep -qiE '(^|\s)--input(=|\s)' \
    || echo "$cmd" | grep -qiE '(^|\s)(--field|--raw-field)(=|\s)' \
    || echo "$cmd" | grep -qE '(^|\s)-[a-zA-Z]*[fF](\s|=|$)'; then
        ask "gh api write operation detected (non-GET method, --input, or field flags) — approve to proceed."
    fi
fi

# ── gh pr / issue / repo / release / workflow / run write guard ───────────────
# gh pr list, gh pr view, and similar read subcommands are auto-approved via the
# allow list. This guard catches write subcommands — whether standalone or chained
# with a read command (e.g. "gh pr list && gh pr merge 123"), preventing the
# allow-list prefix match from silently approving the entire command string.
if echo "$cmd" | grep -qE '\bgh\s+pr\s+(merge|close|edit|review|comment|create|reopen|ready|checkout)\b' \
|| echo "$cmd" | grep -qE '\bgh\s+issue\s+(create|close|edit|comment|reopen|delete|develop)\b' \
|| echo "$cmd" | grep -qE '\bgh\s+repo\s+(create|delete|edit|fork|rename|archive|unarchive)\b' \
|| echo "$cmd" | grep -qE '\bgh\s+release\s+(create|delete|edit|upload)\b' \
|| echo "$cmd" | grep -qE '\bgh\s+workflow\s+(run|enable|disable)\b' \
|| echo "$cmd" | grep -qE '\bgh\s+run\s+(cancel|rerun|delete)\b'; then
    ask "gh write operation detected (merge/close/create/edit/etc.) — approve to proceed."
fi

# ── git -C (allowlist — known read-only subcommands pass silently; write ops prompt) ──
if echo "$cmd" | grep -qE '^\s*git\b' && echo "$cmd" | grep -qE '\s-C\s'; then
    # Extract subcommand: strip 'git', all '-C <path>' pairs, then leading flags
    subcmd=$(echo "$cmd" \
        | sed 's/^\s*git\s*//' \
        | sed ':a; s/-C[[:space:]]\+[^[:space:]]\+[[:space:]]*//; ta' \
        | sed -E 's/(^|[[:space:]])-{1,2}[a-zA-Z][a-zA-Z-]*//g' \
        | awk '{print $1}')

    case "$subcmd" in
        # Unconditionally read-only — pass silently
        log|status|diff|show|blame|ls-files|ls-tree|rev-parse|rev-list|\
        describe|shortlog|cat-file|for-each-ref|name-rev|check-ignore|\
        check-attr|grep|verify-commit|verify-tag|count-objects|fsck|fetch)
            : # allowed
            ;;
        reflog)
            if echo "$cmd" | grep -qE '\breflog\s+(delete|expire|drop)\b'; then
                ask "git -C reflog delete/expire/drop modifies reflog history — approve to proceed."
            fi
            ;;
        stash)
            if ! echo "$cmd" | grep -qE '\bstash\s+(list|show)\b'; then
                ask "git -C stash (non-list/show) modifies the stash — approve to proceed."
            fi
            ;;
        config)
            if ! echo "$cmd" | grep -qE '\bconfig\b.*(--get|--list|--show-origin|--show-scope)\b'; then
                ask "git -C config without --get/--list modifies git configuration — approve to proceed."
            fi
            ;;
        push)
            if git_push_authorized; then
                : # authorized by user message — allow
            else
                deny "$PUSH_DENY_MSG"
            fi
            ;;
        branch)
            if echo "$cmd" | grep -qE '\bbranch\b.*-[a-zA-Z]*[dDmMcC]'; then
                ask "git -C branch with -d/-D/-m/-M/-c/-C modifies branches — approve to proceed."
            fi
            ;;
        remote)
            if echo "$cmd" | grep -qE '\bremote\s+(add|remove|rename|set-url|set-head|prune|update)\b'; then
                ask "git -C remote add/remove/rename/set-url modifies remotes — approve to proceed."
            fi
            ;;
        "")
            : # bare 'git -C path' with no subcommand — prints help, harmless
            ;;
        *)
            ask "git -C '$subcmd' is not in the read-only allowlist — approve to proceed."
            ;;
    esac
fi

# ── git push (all forms: direct, chained with &&/;, etc.) ────────────────────
# Uses \b word boundary (not ^ anchor) so it also catches "cd /path && git push".
# git -C ... push is handled above; this catches everything else.
if echo "$cmd" | grep -qE '\bgit\s+push\b'; then
    if git_push_authorized; then
        : # authorized by user message — allow
    else
        deny "$PUSH_DENY_MSG"
    fi
fi

# ── git branch (prompt for write flags, bare — without -C) ───────────────────
if echo "$cmd" | grep -qE '^\s*git\s+branch\b' && ! echo "$cmd" | grep -qE '\s-C\s'; then
    if echo "$cmd" | grep -qE '\bbranch\b.*-[a-zA-Z]*[dDmMcC]' \
    || echo "$cmd" | grep -qiE '(^|\s)(--delete|--move|--copy|--force-create)(\s|=|$)'; then
        ask "git branch with write flags (-d/-D/-m/-M/-c/-C) modifies branches — approve to proceed."
    fi
fi

# ── git remote (prompt for write subcommands, bare — without -C) ─────────────
if echo "$cmd" | grep -qE '^\s*git\s+remote\b' && ! echo "$cmd" | grep -qE '\s-C\s'; then
    if echo "$cmd" | grep -qE '\bremote\s+(add|remove|rename|set-url|set-head|prune|update)\b'; then
        ask "git remote add/remove/rename/set-url/prune/update modifies remotes — approve to proceed."
    fi
fi

# ── env (prompt when used to execute a command) ───────────────────────────────
if echo "$cmd" | grep -qE '^\s*env\b'; then
    remainder=$(echo "$cmd" | sed 's/^\s*env\s*//')
    if [ -n "$remainder" ] && echo "$remainder" | tr ' \t' '\n' | grep -qE '^([a-z][a-zA-Z0-9_.-]*|[./][^[:space:]]*)$'; then
        ask "env used to execute a command — approve to proceed."
    fi
fi

# ── date (HARD BLOCK: modifying system time — no legitimate use case) ─────────
if echo "$cmd" | grep -qE '^\s*date\b'; then
    if echo "$cmd" | grep -qE '(^|\s)(-s\s|--set[[:space:]=])'; then
        deny "Blocked: date -s / --set modifies the system clock. This is never allowed."
    fi
fi

# ── cat (prompt for output redirection) ──────────────────────────────────────
if echo "$cmd" | grep -qE '^\s*cat\b'; then
    if echo "$cmd" | grep -qE '(^|[[:space:]])>{1,2}[[:space:]]*[^[:space:]]'; then
        ask "cat with output redirection (> or >>) would write to a file — approve to proceed."
    fi
fi

# ── find (prompt for destructive operations) ──────────────────────────────────
if echo "$cmd" | grep -qE '^\s*find\b'; then
    if echo "$cmd" | grep -qE '(^|\s)-delete\b' \
    || echo "$cmd" | grep -qE '(^|\s)-exec(dir)?\b'; then
        ask "find with -delete or -exec/-execdir can modify the filesystem — approve to proceed."
    fi
fi

# ── sort (prompt for file output flags) ───────────────────────────────────────
if echo "$cmd" | grep -qE '^\s*sort\b'; then
    if echo "$cmd" | grep -qE '(^|\s)(-o[[:space:]]|--output[[:space:]=])' \
    || echo "$cmd" | grep -qE '(^|[[:space:]])>{1,2}[[:space:]]*[^[:space:]]'; then
        ask "sort with -o/--output or output redirection writes to a file — approve to proceed."
    fi
fi

# ── awk (prompt for file output operations) ───────────────────────────────────
if echo "$cmd" | grep -qE '^\s*awk\b'; then
    if echo "$cmd" | grep -qE 'print[[:space:]]*>{1,2}' \
    || echo "$cmd" | grep -qE "['\"][[:space:]]*>{1,2}[[:space:]]*[^[:space:]]"; then
        ask "awk with output redirection or print > file may write files — approve to proceed."
    fi
fi

# ── tee (prompt — writes output to a file) ───────────────────────────────────
# tee copies stdin to stdout AND to each named file — any real filename is a write.
# Harmless: bare tee (no args), tee /dev/null, tee /dev/stdout, tee /dev/stderr.
if echo "$cmd" | grep -qE '\btee\b'; then
    _tee_args=$(echo "$cmd" | grep -oP '(?<=\btee\b)[^|;&]*' | head -1)
    _tee_file=$(echo "$_tee_args" | tr ' \t' '\n' \
        | grep -vE '^(-[a-zA-Z]+|--|/dev/(null|stdout|stderr|fd/[0-9]+)|[0-9]+>?)$' \
        | grep -vE '^$' | head -1)
    if [ -n "$_tee_file" ]; then
        ask "tee writes to a file — approve to proceed."
    fi
fi

# ── hostname (prompt when setting system hostname) ────────────────────────────
if echo "$cmd" | grep -qE '^\s*hostname\b'; then
    remainder=$(echo "$cmd" | sed 's/^\s*hostname\s*//' | tr ' \t' '\n' | grep -vE '^-' | tr -d '[:space:]')
    if [ -n "$remainder" ]; then
        ask "hostname with a name argument sets the system hostname — approve to proceed."
    fi
fi

# ── rm (prompt for all deletions) ────────────────────────────────────────────
if echo "$cmd" | grep -qE '^\s*rm\b'; then
    if echo "$cmd" | grep -qE '(^|\s)-[a-zA-Z]*[rRfFdi]'; then
        ask "rm with recursive/force/directory flags detected — approve to proceed."
    else
        ask "rm will permanently delete files — approve to proceed."
    fi
fi

# ── rmdir (prompt — removes directories) ─────────────────────────────────────
if echo "$cmd" | grep -qE '^\s*rmdir\b'; then
    ask "rmdir will remove directories — approve to proceed."
fi

# ── npm audit (prompt for fix — modifies package.json and lock file) ─────────
if echo "$cmd" | grep -qE '^\s*npm\s+audit\b'; then
    if echo "$cmd" | grep -qE '\baudit\b.*\bfix\b'; then
        ask "npm audit fix modifies package.json and lock file — approve to proceed."
    fi
fi

# ── Generic output redirect guard ────────────────────────────────────────────
# Safety net: catch any command writing to a file via > or >> that was not
# already handled by a specific guard above (those guards exit 0 on match,
# so this only fires for unhandled commands).
# Excludes: /dev/null (harmless), fd-to-fd redirects like 2>&1 and >&2.
if echo "$cmd" | grep -qE '>{1,2}[[:space:]]*[^[:space:]&>/]' \
&& ! echo "$cmd" | grep -qE '>{1,2}[[:space:]]*/dev/null'; then
    ask "Output redirection to a file detected — approve to proceed."
fi

WSL_DENY_MSG="BLOCKED: This command would leave the WSL Ubuntu workspace. Claude must never navigate to, execute from, or access the Windows filesystem or Windows processes. All work must stay within the WSL Linux environment."

# ── WSL boundary guard ────────────────────────────────────────────────────────
# WSL mounts Windows drives at /mnt/<letter>/ (e.g. /mnt/c/ = C:\).
# Windows executables (*.exe) run via WSL interop spawn Windows-side processes.
# Both are hard-blocked: there is no legitimate reason to leave the WSL workspace.

# Block cd to Windows drive mount points (/mnt/c/, /mnt/d/, etc.)
# Matches: cd /mnt/c  |  cd /mnt/c/  |  cd /mnt/c/Users/...  (single-letter drive only)
if echo "$cmd" | grep -qE '(^|[;&|[:space:]])(cd)[[:space:]]+/mnt/[a-zA-Z](/|[[:space:]]|$)'; then
    deny "$WSL_DENY_MSG"
fi

# Block any command that references a Windows drive mount path (/mnt/<letter>/)
# Catches file reads, writes, cp, mv, rsync, etc. targeting Windows filesystem.
if echo "$cmd" | grep -qE '(^|[[:space:]])/mnt/[a-zA-Z](/|[[:space:]]|$)'; then
    deny "$WSL_DENY_MSG"
fi

# Block Windows executables run via WSL interop (named or path-referenced *.exe)
# Covers: cmd.exe, powershell.exe, pwsh.exe, explorer.exe, wsl.exe, notepad.exe, etc.
if echo "$cmd" | grep -qiE '(^|[[:space:]/])[^[:space:]]*\.exe([[:space:]]|$)'; then
    deny "$WSL_DENY_MSG"
fi

# Block wsl / wsl.exe without extension (e.g. `wsl --exec`, `wsl -e cmd`)
# The wsl binary itself can run commands on the Windows host or switch distros.
if echo "$cmd" | grep -qiE '(^|[[:space:]])(wsl)([[:space:]]|$)'; then
    deny "$WSL_DENY_MSG"
fi

exit 0
