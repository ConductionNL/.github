#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# gate-118 (spec-screens): acceptance over a REAL git history, through the
# real runner.
#
# A DELTA gate cannot be covered by a `gate-acceptance/` bundle: that format
# has no git history, so the gate could only report NOT APPLICABLE there. The
# rule-by-rule arms live in test_check_spec_screens.py. This suite pins what
# only the runner can get wrong: the verdict word, the scope, and the blocking.
#
#   ARM 1  a touched spec with `No board found yet` FAILS, and the finding is
#          printed and counted in the run's failures (no warning period)
#   ARM 2  a touched change naming a real board PASSES, with the census line
#   ARM 3  inherited debt: a base carrying `No board found yet` and a change
#          that touches no openspec directory is NOT APPLICABLE
#   ARM 4  archiving a change judges the archive directory, not the old path
#   ARM 5  no delta base is NOT APPLICABLE, never PASS
#   ARM 6  an unreachable design-system is SKIPPED (wiring), never PASS
#
# The board list is a local copy (HYDRA_GATE_SCREENS_SOURCE), so no arm needs
# the network.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
RUNNER="${SCRIPT_DIR}/../run-hydra-gates.sh"

_fail_n=0
_ok()  { printf '  ok:   %s\n' "$1"; }
_bad() { _fail_n=$((_fail_n + 1)); printf '  FAIL: %s\n' "$1"; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/gate118-scope.XXXXXXXX")"
trap 'rm -rf "${WORK}"' EXIT
DS="${WORK}/ds"
APP="${WORK}/app"
mkdir -p "${DS}/preview/screens" "${DS}/screens-src/zuiddrecht/apps" "${APP}/appinfo"
printf '{"boards": {"FxStart": {"id": "fixture/FxStart", "app": "fixture"}}}\n' > "${DS}/preview/screens/screens.json"
printf '{"boards": {}}\n' > "${DS}/screens-src/zuiddrecht/apps/fixture.json"
export HYDRA_GATE_SCREENS_SOURCE="${DS}"

cat > "${APP}/appinfo/info.xml" <<'XML'
<?xml version="1.0"?>
<info>
    <id>fixture</id>
    <name>Fixture</name>
    <version>1.0.0</version>
</info>
XML

_screens() {  # <dir> <bullet>
    mkdir -p "$1"
    printf '# Screens\n\n- %s\n' "$2" > "$1/screens.md"
}

cd "${APP}" || exit 1
git init --quiet .
git config user.email fixture@example.invalid
git config user.name Fixture

# ── base: one spec with a real board, one change with a real board.
mkdir -p openspec/specs/cases openspec/changes/add-start
echo "# cases" > openspec/specs/cases/spec.md
_screens openspec/specs/cases "FxStart https://identity.conduction.nl/screens/board?id=fixture/FxStart"
echo "# add start" > openspec/changes/add-start/proposal.md
_screens openspec/changes/add-start "FxStart"
echo "x" > README.md
git add -A && git commit --quiet -m "base"
git branch -M base

# ── unsettled: the change edits a spec whose screens.md is unsettled.
git checkout --quiet -b unsettled
_screens openspec/specs/cases "No board found yet (decision 150)"
echo "more" >> openspec/specs/cases/spec.md
git add -A && git commit --quiet -m "unsettled spec"

# ── clean: the change edits the change dir, which names a real board.
git checkout --quiet base
git checkout --quiet -b clean
echo "- [x] task" > openspec/changes/add-start/tasks.md
git add -A && git commit --quiet -m "tick a task"

# ── debt-base / unrelated: the base already carries an unsettled spec, and
#    the change touches only the README.
git checkout --quiet base
git checkout --quiet -b debt-base
_screens openspec/specs/cases "No board found yet (decision 150)"
git add -A && git commit --quiet -m "inherited debt"
git checkout --quiet -b unrelated
echo "y" >> README.md
git add -A && git commit --quiet -m "an unrelated change"

# ── archived: the change moves to archive/ without its screens.md.
git checkout --quiet base
git checkout --quiet -b archived
mkdir -p openspec/changes/archive
git mv openspec/changes/add-start openspec/changes/archive/2026-10-10-add-start
git rm --quiet -f openspec/changes/archive/2026-10-10-add-start/screens.md
git commit --quiet -m "archive add-start, losing screens.md"

_run() {  # <branch> [extra runner args...]
    local _b="$1"; shift
    git checkout --quiet "${_b}"
    mkdir -p "${WORK}/logs-${_b}"
    HYDRA_GATE_LOG_DIR="${WORK}/logs-${_b}" bash "${RUNNER}" "$@" "${APP}" 2>&1
}

_verdict() {
    printf '%s\n' "$1" | grep -E '^\[gate-118\] spec-screens: (PASS|FAIL|WARNING|SKIPPED|NOT APPLICABLE)' | head -1
}

echo "-- ARM 1: an unsettled touched spec FAILS and blocks --"
_out="$(_run unsettled --base base)"
_v="$(_verdict "${_out}")"
case "${_v}" in
    *FAIL*) _ok "gate-118 reports FAIL on 'No board found yet' in a touched spec" ;;
    *)      _bad "expected FAIL on the unsettled branch, got: ${_v:-<no gate-118 verdict line>}" ;;
