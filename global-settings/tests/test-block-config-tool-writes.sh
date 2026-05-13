#!/usr/bin/env bash
# shellcheck disable=SC2016,SC2088 # literal $VAR / ~ tokens are intentional test fixtures fed to the hook as data
# test-block-config-tool-writes.sh — tests for the Write/Edit/MultiEdit hook
# added in v1.7.0. Verifies that the hook hard-denies:
#   (a) file_path targeting ~/.claude/ config files (defense in depth alongside
#       the deny rules in settings.json), and
#   (b) Write/Edit/MultiEdit calls that would create a script whose body
#       contains a write operation against a protected path.
#
# Usage:
#   ./tests/test-block-config-tool-writes.sh        # run all
#   ./tests/test-block-config-tool-writes.sh -v     # verbose
#   HOOK=/path/to/hook.sh ./tests/test-block-config-tool-writes.sh
#
# Exit 0 on full pass, 1 on any failure.

set -u
TEST_HOME="${TEST_HOME:-$HOME}"
HOOK="${HOOK:-$(cd "$(dirname "$0")/.." && pwd)/block-config-tool-writes.sh}"
VERBOSE=0; [[ "${1:-}" == "-v" ]] && VERBOSE=1

if [[ ! -r "$HOOK" ]]; then
    echo "ERROR: hook not found or unreadable: $HOOK" >&2
    exit 1
fi

declare -a TESTS_ALLOW TESTS_DENY
add_allow() { TESTS_ALLOW+=("$1"$'\t'"$2"); }
add_deny()  { TESTS_DENY+=("$1"$'\t'"$2"); }

# ── Input envelope builders ───────────────────────────────────────────────────
mk_write() {
    local file_path="$1" content="$2"
    jq -c -n --arg p "$file_path" --arg c "$content" \
        '{tool_name:"Write", tool_input:{file_path:$p, content:$c}, transcript_path:""}'
}
mk_edit() {
    local file_path="$1" new_string="$2"
    jq -c -n --arg p "$file_path" --arg n "$new_string" \
        '{tool_name:"Edit", tool_input:{file_path:$p, old_string:"x", new_string:$n}, transcript_path:""}'
}
mk_multi() {
    local file_path="$1"; shift
    local edits='['
    local sep=""
    for ns in "$@"; do
        edits+="${sep}$(jq -nc --arg n "$ns" '{old_string:"x", new_string:$n}')"
        sep=","
    done
    edits+=']'
    jq -c -n --arg p "$file_path" --argjson e "$edits" \
        '{tool_name:"MultiEdit", tool_input:{file_path:$p, edits:$e}, transcript_path:""}'
}
run_hook_with() { echo "$1" | bash "$HOOK" >/dev/null 2>&1; return $?; }

# ── Guard 1: protected file_path ─────────────────────────────────────────────
PROT=(
    "${TEST_HOME}/.claude/settings.json"
    "~/.claude/settings.json"
    "\$HOME/.claude/settings.json"
    "\${HOME}/.claude/settings.json"
    "${TEST_HOME}/.claude/settings-version"
    "${TEST_HOME}/.claude/settings-repo-path"
    "${TEST_HOME}/.claude/settings-repo-url"
    "${TEST_HOME}/.claude/settings-repo-ref"
    "${TEST_HOME}/.claude/hooks/block-write-commands.sh"
    "${TEST_HOME}/.claude/hooks/block-config-tool-writes.sh"
    "${TEST_HOME}/.claude/hooks/check-settings-version.sh"
    "${TEST_HOME}/.claude/hooks/any-other-hook.sh"
)
for p in "${PROT[@]}"; do
    add_deny "Write file_path=$p"     "$(mk_write "$p" "anything")"
    add_deny "Edit file_path=$p"      "$(mk_edit "$p" "anything")"
    add_deny "MultiEdit file_path=$p" "$(mk_multi "$p" "a" "b")"
done

# Non-protected paths must pass when content is innocuous.
for p in "/tmp/foo.sh" "${TEST_HOME}/project/main.py" "${TEST_HOME}/.config/some-app/x.json" "/var/log/app.log"; do
    add_allow "Write innocuous → $p" "$(mk_write "$p" "echo hi")"
done

# ── Guard 2: script content targets protected file ───────────────────────────
BAD_REDIRECT='#!/bin/bash
echo evil > $HOME/.claude/settings.json'
BAD_CP='#!/bin/bash
cp /tmp/x ~/.claude/settings.json'
BAD_RM='#!/bin/bash
rm -f $HOME/.claude/hooks/block-write-commands.sh'
BAD_CHATTR='#!/bin/bash
chattr -i $HOME/.claude/settings.json'
BAD_TEE='#!/bin/bash
echo evil | tee $HOME/.claude/settings.json'
BAD_SED='#!/bin/bash
sed -i s/a/b/ $HOME/.claude/settings.json'
GOOD_HELLO='#!/bin/bash
echo hello > /tmp/output.log'
GOOD_READS_ONLY='#!/bin/bash
# Reads ~/.claude/settings.json but never writes to it.
cat $HOME/.claude/settings.json | head -5'
GOOD_PURE_DOC='#!/bin/bash
# This script does nothing harmful.
echo "Documentation says: see ~/.claude/settings.json"'

