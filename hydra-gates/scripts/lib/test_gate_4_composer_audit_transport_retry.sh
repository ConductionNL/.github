#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# test_gate_4_composer_audit_transport_retry.sh — gate-4 retries a transport
# failure of the advisory feed, and ONLY a transport failure.
#
# WHAT THIS GUARDS
# ----------------
# `composer audit` talks to https://packagist.org/api/security-advisories/ on
# every run. When that endpoint does not answer, composer exits 100
# (Installer::ERROR_TRANSPORT_EXCEPTION) having audited nothing. gate-4 ran the
# command exactly once, so one hiccup of one endpoint was a red PR, fleet-wide:
#
#   2026-09-03 11:56 UTC  keepiq#601 and keepiq#602 failed gate-4 in the SAME
#                         MINUTE with "exit 100, and the output names no
#                         advisory". Every hydra run before and after passed it
#                         on a byte-identical composer.lock.
#
# The fix is a three-attempt loop in the gate. A retry loop is only a fix if it
# cannot ALSO hide findings, so this suite pins down both halves:
#
#   ARM 1  CONTROL. A named advisory (exit 1 plus a `Package:` block) FAILs
#          the gate on the FIRST attempt — no retry. A loop that retried real
#          findings would only delay the same verdict; one that swallowed them
#          would be worse than no gate. This arm runs first because every other
#          arm is meaningless if the gate has stopped seeing advisories.
#   ARM 2  A feed that answers on the third attempt yields PASS, and the stub
#          was called exactly three times — the retry actually happened, and
#          the run said so on stdout.
#   ARM 3  A feed that never answers is still FAIL — not PASS, not a skip.
#          Three transport failures leave the tree exactly as unverified as one
#          did. The wording names the attempt count, and the log carries all
#          three attempts for the reader.
#   ARM 4  A clean first attempt is called ONCE. The loop costs nothing on the
#          common path.
#   ARM 5  A non-transport, non-advisory error (composer exits 2 on an unknown
#          option) is called ONCE and FAILs as "COULD NOT COMPLETE (exit 2
#          after 1 of 3 attempt(s))". A code or configuration error is not an
#          outage; retrying it would only repeat the same answer three times
#          and hide, in the attempt count, that nothing was ever reachable to
#          fix. This pins the ORDER of the break conditions: a refactor that
#          dropped the `-ne 100` half of the transport test would retry every
#          non-zero exit, and ARMs 1–4 would stay green.
#
# The composer binary is a stub on PATH whose behaviour is chosen per arm; it
# writes its invocation count to a file so each arm can assert how many times
# the runner actually called it. HYDRA_GATE_COMPOSER_RETRY_DELAY=0 removes the
# 10s/20s backoff so the suite does not sleep half a minute per arm.

set -u

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_scripts="$(cd "${_here}/.." && pwd)"
# Overridable so the fix can be MUTATION-CHECKED against the pre-fix runner:
#
#   HYDRA_GATES_RUNNER_UNDER_TEST=/path/to/pre-fix/run-hydra-gates.sh \
#       bash scripts/lib/test_gate_4_composer_audit_transport_retry.sh
#
# Against the pre-fix runner ARM 2 must go RED (a single attempt cannot PASS a
# feed that only answers on the third call) and ARM 3's attempt-count and
# per-attempt-log assertions must go RED. ARMs 1 and 4 stay green, and so do
# ARM 5's call-count assertions — those are the properties the fix must NOT
# change. Only ARM 5's wording assertion goes RED, because the pre-fix
# FAIL text did not name an attempt count.
_runner="${HYDRA_GATES_RUNNER_UNDER_TEST:-${_scripts}/run-hydra-gates.sh}"

_failures=0
_ok()  { echo "  ok   — $1"; }
_bad() { echo "  FAIL — $1"; _failures=$((_failures + 1)); }

echo "test_gate_4_composer_audit_transport_retry.sh"

_tmp="$(mktemp -d "${TMPDIR:-/tmp}/hydra-gate4-retry.XXXXXX")"
trap 'rm -rf "${_tmp}"' EXIT

# ---------------------------------------------------------------------------
# Fixture: the smallest tree in which gate-4 is APPLICABLE. composer.json AND
# composer.lock, so the gate takes its `--locked` path. Every other gate sees
# an otherwise empty app and declines on its own terms; only the gate-4 line
# and the gate-4 log are read here.
# ---------------------------------------------------------------------------
_app="${_tmp}/app"
mkdir -p "${_app}"
(
    cd "${_app}" || exit 1
    git init -q .
    printf '{\n  "name": "fixture/gate4",\n  "license": "EUPL-1.2",\n  "require": {}\n}\n' > composer.json
    printf '{\n  "_readme": ["fixture"],\n  "content-hash": "0",\n  "packages": [],\n  "packages-dev": []\n}\n' > composer.lock
)

