#!/usr/bin/env bash
# Gate 111 acceptance — the gate is PROVEN to refuse, not assumed to.
#
# 🔴 THE THIRD CASE IS THE ONE THAT MATTERS. On a measured instance 38 of 65
# step types are contributed by apps in other repositories, on their own release
# cycles. A gate scoped by INTERFACE rather than by PATH would fire on every one
# of them, in pull requests that cannot fix them. The `no-nodes` tree proves
# this gate says NOT APPLICABLE there rather than passing or failing.
#
# SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECKER="${HERE}/check_flow_node_taxonomy.py"
FIXTURES="${HERE}/../test-fixtures/gate-acceptance/flow-node-taxonomy"

fails=0

expect() {
    local tree="$1" want_rc="$2" want_fails="$3" why="$4"
    local out rc got

    out="$(python3 "${CHECKER}" "${FIXTURES}/${tree}" 2>&1)"
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
    if ! printf '%s\n' "${out}" | grep -qE '^checked [0-9]+ flow node'; then
        echo "FAIL ${tree}: the checker never printed its terminal summary, so a crash would read as a pass"
        fails=$((fails + 1))
        return
    fi

    echo "ok   ${tree}: rc=${rc}, ${got} finding(s) — ${why}"
}

expect clean 0 0 "every node declares its kind and category"
expect planted 1 1 "the planted node is refused, and the declared node beside it is NOT"
expect no-nodes 4 0 "a repository with no flow-node directory is NOT APPLICABLE, which is not a pass"

if [ "${fails}" -ne 0 ]; then
    echo "gate-111 acceptance: ${fails} case(s) failed"
    exit 1
fi

echo "gate-111 acceptance: all cases behaved"
