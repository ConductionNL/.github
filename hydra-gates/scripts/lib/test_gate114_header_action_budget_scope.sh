#!/usr/bin/env bash
#
# gate-114 (header-action-budget) — acceptance over a REAL two-commit history.
#
# WHY THIS IS NOT A gate-acceptance/ BUNDLE
#
# gate-114 is a DELTA gate: its ratchet asks whether a page's header actions
# bar is LONGER than it was at the base. The generic bundle format runs the
# runner against a plain directory with no git history, so the ratchet there
# has nothing to compare against and the gate can only ever report the census
# half. gates 16, 98, 100, 101, 108 and 110 are all covered this way for the
# same reason, and all are registered in gate-acceptance/COVERED-ELSEWHERE.md.
#
# 🔴 WHAT THIS SUITE EXISTS TO STOP RECURRING
#
# ARM 6 is the load-bearing one, and it is here because three ratchets in this
# package already have the defect it pins. Gates 52, 68 and 69 hand their base
# ref to their checker only inside `if [ "${SCOPE_TO_DIFF}" = "1" ]`, and the
# shared quality workflow never puts this runner in diff scope: full scope has
# been the default since ADR-020 was superseded, and `--scope-to-diff` appears
# in no workflow file. So their ratchet halves do not run in CI at all.
#
# Measured on dossiq PR #1985, which added a type:"custom" page and took the
# app from 11 to 12. That run resolved its delta base
# (`Delta base: origin/development ($HYDRA_GATE_BASE_REF) = fa09f5837`),
# reported `SCOPE-MODE: full`, and printed `[gate-69] page-type-discipline:
# PASS` with no ratchet line at all. The base was right there and the gate's
# own wiring threw it away.
#
# A gate that cannot compute its ratchet must SAY SO. ARM 6 requires the named
# line. A PASS with no base and no explanation is the shape this suite refuses.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
RUNNER="${SCRIPT_DIR}/../run-hydra-gates.sh"

