#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# test_gate16_spec_coverage_scope.sh — gate-16 at three scopes, one tree.
#
# WHY THIS EXISTS
# ---------------
# `.github#361`. gate-16 printed **PASS** on every `--full` run while inspecting
# nothing, and — unlike gate-61's `NOT APPLICABLE`, which is excluded from the
# coverage denominator — that PASS **counted toward "N of N applicable gates
# ran"**. So a full-scope "ALL APPLICABLE GATES PASSED" could contain a gate that
# opened no file at all. Measured on one tree, changing only the scope input:
# pipelinq 0 / 185 (origin/beta) / 1466 (report mode); openregister 0 / 232 / 234.
#
# Mechanism: `bin/hydra-gates` forwards `--base` only when the run is diff-scoped,
# so on `--full` the runner keeps its default `BASE_REF="origin/development"` and
# handed it to the checker unconditionally. On `development` itself that diffs the
# branch against itself: empty changed-line set, `# count=0`, PASS.
#
# THE FIX THIS SUITE PINS, and the two ways it could have gone wrong
# ------------------------------------------------------------------
# 1. NOT a full sweep. gate-19's else-branch drops `HYDRA_GATE_BASE_REF` and
#    scans the whole tree. Doing that for gate-16 would flag the ENTIRE legacy
#    `@spec` surface — the wrong contract under ADR-020, and a false RED in every
#    repo in the fleet. `LegacyDebtController.php` in this fixture is that legacy
#    surface, and arm 3 asserts it is NOT reported.
# 2. The skip category MUST be one of `na|structural|wiring`. `_skip`'s `*)` arm
#    turns anything else into `FAIL — internal error`, so a plausible-looking
#    category such as `scope` would have been the exact fleet-wide false RED the
#    change exists to avoid. Arm 3 asserts the verdict is NOT APPLICABLE and that
#    the run does not fail.
#
# `na` is also the only category that is honest AND free: `_NA_GATES` is
# subtracted from the applicable denominator and is explicitly exempt from
# `--require-full-coverage`, so this can neither hide a gap nor manufacture one.
#
# Run: bash scripts/lib/test_gate16_spec_coverage_scope.sh
set -uo pipefail

GF_PKG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../.." && pwd)"
export GF_PKG_ROOT
# shellcheck source=./gate_fixture_support.sh
. "${GF_PKG_ROOT}/scripts/lib/gate_fixture_support.sh"

SRC="${GF_PKG_ROOT}/scripts/test-fixtures/spec-coverage-scope/app"
CHECKER="${GF_PKG_ROOT}/scripts/lib/check_spec_coverage.py"

_fail_n=0; _pass_n=0
_ok()  { _pass_n=$((_pass_n + 1)); printf 'PASS — %s\n' "$1"; }
_bad() { _fail_n=$((_fail_n + 1)); printf 'FAIL — %s\n' "$1"; }

if [ ! -d "${SRC}" ]; then
    echo "FAIL — spec-coverage-scope fixture missing at ${SRC}; every assertion below would be vacuous."
    exit 1
fi
if [ ! -f "${CHECKER}" ]; then
    echo "FAIL — ${CHECKER} not found; the positive control below could not fire."
    exit 1
fi

WORK="$(mktemp -d "${TMPDIR:-/tmp}/hydra-gate16.XXXXXXXX")"
trap 'rm -rf "${WORK}"' EXIT

# ---------------------------------------------------------------------------
# The tree used by arms 1 and 3: legacy debt only, and a diff that touches docs.
# ---------------------------------------------------------------------------
gf_build_repo "${WORK}/inherited" "${SRC}"
gf_commit_all "${WORK}/inherited" "base: app carrying inherited @spec debt"
gf_mark_base  "${WORK}/inherited"
printf '\n- unrelated doc tweak\n' >> "${WORK}/inherited/docs/CHANGELOG.md"
gf_commit_paths "${WORK}/inherited" "docs: unrelated change" docs/CHANGELOG.md

