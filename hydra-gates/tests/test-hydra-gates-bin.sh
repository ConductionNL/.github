#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# test-hydra-gates-bin.sh — invariant tests for the conduction/hydra-gates
# entry point.
#
# These are not tests of the gates themselves (the gates own their fixtures in
# scripts/lib/test_*.py). They test the four properties a CONSUMING repo
# depends on, each of which has a documented history of being silently wrong:
#
#   1. The exit code is the FAILURE COUNT, never collapsed to 0/1.
#   2. An unresolvable base ref FAILS LOUDLY (exit 99) instead of scoping to
#      an empty set and reporting a clean run.
#   3. An empty diff is REPORTED AS EMPTY, not as a green.
#   4. The green states its own coverage — which gates ran, which did not.
#
# Every assertion here is two-directional where it can be: we prove the
# failing case fails AND that the same fixture passes once the violation is
# removed. A one-directional control cannot distinguish "the check caught it"
# from "the check never ran".

set -u

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PKG_ROOT="$(cd "${SELF_DIR}/.." && pwd)"
BIN="${PKG_ROOT}/bin/hydra-gates"

PASS=0
FAIL=0
_ok()   { echo "  ok   — $1"; PASS=$((PASS + 1)); }
_bad()  { echo "  FAIL — $1"; FAIL=$((FAIL + 1)); }

WORK="$(mktemp -d -t hydra-gates-test.XXXXXX)"
trap 'rm -rf "${WORK}"' EXIT

# ---------------------------------------------------------------------------
# Fixture: a minimal repo in the standard Conduction NC app layout, with a
# clean mainline and a branch that introduces exactly two gate violations.
# ---------------------------------------------------------------------------
FIX="${WORK}/fixture"
mkdir -p "${FIX}/lib" "${FIX}/appinfo"
# `|| exit 1` matters here: if this cd fails the fixture gets built in the
# CURRENT directory instead, and every assertion below then measures the wrong
# repository while still looking like a normal run.
cd "${FIX}" || exit 1
# `git init -b <branch>` needs git >= 2.28; Ubuntu 20.04 ships 2.25. Set the
# initial branch through symbolic-ref instead so the fixture builds everywhere.
# When this failed silently the whole suite returned 99 for every case, which
# looked like a wrapper bug rather than a fixture that was never created.
git init -q .
git symbolic-ref HEAD refs/heads/development
git config user.email "test@example.invalid"
git config user.name "hydra-gates test"

cat > appinfo/info.xml <<'XML'
<?xml version="1.0"?>
<info><id>fixture</id><name>Fixture</name><version>1.0.0</version></info>
XML

# A compliant file: SPDX tags present, no debug helpers.
cat > lib/Clean.php <<'PHP'
<?php
/**
 * Clean fixture class.
 *
 * @copyright Copyright (c) 2026 Conduction
 * @license   EUPL-1.2
 */

namespace OCA\Fixture;

class Clean
{
    public function value(): int
    {
        return 1;
    }
}
PHP

git add -A
git commit -qm "base: a clean tree"
BASE_SHA="$(git rev-parse HEAD)"

# ---------------------------------------------------------------------------
# Test 1 — an unresolvable base ref fails loudly, and does NOT report clean.
# ---------------------------------------------------------------------------
echo "[test] unresolvable base ref"
OUT="$("${BIN}" --app-dir "${FIX}" --base origin/does-not-exist 2>&1)"; RC=$?
if [ "${RC}" -eq 99 ]; then
    _ok "exit 99 (could-not-run), not 0"
else
    _bad "expected exit 99, got ${RC}"
fi
if printf '%s' "${OUT}" | grep -q "NOTHING WAS CHECKED"; then
    _ok "states plainly that nothing was checked"
else
    _bad "did not state that nothing was checked"
fi
if printf '%s' "${OUT}" | grep -qi "ALL .* PASSED"; then
    _bad "an unresolvable base printed a green — this is the exact bug"
else
    _ok "no green printed for an unresolvable base"
fi

