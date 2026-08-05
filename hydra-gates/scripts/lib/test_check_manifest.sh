#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# test_check_manifest.sh — gate-22 (manifest-validation) verification.
#
# Proves the contract of scripts/lib/check_manifest.js:
#   1. valid-apphost     → PASS (observability + deepLinks validated for-real)
#   2. malformed-apphost → FAIL (unknown check type / metric kind / missing
#      deepLink required key → really validating, not fail-open)
#   3. non-apphost       → PASS (no observability/deepLinks → unaffected)
#   4. no Ajv            → exit 3 DEGRADED, never 0. A run that never applied
#      the schema is not a pass, and it must say so on both channels.
#   5. --scope-ids       → ADR-020: a finding on an entry the PR did not touch
#      is reported PRE-EXISTING and does not set the exit code; the SAME
#      finding does block once that entry is in scope.
#
# THE FIXTURES ARE PART OF THIS TEST. Before 2026-08-03 this file referenced
# ../test-fixtures/manifest-validation/*.json — a directory that has never
# existed in this repository. `node check_manifest.js <missing-path>` prints
# "no src/manifest.json — Tier 0, skipping" and exits 0, which is exactly what
# assertions 1 and 3 expected. Two of the three therefore passed by inspecting
# NOTHING; only the malformed case (which wanted rc=1) ever reported the truth.
# A suite that is green because its inputs are absent is the same defect this
# package exists to catch, one level down.
#
# Run twice: once with Ajv available (full schema path) and once with Ajv
# forced unavailable (structural-lint fallback), so both code paths are covered.

# Private per-invocation log. A fixed /tmp path made this suite fail under
# the helper-suite harness when two runs overlapped: the second run
# truncated the first run's validator output between the write and the grep.
_TCM_LOG="$(mktemp "${TMPDIR:-/tmp}/hydra-tcm.XXXXXXXX.log")"

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
VALIDATOR="${SCRIPT_DIR}/check_manifest.js"
FIX="${SCRIPT_DIR}/../test-fixtures/manifest-validation"

_fails=0
_ok() { echo "PASS — $1"; }
_no() { echo "FAIL — $1"; _fails=$((_fails + 1)); }

# Guard the guard: if the fixtures go missing again, say so rather than quietly
# re-running the "Tier 0, skipping" exit-0 path and reporting it as green.
for _f in valid-apphost malformed-apphost non-apphost; do
	if [ ! -f "${FIX}/${_f}.manifest.json" ]; then
		echo "FAIL — fixture ${FIX}/${_f}.manifest.json is MISSING; this suite cannot assert anything"
		exit 1
	fi
done

_assert() { # <expected-rc> <fixture> <label> [extra args...]
	local want="$1" fixture="$2" label="$3" rc
	shift 3
	node "${VALIDATOR}" "${FIX}/${fixture}" "$@" >"${_TCM_LOG}" 2>&1
	rc=$?
	if [ "${rc}" -eq "${want}" ]; then
		_ok "${label} (rc=${rc})"
	else
		_no "${label}: expected rc=${want}, got ${rc}"
		sed 's/^/    /' "${_TCM_LOG}"
	fi
}

_assert_log() { # <grep-ere> <label>
	if grep -qE "$1" "${_TCM_LOG}"; then
		_ok "$2"
	else
		_no "$2 (pattern not found: $1)"
		sed 's/^/    /' "${_TCM_LOG}"
	fi
}

_HAVE_AJV=0
if node -e "require('ajv/dist/2020')" >/dev/null 2>&1; then _HAVE_AJV=1; fi

echo "== Ajv path =="
if [ "${_HAVE_AJV}" -eq 0 ]; then
	# Say it out loud rather than reporting a green over a path that never ran —
	# the caller (CI) is expected to `npm i ajv ajv-formats` first.
	echo "SKIP — ajv is not resolvable here, so the FULL SCHEMA path was NOT exercised."
	echo "SKIP — install it (npm i ajv ajv-formats, or set NODE_PATH) to test it for real."