# ===========================================================================
echo "== positive control: the legacy debt IS findable in this tree =="
# ===========================================================================
# Without this, a NOT APPLICABLE at full scope is ambiguous between "gate-16 is
# honest about an empty scope" and "the fixture contains nothing to find".
# `--mode report` is the checker's own NON-diff-scoped path: it walks every
# in-scope file and evaluates every method, so it answers exactly the question a
# control has to answer — is the subject matter in this tree at all — without
# depending on any base ref. (It is also the third column of the #361
# measurement: 0 / 185 / 1466.)
_pc="$(cd "${WORK}/inherited" && python3 "${CHECKER}" . --mode report 2>&1)"
_pc_count="$(printf '%s\n' "${_pc}" | grep -oE '"uncovered_count": [0-9]+' | grep -oE '[0-9]+' | tail -1)"
if printf '%s' "${_pc}" | grep -qF 'LegacyDebtController.php'; then
    _ok "positive control: the checker NAMES lib/Controller/LegacyDebtController.php when it is not diff-scoped"
else
    echo "FAIL — the positive control did not fire: check_spec_coverage.py named no"
    echo "       untagged method in a tree that contains two. EITHER the fixture stopped"
    echo "       carrying the plant OR the checker went blind. Both are fatal here, because"
    echo "       every arm below reads a NOT APPLICABLE as meaningful only if this control"
    echo "       proves the subject was findable. Refusing to grade."
    printf '%s\n' "${_pc}" | sed 's/^/       /'
    exit 1
fi
if [ "${_pc_count:-0}" -ge 2 ]; then
    _ok "positive control: ${_pc_count} untagged method(s) are present to be judged"
else
    _bad "positive control: expected at least 2 untagged methods, checker reported 'uncovered_count=${_pc_count:-<none>}'"
fi

# ===========================================================================
echo
echo "== arm 1 — DIFF scope, diff touches only docs =="
# ===========================================================================
# ADR-020. The legacy debt above is real and the positive control just found it,
# but this PR did not touch it, so gate-16 must not report it. PASS is correct
# here: the gate DID open the diff, and the diff contained no in-scope method.
_out="$(gf_run_wrapper "${WORK}/inherited" "${WORK}/log-diff-untouched")"
_v="$(gf_verdict "${_out}" 16)"
case "${_v}" in
    *PASS*) _ok "gate-16 passes on a docs-only diff — inherited debt does not block an unrelated PR (ADR-020)" ;;
    "")     _bad "gate-16 emitted no verdict at all on the docs-only diff arm" ;;
    *)      _bad "gate-16 on a docs-only diff wanted PASS, got: ${_v:0:140}" ;;
esac

# ===========================================================================
echo
echo "== arm 2 — DIFF scope, diff ADDS an untagged method =="
# ===========================================================================
# Proves gate-16 can fire through the real wrapper at all. If this arm ever goes
# green the gate is dead at every scope and arm 3 proves nothing.
gf_build_repo "${WORK}/newwork" "${SRC}"
gf_commit_all "${WORK}/newwork" "base: no new controller yet"
gf_mark_base  "${WORK}/newwork"
cp "${SRC}/lib/Controller/NewWorkController.php.new" "${WORK}/newwork/lib/Controller/NewWorkController.php"
rm -f "${WORK}/newwork/lib/Controller/NewWorkController.php.new"
gf_commit_paths "${WORK}/newwork" "feat: add an untagged endpoint (NEW debt)" \
    lib/Controller/NewWorkController.php

_out2="$(gf_run_wrapper "${WORK}/newwork" "${WORK}/log-diff-touched")"
_v2="$(gf_verdict "${_out2}" 16)"
case "${_v2}" in
    *FAIL*) _ok "gate-16 FAILS when the diff adds an untagged method — ${_v2:0:90}" ;;
    *)      _bad "gate-16 did NOT fail on a diff that ADDS an untagged in-scope method; got: ${_v2:0:140}" ;;
esac
if grep -qF 'NewWorkController.php' "${WORK}/log-diff-touched/hydra-gate-spec-coverage.log" 2>/dev/null; then
    _ok "gate-16 NAMES the newly added file in its log"
else
    _bad "gate-16 failed without naming NewWorkController.php — a bare count is not a finding"
fi