# .sh extension → triggers content scan
for badname in redirect cp rm chattr tee sed; do
    case "$badname" in
        redirect) val="$BAD_REDIRECT" ;;
        cp)       val="$BAD_CP" ;;
        rm)       val="$BAD_RM" ;;
        chattr)   val="$BAD_CHATTR" ;;
        tee)      val="$BAD_TEE" ;;
        sed)      val="$BAD_SED" ;;
    esac
    add_deny "Write /tmp/x.sh — $badname" "$(mk_write "/tmp/x.sh" "$val")"
    add_deny "Edit /tmp/x.sh — $badname"  "$(mk_edit  "/tmp/x.sh" "$val")"
done
add_deny "MultiEdit /tmp/x.sh — one bad edit" "$(mk_multi "/tmp/x.sh" "echo a" "$BAD_REDIRECT" "echo b")"

# .py, .pl, .rb, .js, .ts also count as scripts.
add_deny "Write /tmp/x.py with rm of protected" \
    "$(mk_write "/tmp/x.py" "import os; os.system('rm ~/.claude/settings.json')")"

# /tmp + shebang triggers the scan even without a script extension.
add_deny "Write /tmp/wrapper (shebang, no ext)" "$(mk_write "/tmp/wrapper" "$BAD_REDIRECT")"

# Shebang-in-content triggers the scan regardless of path.
add_deny "Write /home/user/wrap (shebang, no ext)" "$(mk_write "${TEST_HOME}/wrap" "$BAD_REDIRECT")"

# Innocuous scripts: ALLOW.
add_allow "Write /tmp/x.sh hello"          "$(mk_write "/tmp/x.sh" "$GOOD_HELLO")"
add_allow "Write /tmp/x.sh reads-only"     "$(mk_write "/tmp/x.sh" "$GOOD_READS_ONLY")"
add_allow "Write /tmp/x.sh doc comment"    "$(mk_write "/tmp/x.sh" "$GOOD_PURE_DOC")"
add_allow "Edit /tmp/x.sh innocuous"       "$(mk_edit  "/tmp/x.sh" "$GOOD_HELLO")"
add_allow "MultiEdit /tmp/x.sh all clean"  "$(mk_multi "/tmp/x.sh" "echo a" "echo b" "echo c")"

# Non-script files referencing protected paths in docs must NOT trigger.
add_allow "Write /tmp/README.md mentions path" \
    "$(mk_write "/tmp/README.md" "Run \`chmod 644 ~/.claude/settings.json\` to unlock.")"
add_allow "Write /tmp/notes.txt mentions path" \
    "$(mk_write "/tmp/notes.txt" "Path: ~/.claude/settings.json")"
add_allow "Write /tmp/config.json with text" \
    "$(mk_write "/tmp/config.json" '{"path": "~/.claude/settings.json"}')"

# Empty content must not deny.
add_allow "Write /tmp/x.sh empty content"  "$(mk_write "/tmp/x.sh" "")"

# ── runner ────────────────────────────────────────────────────────────────────
pass=0; fail=0; fail_details=()
for t in "${TESTS_ALLOW[@]}"; do
    label="${t%%	*}"; inp="${t#*	}"
    run_hook_with "$inp"; ec=$?
    if [[ $ec -eq 2 ]]; then
        fail=$((fail+1)); fail_details+=("[ALLOW expected, DENIED] $label")
        [[ $VERBOSE -eq 1 ]] && echo "FAIL: $label"
    else
        pass=$((pass+1))
        [[ $VERBOSE -eq 1 ]] && echo "PASS: $label"
    fi
done
allow_pass=$pass; allow_fail=$fail; allow_total=${#TESTS_ALLOW[@]}

pass=0; fail=0
for t in "${TESTS_DENY[@]}"; do
    label="${t%%	*}"; inp="${t#*	}"
    run_hook_with "$inp"; ec=$?
    if [[ $ec -eq 2 ]]; then
        pass=$((pass+1))
        [[ $VERBOSE -eq 1 ]] && echo "PASS: $label"
    else
        fail=$((fail+1)); fail_details+=("[DENY expected, PASSED] $label")
        [[ $VERBOSE -eq 1 ]] && echo "FAIL: $label"
    fi
done
deny_pass=$pass; deny_fail=$fail; deny_total=${#TESTS_DENY[@]}

total=$((allow_total + deny_total))
total_pass=$((allow_pass + deny_pass))
total_fail=$((allow_fail + deny_fail))

echo
echo "═══════════════════════════════════════════════════════════"
echo "HOOK:   $HOOK"
echo "TOTAL:  $total"
echo "  ALLOW expected: $allow_total  (pass=$allow_pass, fail=$allow_fail)"
echo "  DENY  expected: $deny_total  (pass=$deny_pass,  fail=$deny_fail)"
echo "  OVERALL:        $total_pass / $total"
echo "═══════════════════════════════════════════════════════════"

if [[ $total_fail -gt 0 ]]; then
    echo
    echo "FAILURES (${#fail_details[@]} — first 40 shown):"
    printf '  %s\n' "${fail_details[@]}" | head -40
    exit 1
fi
exit 0