_fail_n=0
_ok()  { printf '  ok   — %s\n' "$1"; }
_bad() { _fail_n=$((_fail_n + 1)); printf '  FAIL — %s\n' "$1"; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/gate114-scope.XXXXXXXX")"
trap 'rm -rf "${WORK}"' EXIT

APP="${WORK}/app"
mkdir -p "${APP}/src/manifest.d"

# _manifest <CaseDetail-count> [extra-page-id] [extra-page-count]
#
# One detail page whose bar is the subject, plus an index page that never has
# one. The BASELINE deliberately already carries a long bar (five actions), so
# that inherited debt is present in every arm. A ratchet that cannot tell
# inherited length from new growth is the bug, not the feature.
_manifest() {
    python3 - "$@" <<'PY'
import json, sys
n = int(sys.argv[1])
pages = [
    {"id": "Cases", "route": "/cases", "type": "index", "title": "Cases",
     "config": {"register": "fixture", "schema": "case"}},
    {"id": "CaseDetail", "route": "/cases/:id", "type": "detail", "title": "Case",
     "config": {"register": "fixture", "schema": "case",
                "headerActions": [
                    {"id": f"act-{i}", "type": "open-modal", "label": f"Action {i}",
                     "target": "SomeDialog"} for i in range(n)]}},
]
if len(sys.argv) > 3:
    pages.append({
        "id": sys.argv[2], "route": "/other", "type": "detail", "title": "Other",
        "config": {"register": "fixture", "schema": "other",
                   "headerActions": [
                       {"id": f"other-{i}", "type": "open-modal", "label": f"Other {i}",
                        "target": "SomeDialog"} for i in range(int(sys.argv[3]))]}})
print(json.dumps({"version": "1.0.0", "pages": pages}, indent=2))
PY
}

cd "${APP}" || exit 1
git init --quiet .
git config user.email fixture@example.invalid
git config user.name Fixture

# ── COMMIT 1: the baseline, already carrying a five-button bar.
_manifest 5 > src/manifest.json
echo '{"pages": [], "menu": []}' > src/manifest.d/_placeholder.json
echo "x" > README.md
git add -A && git commit --quiet -m "baseline, carrying a five-button bar"
git branch -M base

# ── planted: one more button on the SAME page.
git checkout --quiet -b planted
_manifest 6 > src/manifest.json
git add -A && git commit --quiet -m "a sixth header action on the case page"

# ── newpage: a brand new page arriving with a long bar. Nothing to compare
#    against, so this must NOT be a finding — the anti-widening arm.
git checkout --quiet base
git checkout --quiet -b newpage
_manifest 5 BezwaarDetail 7 > src/manifest.json
git add -A && git commit --quiet -m "a new page with seven header actions"

# ── shrunk: a button removed. A ratchet that fired on any delta would report
#    this, and then nobody would ever remove one.
git checkout --quiet base
git checkout --quiet -b shrunk
_manifest 3 > src/manifest.json
git add -A && git commit --quiet -m "three header actions instead of five"

# ── unrelated: touches no manifest at all. The inherited five-button bar must
#    not be reported as this change's problem.
git checkout --quiet base
git checkout --quiet -b unrelated
echo "y" >> README.md
git add -A && git commit --quiet -m "an unrelated change"

_run() {  # <branch> [extra runner args...] -> full runner output on stdout
    local _b="$1"; shift
    git checkout --quiet "${_b}"
    mkdir -p "${WORK}/logs-${_b}"
    HYDRA_GATE_LOG_DIR="${WORK}/logs-${_b}" bash "${RUNNER}" "$@" "${APP}" 2>&1
}

_verdict() {  # <output> -> the [gate-114] verdict line
    printf '%s\n' "$1" | grep -E '^\[gate-114\] header-action-budget: (PASS|FAIL|WARNING|SKIPPED|NOT APPLICABLE)' | head -1
}

echo "-- ARM 1: one more button on an existing page is a finding, and it is named --"
_out_planted="$(_run planted --base base)"
_v="$(_verdict "${_out_planted}")"
case "${_v}" in
    *WARNING*) _ok "gate-114 reports WARNING when a bar grew" ;;
    *)         _bad "expected WARNING on the planted branch, got: ${_v:-<no gate-114 verdict line>}" ;;
esac
if grep -q 'WARN CaseDetail: header actions went 5 to 6' "${WORK}/logs-planted/hydra-gate-header-action-budget.log" 2>/dev/null; then
    _ok "the finding NAMES the page and both counts, not a bare number"
else
    _bad "the log does not name CaseDetail and the 5 to 6 move: $(head -3 "${WORK}/logs-planted/hydra-gate-header-action-budget.log" 2>/dev/null | tr '\n' ' ')"
fi
case "${_out_planted}" in
    *"[gate-114] header-action-budget: base=5 head=6 delta=+1"*)
        _ok "the census and the delta are printed on stdout, not only in the log" ;;
    *)  _bad "no base/head/delta line on stdout for the planted branch" ;;
esac

echo "-- ARM 2: the WARNING does not block, and is not counted as a failure --"
# The RUNNER's own summary line. `RESULT: N GATE(S) FAILED` belongs to
# bin/hydra-gates, the wrapper, and this suite drives the runner directly.
_result_n="$(printf '%s\n' "${_out_planted}" | sed -n 's/^\[hydra-gates\] \([0-9]\{1,\}\) gate(s) failed$/\1/p' | head -1)"
[ -z "${_result_n}" ] && printf '%s\n' "${_out_planted}" | grep -qE '^\[hydra-gates\] ALL .* GREEN|no gate\(s\) failed' && _result_n=0
_fail_lines="$(printf '%s\n' "${_out_planted}" | grep -cE '^\[gate-[0-9]+\] [a-z0-9-]+: FAIL' || true)"
if [ -n "${_result_n}" ] && [ "${_result_n}" = "${_fail_lines}" ]; then
    _ok "the run's failure count (${_result_n}) equals its FAIL lines — the warning reached neither"