# ===========================================================================
echo
echo "== arm 3 — FULL file scope, NO delta base (.github#361 / #374) =="
# ===========================================================================
#
# REWRITTEN FOR THE ADR-020 REVERSAL (hydra-gates/ADR-020-SUPERSEDED.md).
#
# This arm used to run `--full` against a tree that `gf_mark_base` had given a
# `refs/remotes/origin/development` ref, and assert NOT APPLICABLE — because
# `--full` used to mean BOTH "read the whole tree" AND "compute no diff".
#
# Those are now two separate inputs, and that conflation was the bug: a full
# file scope says nothing about whether a base exists. gate-16 is a DELTA gate;
# what it needs is a BASE, not a narrowed file list. So the arm splits:
#
#   3a  full file scope, NO base   -> NOT APPLICABLE, with a reason  (below)
#   3b  full file scope, WITH base -> it JUDGES the change set, and still does
#                                     NOT sweep the legacy surface  (further down)
#
# 3b is the one that matters most: it is the only assertion standing between
# this package and the false RED `#361`'s fix was written to avoid — reporting
# every legacy `@spec` gap in the fleet because the file scope went wide.
#
# The tree is arm 1's, rebuilt WITHOUT `gf_mark_base`, so nothing in it
# resolves as a base. Building it explicitly rather than deleting the ref keeps
# the two arms independent.
gf_build_repo "${WORK}/inherited-nobase" "${SRC}"
gf_commit_all "${WORK}/inherited-nobase" "base: app carrying inherited @spec debt"
printf '\n- unrelated doc tweak\n' >> "${WORK}/inherited-nobase/docs/CHANGELOG.md"
gf_commit_paths "${WORK}/inherited-nobase" "docs: unrelated change" docs/CHANGELOG.md

_outf="$(gf_run_wrapper "${WORK}/inherited-nobase" "${WORK}/log-full" --full)"

if printf '%s' "${_outf}" | grep -qF 'SCOPE-MODE: full'; then
    _ok "the run announces its file scope in one machine-readable line"
else
    _bad "the run printed no 'SCOPE-MODE: full' line; the rest of this arm is unsafe to interpret because nothing states which scope produced it"
fi
if printf '%s' "${_outf}" | grep -qF 'Delta base: NONE'; then
    _ok "the run states it resolved NO delta base"
else
    _bad "the run did not state that it has no delta base — a delta gate's NOT APPLICABLE below would then be unattributable to any input"
fi

_vf="$(gf_verdict "${_outf}" 16)"
case "${_vf}" in
    *"NOT APPLICABLE"*)
        _ok "gate-16 on --full reports NOT APPLICABLE instead of PASSing over a scope it never read"
        ;;
    *PASS*)
        _bad ".github#361 is LIVE: gate-16 printed PASS on a run with NO delta base, over a tree whose two untagged methods the positive control just named. 0 inspected, and this PASS counts toward 'N of N applicable gates ran'."
        ;;
    *FAIL*)
        _bad ".github#361 was fixed by SWEEPING THE WHOLE TREE. gate-16 is a DELTA gate: widening its FILE scope does not give it a change set, it just reports inherited @spec debt the author never touched — a false RED in every repo in the fleet, and exactly what the ADR-020 reversal must NOT do to this gate. Expected NOT APPLICABLE. Got: ${_vf:0:140}"
        ;;
    "")  _bad "gate-16 emitted no verdict at all on the --full arm" ;;
    *)   _bad "gate-16 on --full gave an unrecognised verdict: ${_vf:0:140}" ;;
esac

# The reason must name the ABSENCE of a diff, never claim a diff EXCLUDED
# something — the invariant test_gate_scope_matrix.sh enforces gate-agnostically.
case "${_vf}" in
    *"out of scope"*|*"in this diff"*|*"the diff against"*)
        _bad "gate-16's --full reason blames a diff on a run that computed none — the gate-61 sentence pattern. Got: ${_vf:0:200}"
        ;;
    *)
        _ok "gate-16's --full reason does not blame a diff the run never computed"
        ;;
esac
if printf '%s' "${_vf}" | grep -qE 'NOT APPLICABLE (—|-) .{20,}'; then
    _ok "gate-16's --full NOT APPLICABLE carries a stated reason"
else
    _bad "gate-16's --full verdict is not a reason-bearing NOT APPLICABLE (a bare skip is unfalsifiable, and so is a PASS). Got: ${_vf:0:140}"
fi

# The legacy surface must NOT be named anywhere: naming it is the full-sweep
# regression wearing a NOT APPLICABLE hat.
if grep -qF 'LegacyDebtController.php' "${WORK}/log-full/hydra-gate-spec-coverage.log" 2>/dev/null; then
    _bad "the --full run wrote inherited legacy @spec debt into gate-16's log. Even without a FAIL verdict that is the full-sweep contract creeping back in."
else
    _ok "the --full run reports no inherited legacy @spec debt — ADR-020 upheld"
fi