else
	_assert 0 valid-apphost.manifest.json     "valid observability + deepLinks → PASS"
	_assert 1 malformed-apphost.manifest.json "malformed observability/deepLinks → FAIL"
	_assert_log '^at /observability/health/checks/0/type' "the failure NAMES the bad health-check type"
	_assert_log '^at /deepLinks/0' "the failure NAMES the incomplete deepLink"
	_assert 0 non-apphost.manifest.json       "non-AppHost manifest → PASS (unaffected)"
fi

# --- the degraded contract --------------------------------------------------
echo
echo "== no-Ajv path: a weaker check must not report as a pass =="
if NODE_PATH=/nonexistent-no-ajv node -e "try{require('ajv/dist/2020');process.exit(0)}catch(e){process.exit(3)}" 2>/dev/null; then
	echo "SKIP — ajv resolves even with NODE_PATH overridden; cannot exercise the degraded path here"
else
	NODE_PATH=/nonexistent-no-ajv _assert 3 valid-apphost.manifest.json \
		"clean manifest without Ajv → exit 3 DEGRADED, NOT 0"
	_assert_log 'SCHEMA VALIDATION DID NOT HAPPEN' "the degradation is stated in words, not just an exit code"
	_assert_log '"status":"degraded"' "the machine-readable summary says degraded, not passed"
	# A real finding must still win: the degradation must never mask a violation.
	NODE_PATH=/nonexistent-no-ajv _assert 1 malformed-apphost.manifest.json \
		"malformed manifest without Ajv → exit 1 (a real finding still wins over the degradation)"
fi

# --- ADR-020 diff scoping ---------------------------------------------------
echo
echo "== --scope-ids: findings on untouched entries must not block =="
_scope_in="$(mktemp)"
if [ "${_HAVE_AJV}" -eq 0 ]; then
	# Without Ajv a zero-blocking run correctly exits 3 (DEGRADED), which would
	# make the exit codes below untestable for the reason they are meant to
	# test. State the skip; do not weaken the assertions to fit.
	echo "SKIP — ajv unavailable: a scoped-clean run exits 3 (degraded), so the exit-code contract cannot be isolated here."
	rm -f "${_scope_in}"
	if [ "${_fails}" -eq 0 ]; then
		echo
		echo "gate-22 manifest-validation: all RUNNABLE assertions PASSED (schema + scope paths SKIPPED — no ajv)"
		exit 0
	fi
	echo
	echo "${_fails} gate-22 assertion(s) FAILED"
	exit 1
fi

# The malformed fixture's findings all hang off top-level blocks
# (/observability, /deepLinks), so a scope naming a DIFFERENT block must
# suppress every one of them.
printf 'key:pages\n' > "${_scope_in}"
_assert 0 malformed-apphost.manifest.json \
	"out-of-scope findings → exit 0 (reported, not blocking)" --scope-ids "${_scope_in}"
_assert_log 'PRE-EXISTING' "out-of-scope findings are still PRINTED, marked PRE-EXISTING"

# Reverse direction on the SAME fixture: this is what makes the pass above
# evidence rather than an absent check.
printf 'key:observability\nkey:deepLinks\n' > "${_scope_in}"
_assert 1 malformed-apphost.manifest.json \
	"same fixture, entries IN scope → exit 1 (the scoping can fail)" --scope-ids "${_scope_in}"
_assert_log '^at /observability/health/checks/0/type: must' "an in-scope finding is printed WITHOUT the PRE-EXISTING marker"

printf 'ALL\n' > "${_scope_in}"
_assert 1 malformed-apphost.manifest.json \
	"ALL token → nothing is scoped out (fail toward enforcement)" --scope-ids "${_scope_in}"

rm -f "${_scope_in}"

if [ "${_fails}" -eq 0 ]; then
	echo
	echo "ALL gate-22 manifest-validation assertions PASSED"
	exit 0
fi
echo
echo "${_fails} gate-22 assertion(s) FAILED"
exit 1
