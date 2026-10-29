#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# gate-122 (sig-maintainability): acceptance through the real runner. The
# rule-by-rule arms live in test_check_sig_maintainability.py; this suite pins
# what only the runner can get wrong: the mode chosen from the delta base, the
# verdict word, the promotion switch, and a missing tool read as a pass.
#
#   ARM 1  a new unit with five parameters: WARNING, naming file, line and unit
#   ARM 2  ARM 1 with HYDRA_GATE_SIG_MAINTAINABILITY_BLOCKING=1: FAIL
#   ARM 3  a small new unit: PASS, with the census line
#   ARM 4  no delta base: report mode, PASS, and sig-profile.json and .md land
#          in HYDRA_GATE_SIG_REPORT_DIR
#   ARM 5  a change that touches no measured source: NOT APPLICABLE
#   ARM 6  the pinned tools unavailable and installing forbidden: SKIPPED
#          (wiring), never PASS

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
RUNNER="${SCRIPT_DIR}/../run-hydra-gates.sh"

_fail_n=0
_ok()  { printf '  ok:   %s\n' "$1"; }
_bad() { _fail_n=$((_fail_n + 1)); printf '  FAIL: %s\n' "$1"; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/gate122-scope.XXXXXXXX")"
trap 'rm -rf "${WORK}"' EXIT
APP="${WORK}/app"
mkdir -p "${APP}/appinfo" "${APP}/lib/Service"

_method() {  # <name> <params> -> a small PHP method
    local _p="" _i
    for _i in $(seq 1 "$2"); do _p="${_p}${_p:+, }\$p${_i}"; done
    printf '    public function %s(%s): int\n    {\n        return strlen(\x27%s\x27);\n    }\n' "$1" "${_p}" "$1"
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
_class Base "$(_method existing 1)"
printf 'fixture\n' > README.md
git add -A && git commit --quiet -m "base"
git branch -M base

_branch() { git checkout --quiet base && git checkout --quiet -b "$1"; }

_branch planted
_class Fresh "$(_method wide 5)"
git add -A && git commit --quiet -m "a five-parameter unit"

_branch clean
_class Fresh "$(_method narrow 2)"
git add -A && git commit --quiet -m "a small unit"

_branch docs
printf 'changed\n' > README.md
git commit --quiet -am "docs only"

_run() {  # <branch> [extra runner args...]
    local _b="$1"; shift
    git -C "${APP}" checkout --quiet "${_b}"
    mkdir -p "${WORK}/logs-${_b}"
    HYDRA_GATE_LOG_DIR="${WORK}/logs-${_b}" bash "${RUNNER}" "$@" "${APP}" 2>&1
}

_verdict() {
    printf '%s\n' "$1" | grep -E '^\[gate-122\] sig-maintainability: (PASS|FAIL|WARNING|SKIPPED|NOT APPLICABLE)' | head -1
}

echo "-- ARM 1: a five-parameter unit: WARNING --"
_out="$(_run planted --base base)"
_v="$(_verdict "${_out}")"
case "${_v}" in
    *WARNING*) _ok "a new wide unit warns" ;;
    *)         _bad "expected WARNING, got: ${_v:-<no verdict>}" ;;
esac
if printf '%s\n' "${_out}" | grep -q 'lib/Service/Fresh.php:6 Fresh::wide: 5 or more parameters: 5'; then
    _ok "the finding names the file, line and unit"
else
    _bad "the finding does not name lib/Service/Fresh.php:6 Fresh::wide"
fi

echo "-- ARM 2: the promotion switch blocks --"
_v="$(_verdict "$(HYDRA_GATE_SIG_MAINTAINABILITY_BLOCKING=1 _run planted --base base)")"
case "${_v}" in
    *FAIL*) _ok "HYDRA_GATE_SIG_MAINTAINABILITY_BLOCKING=1 makes it FAIL" ;;
    *)      _bad "expected FAIL with the switch on, got: ${_v:-<no verdict>}" ;;
esac

echo "-- ARM 3: a small unit: PASS with the census line --"
_out="$(_run clean --base base)"
_v="$(_verdict "${_out}")"
case "${_v}" in
    *PASS*) _ok "a small unit passes" ;;
    *)      _bad "expected PASS, got: ${_v:-<no verdict>}" ;;
esac
if printf '%s\n' "${_out}" | grep -q '^\[gate-122\] sig-maintainability: checked 1 changed unit(s) in 1 file(s), 0 finding(s)'; then
    _ok "the census line counts what was judged"
else
    _bad "no census line in the PASS output"
fi

echo "-- ARM 4: no delta base: report mode --"
REPORTS="${WORK}/reports"
_out="$(HYDRA_GATE_SIG_REPORT_DIR="${REPORTS}" _run planted)"
_v="$(_verdict "${_out}")"
case "${_v}" in
    *PASS*) _ok "a full-scope run with no base reports and passes" ;;
    *)      _bad "expected PASS (report-only), got: ${_v:-<no verdict>}" ;;
esac
if [ -s "${REPORTS}/sig-profile.json" ] && [ -s "${REPORTS}/sig-profile.md" ] \
    && python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d["languages"]["php"]["units"] == 2 else 1)' "${REPORTS}/sig-profile.json"; then
    _ok "sig-profile.json (2 php units) and sig-profile.md are written to HYDRA_GATE_SIG_REPORT_DIR"
else
    _bad "the report files are missing or do not count the 2 php units"
fi
if printf '%s\n' "${_out}" | grep -q '^\[gate-122\] sig-maintainability: report: 2 unit(s) in 2 file(s)'; then
    _ok "the report census line reaches the run's output"
else
    _bad "no report census line in the run's output"
fi

echo "-- ARM 5: docs only: NOT APPLICABLE --"
_v="$(_verdict "$(_run docs --base base)")"
case "${_v}" in
    *"NOT APPLICABLE"*) _ok "a change with no measured source is not applicable" ;;
    *)                  _bad "expected NOT APPLICABLE, got: ${_v:-<no verdict>}" ;;
esac

echo "-- ARM 6: tools unavailable: SKIPPED (wiring) --"
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
    echo "gate-122 scope: all arms passed"
    exit 0
fi
echo "gate-122 scope: ${_fail_n} arm(s) failed"
exit 1