# NOT APPLICABLE must not be a FAIL in disguise. `_skip` turns an unrecognised
# category into `FAIL — internal error`, which is how a category such as `scope`
# would have reddened the whole fleet.
if printf '%s' "${_outf}" | grep -E '^\[gate-16\]' | grep -qF 'internal error'; then
    _bad "gate-16's skip used a category outside na|structural|wiring — _skip turned it into an internal-error FAIL, which is a fleet-wide false RED"
else
    _ok "gate-16's skip category is accepted by _skip (no internal-error FAIL)"
fi

# And it must be counted as not-applicable, not as a silent no-show.
if printf '%s' "${_outf}" | grep -qE '^\[hydra-gates\] NOT APPLICABLE: .*\b16\b'; then
    _ok "gate-16 is named in the NOT APPLICABLE block of the coverage summary"
else
    _bad "gate-16 did not appear in the coverage summary's NOT APPLICABLE block — it is being counted as a gate that simply did not run, which --require-full-coverage would fail on"
fi

# ===========================================================================
echo
echo "== arm 3b — FULL file scope WITH a delta base (the ADR-020 reversal) =="
# ===========================================================================
#
# THE ARM THAT DID NOT EXIST, AND THE ONE THE REVERSAL MAKES NECESSARY.
#
# Full file scope is now the DEFAULT, so this is the shape every PR in the
# fleet runs in: the whole tree open to the state gates, and a real base for
# the five delta gates. Two things must hold simultaneously, and they pull in
# opposite directions:
#
#   1. gate-16 must still JUDGE THE CHANGE — otherwise flipping the default
#      silently retired @spec enforcement fleet-wide, which is a straight
#      downgrade dressed as an improvement.
#   2. gate-16 must still NOT NAME THE LEGACY SURFACE — otherwise the wide file
#      scope leaked into a delta gate and every repo goes red on inherited debt
#      nobody touched. That is `#361`'s false-RED, arriving by a new route.
#
# Arm 1 already proves (2) under `--scope-to-diff`. It proves nothing about the
# default any more, because the default changed.
_outfb="$(gf_run_wrapper "${WORK}/newwork" "${WORK}/log-full-base" --full)"

if printf '%s' "${_outfb}" | grep -qE '^\[hydra-gates\] Delta base: [^N]'; then
    _ok "the full-scope run resolved a delta base and named it"
else
    _bad "the full-scope run resolved NO delta base though the fixture has refs/remotes/origin/development — arm 3b would then be measuring arm 3a again and proving nothing"
fi

_vfb="$(gf_verdict "${_outfb}" 16)"
case "${_vfb}" in
    *FAIL*)
        _ok "gate-16 still JUDGES the change at full file scope — the delta gate survived the reversal: ${_vfb:0:90}"
        ;;
    *"NOT APPLICABLE"*)
        _bad "gate-16 went NOT APPLICABLE at full file scope DESPITE a resolved base. This is the regression the reversal must not cause: keying a delta gate on the FILE scope retires it on every PR in the fleet. Got: ${_vfb:0:160}"
        ;;
    *PASS*)
        _bad "gate-16 PASSed at full file scope over a diff that ADDS an untagged method. It had a base and did not use it. Got: ${_vfb:0:160}"
        ;;
    *) _bad "gate-16 gave an unrecognised verdict on the full+base arm: ${_vfb:0:160}" ;;
esac

if grep -qF 'NewWorkController.php' "${WORK}/log-full-base/hydra-gate-spec-coverage.log" 2>/dev/null; then
    _ok "gate-16 names the NEWLY ADDED file at full file scope"
else
    _bad "gate-16 did not name NewWorkController.php at full file scope — it produced a verdict without evidence"
fi
if grep -qF 'LegacyDebtController.php' "${WORK}/log-full-base/hydra-gate-spec-coverage.log" 2>/dev/null; then
    _bad "the full-scope run wrote INHERITED legacy @spec debt into gate-16's log. The wide file scope has leaked into a delta gate — this is #361's false RED arriving by a new route, and it would redden every repo in the fleet on code nobody touched."
else
    _ok "gate-16 does NOT sweep the inherited legacy surface even at full file scope — the delta contract survived the reversal"
fi

echo
echo "== summary =="
echo "   passed: ${_pass_n}"
echo "   failed: ${_fail_n}"
[ "${_fail_n}" -eq 0 ] || exit 1
[ "${_pass_n}" -gt 0 ] || { echo "FAIL — zero assertions ran; an empty suite is not a green one."; exit 1; }
echo
echo "ALL gate-16 scope controls PASSED"
exit 0