# ---------------------------------------------------------------------------
# The composer stub. GATE4_STUB_MODE selects the behaviour; GATE4_STUB_COUNTER
# is a file that receives the running invocation count. The output of each
# mode is lifted from real composer 2.10 output, because the gate decides by
# reading that output: the transport case must carry the "could not be
# downloaded" line and exit 100, the advisory case must carry a `Package:`
# block and exit 1, and the config_error case must carry NEITHER shape and
# exit with a code other than 100.
# ---------------------------------------------------------------------------
_fakebin="${_tmp}/bin"
mkdir -p "${_fakebin}"
_counter="${_tmp}/calls"
cat > "${_fakebin}/composer" <<'STUB'
#!/usr/bin/env bash
n=$(cat "${GATE4_STUB_COUNTER}" 2>/dev/null || echo 0)
n=$((n + 1))
echo "${n}" > "${GATE4_STUB_COUNTER}"
case "${GATE4_STUB_MODE}" in
    clean)
        echo "No security vulnerability advisories found."
        exit 0 ;;
    flaky)
        # Two transport failures, then the feed answers.
        if [ "${n}" -lt 3 ]; then
            echo 'In CurlDownloader.php line 400:'
            echo 'The "https://packagist.org/api/security-advisories/" file could not be downloaded (HTTP/2 502 )'
            exit 100
        fi
        echo "No security vulnerability advisories found."
        exit 0 ;;
    outage)
        echo 'In CurlDownloader.php line 400:'
        echo 'The "https://packagist.org/api/security-advisories/" file could not be downloaded (HTTP/2 502 )'
        exit 100 ;;
    advisory)
        echo "Found 1 security vulnerability advisory affecting 1 package:"
        echo "Package: acme/planted"
        echo "CVE: CVE-2026-0001"
        echo "Title: planted true positive"
        echo "URL: https://example.invalid/advisory"
        echo "Affected versions: <9.9.9"
        echo "Reported at: 2026-01-01T00:00:00+00:00"
        exit 1 ;;
    config_error)
        # Neither an advisory nor a transport error: composer's own exit 2 for
        # a bad invocation. Nothing here matches the gate's transport regex.
        echo 'The "--foo" option does not exist.'
        echo 'audit [--format FORMAT] [--locked] [--abandoned ABANDONED]'
        exit 2 ;;
    *)
        echo "stub: unknown GATE4_STUB_MODE '${GATE4_STUB_MODE:-}'" >&2
        exit 99 ;;
esac
STUB
chmod +x "${_fakebin}/composer"

# _run <mode> — one full runner pass with the stub in <mode>. Output lands in
# ${_tmp}/out-<mode>, the gate logs in ${_tmp}/logs-<mode>.
_run() {
    : > "${_counter}"
    mkdir -p "${_tmp}/logs-$1"
    (
        cd "${_app}" || exit 1
        GATE4_STUB_MODE="$1" GATE4_STUB_COUNTER="${_counter}" \
        HYDRA_GATE_COMPOSER_RETRY_DELAY=0 \
        PATH="${_fakebin}:${PATH}" HYDRA_GATE_LOG_DIR="${_tmp}/logs-$1" \
            bash "${_runner}" . > "${_tmp}/out-$1" 2>&1
    )
}
_calls()   { cat "${_counter}" 2>/dev/null || echo 0; }
_verdict() { grep -E '^\[gate-4\] composer-audit: ' "${_tmp}/out-$1" | tail -1; }
_gatelog() { echo "${_tmp}/logs-$1/hydra-gate-composer-audit.log"; }

# ---------------------------------------------------------------------------
# ARM 1 — CONTROL: a real advisory is a verdict on the first attempt.
# ---------------------------------------------------------------------------
_run advisory
_v="$(_verdict advisory)"
if [ "$(_calls)" -ge 1 ]; then
    _ok "control: the composer stub was actually called ($(_calls)x) — the runner found composer.json, composer.lock and the stub on PATH"
else
    _bad "control FAILED: the stub was never called — gate-4 did not run, so every assertion below proves nothing (verdict: '${_v:-none emitted}')"
fi
if printf '%s' "${_v}" | grep -q 'FAIL — CVEs or advisories'; then
    _ok "a named advisory FAILs gate-4 as 'CVEs or advisories'"
else
    _bad "a named advisory produced '${_v:-none emitted}' — expected 'FAIL — CVEs or advisories'"
fi
if [ "$(_calls)" -eq 1 ]; then
    _ok "a named advisory is NOT retried (composer called once)"
else
    _bad "a named advisory was retried (composer called $(_calls)x) — the loop is delaying a real verdict"
fi

# ---------------------------------------------------------------------------
# ARM 2 — a feed that comes back on the third attempt: PASS, three calls.
# ---------------------------------------------------------------------------
_run flaky
_v="$(_verdict flaky)"
if printf '%s' "${_v}" | grep -q ': PASS$'; then
    _ok "two transport failures followed by a clean answer yield PASS"
