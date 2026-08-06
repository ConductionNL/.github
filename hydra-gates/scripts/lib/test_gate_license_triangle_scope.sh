#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# test_gate_license_triangle_scope.sh — control-pair suite for gate-28's
# THREE-WAY distinction between "diff-scoped out", "a real gap", and "clean".
#
# WHY THIS EXISTS
# ---------------
# ConductionNL/.github#172 fixed a real defect: gate-28 reported PASS on repos
# where it had opened zero files, so a green said nothing. The fix made an
# empty read report `structural` instead — a claim that the REPOSITORY is
# missing licence declarations.
#
# But there are two ways to read zero files, and #172 gave them the same word:
#
#   (a) lib/**/*.php files exist and ARE in this diff, and none carries a tag
#       — a genuine gap in the repository, correctly `structural`;
#   (b) no lib/**/*.php file is in this diff AT ALL — diff-scoping working
#       exactly as ADR-020 designed it, and NOT a statement about the repo.
#
# (b) is the ordinary case: every workflow-only and frontend-only PR hits it.
# With `hydra-gates-require-full-coverage` on by default, calling it
# `structural` fails the run with exit 98 for a licence problem that does not
# exist. Measured on the fleet's own unpinning PRs — each a single-file
# workflow diff — hrmq#74 went from a CLEAN baseline to red on nothing but
# this, and app-versions#129, opencatalogi#813 and nextcloud-app-template#132
# named gate 28 as their only gate that did not run. hrmq's 168 lib PHP files
# all carry their tags; the gate had simply not been given any of them to read.
#
# THE RISK THIS SUITE GUARDS
# --------------------------
# The obvious "fix" — make an empty read NOT APPLICABLE — walks straight back
# into #172, because case (a) also reads zero files. A gate that stops failing
# is worse than the false positive it replaced. So every assertion here is one
# half of a control pair: for each state that must NOT fail the coverage
# verdict, there is a neighbouring fixture where the same code path MUST.
#
#   wf-only diff, tagged repo   -> NOT APPLICABLE  (b: diff-scoped out)
#   untagged PHP in the diff    -> structural      (a: the real gap, still red)
#   tagged PHP in the diff      -> PASS            (the gate actually compared)
#   no lib/ at all              -> NOT APPLICABLE  (#172's original case)
#
# Run: bash scripts/lib/test_gate_license_triangle_scope.sh  (exit 0 = green)
set -uo pipefail

PKG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../.." && pwd)"
RUNNER="${PKG_ROOT}/scripts/run-hydra-gates.sh"

_fail_n=0
_pass_n=0
_ok()  { _pass_n=$((_pass_n + 1)); printf 'PASS — %s\n' "$1"; }
_bad() { _fail_n=$((_fail_n + 1)); printf 'FAIL — %s\n' "$1"; }

_TMP="$(mktemp -d "${TMPDIR:-/tmp}/gate28-scope.XXXXXXXX")"
trap 'rm -rf "${_TMP}"' EXIT

_LICENSED_PHP='<?php
/**
 * @copyright Copyright (c) 2026 Conduction
 * @license   EUPL-1.2
 */

namespace OCA\Fixture;

class Tagged
{
    public function value(): int
    {
        return 1;
    }
}
'
_UNLICENSED_PHP='<?php

namespace OCA\Fixture;

class Untagged
{
    public function value(): int
    {
        return 2;
    }
}
'

# _mkrepo <name> <with-lib: yes|no>  — a committed base tree. Echoes the base SHA.
_REPO=""
_BASE=""
_mkrepo() {
    local _name="$1" _withlib="$2"
    _REPO="${_TMP}/${_name}"
    mkdir -p "${_REPO}/appinfo" "${_REPO}/.github/workflows"
    (
        cd "${_REPO}" || exit 1
        git init -q .
        git symbolic-ref HEAD refs/heads/development
        git config user.email "ci@example.invalid"
        git config user.name "gate28 test"
        printf '<?xml version="1.0"?>\n<info><id>fixture</id><version>1.0.0</version></info>\n' > appinfo/info.xml
        printf '{\n  "name": "conduction/fixture",\n  "license": "EUPL-1.2"\n}\n' > composer.json
        printf 'name: ci\non: push\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo base\n' > .github/workflows/ci.yml
        if [ "${_withlib}" = "yes" ]; then
            mkdir -p lib
            printf '%s' "${_LICENSED_PHP}" > lib/Tagged.php
        fi
        git add -A
        git commit -qm "base"
    ) >/dev/null 2>&1
    _BASE="$(git -C "${_REPO}" rev-parse HEAD)"
}

# _run — capture the run. A run that aborts before the COVERAGE line is not a
# result, however many PASS lines precede it.
_OUT=""
_run() {
    local _logdir
    _logdir="$(mktemp -d "${TMPDIR:-/tmp}/hydra-gate-test.XXXXXXXX")"
    _OUT="$(HYDRA_GATE_LOG_DIR="${_logdir}" bash "${RUNNER}" \
        --app-dir "${_REPO}" --base "${_BASE}" --scope-to-diff 2>&1 || true)"
    rm -rf "${_logdir}"
    if ! printf '%s' "${_OUT}" | grep -q '^\[hydra-gates\] COVERAGE:'; then
        _bad "run in ${_REPO} ABORTED before the summary — not a result"
        printf '%s\n' "${_OUT}" | tail -15 | sed 's/^/       /'
        return 1
    fi
    return 0
}

