#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# test_gate_3_external_contract_and_tabs.sh: two gate-3 caller-identity defects
# measured on learniq (development @ 9b70119, 2026-10-04).
#
# 1. A CONTRACT FROM ANOTHER APP COULD NEVER BE RESOLVED.
#    Six learniq guards implement OpenRegister's LifecycleGuardInterface::check(
#    array $object, string $action, string $userId), mark $userId unused on the
#    @param line, and were still reported, because the exemption only looked
#    for the supertype under lib/. The contract is mirrored as a PHP stub under
#    tests/Stubs (the fleet convention psalm, phpstan and phpunit already need),
#    so the helper now reads stub directories too. Fail-closed is unchanged:
#    a supertype found nowhere, a stub without the parameter, or a missing
#    unused marker all still report.
#
# 2. A TAB-INDENTED BODY RAN TO EOF.
#    The body stopped at `^    \}`, which a tab-indented file never contains, so
#    a stub that ignored $userId was read as using it whenever a LATER method in
#    the same file mentioned $userId. The body now ends at the brace that
#    matches the signature's own indent.
#
# Run: bash scripts/lib/test_gate_3_external_contract_and_tabs.sh
set -uo pipefail

LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
RUNNER="${LIB_DIR}/../run-hydra-gates.sh"

_fail_count=0
_pass_count=0
_ok()  { echo "  PASS: $1"; _pass_count=$((_pass_count + 1)); }
_bad() { echo "  FAIL: $1"; _fail_count=$((_fail_count + 1)); }

[ -f "${RUNNER}" ] || { echo "FAIL: runner not found at ${RUNNER}"; exit 1; }

# Build a repo from `path=content` pairs, run the runner, echo gate-3's
# caller-identity findings. The runner's exit code aggregates every gate and
# says nothing about gate-3, so the verdict is the log; gate-3's own verdict
# line must be present, or an unrun gate would read as a clean one.
_run_gate3_multi() {
	local root logdir out pair rel content
	root="$(mktemp -d "${TMPDIR:-/tmp}/g3ext.XXXXXX")" || return 1
	for pair in "$@"; do
		rel="${pair%%=*}"
		content="${pair#*=}"
		mkdir -p "${root}/$(dirname "${rel}")"
		printf '%s' "${content}" > "${root}/${rel}"
	done
	(
		cd "${root}" || exit 1
		git init -q .
		git config user.email t@example.com
		git config user.name t
		git config commit.gpgsign false
		git add -A && git commit -qm base
	) >/dev/null 2>&1
	logdir="$(mktemp -d "${TMPDIR:-/tmp}/g3extlogs.XXXXXX")"
	out="$(cd "${root}" && HYDRA_GATE_LOG_DIR="${logdir}" bash "${RUNNER}" . 2>&1)"
	if ! printf '%s\n' "${out}" | grep -qE '^\[gate-3\] stub-scan: (PASS|FAIL)'; then
		echo "NO-GATE-3-VERDICT"
	fi
	grep 'caller-identity-ignored' "${logdir}/hydra-gate-stub-scan.log" 2>/dev/null
	rm -rf "${root}" "${logdir}"
	return 0
}

# _expect <arm label> <expected count> <method or ''> -- pairs...
_expect() {
	local label="$1" want="$2" method="$3" out n
	shift 3
	out="$(_run_gate3_multi "$@")"
	if printf '%s' "${out}" | grep -q NO-GATE-3-VERDICT; then
		_bad "${label}: gate-3 printed no PASS/FAIL verdict"
		return
	fi
	n="$(printf '%s' "${out}" | grep -c . || true)"
	if [ "${n}" -eq "${want}" ] && { [ -z "${method}" ] || printf '%s' "${out}" | grep -q "method=${method} "; }; then
		_ok "${label}"
	else
		_bad "${label}: expected ${want} finding(s)${method:+ for ${method}}, got ${n}:"
		printf '%s\n' "${out}" | sed 's/^/         /'
	fi
}

# shellcheck disable=SC2016  # PHP source: single quotes are REQUIRED
_STUB_IFACE='<?php

namespace OCA\OpenRegister\Lifecycle;

interface LifecycleGuardInterface {
	/**
	 * @param array  $object The object.
	 * @param string $action The transition.
	 * @param string $userId The caller.
	 */
	public function check(array $object, string $action, string $userId): GuardResult;
}//end interface
'

_STUB_IFACE_NOPARAM='<?php

namespace OCA\OpenRegister\Lifecycle;

interface LifecycleGuardInterface {
	/**
	 * @param array  $object The object.
	 * @param string $action The transition.
	 */
	public function check(array $object, string $action): GuardResult;
}//end interface
'

_GUARD='<?php

namespace OCA\Learniq\Service;

