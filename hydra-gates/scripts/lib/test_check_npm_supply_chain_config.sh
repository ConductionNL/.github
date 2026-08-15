#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# Self-test for check_npm_supply_chain_config.py (gate-84).
#
# Discovered and run by tests/run-helper-suites.sh — no workflow edit needed.
#
# The cooldown is three settings that only work together, so the suite asserts
# each one is INDIVIDUALLY load-bearing: drop any one from an otherwise
# conformant repo and the gate must still fail. A gate that only fires when
# everything is missing would have passed 4 of the fleet's 19 apps, which were
# carrying a correct `min-release-age=1` on a toolchain that cannot read it.
#
# The `engines.npm: ">=10"` case is the one most likely to rot. It is a range
# a person would write meaning "modern npm", and it silently admits npm 10,
# where `min-release-age` does not exist at all.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECKER="${HERE}/check_npm_supply_chain_config.py"
pass=0
fail=0

ok() { echo "  PASS  $1"; pass=$((pass + 1)); }
no() { echo "  FAIL  $1"; [ -n "${2:-}" ] && printf '        %s\n' "$2"; fail=$((fail + 1)); }

TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

GOOD_NPMRC='min-release-age=2\nmin-release-age-exclude[]=@conduction/*\n'
GOOD_PKG='{"name":"x","engines":{"npm":"^11.0.0"}}'

# $1 label, $2 .npmrc body, $3 package.json body, $4 expected rc
case_test() {
    local d="${TMP}/case"
    rm -rf "$d"; mkdir -p "$d"
    [ -n "$2" ] && printf '%b' "$2" > "$d/.npmrc"
    [ -n "$3" ] && printf '%b' "$3" > "$d/package.json"
    python3 "${CHECKER}" "$d" >/dev/null 2>&1
    local rc=$?
    if [ "${rc}" = "$4" ]; then ok "$1"; else no "$1" "rc=${rc}, expected $4"; fi
}

echo "check_npm_supply_chain_config.py (gate-84)"

case_test "fully conformant repo passes" "${GOOD_NPMRC}" "${GOOD_PKG}" 0

# Each setting is individually load-bearing.
case_test "missing the @conduction/* exclusion fails" \
    'min-release-age=2\n' "${GOOD_PKG}" 1
case_test "missing engines.npm fails" \
    "${GOOD_NPMRC}" '{"name":"x"}' 1
case_test "missing .npmrc entirely fails" \
    '' "${GOOD_PKG}" 1

# The window itself.
case_test "min-release-age=0 (disabled) fails" \
    'min-release-age=0\nmin-release-age-exclude[]=@conduction/*\n' "${GOOD_PKG}" 1
case_test "min-release-age=1 (below the 2-day floor) fails" \
    'min-release-age=1\nmin-release-age-exclude[]=@conduction/*\n' "${GOOD_PKG}" 1
case_test "min-release-age=7 (above the floor) passes" \
    'min-release-age=7\nmin-release-age-exclude[]=@conduction/*\n' "${GOOD_PKG}" 0

# The toolchain. npm 10 does not implement min-release-age AT ALL, so any
# range admitting it leaves the two settings above read by nothing.
case_test "engines.npm ^10.0.0 fails" \
    "${GOOD_NPMRC}" '{"name":"x","engines":{"npm":"^10.0.0"}}' 1
case_test 'engines.npm ">=10" fails (admits npm 10)' \
    "${GOOD_NPMRC}" '{"name":"x","engines":{"npm":">=10"}}' 1
case_test "engines.npm ^12.0.0 passes (newer is fine)" \
    "${GOOD_NPMRC}" '{"name":"x","engines":{"npm":"^12.0.0"}}' 0

# The state the whole fleet was in on 2026-08-15.
case_test "the pre-change fleet state fails" \
    'min-release-age=0\n' '{"name":"x","engines":{"npm":"^10.0.0"}}' 1

# Comments and npm's array syntax must be parsed, not pattern-matched loosely.
case_test "commented-out settings do not count" \
    '# min-release-age=2\n# min-release-age-exclude[]=@conduction/*\n' "${GOOD_PKG}" 1

# Applicability and wiring.
case_test "no package.json is NOT APPLICABLE, not a pass" '' '' 4
case_test "unparseable package.json fails, never reads as clean" \
    "${GOOD_NPMRC}" '{ this is not json' 1

# The terminal summary the runner greps for must be printed.
d="${TMP}/summary"; rm -rf "$d"; mkdir -p "$d"
printf '%b' "${GOOD_NPMRC}" > "$d/.npmrc"; printf '%b' "${GOOD_PKG}" > "$d/package.json"
out="$(python3 "${CHECKER}" "$d" 2>&1 || true)"
printf '%s' "${out}" | grep -qE '^checked [0-9]+ npm supply-chain setting' \
    && ok "prints the terminal summary the runner asserts on" \
    || no "prints the terminal summary the runner asserts on" "got: ${out}"

echo "  ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
