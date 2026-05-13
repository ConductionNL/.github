#!/bin/bash
# Guard Write / Edit / MultiEdit tool calls against the "write a script that
# modifies ~/.claude/, then run it via Bash" bypass. Complements
# block-write-commands.sh (which guards the Bash tool) — together they cover
# both halves of that attack at separate enforcement points.
#
# Two checks:
#   1. file_path itself targets a protected ~/.claude/ config file. Hard-deny.
#      (Redundant with the Edit/Write deny rules in settings.json — kept here
#      so the hook continues to enforce even if the deny list is altered.)
#   2. file_path looks like a script (by extension, /tmp staging path with
#      shebang, or shebang in content) AND the content payload contains a
#      write operation targeting a protected file. Hard-deny.
#
# Acknowledged limitations: the content scan is regex-based and can be evaded
# by obfuscation (encoded content, path obfuscation via variables, etc.). It
# raises the bar but is not airtight — kernel-level immutability (chattr +i)
# is the only complete defense. See README.md "Security model".

input=$(cat)
tool_name=$(echo "$input" | jq -r '.tool_name // ""' 2>/dev/null)
file_path=$(echo "$input" | jq -r '.tool_input.file_path // ""' 2>/dev/null)

hard_deny() {
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$*"
    exit 2
}

# ── Protected-path regex (mirrors block-write-commands.sh) ───────────────────
# shellcheck disable=SC2016 # single quotes intentional: literal regex for sed
_h=$(printf '%s' "$HOME" | sed 's/[.[\*^$()+?{}|]/\\&/g')
_prot="(~|\\\$HOME|\\\$\\{HOME\\}|${_h})[\"']?/\.claude/(settings\.json|hooks/?|settings-version|settings-repo-path|settings-repo-url|settings-repo-ref)"

# ── Guard 1: file_path targets a protected file ──────────────────────────────
# The deny list in settings.json matches the unexpanded `~/.claude/...` form.
# Claude Code expands `~` and `$HOME` before invoking the hook in many cases,
# so we also match the expanded literal path.
if [ -n "$file_path" ]; then
    _expanded="$file_path"
    # shellcheck disable=SC2088,SC2016 # case patterns and ${var#…} prefixes match literal tokens — tilde/$HOME are intentionally NOT expanded
    case "$_expanded" in
        '~/'*)         _expanded="${HOME}/${_expanded#'~'/}" ;;
        '$HOME/'*)     _expanded="${HOME}/${_expanded#'$HOME/'}" ;;
        '${HOME}/'*)   _expanded="${HOME}/${_expanded#'${HOME}/'}" ;;
    esac
    case "$_expanded" in
        "${HOME}/.claude/settings.json" \
        | "${HOME}/.claude/settings-version" \
        | "${HOME}/.claude/settings-repo-path" \
        | "${HOME}/.claude/settings-repo-url" \
        | "${HOME}/.claude/settings-repo-ref" \
        | "${HOME}/.claude/hooks/"*)
            hard_deny "BLOCKED: Claude cannot ${tool_name} ~/.claude/ config files. Updates must run via canonical Bash commands (gh api / git show origin/main) that block-write-commands.sh validates."
            ;;
    esac
fi

# ── Guard 2: content payload scan ────────────────────────────────────────────
# Only triggers when the target file looks like a script — otherwise this would
# flag every Markdown doc that documents the update flow.

# Aggregate the content the tool would write (Write.content, Edit.new_string,
# MultiEdit.edits[].new_string joined).
content=""
case "$tool_name" in
    Write)
        content=$(echo "$input" | jq -r '.tool_input.content // ""' 2>/dev/null)
        ;;
    Edit)
        content=$(echo "$input" | jq -r '.tool_input.new_string // ""' 2>/dev/null)
        ;;
    MultiEdit)
        content=$(echo "$input" | jq -r '[.tool_input.edits[]?.new_string // empty] | join("\n")' 2>/dev/null)
        ;;
esac

[ -z "$content" ] && exit 0

# Cap content size to keep the hook fast against very large writes.
if [ ${#content} -gt 524288 ]; then
    content=${content:0:524288}
fi

# A file is treated as a script if any of these hold:
#   - extension is a known scripting extension
#   - path is under /tmp or /var/tmp AND the content starts with a shebang
#   - content starts with a shebang line (regardless of extension)
_looks_like_script=false
if echo "$file_path" | grep -qE '\.(sh|bash|zsh|fish|py|pl|rb|js|ts|mjs|cjs|lua|go)$'; then
    _looks_like_script=true
elif echo "$file_path" | grep -qE '^(/tmp|/var/tmp)/' && printf '%s' "$content" | head -1 | grep -qE '^#!'; then
    _looks_like_script=true
elif printf '%s' "$content" | head -1 | grep -qE '^#!'; then
    _looks_like_script=true
fi

$_looks_like_script || exit 0

# Look for a protected-path write inside the content. We replicate the
# operator set from block-write-commands.sh so behaviour matches whether the
# command lands at the Write step (here) or the Bash step (the other hook).
if printf '%s' "$content" | grep -qE "(>{1,2}[[:space:]]*[\"']?${_prot}|(^|[;&|[:space:](\"'\\\\])(cp|mv|rm|tee|chmod|chattr|truncate|shred|unlink|ln|dd|sed|wget|curl)\b[^|]*${_prot})"; then
    hard_deny "BLOCKED: this ${tool_name} would create a script whose body contains a write operation targeting ~/.claude/ config files. Writing then executing such a script bypasses the canonical update flow (gh api / git show origin/main)."
fi

exit 0
