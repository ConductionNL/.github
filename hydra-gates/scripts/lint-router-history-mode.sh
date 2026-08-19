#!/usr/bin/env bash
#
# lint-router-history-mode.sh — path-based Vue Router history is the fleet
# convention; hash-based (`#/…`) is the thing being migrated away from.
#
# BACKGROUND. The fleet was split roughly 50/50 (verified 2026-08-15, 19 apps):
# doriath, larpingapp, opencatalogi, openconnector, openregister, pipelinq,
# softwarecatalog, zaakafhandelapp on `createWebHashHistory`; decidesk,
# docudesk, hermiq, hrmq, openbuild, portaliq, procest, scholiq, shillinq
# already on `createWebHistory` — with no documented rule for which to pick.
# Hash routing needs zero server-side work (everything after `#` never
# reaches the server) at the cost of ugly URLs; path routing needs a
# server-side SPA catch-all route or a direct hit on a deep client route
# 404s. See docs/claude/frontend-standards.md#routing-history-mode for the
# full writeup and the two sanctioned ways to get that catch-all.
#
# Mode: WARN-only (see run-hydra-gates.sh's own convention for this — new
# gates land observing before they land blocking, so a fleet-wide rollout
# is not one all-or-nothing breaking change). Flips to BLOCK by editing
# HISTORY_GATE_MODE below once every app has a working catch-all — track
# progress with `bash lint-router-history-mode.sh --fleet` from
# apps-extra/.
#
# Two independent checks, because they can each be wrong in a way the other
# does not catch:
#   1. Router mode: does src/main.js call createWebHistory (compliant) or
#      createWebHashHistory (flagged, not yet converted)?
#   2. Catch-all presence: for an app ALREADY on createWebHistory, does
#      appinfo/routes.php actually declare a `/{path}`-shaped fallback (or
#      call `AppHost\Routes::standard()`, which includes one)? An app on
#      path-history with NO catch-all is not "ahead of the convention" — it
#      is BROKEN on every deep-link refresh, and that is worse than staying
#      on hash-history. This check runs regardless of gate MODE, because a
#      missing catch-all on a path-history app is a real, present bug, not
#      a migration-in-progress state.
#
# Run from a single app repo root:
#   bash hydra/scripts/lint-router-history-mode.sh
#
# Run the fleet summary (from apps-extra/, sweeps every app with a main.js):
#   bash .github/hydra-gates/scripts/lint-router-history-mode.sh --fleet
#
# License: EUPL-1.2.
# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl>

set -euo pipefail

# WARN or BLOCK. See the docblock above before flipping this.
HISTORY_GATE_MODE="${HYDRA_ROUTER_HISTORY_GATE_MODE:-WARN}"

check_one_app() {
	local app_dir="$1"
	local app_name
	app_name="$(basename "$app_dir")"
	local main_js="$app_dir/src/main.js"
	local routes_php="$app_dir/appinfo/routes.php"

	[ -f "$main_js" ] || return 0

	local mode="unknown"
	if grep -q "createWebHistory(" "$main_js" 2>/dev/null \
		&& ! grep -q "createWebHashHistory" "$main_js" 2>/dev/null; then
		mode="path"
	elif grep -q "createWebHashHistory(" "$main_js" 2>/dev/null; then
		mode="hash"
	else
		# Neither call found — most likely no vue-router at all in this app.
		return 0
	fi

	if [ "$mode" = "hash" ]; then
		echo "  [HASH]  $app_name — src/main.js uses createWebHashHistory"
		return 1
	fi

	# mode = path: the catch-all is not optional here, verify it exists.
	# Deliberately a loose substring check, not a PHP-array-syntax regex — the
	# first version of this gate matched `requirements' => ['path'` literally
	# and false-flagged openconnector's own working catch-all (single-quote
	# spacing differed by one character). A route URL containing `{path}` at
	# all is the actual signal; how the surrounding array is formatted is not
	# this gate's business to parse.
	if [ -f "$routes_php" ] \
		&& { grep -qF '{path}' "$routes_php" 2>/dev/null \
			|| grep -qF 'AppHost\Routes::standard' "$routes_php" 2>/dev/null \
			|| grep -qF 'dashboard#catchAll' "$routes_php" 2>/dev/null; }; then
		echo "  [OK]    $app_name — path history, catch-all present"
		return 0
	fi

	# This is the one unconditional failure: broken regardless of gate mode.
	echo "  [BROKEN] $app_name — createWebHistory with NO catch-all route found in appinfo/routes.php (deep-link refresh will 404)"
	return 2
}

if [ "${1:-}" = "--fleet" ]; then
	echo "=== Router history mode — fleet sweep ==="
	total=0
	hash_count=0
	broken_count=0
	for dir in */; do
		dir="${dir%/}"
		[ -f "$dir/src/main.js" ] || continue
		total=$((total + 1))
		set +e
		check_one_app "$dir"
		rc=$?
		set -e
		[ "$rc" -eq 1 ] && hash_count=$((hash_count + 1))
		[ "$rc" -eq 2 ] && broken_count=$((broken_count + 1))
	done
	echo
	echo "apps checked: $total   still hash: $hash_count   BROKEN (path, no catch-all): $broken_count"
	echo "mode: $HISTORY_GATE_MODE"
	if [ "$broken_count" -gt 0 ]; then
		echo "FAIL: $broken_count app(s) have a broken catch-all — this is not a mode question, always exits non-zero."
		exit 1
	fi
	if [ "$HISTORY_GATE_MODE" = "BLOCK" ] && [ "$hash_count" -gt 0 ]; then
		exit 1
	fi
	exit 0
fi

# Single-app mode.
set +e
check_one_app "."
rc=$?
set -e

if [ "$rc" -eq 2 ]; then
	echo "FAIL: broken catch-all (unconditional, not gated by mode)."
	exit 1
fi

if [ "$rc" -eq 1 ]; then
	if [ "$HISTORY_GATE_MODE" = "BLOCK" ]; then
		echo "FAIL: still on hash-based history (mode=BLOCK)."
		exit 1
	fi
	echo "WARN: still on hash-based history (mode=WARN, not blocking)."
fi

exit 0
