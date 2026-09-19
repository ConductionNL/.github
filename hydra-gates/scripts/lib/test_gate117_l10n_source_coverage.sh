#!/usr/bin/env bash
# Gate 117 acceptance — the gate is PROVEN to refuse, not assumed to.
#
# 🔴 THE FOURTH CASE IS THE ONE THAT MATTERS. Every vendored `check-l10n.js` in
# the fleet computed `missing` from src/ t() calls alone, so a PHP or schema
# string that reached no catalogue was invisible to all of them. The `planted`
# tree hides exactly one PHP string and one schema title, and leaves the src/
# and manifest strings covered. Run at the incumbent's scope it reads CLEAN;
# run at this checker's scope it reports two. A promoted checker that could not
# tell those two readings apart would have promoted the defect.
#
# SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECKER="${HERE}/../check-l10n.js"
FIXTURES="${HERE}/../test-fixtures/gate-acceptance/l10n-source-coverage"

fails=0

expect() {
    local tree="$1" want_rc="$2" want_fails="$3" why="$4"
    shift 4
    local out rc got

    out="$(node "${CHECKER}" "${FIXTURES}/${tree}" "$@" 2>&1)"
    rc=$?
    got="$(printf '%s\n' "${out}" | grep -c '^FAIL ')"

    if [ "${rc}" -ne "${want_rc}" ] || [ "${got}" -ne "${want_fails}" ]; then
        echo "FAIL ${tree}: expected rc=${want_rc} with ${want_fails} finding(s), got rc=${rc} with ${got}"
        echo "      ${why}"
        printf '%s\n' "${out}" | sed 's/^/      | /'
        fails=$((fails + 1))
        return
    fi

    # A CHECKER THAT CRASHES MUST NOT READ AS CLEAN. The terminal summary is
    # how the runner tells the two apart, so the acceptance test asserts it.
    if ! printf '%s\n' "${out}" | grep -qE '^checked [0-9]+ source string'; then
        echo "FAIL ${tree}: the checker never printed its terminal summary, so a crash would read as a pass"
        fails=$((fails + 1))
        return
    fi

    echo "ok   ${tree}: rc=${rc}, ${got} finding(s) — ${why}"
}

expect clean 0 0 "every source string has an English key and a Dutch one"
expect planted 1 2 "the hidden PHP string and the hidden schema title are both refused"
expect no-catalogue 4 0 "a repository with no l10n/en.json is NOT APPLICABLE, which is not a pass"

# The control. Narrowed to the sources the vendored copies actually read, the
# planted tree reports ZERO missing. That is the defect this gate exists to
# end, asserted rather than described.
control="$(node "${CHECKER}" "${FIXTURES}/planted" --source=SRC,MANIFEST 2>&1)"
if printf '%s\n' "${control}" | grep -q '^missing from en.json: 0 '; then
    echo "ok   planted at the incumbent's scope: 0 missing — the blind spot is reproduced"
else
    echo "FAIL planted at the incumbent's scope should report 0 missing, so the wider scope is what finds the two"
    printf '%s\n' "${control}" | sed 's/^/      | /'
    fails=$((fails + 1))
fi

# --warn-only must hold back the exit code and nothing else: the findings still
# print. A launch-as-warning that also swallowed the findings would be a gate
# that runs nowhere.
warn="$(node "${CHECKER}" "${FIXTURES}/planted" --warn-only 2>&1)"
warn_rc=$?
warn_n="$(printf '%s\n' "${warn}" | grep -c '^FAIL ')"
if [ "${warn_rc}" -eq 0 ] && [ "${warn_n}" -eq 2 ]; then
    echo "ok   planted with --warn-only: rc=0 and 2 finding(s) still printed"
else
    echo "FAIL planted with --warn-only: expected rc=0 with 2 finding(s), got rc=${warn_rc} with ${warn_n}"
    fails=$((fails + 1))
fi

if [ "${fails}" -ne 0 ]; then
    echo "gate-117 acceptance: ${fails} case(s) failed"
    exit 1
fi

echo "gate-117 acceptance: all cases behaved"