# ---------------------------------------------------------------------------
# Test 2 — an EMPTY diff is reported as empty rather than as a clean pass.
# ---------------------------------------------------------------------------
# An empty diff and a base that IS HEAD are different facts, and this test used
# to conflate them: its fixture set BASE_SHA to HEAD, so "empty diff exits 0"
# was really asserting "scoping a commit against itself exits 0".
#
# They are separated here because only one of them is legitimate.
#
#   base != HEAD, diff empty   a real PR that changes nothing in scope. Stated,
#                              and green — unchanged, asserted below.
#   base == HEAD               the run cannot inspect anything, by construction.
#                              Measured on shillinq `development` c64e9fe: 22
#                              seconds, 52 gates PASS. Unscoped, the same
#                              commit FAILS 18. Every push-to-mainline scoped
#                              run in the fleet has this shape.
echo "[test] empty diff (base BEHIND head) is stated, not silently green"
git -C "${FIX}" commit -q --allow-empty -m "an empty commit: base is behind HEAD, diff is empty"
OUT="$("${BIN}" --app-dir "${FIX}" --base "${BASE_SHA}" 2>&1)"; RC=$?
if printf '%s' "${OUT}" | grep -q "SCOPE WAS EMPTY"; then
    _ok "empty scope is called out explicitly"
else
    _bad "empty scope was not called out"
fi
if [ "${RC}" -eq 0 ]; then
    _ok "empty diff still exits 0 (it is a legitimate outcome, just a stated one)"
else
    _bad "expected exit 0 on an empty diff, got ${RC}"
fi

echo "[test] a base that IS HEAD is refused, not reported green"
_HEAD_SHA="$(git -C "${FIX}" rev-parse HEAD)"
OUT_SELF="$("${BIN}" --app-dir "${FIX}" --base "${_HEAD_SHA}" 2>&1)"; RC_SELF=$?
if [ "${RC_SELF}" -eq 99 ]; then
    _ok "scoping a commit against itself exits 99 (configuration error, not a clean tree)"
else
    _bad "expected exit 99 when the base IS HEAD, got ${RC_SELF}"
fi
if printf '%s' "${OUT_SELF}" | grep -qE '^\[gate-[0-9]+\] [a-z-]+: PASS'; then
    _bad "a run scoped against its own HEAD still printed gate PASS lines — that is the vacuous green"
else
    _ok "no gate reported PASS: nothing was inspected, and nothing claimed to be"
fi

# ---------------------------------------------------------------------------
# Test 3 — POSITIVE CONTROL, both directions.
#
# Introduce two violations in one new file:
#   gate-1  spdx-headers      — no @license / @copyright
#   gate-2  forbidden-patterns — error_log() shipped in lib/
# Then assert the exit code is 2 — the COUNT — and that BOTH gates are named.
# Then remove the violations and assert the same fixture goes green, which is
# what proves the gates actually inspected the file rather than never running.
# ---------------------------------------------------------------------------
echo "[test] positive control — violation caught, exit code is the count"
git checkout -q -b feature/violation
cat > lib/Dirty.php <<'PHP'
<?php

namespace OCA\Fixture;

class Dirty
{
    public function debug(): void
    {
        error_log('this must not ship');
    }
}
PHP
git add -A
git commit -qm "introduce two gate violations"

OUT="$("${BIN}" --app-dir "${FIX}" --base "${BASE_SHA}" 2>&1)"; RC=$?
if printf '%s' "${OUT}" | grep -qE '^\[gate-1\] .*: FAIL'; then
    _ok "gate-1 spdx-headers named the violation"
else
    _bad "gate-1 did not fire — the injected violation never reached the gate"
fi
if printf '%s' "${OUT}" | grep -qE '^\[gate-2\] .*: FAIL'; then
    _ok "gate-2 forbidden-patterns named the violation"
else
    _bad "gate-2 did not fire — the injected violation never reached the gate"
fi
if [ "${RC}" -eq 2 ]; then
    _ok "exit code is 2 — the failure COUNT, not a boolean 1"
else
    _bad "expected exit 2 (the count), got ${RC}"
fi

echo "[test] positive control — reverse direction"
cat > lib/Dirty.php <<'PHP'
<?php
/**
 * Now compliant.
 *
 * @copyright Copyright (c) 2026 Conduction
 * @license   EUPL-1.2
 */

namespace OCA\Fixture;

class Dirty
{
    public function debug(): void
    {
        // the debug helper is gone
    }
}
PHP
git add -A
git commit -qm "remove both violations"

OUT="$("${BIN}" --app-dir "${FIX}" --base "${BASE_SHA}" 2>&1)"; RC=$?
if [ "${RC}" -eq 0 ]; then
    _ok "same fixture, violations removed — exit 0"
