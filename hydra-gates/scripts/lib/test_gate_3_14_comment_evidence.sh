#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# test_gate_3_14_comment_evidence.sh — acceptance arms for the two RUNNER-INLINE
# false negatives in the #415 class (.github#422).
#
# THE CLASS
# ---------
# A checker asks a question about CODE and answers it by matching bytes of a
# FILE. Prose is made of the same bytes. In the false-negative direction the
# gate looks for a POSITIVE signal — a route, a use of a parameter — and prose
# containing the words is accepted as the signal.
#
#   gate-14  invariant 1 asked "does a route entry for this method exist?" with
#            `grep -qF "'thing#orphanReport'"` over the RAW appinfo/routes.php.
#            The note at that grep says comment hits are "vanishingly rare" —
#            it anticipated the false POSITIVE and missed the false NEGATIVE,
#            which is the direction that ships a 404.
#
#   gate-3   the caller-identity arm counted references to `$uid` with
#            `grep -cF` over the RAW body. This gate exists BECAUSE the
#            builder's fix-mode wrote methods that accept a caller identity and
#            ignore it (decidesk#45) — and a stub that DOCUMENTS what it does
#            not do was reported finished.
#
# EACH ARM IS PAIRED. The mask that closes each false negative keeps STRING
# CONTENTS, and both gates are why: a route name IS the literal
# `'thing#index'`, and `"no such user: $uid"` INTERPOLATES $uid, so it is a
# genuine use. Arms 3 and 6 fail the moment somebody generalises
# "strings are not evidence" across this file.
#
# Reverted against origin/main, arms 2, 4 and 5 FLIP (PASS -> FAIL). Arms 1, 3
# and 6 pass either way and are labelled CONTROLS.
#
# Arm 4 was WRITTEN as a control and the revert says it is evidence: a
# commented-out `'resources' => [...]` block really did exempt a live
# controller's whole CRUD quintet from invariant 1 on origin/main. Relabelled
# rather than left as written — an arm's label is a claim about what it
# measures, and the revert is what decides it, not the author.
#
# Run: bash scripts/lib/test_gate_3_14_comment_evidence.sh   (exit 0 = green)
set -uo pipefail

PKG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../.." && pwd)"
RUNNER="${PKG_ROOT}/scripts/run-hydra-gates.sh"
WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT

_pass_n=0
_fail_n=0
_ok()  { _pass_n=$((_pass_n + 1)); printf 'PASS — %s\n' "$1"; }
_bad() { _fail_n=$((_fail_n + 1)); printf 'FAIL — %s\n' "$1"; }

APP="${WORK}/app"

# --- fixture -----------------------------------------------------------------
# `orphanReport` returns a Response shape and has NO route entry; `authorize`
# takes a caller identity and never uses it. Both are real defects, and both
# are what the arms below try to hide behind a comment.
_scaffold() {
    rm -rf "${APP}"
    mkdir -p "${APP}/lib/Controller" "${APP}/lib/Service" "${APP}/appinfo"
    cat > "${APP}/appinfo/info.xml" <<'XML'
<?xml version="1.0"?>
<info><id>fixture</id></info>
XML
    cat > "${APP}/lib/Controller/ThingController.php" <<'PHP'
<?php
namespace OCA\Fixture\Controller;

use OCP\AppFramework\Http\JSONResponse;

class ThingController {
	public function index(): JSONResponse {
		return new JSONResponse([]);
	}

	public function orphanReport(): JSONResponse {
		return new JSONResponse([]);
	}
}
PHP
    _routes_bare
    _authz_bare
    (cd "${APP}" && git init -q . \
        && git config user.email fixture@example.invalid \
        && git config user.name fixture \
        && git add -A && git commit -qm fixture)
}

_routes_bare() {
    cat > "${APP}/appinfo/routes.php" <<'PHP'
<?php
return ['routes' => [
    ['name' => 'thing#index', 'url' => '/api/things', 'verb' => 'GET'],
]];
PHP
}

_authz_bare() {
    cat > "${APP}/lib/Service/AuthzService.php" <<'PHP'
<?php
namespace OCA\Fixture\Service;

class AuthzService {
	public function authorize(string $uid, string $objectId): bool {
		$this->logger->info('authorize called');
		return true;
	}
}
PHP
}

_commit() { (cd "${APP}" && git add -A && git commit -qm arm); }

_OUT=""
_run() {
    local _logdir
    _logdir="$(mktemp -d "${WORK}/logs.XXXXXXXX")"
    _OUT="$(HYDRA_GATE_LOG_DIR="${_logdir}" bash "${RUNNER}" "${APP}" 2>&1 || true)"
    # A run that aborts before its summary leaves the per-gate PASS lines on
    # stdout and reads exactly like a clean run (.github#374).
    if ! printf '%s' "${_OUT}" | grep -q '^\[hydra-gates\] COVERAGE:'; then
        _bad "the run ABORTED before its summary — the verdicts above it are not a result"
        printf '%s\n' "${_OUT}" | tail -20 | sed 's/^/       /'
        return 1
    fi
    return 0
}

