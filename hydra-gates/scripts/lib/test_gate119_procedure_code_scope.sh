#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# gate-119 (procedure-code): acceptance over a REAL git history, through the
# real runner. The rule-by-rule arms live in test_check_procedure_code.py; this
# suite pins what only the runner can get wrong: the verdict word, the scope,
# and the ratchet in both directions.
#
#   ARM 1  no baseline file is NOT APPLICABLE, never PASS (the convention for
#          the PR that adds the gate)
#   ARM 2  count equals the baseline: PASS, with the census line
#   ARM 3  a change that adds procedure-named code FAILS
#   ARM 4  a change that removes some without lowering the baseline FAILS and
#          names the number to write
#   ARM 5  removing AND lowering in one change PASSES
#   ARM 6  raising the baseline in the same change FAILS
#   ARM 7  an allowlisted adapter file added by the change does not move the count
#   ARM 8  a baseline that is not JSON FAILS (not NOT APPLICABLE)
#   ARM 9  a checker that cannot run is SKIPPED (wiring), never PASS and never a finding
#   ARM 10 no delta base still judges the count (not a delta gate)

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
RUNNER="${SCRIPT_DIR}/../run-hydra-gates.sh"

_fail_n=0
_ok()  { printf '  ok:   %s\n' "$1"; }
_bad() { _fail_n=$((_fail_n + 1)); printf '  FAIL: %s\n' "$1"; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/gate119-scope.XXXXXXXX")"
trap 'rm -rf "${WORK}"' EXIT
APP="${WORK}/app"
mkdir -p "${APP}/appinfo" "${APP}/lib/Service" "${APP}/src"

cat > "${APP}/appinfo/info.xml" <<'XML'
<?xml version="1.0"?>
<info>
    <id>fixture</id>
    <name>Fixture</name>
    <version>1.0.0</version>
</info>
XML

cd "${APP}" || exit 1
git init --quiet .
git config user.email fixture@example.invalid
git config user.name Fixture

# ── base: two procedure files, one generic file, NO baseline yet.
printf '<?php\nclass BezwaarService {}\n' > lib/Service/BezwaarService.php
printf '<?php\nclass WooService {}\n' > lib/Service/WooService.php
printf '<?php\nclass ObjectService {}\n' > lib/Service/ObjectService.php
echo "x" > README.md
git add -A && git commit --quiet -m "base"
git branch -M base

# ── nobaseline: an unrelated change, no baseline anywhere.
git checkout --quiet -b nobaseline
echo "y" >> README.md
git commit --quiet -am "unrelated"

# ── adopted: base carries a baseline of 2.
git checkout --quiet base
git checkout --quiet -b adopted-base
echo '{"count": 2}' > .procedure-code-baseline.json
git add -A && git commit --quiet -m "adopt baseline"
git branch -M adopted

_branch() { git checkout --quiet adopted && git checkout --quiet -b "$1"; }

_branch equal
echo "y" >> README.md
git commit --quiet -am "unrelated"

_branch grew
printf '<?php\nclass BeschikkingService {}\n' > lib/Service/BeschikkingService.php
git add -A && git commit --quiet -m "add a procedure class"

_branch shrank-stale
git rm --quiet lib/Service/WooService.php
git commit --quiet -m "remove WooService, forget the baseline"

_branch shrank-lowered
git rm --quiet lib/Service/WooService.php
echo '{"count": 1}' > .procedure-code-baseline.json
git add -A && git commit --quiet -m "remove WooService, lower the baseline"

_branch lifted
printf '<?php\nclass BeschikkingService {}\n' > lib/Service/BeschikkingService.php
echo '{"count": 3}' > .procedure-code-baseline.json
git add -A && git commit --quiet -m "add a class and lift the ceiling"

_branch adapter
mkdir -p lib/Service/Zgw
printf '<?php\nclass BesluitMapper {}\n' > lib/Service/Zgw/BesluitMapper.php
printf '<?php\nclass StufBeschikking {}\n' > lib/Service/StufBeschikking.php
git add -A && git commit --quiet -m "add national-standard adapters"

_branch badjson
echo '{not json' > .procedure-code-baseline.json
git commit --quiet -am "break the baseline"

_run() {  # <branch> [extra runner args...]
    local _b="$1"; shift
    git checkout --quiet "${_b}"
    mkdir -p "${WORK}/logs-${_b}"
    HYDRA_GATE_LOG_DIR="${WORK}/logs-${_b}" bash "${RUNNER}" "$@" "${APP}" 2>&1
}

_verdict() {
    printf '%s\n' "$1" | grep -E '^\[gate-119\] procedure-code: (PASS|FAIL|WARNING|SKIPPED|NOT APPLICABLE)' | head -1
}

echo "-- ARM 1: no baseline file is NOT APPLICABLE, never PASS --"
_v="$(_verdict "$(_run nobaseline --base base)")"
case "${_v}" in
    *"NOT APPLICABLE"*) _ok "no baseline: the gate says it compared nothing" ;;
    *)                  _bad "expected NOT APPLICABLE without a baseline, got: ${_v:-<no verdict>}" ;;
