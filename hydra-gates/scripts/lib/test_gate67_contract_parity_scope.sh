#!/usr/bin/env bash
# Gate 67 scope — only OpenRegister is judged.
#
# Any app may keep its own interfaces in lib/Contract/. The gate compares that
# directory with hydra-gates/contracts/, which is OpenRegister's published
# contract, so in any other app it reports drift the app neither owns nor can
# fix. The foreign-app tree proves the gate says NOT APPLICABLE there, and the
# composer-only tree proves that OpenRegister named only by composer.json is
# still judged. The planted and clean trees, through the runner, prove the
# HYDRA_GATE_CONTRACT_PARITY_BLOCKING switch.
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

# HYDRA_GATE_CONTRACT_PARITY_BLOCKING, through the real runner. quality.yml
# sets it to "0" on a stable* release line. Off, the gate must still run, name
# every drifted file and report WARNING, and must not add to the exit code,
# which is the runner's failed-gate count. Unset, or any value but "0", it
# blocks. A clean tree passes in both modes.
run_runner() {  # <tree> [VAR=value ...] — prints the run's output, then "rc=<exit>"
    local tree="$1" logs out rc
    shift
    logs="$(mktemp -d "${TMPDIR:-/tmp}/hydra-gate67.XXXXXXXX")"
    out="$(env HYDRA_GATE_LOG_DIR="${logs}" "$@" bash "${RUNNER}" "${FIXTURES}/${tree}" 2>&1)"
    rc=$?
    rm -rf "${logs}"
    printf '%s\nrc=%s\n' "${out}" "${rc}"
}
verdict() { printf '%s\n' "$1" | grep -m1 -E '^\[gate-67\] '; }
exit_of() { printf '%s\n' "$1" | sed -n 's/^rc=//p' | tail -1; }

blocking="$(run_runner planted)"
advisory="$(run_runner planted HYDRA_GATE_CONTRACT_PARITY_BLOCKING=0)"
typo="$(run_runner planted HYDRA_GATE_CONTRACT_PARITY_BLOCKING=false)"

case "$(verdict "${blocking}")" in
    *": FAIL — 3 contract file(s) out of step"*)
        echo "ok   runner over planted, switch unset: FAIL" ;;
    *)
        echo "FAIL runner over planted, switch unset: wanted FAIL with 3 files, got: $(verdict "${blocking}")"
        fails=$((fails + 1)) ;;
esac

case "$(verdict "${advisory}")" in
    *": WARNING — 3 contract file(s) out of step"*"NOT BLOCKING this run"*)
        echo "ok   runner over planted, switch 0: WARNING, not blocking" ;;
    *)
        echo "FAIL runner over planted, switch 0: wanted WARNING with 3 files, got: $(verdict "${advisory}")"
        fails=$((fails + 1)) ;;
esac

# The advisory run is green on this gate, so the files must reach the output.
named=0
for f in Contract/ObjectServiceInterface.php OrphanInterface.php Contract/UnshippedInterface.php; do
    printf '%s\n' "${advisory}" | grep -qE "^  .*${f}: " && named=$((named + 1))
done
if [ "${named}" -eq 3 ]; then
    echo "ok   runner over planted, switch 0: all 3 drifted files are named in the output"
else
    echo "FAIL runner over planted, switch 0: ${named} of 3 drifted files named in the output"
    fails=$((fails + 1))
fi

# Same tree, so every other gate reports the same; only gate 67 may move.
rc_b="$(exit_of "${blocking}")"
rc_a="$(exit_of "${advisory}")"
if [ -n "${rc_b}" ] && [ -n "${rc_a}" ] && [ "$((rc_b - rc_a))" -eq 1 ]; then
    echo "ok   runner over planted: exit ${rc_b} blocking, ${rc_a} with switch 0 (gate 67 no longer counted)"
else
    echo "FAIL runner over planted: wanted the switch to lower the exit by exactly 1, got ${rc_b:-?} blocking and ${rc_a:-?} with switch 0"
    fails=$((fails + 1))
fi

case "$(verdict "${typo}")" in
    *": FAIL — "*)
        echo "ok   runner over planted, switch 'false': still FAIL (only a literal 0 demotes)" ;;
    *)
        echo "FAIL runner over planted, switch 'false': wanted FAIL, got: $(verdict "${typo}")"
        fails=$((fails + 1)) ;;
esac

for mode in "" "HYDRA_GATE_CONTRACT_PARITY_BLOCKING=0"; do
    # shellcheck disable=SC2086 # an empty mode must expand to no argument
    out="$(run_runner clean ${mode})"
    case "$(verdict "${out}")" in
        *": PASS"*)
            echo "ok   runner over clean${mode:+, ${mode}}: PASS" ;;
        *)
            echo "FAIL runner over clean${mode:+, ${mode}}: wanted PASS, got: $(verdict "${out}")"
            fails=$((fails + 1)) ;;
    esac
done

if [ "${fails}" -ne 0 ]; then
    echo "gate-67 scope: ${fails} case(s) failed"
    exit 1
fi

echo "gate-67 scope: all cases behaved"
