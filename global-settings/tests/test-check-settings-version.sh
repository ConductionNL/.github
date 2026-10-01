#!/usr/bin/env bash
# shellcheck disable=SC2016 # literal $HOME tokens in expected output are fixtures, not expansions
# test-check-settings-version.sh — offline test harness for check-settings-version.sh.
#
# Builds a throwaway canonical repo (a file:// origin holding this directory's
# global-settings/), a clone the hook can `git fetch` from, and a fake home with
# an installed copy. The first part runs without settings-repo-url, so the hook
# takes the git-fetch path; the second part configures it and puts a curl shim
# in PATH that serves the same canonical files, so the GitHub path is exercised
# too. Nothing touches the network. Asserts:
#   - the update notice lists every hook the canonical settings.json registers,
#     derived rather than hand-maintained: a hook registered only in
#     settings.json appears without any change to the hook script itself
#   - a matching install is reported up to date, with every file verified
#   - a missing or changed hook, or a changed settings.json, is reported
#     FILES OUT OF SYNC with repair blocks for those files only
#   - a settings.json that only gained `model`, `modelSettings` or another
#     model-choice key (the picker's and /effort's writes under relock
#     option B) and a trailing-newline difference are not drift
#
# Usage:
#   ./tests/test-check-settings-version.sh            # run all
#   ./tests/test-check-settings-version.sh -v         # verbose
#   HOOK=/path/to/hook.sh ./tests/test-check-settings-version.sh
#
# Exit code: 0 if all tests pass, 1 if any fail. The harness carries its own
# positive control: it first proves the hook reports an install pinned to v0.0.1
# as outdated, so an unreadable or empty hook cannot read as green.

set -u
SRC_DIR="$(cd "$(dirname "$0")/.." && pwd)"          # the global-settings/ under test
HOOK="${HOOK:-$SRC_DIR/check-settings-version.sh}"
VERBOSE=0; [[ "${1:-}" == "-v" ]] && VERBOSE=1

for tool in git jq realpath md5sum; do
    command -v "$tool" >/dev/null 2>&1 || { echo "ERROR: $tool is required" >&2; exit 1; }
done
if [[ ! -r "$HOOK" ]]; then
    echo "ERROR: hook not found or unreadable: $HOOK" >&2
    exit 1
fi

# ── fixture: canonical origin, clone, fake home ──────────────────────────────
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
FAKE_HOME="$TMP/home"
CLAUDE_DIR="$FAKE_HOME/.claude"
HOOKS_DIR="$CLAUDE_DIR/hooks"
CANON="$TMP/canon"; CANON_GS="$CANON/global-settings"; CLONE="$TMP/clone"
mkdir -p "$HOOKS_DIR" "$TMP/run" "$CANON_GS"

export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
export GIT_AUTHOR_NAME=test GIT_AUTHOR_EMAIL=test@example.invalid
export GIT_COMMITTER_NAME=test GIT_COMMITTER_EMAIL=test@example.invalid

cp -R "$SRC_DIR"/. "$CANON_GS/"
rm -rf "$CANON_GS/tests"
git -C "$CANON" init -q
git -C "$CANON" symbolic-ref HEAD refs/heads/main
git -C "$CANON" add -A
git -C "$CANON" commit -q -m "canonical global settings"
git clone -q "file://$CANON" "$CLONE"
echo "$CLONE" > "$CLAUDE_DIR/settings-repo-path"

# canon_hooks — the hook basenames the canonical settings.json registers.
canon_hooks() {
    jq -r '.hooks // {} | .[]? | .[]? | (.hooks // [])[]? | .command? // empty' "$CANON_GS/settings.json" \
        | grep -oE '\.claude/hooks/[a-zA-Z0-9_.-]+\.sh' | sed 's#.*/##' | sort -u
}

# install_all — a fresh install of the canonical files into the fake home, the
# way the README's Install step does it.
install_all() {
    rm -rf "$HOOKS_DIR"; mkdir -p "$HOOKS_DIR"
    cp "$CANON_GS/settings.json" "$CLAUDE_DIR/settings.json"
    local h
    for h in $(canon_hooks); do cp "$CANON_GS/$h" "$HOOKS_DIR/$h"; done
    cp "$CANON_GS/VERSION" "$CLAUDE_DIR/settings-version"
}

