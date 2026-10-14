#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# gate-120 (register-version-needs-app-version): acceptance over a REAL git
# history, through the real runner. The rule-by-rule arms live in
# test_check_register_version_bump.py; this suite pins what only the runner can
# get wrong: the verdict word, the delta base, and a crash read as a finding.
#
#   ARM 1  the register's info.version raised, appinfo <version> not: FAIL,
#          naming the document and both versions (portaliq #1549)
#   ARM 2  both raised in the change: PASS, with the census line (the mock
#          is not counted as a document)
#   ARM 3  only a mock's version raised: PASS
#   ARM 4  no delta base: NOT APPLICABLE, never PASS
#   ARM 5  a repo with no lib/Settings: NOT APPLICABLE
#   ARM 6  a register document that is not JSON: SKIPPED (wiring), never PASS
#          and never a finding

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
RUNNER="${SCRIPT_DIR}/../run-hydra-gates.sh"

_fail_n=0
_ok()  { printf '  ok:   %s\n' "$1"; }
_bad() { _fail_n=$((_fail_n + 1)); printf '  FAIL: %s\n' "$1"; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/gate120-scope.XXXXXXXX")"
trap 'rm -rf "${WORK}"' EXIT
APP="${WORK}/app"
mkdir -p "${APP}/appinfo" "${APP}/lib/Settings"

_info() {
    printf '<?xml version="1.0"?>\n<info>\n    <id>fixture</id>\n    <name>Fixture</name>\n    <version>%s</version>\n</info>\n' "$1" > appinfo/info.xml
}
_register() {  # <file> <version> [mock]
    local _type='"application"'
    [ "${3:-}" = "mock" ] && _type='"mock"'
    printf '{"openapi":"3.0.0","info":{"title":"Fixture","version":"%s"},"x-openregister":{"type":%s},"components":{"registers":{"fixture":{"slug":"fixture"}}}}\n' "$2" "${_type}" > "lib/Settings/$1"
}

cd "${APP}" || exit 1
git init --quiet .
git config user.email fixture@example.invalid
git config user.name Fixture

_info 1.0.0
_register fixture_register.json 0.96.0
_register fixture_mock_register.json 0.27.0 mock
git add -A && git commit --quiet -m "base"
git branch -M base

_branch() { git checkout --quiet base && git checkout --quiet -b "$1"; }

_branch register-only
_register fixture_register.json 0.97.0
git commit --quiet -am "close the register, forget the app version"

_branch both
_register fixture_register.json 0.97.0
_info 1.0.1
git commit --quiet -am "close the register and raise the app version"

_branch mock-only
_register fixture_mock_register.json 0.28.0 mock
git commit --quiet -am "more sample data"

_branch broken
echo '{not json' > lib/Settings/fixture_register.json
git commit --quiet -am "break the register"

_run() {  # <app-dir> <branch> [extra runner args...]
    local _dir="$1" _b="$2"; shift 2
    git -C "${_dir}" checkout --quiet "${_b}"
    mkdir -p "${WORK}/logs-${_b}"
    HYDRA_GATE_LOG_DIR="${WORK}/logs-${_b}" bash "${RUNNER}" "$@" "${_dir}" 2>&1
}

_verdict() {
    printf '%s\n' "$1" | grep -E '^\[gate-120\] register-version-needs-app-version: (PASS|FAIL|WARNING|SKIPPED|NOT APPLICABLE)' | head -1
}

echo "-- ARM 1: register raised, app version not: FAIL --"
_out="$(_run "${APP}" register-only --base base)"
_v="$(_verdict "${_out}")"
case "${_v}" in
    *FAIL*) _ok "the forgotten app version fails" ;;
    *)      _bad "expected FAIL, got: ${_v:-<no verdict>}" ;;
esac
if printf '%s\n' "${_out}" | grep -q 'lib/Settings/fixture_register.json: info.version 0.96.0 -> 0.97.0'; then
    _ok "the finding names the document and both versions"
else
    _bad "the finding does not name lib/Settings/fixture_register.json 0.96.0 -> 0.97.0"
fi

echo "-- ARM 2: both raised: PASS with the census line --"
_out="$(_run "${APP}" both --base base)"
_v="$(_verdict "${_out}")"
case "${_v}" in
    *PASS*) _ok "raising both passes" ;;
    *)      _bad "expected PASS, got: ${_v:-<no verdict>}" ;;
esac
if printf '%s\n' "${_out}" | grep -q '^\[gate-120\] register-version-needs-app-version: checked 1 document(s), 1 version change(s)'; then
    _ok "the census line counts what was compared"
else
    _bad "no census line in the PASS output"
fi

echo "-- ARM 3: only a mock moved: PASS --"
_v="$(_verdict "$(_run "${APP}" mock-only --base base)")"
case "${_v}" in
    *PASS*) _ok "a mock's version is not a register change" ;;
    *)      _bad "expected PASS for a mock-only change, got: ${_v:-<no verdict>}" ;;
esac

echo "-- ARM 4: no delta base: NOT APPLICABLE --"
_v="$(_verdict "$(HYDRA_GATE_BASE_REF='' _run "${APP}" register-only)")"
case "${_v}" in
    *"NOT APPLICABLE"*) _ok "without a base the gate says it compared nothing" ;;
    *PASS*)             _bad "PASS without a base: a delta rule that judged nothing" ;;
    *)                  _bad "expected NOT APPLICABLE without a base, got: ${_v:-<no verdict>}" ;;
esac

echo "-- ARM 5: no lib/Settings: NOT APPLICABLE --"
BARE="${WORK}/bare"
mkdir -p "${BARE}/appinfo" "${BARE}/lib/Service"
(
    cd "${BARE}" || exit 1
    git init --quiet . && git config user.email f@x.invalid && git config user.name F
    _info 1.0.0
    printf '<?php\n' > lib/Service/A.php
    git add -A && git commit --quiet -m base && git branch -M main
)
_v="$(_verdict "$(_run "${BARE}" main --base main)")"
case "${_v}" in
    *"NOT APPLICABLE"*) _ok "a repo with no register configuration is not applicable" ;;
    *)                  _bad "expected NOT APPLICABLE without lib/Settings, got: ${_v:-<no verdict>}" ;;
esac

echo "-- ARM 6: unreadable register: SKIPPED (wiring), never PASS or FAIL --"
_v="$(_verdict "$(_run "${APP}" broken --base base)")"
case "${_v}" in
    *SKIPPED*) _ok "a document the checker cannot read is wiring, not a verdict" ;;
    *)         _bad "expected SKIPPED for unreadable JSON, got: ${_v:-<no verdict>}" ;;
esac

echo
if [ "${_fail_n}" -eq 0 ]; then
    echo "gate-120 scope: all arms passed"
    exit 0
fi
echo "gate-120 scope: ${_fail_n} arm(s) failed"
exit 1