else
    _bad "failure count '${_result_n:-<none>}' does not equal the ${_fail_lines} FAIL line(s); a warning has leaked into the exit code"
fi
if printf '%s\n' "${_out_planted}" | grep -qE '^\[gate-114\] header-action-budget: FAIL'; then
    _bad "gate-114 reported FAIL while shipping advisory — this gate resolves at @main for 21 repos"
else
    _ok "gate-114 never printed a FAIL verdict on the planted branch"
fi

echo "-- ARM 3: inherited debt is not this change's problem --"
_v="$(_verdict "$(_run unrelated --base base)")"
case "${_v}" in
    *PASS*) _ok "a change touching no manifest is clean, though the base carries a five-button bar" ;;
    *)      _bad "expected PASS on a change that touches no manifest, got: ${_v:-<no verdict>}" ;;
esac

echo "-- ARM 4: a NEW page is censused, not ratcheted --"
_out_new="$(_run newpage --base base)"
_v="$(_verdict "${_out_new}")"
case "${_v}" in
    *PASS*) _ok "a page that did not exist at the base raises no finding" ;;
    *)      _bad "a new page was treated as growth: ${_v:-<no verdict>}" ;;
esac
case "${_out_new}" in
    *"max=7 on BezwaarDetail"*) _ok "and its bar is still visible in the census on stdout" ;;
    *) _bad "the new page's seven-button bar is absent from the census, so it is invisible as well as unratcheted" ;;
esac

echo "-- ARM 5: removing a button is not a finding --"
_out_shrunk="$(_run shrunk --base base)"
_v="$(_verdict "${_out_shrunk}")"
case "${_v}" in
    *PASS*) _ok "a bar that got shorter is clean" ;;
    *)      _bad "a removal was reported as a finding: ${_v:-<no verdict>}" ;;
esac
case "${_out_shrunk}" in
    *"delta=-2"*) _ok "and the shrink is reported, so a migration can show the number coming down" ;;
    *) _bad "no negative delta on stdout — a gate that only reports growth cannot evidence a burn-down" ;;
esac

echo "-- ARM 6: with NO delta base the ratchet does not run, and the run SAYS SO --"
# THE ARM THAT GATES 52, 68 AND 69 DO NOT HAVE. Without it, a ratchet wired to
# a base it never receives prints PASS and reads exactly like one that ran.
_out_nobase="$(_run planted --full)"
_v="$(_verdict "${_out_nobase}")"
case "${_out_nobase}" in
    *"gate-114 header-action-budget: the RATCHET half was NOT computed"*)
        _ok "the run names the half that did not run, rather than passing over it" ;;
    *)  _bad "no base, no ratchet, and NO line saying so — a PASS here is indistinguishable from a ratchet that ran" ;;
esac
case "${_out_nobase}" in
    *"[gate-114] header-action-budget: base="*)
        _bad "a base/head/delta line was printed with no delta base — the ratchet claims a comparison it did not make" ;;
    *)  _ok "no base/head/delta line is claimed when there is no base" ;;
esac
case "${_v}" in
    *PASS*) _ok "the census half still reported, so the gate is not silent" ;;
    *)      _bad "gate-114 produced no verdict at all without a base: ${_v:-<none>}" ;;
esac

echo "-- ARM 7: a repo that has worked its bars down can opt in to blocking --"
_v="$(_verdict "$(HYDRA_GATE_HEADER_ACTION_BUDGET_BLOCKING=1 _run planted --base base)")"
case "${_v}" in
    *FAIL*) _ok "HYDRA_GATE_HEADER_ACTION_BUDGET_BLOCKING=1 makes the same finding block" ;;
    *)      _bad "the per-repo opt-in did not promote the finding: ${_v:-<no verdict>}" ;;
esac

echo ""
if [ "${_fail_n}" -eq 0 ]; then
    echo "gate-114 header-action-budget acceptance: all arms passed."
    exit 0
fi
echo "gate-114 header-action-budget acceptance: ${_fail_n} arm(s) failed."
exit 1