# run_hook — runs the hook against the fake home; stdout in $OUT, stderr in $ERR.
# A fresh transcript path per run defeats the session-once guard. RUN_PATH is
# the PATH the hook sees; the GitHub part prepends the curl shim to it.
n=0
RUN_PATH="$PATH"
run_hook() {
    n=$((n + 1))
    OUT=$(printf '{"transcript_path":"%s/transcript-%d.jsonl"}' "$TMP" "$n" \
        | HOME="$FAKE_HOME" XDG_RUNTIME_DIR="$TMP/run" PATH="$RUN_PATH" bash "$HOOK" 2>"$TMP/stderr")
    ERR=$(cat "$TMP/stderr")
}

pass=0; fail=0; details=()
check() {   # $1 = description, $2 = exit code of the assertion (0 = pass)
    if [[ "$2" -eq 0 ]]; then
        pass=$((pass + 1)); [[ $VERBOSE -eq 1 ]] && echo "ok   $1"
    else
        fail=$((fail + 1)); details+=("$1")
    fi
}
has()  { grep -qF -- "$1" <<<"$OUT"; }
lacks() { ! grep -qF -- "$1" <<<"$OUT"; }
eq()   { [[ "$1" == "$2" ]]; }
# fixture_restored — the canonical repo is back to this directory's contents
fixture_restored() {
    [[ "$(cat "$CANON_GS/VERSION")" == "$(cat "$SRC_DIR/VERSION")" && ! -e "$CANON_GS/extra-guard.sh" ]]
}
# block_for <name> — the fetch line of the update/repair block for <name>, in the
# shape of the path under test (git show, or the literal canonical URL).
MODE=git
block_for() {
    if [[ "$MODE" == raw ]]; then
        has "content=\$(curl -fsSL --max-time 10 'https://raw.githubusercontent.com/ConductionNL/.github/main/global-settings/$1')"
    else
        has "show 'origin/main:global-settings/$1' >"
    fi
}
# last_fetched — the name in the last update/repair block; VERSION must be last.
last_fetched() {
    if [[ "$MODE" == raw ]]; then
        grep -oE "/global-settings/[A-Za-z0-9_.-]+'\)" <<<"$OUT" | tail -1 | sed -E "s#/global-settings/([^']+)'\)#\1#"
    else
        grep -oE "origin/main:global-settings/[A-Za-z0-9_.-]+" <<<"$OUT" | tail -1 | sed 's#.*/##'
    fi
}

# ── positive control ─────────────────────────────────────────────────────────
install_all
echo 0.0.1 > "$CLAUDE_DIR/settings-version"
run_hook
if ! has 'UPDATE REQUIRED'; then
    echo "POSITIVE CONTROL FAILED: an install pinned to v0.0.1 was not reported as outdated" >&2
    echo "--- stdout ---"; echo "$OUT"; echo "--- stderr ---"; echo "$ERR"
    exit 1
fi

# ── 1. the update notice lists every registered hook, and VERSION last ───────
for h in block-polling.sh block-write-commands.sh check-settings-version.sh \
         block-config-tool-writes.sh sound-notify.sh user-hooks-dispatch.sh; do
    canon_hooks | grep -qx "$h"; check "canonical settings.json registers $h (extraction sanity)" $?
done
block_for settings.json; check "update: block for settings.json" $?
for h in $(canon_hooks); do
    block_for "$h"; check "update: block for registered hook $h" $?
done
block_for VERSION; check "update: block for VERSION" $?
eq "$(last_fetched)" VERSION; check "update: VERSION block is emitted last" $?
has 'Then say: "update my global settings to'; check "update: phrase present" $?
has 'sudo chattr -i'; check "update: unlock steps present" $?
has 'sudo chattr +i'; check "update: relock steps present" $?
has 'mkdir -p ~/.claude/hooks'; check "update: hooks directory is created before the first hook" $?
lacks 'OUT OF SYNC'; check "update: no OUT OF SYNC notice alongside UPDATE REQUIRED" $?

# ── 2. the list follows settings.json: register a new hook upstream ──────────
printf '#!/bin/bash\nexit 0\n' > "$CANON_GS/extra-guard.sh"
jq '.hooks.PreToolUse += [{"matcher":"Bash","hooks":[{"type":"command","command":"bash ~/.claude/hooks/extra-guard.sh"}]}]' \
    "$CANON_GS/settings.json" > "$TMP/settings.new"
cat "$TMP/settings.new" > "$CANON_GS/settings.json"
echo 9.9.9 > "$CANON_GS/VERSION"
git -C "$CANON" add -A
git -C "$CANON" commit -q -m "register extra-guard.sh"
run_hook
has 'UPDATE REQUIRED'; check "derived: a bumped canonical VERSION triggers the update notice" $?
block_for extra-guard.sh; check "derived: a hook registered only in settings.json appears in the update list" $?
git -C "$CANON" revert --no-edit HEAD >/dev/null
fixture_restored; check "derived: canonical repo restored for the remaining scenarios (fixture sanity)" $?