else
    _bad "two transport failures followed by a clean answer yield '${_v:-none emitted}' — expected PASS (this is the keepiq#601 case)"
fi
if [ "$(_calls)" -eq 3 ]; then
    _ok "the retry actually happened (composer called 3x)"
else
    _bad "composer was called $(_calls)x — expected 3 (attempt, retry, retry)"
fi
if grep -qE '^\[hydra-gates\] gate-4 composer-audit: attempt 1/3 could not reach the advisory feed \(exit 100\); retrying in' "${_tmp}/out-flaky"; then
    _ok "each retry is announced on stdout with the attempt number and the exit code"
else
    _bad "no retry notice on stdout — a reader of the run cannot see that the first attempt failed"
fi
if [ "$(grep -c '^### composer audit — attempt' "$(_gatelog flaky)" 2>/dev/null)" -eq 3 ]; then
    _ok "the gate log carries all three attempts under their own headers"
else
    _bad "the gate log does not carry three attempt headers — earlier attempts' output was discarded"
fi

# ---------------------------------------------------------------------------
# ARM 3 — a feed that never comes back: still FAIL, never PASS or a skip.
# ---------------------------------------------------------------------------
_run outage
_v="$(_verdict outage)"
if printf '%s' "${_v}" | grep -q 'FAIL — audit COULD NOT COMPLETE'; then
    _ok "a persistent transport failure is still FAIL (audit COULD NOT COMPLETE)"
elif printf '%s' "${_v}" | grep -qE ': (PASS|NOT APPLICABLE|SKIPPED)'; then
    _bad "a persistent transport failure produced '${_v}' — an UNVERIFIED tree has been rendered as green or as out of scope"
else
    _bad "a persistent transport failure produced '${_v:-none emitted}' — expected 'FAIL — audit COULD NOT COMPLETE'"
fi
if printf '%s' "${_v}" | grep -q 'exit 100 after 3 of 3 attempt(s)'; then
    _ok "the FAIL names the attempt count, so the reader can tell an outage from a one-off crash"
else
    _bad "the FAIL does not say 'exit 100 after 3 of 3 attempt(s)' — got '${_v}'"
fi
if [ "$(_calls)" -eq 3 ]; then
    _ok "the loop stops after three attempts (composer called 3x, not forever)"
else
    _bad "composer was called $(_calls)x on a persistent outage — expected exactly 3"
fi
if printf '%s' "${_v}" | grep -q 'NOT known-vulnerable'; then
    _ok "the FAIL still says the tree is UNVERIFIED, not vulnerable"
else
    _bad "the FAIL no longer distinguishes 'unverified' from 'vulnerable'"
fi

# ---------------------------------------------------------------------------
# ARM 4 — the common path costs nothing: one call, PASS.
# ---------------------------------------------------------------------------
_run clean
_v="$(_verdict clean)"
if printf '%s' "${_v}" | grep -q ': PASS$'; then
    _ok "a clean first attempt is PASS"
else
    _bad "a clean first attempt produced '${_v:-none emitted}' — expected PASS"
fi
if [ "$(_calls)" -eq 1 ]; then
    _ok "a clean first attempt is not retried (composer called once)"
else
    _bad "a clean first attempt called composer $(_calls)x — the loop is running on the success path"
fi

# ---------------------------------------------------------------------------
# ARM 5 — a non-transport, non-advisory error is not retried, ever.
#         composer exits 2 on an unknown option: a code/config bug, not an
#         infra hiccup. The runner must break on the first attempt and the
#         FAIL must say so, "1 of 3", so a reader can tell it from an outage.
# ---------------------------------------------------------------------------
_run config_error
_v="$(_verdict config_error)"
if printf '%s' "${_v}" | grep -q 'FAIL — audit COULD NOT COMPLETE'; then
    _ok "a non-transport error is FAIL (audit COULD NOT COMPLETE), not a CVE finding and not a PASS"
else
    _bad "a non-transport error produced '${_v:-none emitted}' — expected 'FAIL — audit COULD NOT COMPLETE'"
fi
if [ "$(_calls)" -eq 1 ]; then
    _ok "a non-transport error is NOT retried (composer called once)"
else
    _bad "a non-transport error was retried (composer called $(_calls)x) — the runner is treating a code error as an outage"
fi
if printf '%s' "${_v}" | grep -q 'exit 2 after 1 of 3 attempt(s)'; then
    _ok "the FAIL says 'exit 2 after 1 of 3 attempt(s)' — the reader can tell this from a real outage"
else
    _bad "the FAIL does not say 'exit 2 after 1 of 3 attempt(s)' — got '${_v}'"
fi

echo
if [ "${_failures}" -eq 0 ]; then
    echo "test_gate_4_composer_audit_transport_retry.sh: all assertions green"
    exit 0
fi
echo "test_gate_4_composer_audit_transport_retry.sh: ${_failures} assertion(s) RED"
exit 1
