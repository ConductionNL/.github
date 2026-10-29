#!/usr/bin/env bash
# Gate 67 scope — only OpenRegister is judged.
#
# Any app may keep its own interfaces in lib/Contract/. The gate compares that
# directory with hydra-gates/contracts/, which is OpenRegister's published
# contract, so in any other app it reports drift the app neither owns nor can
# fix. The foreign-app tree proves the gate says NOT APPLICABLE there, and the
# composer-only tree proves that OpenRegister named only by composer.json is
# still judged.
#
# SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECKER="${HERE}/check_openregister_contract_parity.py"
RUNNER="${HERE}/../run-hydra-gates.sh"
FIXTURES="${HERE}/../test-fixtures/gate-acceptance/openregister-contract-parity"

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

    # The runner reads a missing terminal line as a crash, so every exit must print it.
    if ! printf '%s\n' "${out}" | grep -qE '^checked [0-9]+ file\(s\)$'; then
        echo "FAIL ${tree}: the checker never printed 'checked N file(s)', so the runner would report a crash"
        fails=$((fails + 1))
        return
    fi

    echo "ok   ${tree}: rc=${rc}, ${got} finding(s) — ${why}"
}

expect planted 1 3 "openregister with three kinds of drift is judged"
expect clean 0 0 "openregister with byte-identical copies passes"
expect foreign-app 3 0 "another app's own lib/Contract/ is NOT APPLICABLE, even when it differs"
expect composer-only 1 1 "openregister named only by composer.json is still judged"

# Through the real runner: the verdict must be NOT APPLICABLE and say why.
logs="$(mktemp -d "${TMPDIR:-/tmp}/hydra-gate67.XXXXXXXX")"
line="$(HYDRA_GATE_LOG_DIR="${logs}" bash "${RUNNER}" "${FIXTURES}/foreign-app" 2>&1 \
    | grep -m1 -E '^\[gate-67\] ')"
rm -rf "${logs}"
case "${line}" in
    *"NOT APPLICABLE"*"this app's own, not the OpenRegister contract"*)
        echo "ok   runner over foreign-app: ${line:0:110}" ;;
    *)
        echo "FAIL runner over foreign-app: wanted NOT APPLICABLE with the app's-own reason, got: ${line:-<no gate-67 line>}"
        fails=$((fails + 1)) ;;
esac

if [ "${fails}" -ne 0 ]; then
    echo "gate-67 scope: ${fails} case(s) failed"
    exit 1
fi

echo "gate-67 scope: all cases behaved"