# _expect <PASS|NOT APPLICABLE|structural> <description>
_expect() {
    local _want="$1" _desc="$2" _line
    _line="$(printf '%s' "${_OUT}" | grep -E '^\[gate-28\] ' | head -1)"
    if [ -z "${_line}" ]; then
        _bad "${_desc} — gate-28 emitted NO line at all (a silent gate is the #147 shape)"
        return
    fi
    case "${_want}" in
        PASS)
            printf '%s' "${_line}" | grep -qE ': PASS' \
                && _ok "${_desc}" || _bad "${_desc} — got: ${_line}" ;;
        NOTAPPLICABLE)
            printf '%s' "${_line}" | grep -qE ': NOT APPLICABLE' \
                && _ok "${_desc}" || _bad "${_desc} — got: ${_line}" ;;
        structural)
            printf '%s' "${_line}" | grep -qE ': SKIPPED \(structural\)' \
                && _ok "${_desc}" || _bad "${_desc} — got: ${_line}" ;;
    esac
}

# --- 1. (b) THE FALSE RED. Repo HAS licensed lib PHP; the diff touches only a
#            workflow file. Nothing was withheld — there was nothing to read.
_mkrepo scope-wf-only yes
printf 'name: ci\non: push\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo changed\n' > "${_REPO}/.github/workflows/ci.yml"
git -C "${_REPO}" add -A >/dev/null 2>&1
git -C "${_REPO}" commit -qm "workflow-only change" >/dev/null 2>&1
if _run; then
    _expect NOTAPPLICABLE "workflow-only diff in a fully-tagged repo: diff-scoped out, not a gap"
    # And it must NOT be counted against coverage, or the taxonomy is cosmetic.
    #
    # THIS ASSERTION TOOK TWO TRIES TO MEASURE ANYTHING, and both failures are
    # worth naming because they are the same mistake in opposite directions:
    #
    #   v1  matched only `GATES THAT DID NOT RUN: 28`, a summary line the
    #       runner emits only under --require-full-coverage. This suite does
    #       not pass that flag, so the pattern matched nothing and the
    #       assertion passed against the FIXED and the UNFIXED runner alike —
    #       a dead assertion inside the suite whose entire purpose is to tell
    #       those two apart.
    #   v2  also matched the indented `[hydra-gates]   gate-28 <name>` roster
    #       — but the runner prints that roster for NOT-APPLICABLE gates too.
    #       So it fired on the correct behaviour and the assertion failed
    #       against the FIXED runner.
    #
    # The roster line is ambiguous on its own; only its HEADING disambiguates.
    # So read the did-not-run block specifically: from its heading up to the
    # next `[hydra-gates] <CAPITAL>` line that starts a new section.
    _didnotrun_block="$(printf '%s\n' "${_OUT}" \
        | sed -n '/^\[hydra-gates\] GATES THAT DID NOT RUN/,/^\[hydra-gates\] [A-Z].*[a-z]/p')"
    if printf '%s' "${_didnotrun_block}" | grep -qE '(^|[[:space:]])gate-28([[:space:]]|$)|DID NOT RUN:.*\b28\b'; then
        _bad "gate-28 was named in GATES THAT DID NOT RUN despite being NOT APPLICABLE — it will still fail the run under --require-full-coverage"
    else
        _ok "gate-28 excluded from the did-not-run tally"
    fi
fi

# --- 2. (a) THE CONTROL. Untagged lib PHP IS in the diff. This is a real gap
#            and MUST stay red, or this whole change is a mute for #172.
_mkrepo scope-untagged yes
printf '%s' "${_UNLICENSED_PHP}" > "${_REPO}/lib/Untagged.php"
rm -f "${_REPO}/lib/Tagged.php"
git -C "${_REPO}" add -A >/dev/null 2>&1
git -C "${_REPO}" commit -qm "add untagged lib PHP" >/dev/null 2>&1
if _run; then
    _expect structural "untagged lib PHP IN scope: still a structural gap (#172 preserved)"
fi

# --- 3. THE CLEAN PATH. Tagged lib PHP in the diff — the gate compared something.
_mkrepo scope-tagged yes
printf '%s' "${_LICENSED_PHP}" > "${_REPO}/lib/Second.php"
git -C "${_REPO}" add -A >/dev/null 2>&1
git -C "${_REPO}" commit -qm "add tagged lib PHP" >/dev/null 2>&1
if _run; then
    _expect PASS "tagged lib PHP in scope: gate-28 actually compared and passed"
fi

# --- 4. #172's ORIGINAL CASE. No lib/ at all — must remain NOT APPLICABLE and
#        must never be PASS, which is the bug #172 was opened for.
_mkrepo scope-no-lib no
printf 'name: ci\non: push\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo changed\n' > "${_REPO}/.github/workflows/ci.yml"
git -C "${_REPO}" add -A >/dev/null 2>&1
git -C "${_REPO}" commit -qm "workflow change, no lib/" >/dev/null 2>&1
if _run; then
    _expect NOTAPPLICABLE "no lib/ at all: NOT APPLICABLE, never PASS (#172)"
fi

echo
echo "== summary =="
echo "   passed: ${_pass_n}"
echo "   failed: ${_fail_n}"
if [ "${_pass_n}" -eq 0 ]; then
    echo "FAIL — zero assertions ran; an empty suite is not a green suite"
    exit 1
fi
[ "${_fail_n}" -eq 0 ] || exit 1
echo "ALL gate-28 scope control pairs PASSED"
exit 0