else
    _bad "expected exit 0 after removing the violations, got ${RC}"
    printf '%s\n' "${OUT}" | grep -E ': FAIL' || true
fi

# ---------------------------------------------------------------------------
# Test 4 — the green states its own coverage.
# ---------------------------------------------------------------------------
echo "[test] the green states its coverage"
if printf '%s' "${OUT}" | grep -q "COVERAGE: .* of .* declared gates reported a result"; then
    _ok "coverage line present on a green"
else
    _bad "green did not state how many gates actually ran"
fi
if printf '%s' "${OUT}" | grep -q "WAIVERS:"; then
    _ok "waiver accounting present"
else
    _bad "no waiver accounting — a green cannot be distinguished from a waived one"
fi

# ---------------------------------------------------------------------------
# Test 4b — a gate that DID NOT RUN is named, and cannot hide under a green.
#
# Measured 2026-08-03 across 13 fleet repos: gate-33 (axe-core) has never run in
# any of them, because the tests/axe/report.json it consumes is produced by a
# scripts/run-browser-tests.sh that exists nowhere. Until then it emitted NOTHING
# when its prerequisite was absent — no line, no count — and the runner still
# printed "ALL 63 GATES GREEN". Every green this fleet has produced therefore
# excluded accessibility runtime checking, and nothing in the output said so.
#
# The fixture has no tests/axe/report.json, so this is the real condition.
# ---------------------------------------------------------------------------
echo "[test] a gate that did not run is named, not folded into the green"
# The fixture has no src/ and no tests/axe/report.json, so gate-33's subject
# matter genuinely does not exist here: NOT APPLICABLE, not a coverage gap. What
# matters is that it SAYS SO — the original defect was that it said nothing at
# all, and silence read as a pass.
if printf '%s' "${OUT}" | grep -qE '^\[gate-33\] axe-core: (SKIPPED|NOT APPLICABLE)'; then
    _ok "gate-33 states its own absence instead of emitting nothing"
else
    _bad "gate-33 emitted neither a SKIPPED nor a NOT APPLICABLE line — its absence is still indistinguishable from a pass"
fi
if printf '%s' "${OUT}" | grep -qE '^\[gate-33\] axe-core: NOT APPLICABLE'; then
    _ok "gate-33 is NOT APPLICABLE on a fixture with no src/ (no frontend to analyse)"
else
    _bad "gate-33 was counted as a coverage gap on a repo with no frontend at all"
fi
if printf '%s' "${OUT}" | grep -qE '^\[hydra-gates\] NOT APPLICABLE'; then
    _ok "the summary names the not-applicable gates"
else
    _bad "the summary did not name a single not-applicable gate, though this fixture has no src/"
fi
# The banner must never claim all N gates ran when some did not — whatever the
# reason they did not. NOT APPLICABLE is a reason not to FAIL; it is not a
# reason to claim the gate ran.
if printf '%s' "${OUT}" | grep -qE 'ALL [0-9]+ GATES (GREEN|PASSED) — and all'; then
    _bad "an 'ALL N GATES ... and all N of them ran' banner was printed while $(printf '%s' "${OUT}" | grep -cE ': NOT APPLICABLE') gate(s) did not run"
else
    _ok "no 'all N of them ran' banner while gates did not run"
fi
# Neither a SKIPPED nor a NOT APPLICABLE gate may be counted as coverage — that
# would turn the fix into the bug. Coverage must be strictly less than declared.
_cov_line="$(printf '%s' "${OUT}" | grep -m1 -oE 'COVERAGE: [0-9]+ of [0-9]+' || true)"
_cov_ran="$(printf '%s' "${_cov_line}" | awk '{print $2}')"
_cov_all="$(printf '%s' "${_cov_line}" | awk '{print $4}')"
if [ -n "${_cov_ran:-}" ] && [ -n "${_cov_all:-}" ] && [ "${_cov_ran}" -lt "${_cov_all}" ]; then
    _ok "SKIPPED and NOT APPLICABLE gates are excluded from the coverage tally (${_cov_ran} of ${_cov_all})"
else
    _bad "coverage read '${_cov_line}' — a gate that did not run is being counted as having reported"
fi