_expect_gate() {  # <n> <PASS|FAIL> <description>
    local _n="$1" _want="$2" _desc="$3" _line
    _line="$(printf '%s' "${_OUT}" | grep -E "^\[gate-${_n}\] " | head -1)"
    if [ -z "${_line}" ]; then
        _bad "${_desc} — gate-${_n} emitted NO verdict line at all"
        return
    fi
    case "${_line}" in
        *": ${_want}"*) _ok "${_desc} — ${_line}" ;;
        *) _bad "${_desc} — wanted ${_want}, got: ${_line}" ;;
    esac
}

echo "== gates 3 + 14: a comment is not the evidence (#422) =="
echo

# ---------------------------------------------------------------------------
# 1. THE POSITIVE CONTROL, FIRST. Everything below is only a measurement
#    because these two fire. (Two of the survey's own fixtures printed the same
#    verdict on both arms because the control had never failed.)
# ---------------------------------------------------------------------------
_scaffold
if _run; then
    _expect_gate 14 FAIL "CONTROL 1: a Response-returning method with no route entry is reported"
    _expect_gate 3 FAIL "CONTROL 1: a method that ignores its caller-identity parameter is reported"
fi

# ---------------------------------------------------------------------------
# 2. gate-14 — the route exists only in a comment. ONE ADDED LINE.
# ---------------------------------------------------------------------------
_scaffold
cat > "${APP}/appinfo/routes.php" <<'PHP'
<?php
return ['routes' => [
    ['name' => 'thing#index', 'url' => '/api/things', 'verb' => 'GET'],
    // TODO: wire up 'thing#orphanReport' once the export lands.
]];
PHP
_commit
if _run; then
    _expect_gate 14 FAIL "ARM 2: a route written only in a TODO does not make the endpoint reachable"
fi

# ---------------------------------------------------------------------------
# 3. gate-14 — CONTROL (anti-widening). A REAL route entry is a STRING, and it
#    must still count. Written under a comment so the mask has to end where the
#    comment ends.
# ---------------------------------------------------------------------------
_scaffold
cat > "${APP}/appinfo/routes.php" <<'PHP'
<?php
return ['routes' => [
    ['name' => 'thing#index', 'url' => '/api/things', 'verb' => 'GET'],
    // The export endpoint, added 2026-08.
    ['name' => 'thing#orphanReport', 'url' => '/api/things/orphans', 'verb' => 'GET'],
]];
PHP
_commit
if _run; then
    _expect_gate 14 PASS "CONTROL 3: a real route entry — a string literal — still satisfies invariant 1"
fi

# ---------------------------------------------------------------------------
# 4. gate-14 — A commented-out `'resources' => [...]` block must not exempt a
#    live controller's CRUD quintet from invariant 1. Same direction, same
#    cause, a different reader of the same file. Written as a control; the
#    revert says it FLIPS, so it is a third false negative, not a control.
# ---------------------------------------------------------------------------
_scaffold
cat > "${APP}/appinfo/routes.php" <<'PHP'
<?php
/*
'resources' => [
    'Thing' => ['url' => '/api/things'],
],
*/
return ['routes' => [
    ['name' => 'thing#index', 'url' => '/api/things', 'verb' => 'GET'],
]];
PHP
_commit
if _run; then
    _expect_gate 14 FAIL "ARM 4: a commented-out resources block does not auto-route a controller"
fi

# ---------------------------------------------------------------------------
# 5. gate-3 — the parameter is "used" only by a TODO. ONE ADDED LINE, and it is
#    the sentence a diligent author writes about the stub they left.
# ---------------------------------------------------------------------------
_scaffold
cat > "${APP}/lib/Service/AuthzService.php" <<'PHP'
<?php
namespace OCA\Fixture\Service;

class AuthzService {
	public function authorize(string $uid, string $objectId): bool {
		// TODO: verify $uid actually owns this object before returning true.
		$this->logger->info('authorize called');
		return true;
	}
}
PHP
_commit
if _run; then
    _expect_gate 3 FAIL "ARM 5: a TODO naming the parameter is not a use of it"
fi

# ---------------------------------------------------------------------------
# 6. gate-3 — CONTROL (anti-widening). `"no such user: $uid"` INTERPOLATES the
#    parameter: in PHP that is a genuine reference, and blanking string
#    contents would report a correct method as an unfinished stub.
# ---------------------------------------------------------------------------
_scaffold
cat > "${APP}/lib/Service/AuthzService.php" <<'PHP'
<?php
namespace OCA\Fixture\Service;