# ── 3. matching install: up to date, every file verified ─────────────────────
install_all
run_hook
has 'Settings are up to date'; check "clean: reported up to date" $?
has 'installed files match the canonical copies'; check "clean: files reported as verified" $?
lacks 'OUT OF SYNC'; check "clean: no OUT OF SYNC notice" $?
lacks 'UPDATE REQUIRED'; check "clean: no UPDATE REQUIRED notice" $?
grep -q 'verified ✓' <<<"$ERR"; check "clean: panel shows files verified" $?

# ── 4. a registered hook is missing ──────────────────────────────────────────
install_all
rm "$HOOKS_DIR/block-polling.sh"
run_hook
has 'FILES OUT OF SYNC'; check "missing: OUT OF SYNC notice" $?
has 'missing : block-polling.sh'; check "missing: the hook is named" $?
block_for block-polling.sh; check "missing: repair block for the missing hook" $?
lacks "origin/main:global-settings/sound-notify.sh"; check "missing: no block for an intact hook" $?
lacks "origin/main:global-settings/settings.json"; check "missing: no block for an intact settings.json" $?
lacks "origin/main:global-settings/VERSION"; check "missing: VERSION is not rewritten" $?
has 'Then say: "repair my global settings"'; check "missing: repair phrase present" $?
has 'sudo chattr -i'; check "missing: unlock steps present" $?
lacks 'Settings are up to date'; check "missing: not reported up to date" $?
grep -q '1 missing, 0 changed' <<<"$ERR"; check "missing: panel counts it" $?

# ── 5. a registered hook has changed ─────────────────────────────────────────
install_all
echo '# local edit' >> "$HOOKS_DIR/sound-notify.sh"
run_hook
has 'FILES OUT OF SYNC'; check "changed: OUT OF SYNC notice" $?
has 'changed : sound-notify.sh'; check "changed: the hook is named" $?
block_for sound-notify.sh; check "changed: repair block for the changed hook" $?
lacks "origin/main:global-settings/block-polling.sh"; check "changed: no block for an intact hook" $?

# ── 6. trailing-newline differences are not drift ────────────────────────────
install_all
printf '\n\n' >> "$HOOKS_DIR/block-polling.sh"
run_hook
lacks 'OUT OF SYNC'; check "newline: extra trailing newlines are not drift" $?
has 'Settings are up to date'; check "newline: reported up to date" $?

# ── 7. settings.json with only `model` added is not drift ────────────────────
install_all
jq '.model = "opus"' "$CANON_GS/settings.json" > "$CLAUDE_DIR/settings.json"   # also reformats
run_hook
lacks 'OUT OF SYNC'; check "model: settings.json with only model added is not drift" $?
has 'Settings are up to date'; check "model: reported up to date" $?

# ── 7b. the effort and other model-choice keys are not drift either ─────────
install_all
jq '.model = "claude-opus-5-5[1m]"
    | .modelSettings = {"claude-opus-5-5": {"effortLevel": "low"}}
    | .effortLevel = "high" | .fastMode = true
    | .advisorModel = "opus" | .switchModelsOnFlag = false' \
    "$CANON_GS/settings.json" > "$CLAUDE_DIR/settings.json"
run_hook
lacks 'OUT OF SYNC'; check "effort: model-choice keys are not drift" $?
has 'Settings are up to date'; check "effort: reported up to date" $?

# ── 7c. a model-choice key next to a policy change still reports the policy ─
install_all
jq '.modelSettings = {"claude-opus-5-5": {"effortLevel": "low"}}
    | .permissions.allow += ["Bash(rm -rf /)"]' \
    "$CANON_GS/settings.json" > "$CLAUDE_DIR/settings.json"
run_hook
has 'changed : settings.json (top-level keys: permissions)'; check "effort: only the policy key is named" $?

# ── 8. settings.json with a permission change is drift, and names the key ────
install_all
jq '.permissions.allow += ["Bash(rm -rf /)"]' "$CANON_GS/settings.json" > "$CLAUDE_DIR/settings.json"
run_hook
has 'FILES OUT OF SYNC'; check "permissions: OUT OF SYNC notice" $?
has 'changed : settings.json (top-level keys: permissions)'; check "permissions: the differing key is named" $?
block_for settings.json; check "permissions: repair block for settings.json" $?
lacks "origin/main:global-settings/block-polling.sh"; check "permissions: no block for an intact hook" $?

