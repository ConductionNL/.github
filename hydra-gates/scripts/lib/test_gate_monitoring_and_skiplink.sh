#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# test_gate_monitoring_and_skiplink.sh — control pairs for gate-30
# (public-monitoring) and gate-38 (skip-link).
#
# WHY THIS EXISTS
# ---------------
# Both gates were reporting correct code, and both remedies were worse than
# the finding.
#
#   gate-30  demanded #[PublicPage] on every monitoring-shaped route,
#            including /api/metrics. ADR-006 makes metrics admin-only ON
#            PURPOSE — openregister's engine-owned GenericMetricsController
#            carries only #[NoCSRFRequired] and says "admin-only, ADR-006",
#            while its GenericHealthController IS #[PublicPage]. The only way
#            to close the finding was to publish the fleet's metrics to
#            anonymous callers.
#
#   gate-38  looked for <NcContent> in the root component. All 18 fleet apps
#            root on <CnAppRoot>, which RENDERS an NcContent one component
#            deeper — so the gate reported every app in the fleet as shipping
#            no skip link. The only way to close it was to bolt a second,
#            redundant skip link on top of the one already there.
#
# Both fixes widen what counts as an answer, and widening is exactly how a
# gate goes quiet. So each fixture here has a sibling that differs by the ONE
# thing the widening accepts, and must still fail:
#
#   stated/      metrics documents its admin-only posture   -> gate-30 PASS
#                health is #[PublicPage]
#                App.vue is a CnAppRoot                     -> gate-38 PASS
#
#   accidental/  metrics says NOTHING about its posture     -> gate-30 FAIL
#                health is admin-only, however documented   -> gate-30 FAIL
#                App.vue is a bespoke shell whose only      -> gate-38 FAIL
#                mention of NcContent/skip-link is a comment
#
# Run: bash scripts/lib/test_gate_monitoring_and_skiplink.sh  (exit 0 = green)
set -uo pipefail

PKG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../.." && pwd)"
RUNNER="${PKG_ROOT}/scripts/run-hydra-gates.sh"
FIXTURES="${PKG_ROOT}/scripts/test-fixtures/monitoring-skiplink"

_fail_n=0
_pass_n=0
_ok()  { _pass_n=$((_pass_n + 1)); printf 'PASS — %s\n' "$1"; }
_bad() { _fail_n=$((_fail_n + 1)); printf 'FAIL — %s\n' "$1"; }

_OUT=""
_PMLOG=""
_SLLOG=""
_run() {
    local _dir="$1"; shift
    local _logdir
    _logdir="$(mktemp -d "${TMPDIR:-/tmp}/hydra-gate-test.XXXXXXXX")"
    _OUT="$(HYDRA_GATE_LOG_DIR="${_logdir}" bash "${RUNNER}" "$@" "${_dir}" 2>&1 || true)"
    _PMLOG="$(cat "${_logdir}/hydra-gate-public-monitoring.log" 2>/dev/null || true)"
    _SLLOG="$(cat "${_logdir}/hydra-gate-skip-link.log" 2>/dev/null || true)"
    # A run that aborts before its summary leaves the per-gate PASS lines on
    # stdout and reads exactly like a clean run.
    if ! printf '%s' "${_OUT}" | grep -q '^\[hydra-gates\] COVERAGE:'; then
        _bad "run in ${_dir} ABORTED before the summary — verdicts above it are not a result"
        printf '%s\n' "${_OUT}" | tail -20 | sed 's/^/       /'
        return 1
    fi
    return 0
}

_expect_gate() {  # <n> <PASS|FAIL> <description>
    local _n="$1" _want="$2" _desc="$3" _line
    _line="$(printf '%s' "${_OUT}" | grep -E "^\[gate-${_n}\] " | head -1)"
    if [ -z "${_line}" ]; then
        _bad "${_desc} — gate-${_n} emitted NO verdict line at all"
        return
    fi
    case "${_line}" in
        *": ${_want}"*) _ok "${_desc} — ${_line}" ;;
        *) _bad "${_desc} — wanted ${_want}, got: ${_line}" ;;
    esac
}

_expect_log() {   # <log-contents> <regex> <description>
    if printf '%s' "$1" | grep -qE "$2"; then _ok "$3"; else
        _bad "$3 — no log line matching /$2/"
    fi
}
_expect_not_log() {
    if printf '%s' "$1" | grep -qE "$2"; then
        _bad "$3 — unexpected: $(printf '%s' "$1" | grep -E "$2" | head -1)"
    else _ok "$3"; fi
}

echo "== gate-30 public-monitoring / gate-38 skip-link control pairs =="
echo

for _f in stated accidental; do
    [ -d "${FIXTURES}/${_f}" ] || _bad "fixture ${FIXTURES}/${_f} does not exist — this suite would be green on nothing"
done

# ---------------------------------------------------------------------------
# 1. THE POSITIVE CONTROL, first. Everything in section 2 is only meaningful
#    because these fire.
# ---------------------------------------------------------------------------
if _run "${FIXTURES}/accidental"; then
    _expect_gate 30 FAIL "accidental: an undeclared monitoring posture is still reported"
    _expect_log "${_PMLOG}" 'MetricsController.php:[0-9]+ method=index' \
        "accidental: metrics with no stated posture at all is named"
    _expect_log "${_PMLOG}" 'HealthController.php:[0-9]+ method=index' \
        "accidental: an admin-only HEALTH endpoint is named — the carve-out is metrics-only"

    _expect_gate 38 FAIL "accidental: a bespoke shell with no skip link is still reported"
    _expect_log "${_SLLOG}" 'App\.vue: no <NcContent> shell' \
        "accidental: gate-38 names the root component"
fi

# ---------------------------------------------------------------------------
# 2. The shapes that were being reported wrongly.
# ---------------------------------------------------------------------------
if _run "${FIXTURES}/stated"; then
    _expect_gate 30 PASS "stated: a documented admin-only metrics endpoint is not a finding"
    _expect_not_log "${_PMLOG}" 'MetricsController' \
        "stated: metrics is absent from the log entirely"
    _expect_not_log "${_PMLOG}" 'HealthController' \
        "stated: a #[PublicPage] health endpoint is absent from the log"

    _expect_gate 38 PASS "stated: a CnAppRoot shell counts as having NC's skip link"
    _expect_not_log "${_SLLOG}" 'App\.vue' \
        "stated: gate-38 log is empty"
fi

echo
echo "== summary =="
printf '   passed: %d\n   failed: %d\n' "${_pass_n}" "${_fail_n}"
[ "${_fail_n}" -eq 0 ] || exit 1
echo
echo "ALL control pairs held."