use OCA\OpenRegister\Lifecycle\GuardResult;
use OCA\OpenRegister\Lifecycle\LifecycleGuardInterface;

class WalletClaimSyncService implements LifecycleGuardInterface {
	/**
	 * Guard entry-point.
	 *
	 * @param array<string,mixed> $object The object as it would be saved.
	 * @param string $action The transition.
	 * @param string $userId The caller (unused: this guard does not depend on who asks).
	 *
	 * @return GuardResult
	 */
	public function check(array $object, string $action, string $userId): GuardResult {
		if ((string)($object['\''learnerRef'\''] ?? '\'''\'') === '\'''\'') {
			return GuardResult::deny('\''missing'\'');
		}

		return GuardResult::allow();
	}//end check()
}//end class
'

_GUARD_UNMARKED='<?php

namespace OCA\Learniq\Service;

use OCA\OpenRegister\Lifecycle\GuardResult;
use OCA\OpenRegister\Lifecycle\LifecycleGuardInterface;

class WalletClaimSyncService implements LifecycleGuardInterface {
	/**
	 * Guard entry-point.
	 *
	 * @param array<string,mixed> $object The object as it would be saved.
	 * @param string $action The transition.
	 * @param string $userId The caller.
	 *
	 * @return GuardResult
	 */
	public function check(array $object, string $action, string $userId): GuardResult {
		if ((string)($object['\''learnerRef'\''] ?? '\'''\'') === '\'''\'') {
			return GuardResult::deny('\''missing'\'');
		}

		return GuardResult::allow();
	}//end check()
}//end class
'

_FREE_THEN_USE='<?php

namespace OCA\Learniq\Service;

class PermissionService {
	/**
	 * Authorize a transition.
	 *
	 * @param array  $object The object.
	 * @param string $userId The caller.
	 *
	 * @return bool
	 */
	public function authorize(array $object, string $userId): bool {
		$this->logger->info('\''authorizing'\'');
		$this->bus->dispatch($object);
		return true;
	}//end authorize()

	/**
	 * A later method that genuinely uses its own $userId.
	 *
	 * @param string $userId The caller.
	 *
	 * @return string
	 */
	public function describe(string $userId): string {
		$name = '\''user '\'' . $userId;
		$this->logger->info($name);
		return $name;
	}//end describe()
}//end class
'

_FREE_MARKED='<?php

namespace OCA\Learniq\Service;

class PermissionService {
	/**
	 * Authorize a transition.
	 *
	 * @param array  $object The object.
	 * @param string $userId The caller (unused).
	 *
	 * @return bool
	 */
	public function authorize(array $object, string $userId): bool {
		$this->logger->info('\''authorizing'\'');
		$this->bus->dispatch($object);
		return true;
	}//end authorize()
}//end class
'

echo "== gate-3: an external contract mirrored by a stub, and tab-indented bodies =="
echo

_expect "arm 1: learniq shape (external interface, tests/Stubs mirror, marked unused, tabs) is not reported" 0 "" \
	"tests/Stubs/Lifecycle/LifecycleGuardInterface.php=${_STUB_IFACE}" \
	"lib/Service/WalletClaimSyncService.php=${_GUARD}"

_expect "arm 2: a root stubs/ mirror resolves the contract too" 0 "" \
	"stubs/LifecycleGuardInterface.php=${_STUB_IFACE}" \
	"lib/Service/WalletClaimSyncService.php=${_GUARD}"

_expect "arm 3 CONTROL: no stub anywhere, so the supertype is unresolvable and the finding stands" 1 check \
	"lib/Service/WalletClaimSyncService.php=${_GUARD}"

_expect "arm 4 CONTROL: stub present but the @param is not marked unused" 1 check \
	"tests/Stubs/Lifecycle/LifecycleGuardInterface.php=${_STUB_IFACE}" \
	"lib/Service/WalletClaimSyncService.php=${_GUARD_UNMARKED}"

_expect "arm 5 CONTROL: the stub declares check() WITHOUT \$userId, so the class chose it" 1 check \
	"tests/Stubs/Lifecycle/LifecycleGuardInterface.php=${_STUB_IFACE_NOPARAM}" \
	"lib/Service/WalletClaimSyncService.php=${_GUARD}"

_expect "arm 6: a tab-indented stub is reported even when a LATER method uses \$userId" 1 authorize \
	"lib/Service/PermissionService.php=${_FREE_THEN_USE}"

_expect "arm 7 CONTROL: tab-indented, marked unused, but implements nothing: still reported" 1 authorize \
	"tests/Stubs/Lifecycle/LifecycleGuardInterface.php=${_STUB_IFACE}" \
	"lib/Service/PermissionService.php=${_FREE_MARKED}"

echo
echo "== summary: ${_pass_count} passed, ${_fail_count} failed =="
[ "${_fail_count}" -eq 0 ] || exit 1
exit 0