# ---------------------------------------------------------------------------
# Test 4c — --require-full-coverage distinguishes THREE states, and only two of
# them fail.
#
# The product owner's requirement, verbatim: "if a gate is legitimately not
# applicable the flag shouldn't fail the run". Before this, it did — measured on
# exactly this fixture: 30 of 63 gates emitted nothing, 25 of them because they
# were guarded by an `if [ -d src ]` on a repo with no frontend, and the flag
# exited 98 on a repository with nothing wrong with it.
#
# Both directions are asserted, because either one alone is satisfiable by a
# broken implementation: a flag that never fails passes 4c-i, and a flag that
# always fails passes 4c-ii.
# ---------------------------------------------------------------------------
echo "[test] --require-full-coverage passes when every non-reporting gate is NOT APPLICABLE"
"${BIN}" --app-dir "${FIX}" --base "${BASE_SHA}" --require-full-coverage > /dev/null 2>&1; RC_RFC=$?
if [ "${RC_RFC}" -eq 0 ]; then
    _ok "a run whose only gaps are not-applicable gates PASSES with the flag set"
else
    _bad "expected exit 0 with --require-full-coverage on an all-not-applicable fixture, got ${RC_RFC}"
fi

echo "[test] --require-full-coverage still FAILS on a structural gap"
# Reverse control. Give the fixture a frontend that registers an integration
# leaf: gate-24's subject matter now EXISTS, and nothing in this repo correlates
# the two halves of it. That is category (b) — structurally impossible — and it
# must fail. Same fixture, same flag, opposite verdict: this is what proves the
# pass above is a verdict and not an inability to fail.
mkdir -p "${FIX}/src"
cat > "${FIX}/src/leaf.js" <<'JS'
// SPDX-License-Identifier: EUPL-1.2
import { registerIntegration } from '@conduction/nextcloud-vue'
registerIntegration({ id: 'fixture-leaf', renderMode: 'component' })
JS
git -C "${FIX}" add -A >/dev/null 2>&1
git -C "${FIX}" commit -qm "fixture: register an integration leaf" >/dev/null 2>&1
OUT_STRUCT="$("${BIN}" --app-dir "${FIX}" --base "${BASE_SHA}" --require-full-coverage 2>&1)"; RC_STRUCT=$?
if [ "${RC_STRUCT}" -eq 98 ]; then
    _ok "a structural gap (leaves registered, no parity check) exits 98 with the flag set"
else
    _bad "expected exit 98 for a structural coverage gap, got ${RC_STRUCT}"
fi
if printf '%s' "${OUT_STRUCT}" | grep -qE '^\[gate-24\] integration-parity: SKIPPED \(structural\)'; then
    _ok "gate-24 names its gap as structural, and says which half of the pair exists"
else
    _bad "gate-24 did not report a structural skip although this fixture registers a leaf"
fi
# Positive control for the applicability declarations: src/ now EXISTS, so the
# gates guarded by `[ -d src ]` must genuinely RUN. If the declaration table
# ever drifts away from the guards it mirrors, it would keep calling them
# not-applicable here — which is the one way this change could hide a live gate.
_still_na=""
for _g in 10 12 13 26 31 32 34 35 36 37 39 40 42 43 44 45; do
    printf '%s' "${OUT_STRUCT}" | grep -qE "^\[gate-${_g}\] [a-z-]+: NOT APPLICABLE" && _still_na="${_still_na}${_g} "
done
if [ -z "${_still_na}" ]; then
    _ok "with src/ present, every src-guarded gate really runs (applicability table tracks its guards)"
else
    _bad "gates ${_still_na}were still called NOT APPLICABLE though src/ exists — the table has drifted from the guards it mirrors"
fi

