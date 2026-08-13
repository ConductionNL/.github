#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# test_gate_3_contract_param.sh — gate-3's `caller-identity-ignored` rule must
# not judge a parameter the class did not choose (.github#339).
#
# WHAT WENT WRONG
# ---------------
# The rule reports any public method under lib/Service / lib/Controller that
# declares a caller-identity parameter and never references it in its body.
# That is decidesk#45's shape — a builder-generated authorize*() stub that
# accepts the caller and forgets to check it.
#
# It is also the shape of a correct strategy implementation. Measured on procest
# (development @ 792fe1f4b), gate-3's three findings were all of the second kind:
#
#   lib/Service/Transitions/ChecklistGuard.php:64        method=evaluate
#   lib/Service/Transitions/RequiredDocumentGuard.php:49 method=evaluate
#   lib/Service/Transitions/RequiredFieldGuard.php:47    method=evaluate
#
# All three implement GuardEvaluatorInterface::evaluate(array, array, string
# $userId). Two of the five implementors (RoleGuard, MandaatGuard) genuinely use
# it. A guard answering "is this required field filled in?" has no business
# consulting the caller, so the only edits that silenced the gate were deleting
# the parameter — breaking the interface and every call site in
# GuardRegistry::evaluateAll() — or referencing it pointlessly to push the grep
# count to 2. The finding had no closing action.
#
# THE EXEMPTION HAS TWO HALVES AND EACH ARM BELOW REMOVES ONE
# -----------------------------------------------------------
# A finding is exempt only when a resolvable supertype declares the same method
# with the same parameter AND the docblock's @param line for THAT parameter is
# explicitly marked unused. Arms 2-5 each delete exactly one of those halves and
# require the finding to come back. An exemption that cannot fail is worth less
# than the finding it removes.
#
# Run: bash scripts/lib/test_gate_3_contract_param.sh
set -uo pipefail

LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
RUNNER="${LIB_DIR}/../run-hydra-gates.sh"

_fail_count=0
_pass_count=0
_ok()  { echo "  PASS — $1"; _pass_count=$((_pass_count + 1)); }
_bad() { echo "  FAIL — $1"; _fail_count=$((_fail_count + 1)); }

[ -f "${RUNNER}" ] || { echo "FAIL — runner not found at ${RUNNER}"; exit 1; }

# Run gate-3 over a repo built from `path=content` pairs; echo the
# caller-identity findings, one per line.
_run_gate3_multi() {
	local root logdir out pair rel content
	root="$(mktemp -d "${TMPDIR:-/tmp}/g3contract.XXXXXX")" || return 1
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
	logdir="$(mktemp -d "${TMPDIR:-/tmp}/g3clogs.XXXXXX")"
	# The runner's exit status is DELIBERATELY not captured: it aggregates 60+
	# gates and says nothing about gate-3. The verdict is the log.
	out="$(cd "${root}" && HYDRA_GATE_LOG_DIR="${logdir}" bash "${RUNNER}" . 2>&1)"
	grep 'caller-identity-ignored' "${logdir}/hydra-gate-stub-scan.log" 2>/dev/null
	# Surface gate-3's own verdict on stderr — an unrun gate and a clean one
	# look identical in an empty result otherwise.
	printf '%s\n' "${out}" | grep -E '\[gate-3\]' >&2
	rm -rf "${root}" "${logdir}"
	return 0
}

# procest's GuardEvaluatorInterface, trimmed to the one method that matters.
# shellcheck disable=SC2016  # $userId is PHP source — single quotes are REQUIRED
_INTERFACE='<?php

namespace OCA\Procest\Service\Transitions;

interface GuardEvaluatorInterface
{
    /**
     * Evaluate one guard configuration against a case.
     *
     * @param array  $guardConfig Guard configuration.
     * @param array  $case        The case object.
     * @param string $userId      Current user UID.
     *
     * @return GuardResult
     */
    public function evaluate(array $guardConfig, array $case, string $userId): GuardResult;
}
'

# ChecklistGuard's shape: contract-imposed AND marked unused on the @param line.
# shellcheck disable=SC2016  # $userId is PHP source — single quotes are REQUIRED
_GUARD_MARKED='<?php

namespace OCA\Procest\Service\Transitions;

class RequiredFieldGuard implements GuardEvaluatorInterface
{
    /**
     * Evaluate the required-field guard.
     *
     * @param array  $guardConfig Guard configuration.
     * @param array  $case        Case object.
     * @param string $userId      Current user UID (unused)
     *
     * @return GuardResult
     */
    public function evaluate(array $guardConfig, array $case, string $userId): GuardResult
    {
        $field = (string)($guardConfig["field"] ?? "");
        if ($field === "") {
            return new GuardResult(false, "missing field");
        }
        return new GuardResult(($case[$field] ?? "") !== "", "field empty");
    }
}
'

# Same class, marker deleted from the @param line. Everything else identical.
# shellcheck disable=SC2016  # $userId is PHP source — single quotes are REQUIRED
_GUARD_UNMARKED='<?php

namespace OCA\Procest\Service\Transitions;

class RequiredFieldGuard implements GuardEvaluatorInterface
{
    /**
     * Evaluate the required-field guard.
     *
     * @param array  $guardConfig Guard configuration.
     * @param array  $case        Case object.
     * @param string $userId      Current user UID.
     *
     * @return GuardResult
     */
    public function evaluate(array $guardConfig, array $case, string $userId): GuardResult
    {
        $field = (string)($guardConfig["field"] ?? "");
        if ($field === "") {
            return new GuardResult(false, "missing field");
        }
        return new GuardResult(($case[$field] ?? "") !== "", "field empty");
    }
}
'

