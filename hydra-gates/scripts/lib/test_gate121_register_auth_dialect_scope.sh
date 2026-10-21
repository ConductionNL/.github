#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# gate-121 (register-auth-dialect): acceptance through the real runner. The
# rule-by-rule arms live in test_check_register_auth_dialect.py; this suite pins
# what only the runner can get wrong: the verdict word, the report-only census,
# the promotion switch, and a crash read as a finding.
#
#   ARM 1  a planted `x-openregister-rbac` on a schema: FAIL, naming the file
#          and the schema path (the shillinq shape)
#   ARM 2  the same schema on `authorization`: PASS, with the census line
#   ARM 3  an open schema next to a closed one: still PASS, and the coverage
#          line says 1 of 2 (report-only)
#   ARM 4  ARM 3 with HYDRA_GATE_REGISTER_AUTHORIZATION_BLOCKING=1: FAIL
#   ARM 5  a repo with no register document: NOT APPLICABLE, never PASS
#   ARM 6  a register document that is not JSON: SKIPPED (wiring), never PASS
#          and never a finding

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
RUNNER="${SCRIPT_DIR}/../run-hydra-gates.sh"

_fail_n=0
_ok()  { printf '  ok:   %s\n' "$1"; }
_bad() { _fail_n=$((_fail_n + 1)); printf '  FAIL: %s\n' "$1"; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/gate121-scope.XXXXXXXX")"
trap 'rm -rf "${WORK}"' EXIT
APP="${WORK}/app"
mkdir -p "${APP}/appinfo" "${APP}/lib/Settings/register.d"

_register() {  # <schemas-json>
    printf '{"openapi":"3.0.0","info":{"title":"Fixture","version":"1.0.0"},"components":{"registers":{"fixture":{"slug":"fixture"}},"schemas":%s}}\n' "$1" > lib/Settings/fixture_register.json
}

cd "${APP}" || exit 1
git init --quiet .
git config user.email fixture@example.invalid
git config user.name Fixture
printf '<?xml version="1.0"?>\n<info>\n    <id>fixture</id>\n    <version>1.0.0</version>\n</info>\n' > appinfo/info.xml
_register '{"Invoice":{"type":"object","authorization":{"read":["staff"]}}}'
git add -A && git commit --quiet -m "base"
git branch -M base

_branch() { git checkout --quiet base && git checkout --quiet -b "$1"; }

_branch planted
_register '{"Invoice":{"type":"object","x-openregister-rbac":{"read":["staff"]}}}'
git commit --quiet -am "rbac the register never reads"

_branch half-open
_register '{"Invoice":{"type":"object","authorization":{"read":["staff"]}},"Note":{"type":"object"}}'
git commit --quiet -am "one schema left open"

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
    printf '%s\n' "$1" | grep -E '^\[gate-121\] register-auth-dialect: (PASS|FAIL|WARNING|SKIPPED|NOT APPLICABLE)' | head -1
}

echo "-- ARM 1: planted x-openregister-rbac: FAIL --"
_out="$(_run "${APP}" planted --base base)"
_v="$(_verdict "${_out}")"
case "${_v}" in
    *FAIL*) _ok "the dead key fails" ;;
    *)      _bad "expected FAIL, got: ${_v:-<no verdict>}" ;;
esac
if printf '%s\n' "${_out}" | grep -q 'lib/Settings/fixture_register.json: components.schemas.Invoice.x-openregister-rbac'; then
    _ok "the finding names the file and the schema path"
else
    _bad "the finding does not name lib/Settings/fixture_register.json components.schemas.Invoice.x-openregister-rbac"
fi

echo "-- ARM 2: authorization: PASS with the census line --"
_out="$(_run "${APP}" base --base base)"
_v="$(_verdict "${_out}")"
case "${_v}" in
    *PASS*) _ok "a schema on authorization passes" ;;
    *)      _bad "expected PASS, got: ${_v:-<no verdict>}" ;;
esac
if printf '%s\n' "${_out}" | grep -q '^\[gate-121\] register-auth-dialect: checked 1 document(s), 1 schema(s), 0 finding(s)'; then
    _ok "the census line counts what was read"
else
    _bad "no census line in the PASS output"
fi

echo "-- ARM 3: an open schema is report-only --"
_out="$(_run "${APP}" half-open --base base)"
_v="$(_verdict "${_out}")"
case "${_v}" in
    *PASS*) _ok "an open schema does not fail the run yet" ;;
    *)      _bad "expected PASS (report-only), got: ${_v:-<no verdict>}" ;;
esac
if printf '%s\n' "${_out}" | grep -q 'authorization coverage: 1 of 2 schema(s) declare an authorization block, 1 do not (report-only)'; then
    _ok "the coverage line reaches the run's output"
else
    _bad "no coverage line in the run's output"
fi

echo "-- ARM 4: the promotion switch fails an open schema --"
_v="$(_verdict "$(HYDRA_GATE_REGISTER_AUTHORIZATION_BLOCKING=1 _run "${APP}" half-open --base base)")"
case "${_v}" in
    *FAIL*) _ok "HYDRA_GATE_REGISTER_AUTHORIZATION_BLOCKING=1 makes coverage blocking" ;;
    *)      _bad "expected FAIL with the switch on, got: ${_v:-<no verdict>}" ;;
esac

echo "-- ARM 5: no register document: NOT APPLICABLE --"
BARE="${WORK}/bare"
mkdir -p "${BARE}/appinfo" "${BARE}/lib/Settings"
(
    cd "${BARE}" || exit 1
    git init --quiet . && git config user.email f@x.invalid && git config user.name F
    printf '<?xml version="1.0"?>\n<info><id>bare</id><version>1.0.0</version></info>\n' > appinfo/info.xml
    printf '<?php\n' > lib/Settings/Admin.php
    git add -A && git commit --quiet -m base && git branch -M main
)
_v="$(_verdict "$(_run "${BARE}" main --base main)")"
case "${_v}" in
    *"NOT APPLICABLE"*) _ok "a repo with no register document is not applicable" ;;
    *)                  _bad "expected NOT APPLICABLE, got: ${_v:-<no verdict>}" ;;
esac

echo "-- ARM 6: unreadable register: SKIPPED (wiring), never PASS or FAIL --"
_v="$(_verdict "$(_run "${APP}" broken --base base)")"
case "${_v}" in
    *SKIPPED*) _ok "a document the checker cannot read is wiring, not a verdict" ;;
    *)         _bad "expected SKIPPED for unreadable JSON, got: ${_v:-<no verdict>}" ;;
esac

echo
if [ "${_fail_n}" -eq 0 ]; then
    echo "gate-121 scope: all arms passed"
    exit 0
fi
echo "gate-121 scope: ${_fail_n} arm(s) failed"
exit 1