echo "[test] an unrecognised skip category is a hard failure, never a silent 'na'"
# A typo'd category that defaulted to `na` would be a lever for making any
# gate's absence stop counting — the accounting hole this block closes, reopened
# from the inside. It must fail loudly instead.
TYPO_PKG="${WORK}/typo"
mkdir -p "${TYPO_PKG}/bin" "${TYPO_PKG}/scripts"
cp "${BIN}" "${TYPO_PKG}/bin/hydra-gates"
cp -r "${PKG_ROOT}/scripts/lib" "${TYPO_PKG}/scripts/lib"
# Corrupt the category on the gate-33 branch this fixture actually REACHES
# (src/ exists, no axe report, caller did not declare enable-axe). Patching a
# branch that does not execute would make this test pass by never running the
# code it claims to test — the same defect the whole suite exists to catch. The
# assertion below therefore also proves the patch LANDED.
python3 - "${PKG_ROOT}/scripts/run-hydra-gates.sh" "${TYPO_PKG}/scripts/run-hydra-gates.sh" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src).read()
needle = '_skip 33 "axe-core" na "no ${_axe_report}, and the caller did not set enable-axe'
assert needle in s, "typo-test needle not found — the gate-33 branch it corrupts has been reworded"
s = s.replace(needle, '_skip 33 "axe-core" nq "no ${_axe_report}, and the caller did not set enable-axe', 1)
open(dst, 'w').write(s)
PY
chmod +x "${TYPO_PKG}/scripts/run-hydra-gates.sh"
OUT_TYPO="$("${TYPO_PKG}/bin/hydra-gates" --app-dir "${FIX}" --base "${BASE_SHA}" 2>&1)"; RC_TYPO=$?
if [ "${RC_TYPO}" -ne 0 ] && printf '%s' "${OUT_TYPO}" | grep -q "is not one of na|structural|wiring"; then
    _ok "an unrecognised reason category fails the gate instead of resolving to 'na'"
else
    _bad "a typo'd reason category did not fail (exit ${RC_TYPO}) — any gate could stop counting by misspelling its category"
fi
# Reverse control: the UNPATCHED runner on the same fixture must NOT emit that
# internal error. Without this, "the error appeared" could equally mean the
# error appears always.
if "${BIN}" --app-dir "${FIX}" --base "${BASE_SHA}" 2>&1 | grep -q "is not one of na|structural|wiring"; then
    _bad "the unpatched runner also reports an unrecognised category — the assertion above proves nothing"
else
    _ok "reverse control — the unpatched runner reports no category error"
fi

# ---------------------------------------------------------------------------
# Test 4d — no gate verdict line may wrap onto a second line.
#
# gate-22 printed "FAIL — 0" on opencatalogi with the rest of its message
# orphaned onto an unparseable second line, because a `grep -c … || echo 1`
# captured "0\n1". Every consumer of this runner anchors on `^\[gate-`, so a
# wrapped verdict silently loses its own reason AND its count.
# ---------------------------------------------------------------------------
echo "[test] every gate verdict is exactly one line"
_orphans="$(printf '%s\n' "${OUT}" | grep -cE '^[0-9]+ (schema violation|parity violation|structural violation|cross-reference)' || true)"
if [ "${_orphans}" = "0" ]; then
    _ok "no orphaned continuation line from a miscounted gate message"
else
    _bad "a gate message wrapped onto a second line — the count variable held a newline"
fi

# ---------------------------------------------------------------------------
# Test 5 — a broken install is exit 99, never a green.
# ---------------------------------------------------------------------------
echo "[test] a package with no runner cannot report green"
BROKEN="${WORK}/broken/bin"
mkdir -p "${BROKEN}"
cp "${BIN}" "${BROKEN}/hydra-gates"
OUT="$("${BROKEN}/hydra-gates" --app-dir "${FIX}" --base "${BASE_SHA}" 2>&1)"; RC=$?
if [ "${RC}" -eq 99 ]; then
    _ok "missing runner exits 99"
else
    _bad "expected exit 99 for a missing runner, got ${RC}"
fi
if printf '%s' "${OUT}" | grep -q "This is NOT a green"; then
    _ok "says so in words"
else
    _bad "did not say the incomplete install is not a green"
fi

# ---------------------------------------------------------------------------
# Test 6 — a gate whose HELPER is absent must SKIP, never PASS.
#
# Distinct from Test 4b, which covers a gate whose INPUT is absent (gate-33 has
# no tests/axe/report.json). This is the other half: the gate's own helper
# script is missing, so the gate ran its file enumeration, found work to do, and
# then could not do it.
#
# Sixteen gates used to handle that by echoing a WARN to STDERR and falling
# through to `_pass`. `_pass` adds the gate to _EMITTED_GATES, so the gate was
# counted as having reported — which means those sixteen branches actively
# defeated the coverage machinery built to catch exactly this. Two of them,
# gate-6 (orphan-auth) and gate-7 (no-admin-idor), are AUTHORIZATION gates.
#
# Measured on a real repo checkout while fixing this: with check_no_admin_idor.py
# present, gate-7 reported `FAIL — 11 method(s) with NoAdminRequired + no guard`.
# With the same helper renamed away, the same gate on the same tree reported
# `PASS`. An empty findings log because the helper never ran was byte-identical
# to an empty log because there were no findings.
#
# The control here is two-directional and attributable: the SAME fixture is run
# against two copies of the package that differ ONLY in whether those two helper
# files exist. Coverage must drop by exactly 2, and the two gates must be named.
# ---------------------------------------------------------------------------
echo "[test] a gate whose helper is absent skips instead of passing"

