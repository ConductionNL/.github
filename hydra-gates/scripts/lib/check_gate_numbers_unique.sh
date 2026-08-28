#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# A GATE NUMBER IS AN IDENTITY. Two gates cannot share one.
#
# WHY THIS EXISTS
# ---------------
# `run-hydra-gates.sh` reports every verdict as `[gate-N] name: PASS|FAIL`, and
# the COVERAGE line counts one slot per number. When two gates share a number:
#
#   * one gate's verdict overwrites the other's in the report;
#   * the COVERAGE tally counts one slot for two gates, so a gate that never
#     ran is indistinguishable from one that passed;
#   * an acceptance suite grepping `\[gate-N\]` reads the OTHER gate's line and
#     fails with a message about a gate it does not test.
#
# All three happened. gate-99 was claimed by `manifest-l10n-coverage` and
# `demo-data-coverage` at once, and `test_gate99_demo_data_scope.sh` failed
# three arms while quoting the l10n gate's "NOT APPLICABLE" sentence.
#
# 🔴 AND THE FIRST FIX MADE IT WORSE. Two sessions found the duplicate
# independently and each moved a DIFFERENT gate to the SAME free number —
# #612 moved demo-data-coverage to 101, #615 moved manifest-l10n-coverage to
# 101. Both diffs were correct in isolation; together they relocated the
# collision rather than resolving it, and nothing noticed until the same
# acceptance suite failed again with the number changed.
#
# There is a gate-95 for ADR number collisions and nothing for GATE numbers.
# This is that check.
#
# WHAT IT CHECKS
# --------------
# The authority is the CALL SITES, not the `# GATE N — name` comments. The
# comments were already distinct (99 and 101) while both gates called
# `_pass 101` — so a checker reading the headers would have passed the exact
# state that was broken.
#
# Usage: check_gate_numbers_unique.sh [path/to/run-hydra-gates.sh]
# Exit:  0 every number maps to exactly one gate name
#        1 at least one number is claimed by more than one name
#        2 the runner could not be read, or declares no gates at all
set -uo pipefail

RUNNER="${1:-$(dirname "${BASH_SOURCE[0]}")/../run-hydra-gates.sh}"

if [ ! -f "$RUNNER" ]; then
	echo "::error::gate-number uniqueness: cannot read ${RUNNER}."
	exit 2
fi

# `_pass 101 "demo-data-coverage"` -> `101 demo-data-coverage`
MAP="$(grep -oE '_(pass|fail|skip|skip_empty_scope) [0-9]+ "[a-z0-9-]+"' "$RUNNER" \
	| sed -E 's/^_[a-z_]+ ([0-9]+) "([a-z0-9-]+)"$/\1 \2/' \
	| sort -u)"

if [ -z "$MAP" ]; then
	# NOT a pass. A checker that finds nothing to check has measured nothing,
	# and this file exists because a silent zero already cost two fix attempts.
	echo "::error::gate-number uniqueness: no gate call sites found in ${RUNNER}. Nothing was checked, which is not the same as everything being unique."
	exit 2
fi

DUPES="$(echo "$MAP" | awk '{print $1}' | uniq -d)"

if [ -n "$DUPES" ]; then
	echo "::error::gate numbers claimed by more than one gate:"
	for n in $DUPES; do
		names="$(echo "$MAP" | awk -v n="$n" '$1 == n {printf "%s ", $2}')"
		echo "::error::  gate-${n} is claimed by: ${names}"
	done
	echo "::error::A gate number is an identity: the report, the COVERAGE tally and every"
	echo "::error::acceptance suite key on it. Give one of them the next free number —"
	echo "::error::and check the call sites, not the '# GATE N' comments, because those"
	echo "::error::were already distinct while both gates called _pass on the same number."
	exit 1
fi

echo "gate-number uniqueness: $(echo "$MAP" | wc -l) gate(s), every number claimed once."
exit 0
