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
echo "[test] empty diff is stated, not silently green"
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

echo ""
echo "=================================================="
echo "hydra-gates entry-point tests: ${PASS} passed, ${FAIL} failed"
echo "=================================================="
[ "${FAIL}" -eq 0 ] || exit 1
exit 0
