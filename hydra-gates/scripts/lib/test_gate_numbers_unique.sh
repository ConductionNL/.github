#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# Acceptance for check_gate_numbers_unique.sh, and a live assertion that the
# runner shipping in THIS commit has no duplicate gate numbers.
#
# ARM 2 is the point of the suite: it reconstructs the exact state that reached
# main — `demo-data-coverage` and `manifest-l10n-coverage` both calling
# `_pass 101` — and asserts the checker names both gates. A suite that only
# ever sees the fixed runner would pass identically if the checker did nothing.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECK="${HERE}/check_gate_numbers_unique.sh"
RUNNER="${HERE}/../run-hydra-gates.sh"

_fail_n=0
_ok()  { echo "  ok   — $1"; }
_bad() { echo "  FAIL — $1"; _fail_n=$((_fail_n + 1)); }

TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

echo "-- ARM 1: the runner in this commit has no duplicate gate numbers --"
out="$(bash "${CHECK}" "${RUNNER}" 2>&1)"; rc=$?
if [ "$rc" -eq 0 ]; then
	_ok "every gate number is claimed exactly once (${out##*: })"
else
	_bad "the shipped runner has a duplicate: ${out}"
fi

echo "-- ARM 2: 🔴 the state that actually reached main is caught --"
# Two sessions fixed one collision by moving DIFFERENT gates to the SAME free
# number. Both diffs were correct alone; together they relocated it.
sed 's/_pass 102 "demo-data-coverage"/_pass 101 "demo-data-coverage"/' "${RUNNER}" > "${TMP}/dupe.sh"
out="$(bash "${CHECK}" "${TMP}/dupe.sh" 2>&1)"; rc=$?
if [ "$rc" -eq 1 ] && printf '%s' "$out" | grep -q 'gate-101 is claimed by'; then
	if printf '%s' "$out" | grep -q 'demo-data-coverage' && printf '%s' "$out" | grep -q 'manifest-l10n-coverage'; then
		_ok "a duplicate is reported, naming BOTH gates"
	else
		_bad "reported a duplicate without naming both gates: ${out}"
	fi
else
	_bad "expected exit 1 naming gate-101; got exit ${rc}: ${out}"
fi

echo "-- ARM 3: the COMMENTS are not the authority --"
# The `# GATE N — name` headers were already distinct (99 and 101) while both
# gates called `_pass 101`. A checker reading headers would pass the broken
# state, so this arm plants exactly that: correct headers, colliding calls.
sed 's/_pass 102 "demo-data-coverage"/_pass 101 "demo-data-coverage"/' "${RUNNER}" > "${TMP}/headers-ok.sh"
out="$(bash "${CHECK}" "${TMP}/headers-ok.sh" 2>&1)"; rc=$?
if [ "$rc" -eq 1 ]; then
	_ok "distinct headers do not excuse colliding call sites"
else
	_bad "a runner with distinct headers and colliding calls was accepted (exit ${rc})"
fi

echo "-- ARM 4: a runner with no gates is NOT a pass --"
printf '#!/usr/bin/env bash\n' > "${TMP}/empty.sh"
out="$(bash "${CHECK}" "${TMP}/empty.sh" 2>&1)"; rc=$?
if [ "$rc" -eq 2 ]; then
	_ok "nothing to check exits 2, not 0"
else
	_bad "an empty runner returned ${rc}; a silent zero is how this class hides"
fi

echo "-- ARM 5: an unreadable runner is a configuration error --"
out="$(bash "${CHECK}" "${TMP}/does-not-exist.sh" 2>&1)"; rc=$?
if [ "$rc" -eq 2 ]; then
	_ok "a missing runner exits 2"
else
	_bad "a missing runner returned ${rc}"
fi

echo
if [ "${_fail_n}" -eq 0 ]; then
	echo "test_gate_numbers_unique.sh: ALL PASS"
	exit 0
fi
echo "test_gate_numbers_unique.sh: ${_fail_n} FAILURE(S)"
exit 1