esac
case "${_v}" in
    *PASS*) _bad "PASS without a baseline" ;;
    *)      _ok "not a PASS" ;;
esac

echo "-- ARM 2: count equals the baseline PASSES --"
_out="$(_run equal --base adopted)"
case "$(_verdict "${_out}")" in
    *PASS*) _ok "2 files, baseline 2" ;;
    *)      _bad "expected PASS at equality, got: $(_verdict "${_out}")" ;;
esac
case "${_out}" in
    *"counted 2 file(s), baseline 2"*) _ok "the census line shows what was counted" ;;
    *) _bad "no census line" ;;
esac

echo "-- ARM 3: adding procedure-named code FAILS --"
_out="$(_run grew --base adopted)"
case "$(_verdict "${_out}")" in
    *FAIL*) _ok "3 files against a baseline of 2" ;;
    *)      _bad "expected FAIL on growth, got: $(_verdict "${_out}")" ;;
esac
if printf '%s\n' "${_out}" | grep -q 'the change added 1'; then _ok "the finding says how many"; else _bad "the finding does not say how many"; fi

echo "-- ARM 4: removing without lowering the baseline FAILS and names the number --"
_out="$(_run shrank-stale --base adopted)"
case "$(_verdict "${_out}")" in
    *FAIL*) _ok "1 file against a baseline of 2" ;;
    *)      _bad "expected FAIL on a stale baseline, got: $(_verdict "${_out}")" ;;
esac
if printf '%s\n' "${_out}" | grep -qF '{"count": 1}'; then _ok "the message gives the number to write"; else _bad "no number to write in the message"; fi

echo "-- ARM 5: removing and lowering in one change PASSES --"
case "$(_verdict "$(_run shrank-lowered --base adopted)")" in
    *PASS*) _ok "the ratchet moved down together" ;;
    *)      _bad "expected PASS when baseline follows the count" ;;
esac

echo "-- ARM 6: raising the baseline FAILS --"
_out="$(_run lifted --base adopted)"
case "$(_verdict "${_out}")" in
    *FAIL*) _ok "count 3, baseline 3, but the ceiling was lifted" ;;
    *)      _bad "expected FAIL when the baseline is raised, got: $(_verdict "${_out}")" ;;
esac
if printf '%s\n' "${_out}" | grep -q 'raised from 2 to 3'; then _ok "the finding names both numbers"; else _bad "the raise is not named"; fi

echo "-- ARM 7: national-standard adapters do not move the count --"
_out="$(_run adapter --base adopted)"
case "$(_verdict "${_out}")" in
    *PASS*) _ok "a Zgw path and a Stuf name are excluded" ;;
    *)      _bad "expected PASS with only adapters added, got: $(_verdict "${_out}")" ;;
esac
case "${_out}" in
    *"2 allowlisted"*) _ok "the census says two were allowlisted" ;;
    *) _bad "allowlisted count not reported" ;;
esac

echo "-- ARM 8: a baseline that is not JSON FAILS --"
case "$(_verdict "$(_run badjson --base adopted)")" in
    *FAIL*) _ok "an unreadable baseline is a finding, not NOT APPLICABLE" ;;
    *)      _bad "expected FAIL on a broken baseline" ;;
esac

echo "-- ARM 9: a checker that cannot run is SKIPPED (wiring) --"
_v="$(HYDRA_GATE_PROCEDURE_CONFIG="${WORK}/does-not-exist.json" _run equal --base adopted | grep -E '^\[gate-119\] procedure-code: (PASS|FAIL|SKIPPED|NOT APPLICABLE)' | head -1)"
case "${_v}" in
    *"SKIPPED (wiring)"*) _ok "a missing config is not a pass and not a finding" ;;
    *)                    _bad "expected SKIPPED (wiring), got: ${_v:-<no verdict>}" ;;
esac

echo "-- ARM 10: no delta base still judges the count --"
case "$(_verdict "$(_run grew --full)")" in
    *FAIL*) _ok "a full-scope run holds the count to the baseline" ;;
    *)      _bad "expected FAIL on a full-scope run of the grown tree" ;;
esac

echo ""
if [ "${_fail_n}" -eq 0 ]; then
    echo "gate-119 procedure-code acceptance: all arms passed."
    exit 0
fi
echo "gate-119 procedure-code acceptance: ${_fail_n} arm(s) failed."
exit 1