# ── 9. settings.json that is not valid JSON is drift ─────────────────────────
install_all
echo '{ "hooks": ' > "$CLAUDE_DIR/settings.json"
run_hook
has 'changed : settings.json (top-level keys: not valid JSON)'; check "broken: invalid JSON is reported as changed" $?
block_for settings.json; check "broken: repair block for settings.json" $?

# ── GitHub path: the same checks through a curl shim ─────────────────────────
# In the field the GitHub raw URL is the primary source. The shim serves
# https://raw.githubusercontent.com/<slug>/<ref>/global-settings/<name> from
# $CURL_SHIM_ROOT/<name>: a bare URL prints to stdout (the VERSION probe), each
# `-o <dest> <url>` pair writes a file (the one-call multi-file fetch), and a
# name it does not have fails the way -f does: exit 22 and no output file.
mkdir -p "$TMP/bin" "$TMP/shimroot"
cat > "$TMP/bin/curl" <<'SHIM'
#!/usr/bin/env bash
rc=0; dest=""
while [ $# -gt 0 ]; do
    case "$1" in
        -o) dest="$2"; shift 2; continue ;;
        --max-time) shift 2; continue ;;
        -*) shift; continue ;;
    esac
    name="${1##*/}"; src="$CURL_SHIM_ROOT/$name"; shift
    if [ ! -f "$src" ]; then rc=22; dest=""; continue; fi
    if [ -n "$dest" ]; then cat "$src" > "$dest"; dest=""; else cat "$src"; fi
done
exit $rc
SHIM
chmod +x "$TMP/bin/curl"
cp -R "$CANON_GS"/. "$TMP/shimroot/"
export CURL_SHIM_ROOT="$TMP/shimroot"
echo "ConductionNL/.github" > "$CLAUDE_DIR/settings-repo-url"
RUN_PATH="$TMP/bin:$PATH"
MODE=raw

# R1. outdated install: every registered hook, curl-shaped, VERSION last
install_all
echo 0.0.1 > "$CLAUDE_DIR/settings-version"
run_hook
has 'UPDATE REQUIRED'; check "raw update: notice present" $?
has 'directly from GitHub'; check "raw update: GitHub path taken" $?
block_for settings.json; check "raw update: block for settings.json" $?
for h in $(canon_hooks); do
    block_for "$h"; check "raw update: block for registered hook $h" $?
done
block_for VERSION; check "raw update: block for VERSION" $?
eq "$(last_fetched)" VERSION; check "raw update: VERSION block is emitted last" $?
has "printf '%s\\n' \"\$content\" >"; check "raw update: content is written with printf, not curl -o" $?

# R2. matching install: up to date via GitHub, every file verified
install_all
run_hook
has 'Settings are up to date'; check "raw clean: reported up to date" $?
has 'via GitHub'; check "raw clean: source named" $?
has 'installed files match the canonical copies'; check "raw clean: files reported as verified" $?
lacks 'OUT OF SYNC'; check "raw clean: no OUT OF SYNC notice" $?
grep -q 'verified ✓' <<<"$ERR"; check "raw clean: panel shows files verified" $?

# R3. missing hook: repair block for that hook only, curl-shaped
install_all
rm "$HOOKS_DIR/block-polling.sh"
run_hook
has 'FILES OUT OF SYNC'; check "raw missing: OUT OF SYNC notice" $?
has 'missing : block-polling.sh'; check "raw missing: the hook is named" $?
block_for block-polling.sh; check "raw missing: repair block for the missing hook" $?
lacks "global-settings/sound-notify.sh')"; check "raw missing: no block for an intact hook" $?
lacks "global-settings/VERSION')"; check "raw missing: VERSION is not rewritten" $?

# R4. a canonical copy that cannot be fetched is reported, never assumed fine
install_all
rm "$TMP/shimroot/sound-notify.sh"
run_hook
lacks 'OUT OF SYNC'; check "raw unverified: an unfetchable canonical copy is not drift" $?
has 'could not be verified'; check "raw unverified: the up-to-date message says so" $?
has 'Could not fetch the canonical copy of: sound-notify.sh'; check "raw unverified: the file is named" $?
grep -q 'not verified' <<<"$ERR"; check "raw unverified: panel shows it" $?
cp "$CANON_GS/sound-notify.sh" "$TMP/shimroot/sound-notify.sh"

# ── summary ──────────────────────────────────────────────────────────────────
echo "check-settings-version: ${pass} passed, ${fail} failed"
for d in "${details[@]}"; do echo "  FAIL: $d"; done
[[ $fail -eq 0 ]]