# A fixture with a controller in the DIFF — gates 6/7 enumerate lib/Controller
# and lib/Service, so an empty scope would give them no files and the
# helper-missing branch would never be reached (which would make this test pass
# for the wrong reason).
SECFIX="${WORK}/sec-fixture"
mkdir -p "${SECFIX}/lib/Controller" "${SECFIX}/appinfo"
cd "${SECFIX}" || exit 1
git init -q .
git symbolic-ref HEAD refs/heads/development
git config user.email "test@example.invalid"
git config user.name "hydra-gates test"
cat > appinfo/info.xml <<'XML'
<?xml version="1.0"?>
<info><id>fixture</id><name>Fixture</name><version>1.0.0</version></info>
XML
git add -A
git commit -qm "base"
SEC_BASE="$(git rev-parse HEAD)"
git checkout -q -b feature/controller
cat > lib/Controller/ThingController.php <<'PHP'
<?php
/**
 * Thing controller fixture.
 *
 * @copyright Copyright (c) 2026 Conduction
 * @license   EUPL-1.2
 */

namespace OCA\Fixture\Controller;

class ThingController
{
    /**
     * Return a constant.
     *
     * @spec exclude fixture-only controller, no product behaviour
     */
    public function show(): int
    {
        return 2;
    }
}
PHP
git add -A
git commit -qm "add a controller to the diff"

# Package copy that differs from the real one ONLY by the two missing helpers.
NOHELP="${WORK}/pkg-no-security-helpers"
cp -r "${PKG_ROOT}" "${NOHELP}"
rm -f "${NOHELP}/scripts/lib/check_orphan_auth.py" \
      "${NOHELP}/scripts/lib/check_no_admin_idor.py"

SEC_WITH="$("${BIN}" --app-dir "${SECFIX}" --base "${SEC_BASE}" 2>&1)" || true
SEC_WITHOUT="$("${NOHELP}/bin/hydra-gates" --app-dir "${SECFIX}" --base "${SEC_BASE}" 2>&1)" || true

# Direction 1 — helpers PRESENT: the gates report a verdict, as before.
if printf '%s\n' "${SEC_WITH}" | grep -qE '^\[gate-6\] orphan-auth: (PASS|FAIL)' \
   && printf '%s\n' "${SEC_WITH}" | grep -qE '^\[gate-7\] no-admin-idor: (PASS|FAIL)'; then
    _ok "helpers present — gates 6 and 7 still report a verdict"
else
    _bad "helpers present — gate 6/7 did not report a verdict; the fixture is not exercising them"
fi

# Direction 2 — helpers ABSENT: SKIPPED, and explicitly NOT a pass.
if printf '%s\n' "${SEC_WITHOUT}" | grep -qE '^\[gate-6\] orphan-auth: SKIPPED' \
   && printf '%s\n' "${SEC_WITHOUT}" | grep -qE '^\[gate-7\] no-admin-idor: SKIPPED'; then
    _ok "helpers absent — the two authorization gates report SKIPPED"
else
    _bad "helpers absent — gate 6/7 did not report SKIPPED"
fi
if printf '%s\n' "${SEC_WITHOUT}" | grep -qE '^\[gate-(6|7)\] [a-z-]+: PASS'; then
    _bad "an authorization gate printed PASS while its helper was missing — the original bug"
else
    _ok "no authorization gate claims PASS without its helper"
fi

# The summary must NAME them, and only in the direction where they skipped.
if printf '%s\n' "${SEC_WITHOUT}" | grep -qE '^\[hydra-gates\]   gate-6 orphan-auth' \
   && printf '%s\n' "${SEC_WITHOUT}" | grep -qE '^\[hydra-gates\]   gate-7 no-admin-idor'; then
    _ok "the summary names gate-6 and gate-7 among the gates that did not run"
else
    _bad "gate 6/7 skipped but were not named in the DID NOT RUN list"
fi
if printf '%s\n' "${SEC_WITH}" | grep -qE '^\[hydra-gates\]   gate-(6|7) '; then
    _bad "gate 6/7 were listed as not-run even though their helpers were present"