esac
if printf '%s\n' "${_out}" | grep -q 'openspec/specs/cases/screens.md:3: .No board found yet'; then
    _ok "the finding names the file and line"
else
    _bad "the finding is not printed with file and line"
fi
if printf '%s\n' "${_out}" | grep -qE '^\[gate-118\] spec-screens: WARNING'; then
    _bad "gate-118 printed a WARNING; decision 151 makes it blocking from day one"
else
    _ok "no WARNING verdict: the gate blocks"
fi

echo "-- ARM 2: a touched change with a real board PASSES --"
_out="$(_run clean --base base)"
_v="$(_verdict "${_out}")"
case "${_v}" in
    *PASS*) _ok "a change naming FxStart passes" ;;
    *)      _bad "expected PASS on the clean branch, got: ${_v:-<no verdict>}" ;;
esac
case "${_out}" in
    *"[gate-118] spec-screens: checked 1 dir(s), 1 board line(s)"*) _ok "the census line shows it read the change directory" ;;
    *) _bad "no census line for the clean branch" ;;
esac

echo "-- ARM 3: inherited debt is not this change's problem --"
_v="$(_verdict "$(_run unrelated --base debt-base)")"
case "${_v}" in
    *"NOT APPLICABLE"*) _ok "a README-only change is not judged, though the base carries an unsettled spec" ;;
    *)                  _bad "expected NOT APPLICABLE on a README-only change, got: ${_v:-<no verdict>}" ;;
esac

echo "-- ARM 4: archiving judges the archive directory --"
_out="$(_run archived --base base)"
_v="$(_verdict "${_out}")"
case "${_v}" in
    *FAIL*) _ok "an archived change without screens.md fails" ;;
    *)      _bad "expected FAIL on the archived branch, got: ${_v:-<no verdict>}" ;;
esac
if printf '%s\n' "${_out}" | grep -q 'openspec/changes/archive/2026-10-10-add-start/: no screens.md'; then
    _ok "the finding names the archive path, not the old one"
else
    _bad "the archive directory is not named"
fi

echo "-- ARM 5: no delta base is NOT APPLICABLE, never PASS --"
_v="$(_verdict "$(_run unsettled --full)")"
case "${_v}" in
    *"NOT APPLICABLE"*) _ok "with no base the gate says it had nothing to judge" ;;
    *)                  _bad "expected NOT APPLICABLE with no base, got: ${_v:-<no verdict>}" ;;
esac

echo "-- ARM 6: an unreachable design-system is SKIPPED, never PASS --"
_v="$(_verdict "$(HYDRA_GATE_SCREENS_SOURCE='' HYDRA_GATE_SCREENS_REPO_URL='http://127.0.0.1:9' _run clean --base base)")"
case "${_v}" in
    *"SKIPPED (wiring)"*) _ok "board lines that could not be checked are not a pass" ;;
    *)                    _bad "expected SKIPPED (wiring) with design-system unreachable, got: ${_v:-<no verdict>}" ;;
esac

echo ""
if [ "${_fail_n}" -eq 0 ]; then
    echo "gate-118 spec-screens acceptance: all arms passed."
    exit 0
fi
echo "gate-118 spec-screens acceptance: ${_fail_n} arm(s) failed."
exit 1
