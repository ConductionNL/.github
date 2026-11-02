#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
#
# gate-123 (sig-floor) through the real runner, on a real git history.
#
#   ARM 1  a planted regression breaks a floored check: FAIL, naming the check
#   ARM 2  a refactor that keeps every check: PASS with the census line, and
#          sig-floor.md (with its 5-star line) is written to the report dir
#   ARM 3  no floor file: NOT APPLICABLE
#   ARM 4  the pinned tools are unavailable: SKIPPED (wiring), never PASS
#
# The rule-by-rule arms (inherited breaches, the floor read from the base, a
# lowered floor file, the raised floor, the cache) are in
# test_check_sig_floor.py.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
RUNNER="${SCRIPT_DIR}/../run-hydra-gates.sh"
HELPER="${SCRIPT_DIR}/check_sig_floor.py"

_fail_n=0
_ok()  { printf '  ok:   %s\n' "$1"; }
_bad() { _fail_n=$((_fail_n + 1)); printf '  FAIL: %s\n' "$1"; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/gate123-scope.XXXXXXXX")"
trap 'rm -rf "${WORK}"' EXIT
APP="${WORK}/app"
mkdir -p "${APP}/appinfo" "${APP}/lib/Service"

_method() {  # <name> <lines> -> a one-parameter PHP method with <lines> statements
    local _b="" _i
    for _i in $(seq 1 "$2"); do _b="${_b}        \$v${_i} = ${_i} + strlen('$1');\n"; done
    printf '    public function %s(int $p): int\n    {\n%b        return $p;\n    }\n' "$1" "${_b}"
}
_class() {  # <name> <methods...>
    local _n="$1"; shift
    printf '<?php\nnamespace OCA\\Fixture\\Service;\n\nclass %s\n{\n%s}\n' "${_n}" "$*" > "lib/Service/${_n}.php"
}

cd "${APP}" || exit 1
git init --quiet .
git config user.email fixture@example.invalid
git config user.name Fixture
printf '<?xml version="1.0"?>\n<info>\n    <id>fixture</id>\n    <version>1.0.0</version>\n</info>\n' > appinfo/info.xml
_m=""
for _i in $(seq 1 12); do _m="${_m}$(_method "m${_i}" 3)"$'\n'; done
_class Small "${_m}"
git add -A && git commit --quiet -m "app"
python3 "${HELPER}" write . > /dev/null || { echo "gate-123 scope: could not write the floor"; exit 1; }
git add -A && git commit --quiet -m "floor"
git branch -M base

_branch() { git checkout --quiet base && git checkout --quiet -b "$1"; }

_branch planted
_class Big "$(_method huge 70)"
git add -A && git commit --quiet -m "a 74-line unit"

_branch refactor
_class Split "$(_method moved 2)"
git add -A && git commit --quiet -m "a small new unit"

_branch nofloor
git rm --quiet .github/sig-floor.json
git commit --quiet -m "no floor"

_run() {  # <branch> [extra runner args...]
    local _b="$1"; shift
    git -C "${APP}" checkout --quiet "${_b}"
    mkdir -p "${WORK}/logs-${_b}"
    HYDRA_GATE_LOG_DIR="${WORK}/logs-${_b}" bash "${RUNNER}" "$@" "${APP}" 2>&1
}

_verdict() {
    printf '%s\n' "$1" | grep -E '^\[gate-123\] sig-floor: (PASS|FAIL|WARNING|SKIPPED|NOT APPLICABLE)' | head -1
}

echo "-- ARM 1: a planted regression: FAIL --"
_out="$(_run planted --base base)"
_v="$(_verdict "${_out}")"
case "${_v}" in
    *FAIL*) _ok "a change that breaks a floored check fails" ;;
    *)      _bad "expected FAIL, got: ${_v:-<no verdict>}" ;;
esac
if printf '%s\n' "${_out}" | grep -q '^  php unit_size >60: .*met at the base'; then
    _ok "the failure names the check and its base share"
else
    _bad "the failure does not name php unit_size >60"
fi

echo "-- ARM 2: a refactor that keeps every check: PASS --"
REPORTS="${WORK}/reports"
_out="$(HYDRA_GATE_SIG_REPORT_DIR="${REPORTS}" _run refactor --base base)"
_v="$(_verdict "${_out}")"
case "${_v}" in
    *PASS*) _ok "a change that keeps the floor passes" ;;
    *)      _bad "expected PASS, got: ${_v:-<no verdict>}" ;;
esac
if printf '%s\n' "${_out}" | grep -q '^\[gate-123\] sig-floor: PASS: [0-9]* floored check(s) held'; then
    _ok "the census line reaches the run's output"
else
    _bad "no census line in the PASS output"
fi
if [ -s "${REPORTS}/sig-floor.md" ] && grep -q '^| php unit_size >60 |' "${REPORTS}/sig-floor.md" \
    && grep -q '5-star checks met' "${REPORTS}/sig-floor.md"; then
    _ok "sig-floor.md, with the 5-star count, is written to HYDRA_GATE_SIG_REPORT_DIR"
else
    _bad "sig-floor.md is missing or lacks the check table"
fi

echo "-- ARM 3: no floor file: NOT APPLICABLE --"
_v="$(_verdict "$(_run nofloor)")"
case "${_v}" in
    *"NOT APPLICABLE"*) _ok "a repository with no floor file is not applicable" ;;
    *)                  _bad "expected NOT APPLICABLE, got: ${_v:-<no verdict>}" ;;
esac

echo "-- ARM 4: tools unavailable: SKIPPED (wiring) --"
if python3 -c 'import lizard' > /dev/null 2>&1; then
    _ok "lizard is importable outside the tool cache on this host, so this arm cannot remove it (not run)"
else
    _v="$(_verdict "$(HYDRA_GATE_TOOLS_DIR="${WORK}/no-tools" HYDRA_GATE_SIG_NO_INSTALL=1 _run planted --base base)")"
    case "${_v}" in
        *"SKIPPED (wiring)"*) _ok "a missing pinned tool is wiring, not a verdict" ;;
        *)                    _bad "expected SKIPPED (wiring), got: ${_v:-<no verdict>}" ;;
    esac
fi

echo
if [ "${_fail_n}" -eq 0 ]; then
    echo "gate-123 scope: all arms passed"
    exit 0
fi
echo "gate-123 scope: ${_fail_n} arm(s) failed"
exit 1