else
    _ok "reverse control — with helpers present they are absent from the DID NOT RUN list"
fi

# Attributable arithmetic: the two runs differ ONLY by those two helper files,
# so the reported coverage must differ by exactly 2. This is what distinguishes
# "the skip is being counted" from "the banner was merely reworded".
_sec_with_n="$(printf '%s\n' "${SEC_WITH}" | grep -m1 -oE 'COVERAGE: [0-9]+' | awk '{print $2}')"
_sec_without_n="$(printf '%s\n' "${SEC_WITHOUT}" | grep -m1 -oE 'COVERAGE: [0-9]+' | awk '{print $2}')"
if [ -n "${_sec_with_n:-}" ] && [ -n "${_sec_without_n:-}" ] \
   && [ "$((_sec_with_n - _sec_without_n))" -eq 2 ]; then
    _ok "coverage drops by exactly 2 when exactly 2 helpers are removed (${_sec_with_n} → ${_sec_without_n})"
else
    _bad "coverage went ${_sec_with_n:-?} → ${_sec_without_n:-?}; removing 2 helpers must remove exactly 2 from the tally"
fi

# ---------------------------------------------------------------------------
# The capability literals ConductionNL/.github's quality.yml probes for.
#
# quality.yml is consumed at @main; this package is consumed at whatever tag the
# caller pinned, so the workflow cannot assume the package it checked out can
# honour --require-full-coverage. It decides by reading two literals out of the
# package's own files:
#
#   _NA_GATES        in scripts/run-hydra-gates.sh   (the not-applicable tally)
#   "NOT APPLICABLE" in bin/hydra-gates              (the wrapper's own recount)
#
# Both were introduced by the accounting fix and are absent from every earlier
# published tag, which is what makes them a usable discriminator against a pin
# that may be a tag, a branch, a SHA or a fork.
#
# Rename either one and the probe answers "this package is too old" for the
# CURRENT package — coverage enforcement would switch itself off in every repo
# in the fleet, and the warning would blame the caller's pin. The rename is the
# realistic accident; that it fails silently, in the direction that looks
# greener, is what makes it worth an assertion here rather than a comment there.
echo "[test] the capability literals quality.yml probes for still exist"
if grep -q '_NA_GATES' "${PKG_ROOT}/scripts/run-hydra-gates.sh"; then
    _ok "run-hydra-gates.sh still carries _NA_GATES (quality.yml's capability probe)"
else
    _bad "run-hydra-gates.sh no longer contains _NA_GATES — quality.yml would read this package as predating the coverage accounting and WITHHOLD --require-full-coverage fleet-wide. Restore the name, or change the probe in .github/workflows/quality.yml in the same commit."
fi
if grep -q 'NOT APPLICABLE' "${BIN}"; then
    _ok "bin/hydra-gates still emits the NOT APPLICABLE verdict (quality.yml's capability probe)"
else
    _bad "bin/hydra-gates no longer contains 'NOT APPLICABLE' — quality.yml would read this package as predating the coverage accounting and WITHHOLD --require-full-coverage fleet-wide. Restore the wording, or change the probe in .github/workflows/quality.yml in the same commit."
fi
# Reverse control: the probe must NOT match a package that genuinely predates
# the fix. Without this, an assertion that greps for a common word would pass on
# every version and prove nothing about the discriminator.
_probe_old="${WORK}/probe-old"
mkdir -p "${_probe_old}"
printf '%s\n' 'echo "[hydra-gates] GATES THAT DID NOT RUN: 4 24 33"' > "${_probe_old}/runner.sh"
printf '%s\n' 'echo "[hydra-gates] COVERAGE: 58 of 61 declared gates reported a result."' > "${_probe_old}/wrapper"
if grep -q '_NA_GATES' "${_probe_old}/runner.sh" || grep -q 'NOT APPLICABLE' "${_probe_old}/wrapper"; then
    _bad "the capability probe matches pre-v1.3.0 output too — it is not a discriminator, and every old pin would be handed a flag it cannot honour"
else
    _ok "reverse control — the probe does NOT match the pre-v1.3.0 shape of either file"
fi

echo ""
echo "=================================================="
echo "hydra-gates entry-point tests: ${PASS} passed, ${FAIL} failed"
echo "=================================================="
[ "${FAIL}" -eq 0 ] || exit 1
exit 0