# The marker, on a class that implements nothing — decidesk#45 with a docblock.
# shellcheck disable=SC2016  # $userId is PHP source — single quotes are REQUIRED
_FREESTANDING_MARKED='<?php

namespace OCA\Procest\Service;

class PermissionService
{
    /**
     * Authorize a case transition.
     *
     * @param array  $case   Case object.
     * @param string $userId Current user UID (unused)
     *
     * @return bool
     */
    public function authorizeTransition(array $case, string $userId): bool
    {
        $this->logger->info("authorizing");
        $this->bus->dispatch(new Authorized($case));
        return true;
    }
}
'

echo "== gate-3: a contract-imposed param the author marked unused is not a stub (#339) =="
echo

# ARM 1 — the false positive is GONE. procest's shape, both halves present.
_out="$(_run_gate3_multi \
	"lib/Service/Transitions/GuardEvaluatorInterface.php=${_INTERFACE}" \
	"lib/Service/Transitions/RequiredFieldGuard.php=${_GUARD_MARKED}" 2>/dev/null)"
_n="$(printf '%s' "${_out}" | grep -c . || true)"
if [ "${_n}" -eq 0 ]; then
	_ok "arm 1: contract-imposed AND marked unused is not reported (procest's shape)"
else
	_bad "arm 1: expected 0 findings, got ${_n}:"
	printf '%s\n' "${_out}" | sed 's/^/         /'
fi

# ARM 2 — CONTROL. Same interface, same class, marker deleted. A contract does
# not by itself excuse an ignored caller: a gutted RoleGuard is contract-imposed
# too, and that IS the defect gate-3 exists for.
_out="$(_run_gate3_multi \
	"lib/Service/Transitions/GuardEvaluatorInterface.php=${_INTERFACE}" \
	"lib/Service/Transitions/RequiredFieldGuard.php=${_GUARD_UNMARKED}" 2>/dev/null)"
_n="$(printf '%s' "${_out}" | grep -c . || true)"
if [ "${_n}" -eq 1 ] && printf '%s' "${_out}" | grep -q 'method=evaluate'; then
	_ok "arm 2 CONTROL: contract WITHOUT the unused marker is STILL reported"
else
	_bad "arm 2 CONTROL: expected exactly 1 finding for evaluate, got ${_n}:"
	printf '%s\n' "${_out}" | sed 's/^/         /'
fi

# ARM 3 — CONTROL. The marker WITHOUT a contract. This is the abuse path: if a
# docblock word alone could silence the rule, a fixer agent would learn to write
# it and decidesk#45 would ship again with better documentation.
_out="$(_run_gate3_multi \
	"lib/Service/PermissionService.php=${_FREESTANDING_MARKED}" 2>/dev/null)"
_n="$(printf '%s' "${_out}" | grep -c . || true)"
if [ "${_n}" -eq 1 ] && printf '%s' "${_out}" | grep -q 'method=authorizeTransition'; then
	_ok "arm 3 CONTROL: the unused marker WITHOUT a contract is STILL reported"
else
	_bad "arm 3 CONTROL: expected exactly 1 finding for authorizeTransition, got ${_n}:"
	printf '%s\n' "${_out}" | sed 's/^/         /'
fi

# ARM 4 — CONTROL, FAIL-CLOSED. Both halves LOOK present, but the interface file
# is absent from the repo, so the supertype cannot be inspected. An unresolvable
# claim is not an exemption.
_out="$(_run_gate3_multi \
	"lib/Service/Transitions/RequiredFieldGuard.php=${_GUARD_MARKED}" 2>/dev/null)"
_n="$(printf '%s' "${_out}" | grep -c . || true)"
if [ "${_n}" -eq 1 ] && printf '%s' "${_out}" | grep -q 'method=evaluate'; then
	_ok "arm 4 CONTROL: an UNRESOLVABLE supertype is not an exemption (fail-closed)"
else
	_bad "arm 4 CONTROL: expected exactly 1 finding for evaluate, got ${_n}:"
	printf '%s\n' "${_out}" | sed 's/^/         /'
fi

# ARM 5 — CONTROL. The interface is present and names the method, but with a
# DIFFERENT parameter list — the class added $userId on its own. The join is on
# the parameter, not on the method name.
# shellcheck disable=SC2016  # $userId is PHP source — single quotes are REQUIRED
_out="$(_run_gate3_multi \
	"lib/Service/Transitions/GuardEvaluatorInterface.php=$(printf '%s' '<?php

namespace OCA\Procest\Service\Transitions;

interface GuardEvaluatorInterface
{
    public function evaluate(array $guardConfig, array $case): GuardResult;
}
')" \
	"lib/Service/Transitions/RequiredFieldGuard.php=${_GUARD_MARKED}" 2>/dev/null)"
_n="$(printf '%s' "${_out}" | grep -c . || true)"
if [ "${_n}" -eq 1 ] && printf '%s' "${_out}" | grep -q 'method=evaluate'; then
	_ok "arm 5 CONTROL: a supertype that does NOT declare the param is not an exemption"
else
	_bad "arm 5 CONTROL: expected exactly 1 finding for evaluate, got ${_n}:"
	printf '%s\n' "${_out}" | sed 's/^/         /'
fi

echo
echo "== summary: ${_pass_count} passed, ${_fail_count} failed =="
[ "${_fail_count}" -eq 0 ] || exit 1
exit 0