class AuthzService {
	public function authorize(string $uid, string $objectId): bool {
		if (!$this->acl->allowed($objectId)) {
			throw new \RuntimeException("no such user: $uid");
		}
		return true;
	}
}
PHP
_commit
if _run; then
    _expect_gate 3 PASS "CONTROL 6: a parameter interpolated into a string is still a use of it"
fi

# ---------------------------------------------------------------------------
# 6b. CONTROL — #434's EXEMPTION STILL READS THE ORIGINAL TEXT.
#
#     #434 (.github#339) exempts a contract-imposed unused parameter when a
#     supertype declares the same signature AND the docblock's `@param` line
#     for that parameter carries an explicit unused marker. That marker LIVES
#     IN A COMMENT BY DESIGN — the exact region this change blanks.
#
#     The two reads are deliberately split, and only `php_mask` being line- and
#     offset-preserving makes the split legal:
#
#       the body question   -> the MASK      ("is $uid referenced in code?")
#       the exemption       -> the ORIGINAL  (`--file "$f" --line "${_line_no}"`)
#
#     Point the second one at the mask and the marker vanishes, the exemption
#     silently stops working, and procest's three GuardEvaluatorInterface
#     implementors go red with no closing action available — delete the
#     parameter and the interface breaks, reference it pointlessly and that is
#     dead code written to satisfy a stub detector. That is gate-17's `@spec
#     exclude` trap in this PR's other gate, and it is why this arm exists
#     rather than a sentence in a commit message.
# ---------------------------------------------------------------------------
_scaffold
cat > "${APP}/lib/Service/GuardEvaluatorInterface.php" <<'PHP'
<?php
namespace OCA\Fixture\Service;

interface GuardEvaluatorInterface {
	public function authorize(string $uid, string $objectId): bool;
}
PHP
cat > "${APP}/lib/Service/AuthzService.php" <<'PHP'
<?php
namespace OCA\Fixture\Service;

class AuthzService implements GuardEvaluatorInterface {
	/**
	 * Always allows: this guard does not consult the caller.
	 *
	 * @param string $uid      Current user UID (unused by this implementor).
	 * @param string $objectId The object under evaluation.
	 */
	public function authorize(string $uid, string $objectId): bool {
		$this->logger->info('authorize called');
		return true;
	}
}
PHP
_commit
if _run; then
    _expect_gate 3 PASS "CONTROL 6b: a contract-imposed param marked unused is still exempt with the mask in place (#434 + #422)"
fi

# ---------------------------------------------------------------------------
# 7. A MASK THAT CANNOT BE PRODUCED IS NOT A LICENCE TO GRADE RAW TEXT.
#
#    Both gates now depend on source_scope.py. A silent fallback to the raw
#    file would be exactly the false negative just closed, and it would leave
#    no log to notice — the shape this package has found four times (#147,
#    #245, #276, #374). So the package is copied WITHOUT the mask helper and
#    both gates must decline rather than report a verdict.
#
#    This arm is NOT a control: on origin/main neither gate consults the
#    helper at all, so removing it changes nothing there. It exists because
#    the fix creates the dependency.
# ---------------------------------------------------------------------------
_scaffold
_PKG_NOMASK="${WORK}/pkg-nomask"
rm -rf "${_PKG_NOMASK}"
mkdir -p "${_PKG_NOMASK}"
cp -r "${PKG_ROOT}/scripts" "${_PKG_NOMASK}/scripts"
rm -f "${_PKG_NOMASK}/scripts/lib/source_scope.py"
_logdir="$(mktemp -d "${WORK}/logs.XXXXXXXX")"
_OUT="$(HYDRA_GATE_LOG_DIR="${_logdir}" bash "${_PKG_NOMASK}/scripts/run-hydra-gates.sh" "${APP}" 2>&1 || true)"
for _g in 3 14; do
    _line="$(printf '%s' "${_OUT}" | grep -E "^\[gate-${_g}\] " | head -1)"
    case "${_line}" in
        *SKIPPED*|*skipped*)
            _ok "ARM 7: with source_scope.py absent, gate-${_g} declines — ${_line}" ;;
        "")
            _bad "ARM 7: gate-${_g} emitted NO verdict line at all with the mask absent" ;;
        *)
            _bad "ARM 7: gate-${_g} reported a verdict it could not support — ${_line}" ;;
    esac
done

echo
echo "----------------------------------------------------------------"
printf '%d passed, %d failed\n' "${_pass_n}" "${_fail_n}"
echo "----------------------------------------------------------------"
[ "${_fail_n}" -eq 0 ]
