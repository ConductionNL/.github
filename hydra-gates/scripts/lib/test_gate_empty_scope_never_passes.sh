#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# test_gate_empty_scope_never_passes.sh — a gate must never report PASS over a
# scope it did not open.
#
# WHAT THIS GUARDS (.github#242, #240)
# ------------------------------------
# Gates 19 (e2e-coverage), 25 (contract-coverage), 62 (store-plane) and
# 63 (settings-surface) diff-scoped themselves INSIDE their own helpers, below
# the runner's base resolution, and did it UNCONDITIONALLY — the base ref was
# defaulted even when the caller had asked for no scoping at all.
#
# Two consequences, and the second is why it stayed hidden:
#
#   1. A full-tree run was silently narrowed to a diff against
#      origin/development, which on a mainline checkout is empty.
#   2. The verdict for "I inspected nothing" was PASS, not a skip. So
#      --require-full-coverage — the one assertion built to catch gates that did
#      not run — had nothing to catch. gate-63 was the clearest case: its log
#      said "gate skipped" on the line above a verdict that said PASS.
#
# Measured on openconnector 2026-08-08:
#   gate-19   5 findings as the runner invoked it   ->  412 over the full tree
#   gate-25   PASS as the runner invoked it         ->   32 over the full tree
#
# THREE ARMS, and all three are needed:
#
#   ARM 1  a planted TRUE POSITIVE is still caught in full-tree mode.
#          Widening a checker until it catches nothing is not a fix, so this
#          arm runs FIRST and everything else is meaningless without it.
#   ARM 2  an empty scope produces a visible SKIP, and --require-full-coverage
#          FAILS the run (exit 98).
#   ARM 3  a genuinely non-empty scope with nothing wrong still PASSes, so the
#          fix has not simply turned every gate into a permanent skip.

set -u

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_scripts="$(cd "${_here}/.." && pwd)"
_runner="${HYDRA_GATES_RUNNER_UNDER_TEST:-${_scripts}/run-hydra-gates.sh}"

_failures=0
_ok()  { echo "  ok   — $1"; }
_bad() { echo "  FAIL — $1"; _failures=$((_failures + 1)); }

echo "test_gate_empty_scope_never_passes.sh"

_tmp="$(mktemp -d "${TMPDIR:-/tmp}/hydra-emptyscope.XXXXXX")"
trap 'rm -rf "${_tmp}"' EXIT

# ---------------------------------------------------------------------------
# A fixture that carries ONE genuine finding for gate-19 and ONE for gate-25:
# a declared scenario with no @e2e tag, and a routed #[PublicPage] method with
# no Newman/PHPUnit contract test and no @contract exclude.
# ---------------------------------------------------------------------------
_app="${_tmp}/app"
mkdir -p "${_app}/src" "${_app}/openspec/specs/thing" "${_app}/appinfo" \
         "${_app}/lib/Controller"
printf '{"name":"fx","menu":[]}\n' > "${_app}/src/manifest.json"
printf '## Purpose\n\n#### Scenario: a thing happens\n- WHEN x\n- THEN y\n' \
    > "${_app}/openspec/specs/thing/spec.md"
printf "<?php\nreturn ['routes'=>[['name'=>'thing#index','url'=>'/api/thing','verb'=>'GET']]];\n" \
    > "${_app}/appinfo/routes.php"
cat > "${_app}/lib/Controller/ThingController.php" <<'PHP'
<?php
namespace OCA\Fx\Controller;
class ThingController {
    #[PublicPage]
    public function index() { return 1; }
}
PHP
(
    cd "${_app}" || exit 1
    git init -q .
    git add -A
    git -c user.email=t@t -c user.name=t commit -qm init
    # A docs-only second commit. This is the ordinary shape of a PR that
    # touches no spec, no manifest and no controller — the EMPTY SCOPE case.
    printf 'docs only\n' > README.md
    git add README.md
    git -c user.email=t@t -c user.name=t commit -qm docs
) >/dev/null 2>&1

_run() {  # _run <outfile> [runner args...]
    local out="$1"; shift
    local logs="${_tmp}/logs.$$.${RANDOM}"
    mkdir -p "${logs}"
    (
        cd "${_app}" || exit 1
        HYDRA_GATE_LOG_DIR="${logs}" bash "${_runner}" "$@" . > "${out}" 2>&1
    )
    return $?
}

_verdict() { grep -oE "^\[gate-$2\] [^:]+: [A-Z]+( \([a-z]+\))?" "$1" | head -1 | sed 's/^[^:]*: //'; }

# ---------------------------------------------------------------------------
# ARM 1 — the planted true positives are still caught, full-tree.
# ---------------------------------------------------------------------------
_full="${_tmp}/full.txt"
_run "${_full}"
for _g in 19 25; do
    if grep -qE "^\[gate-${_g}\][^:]*: FAIL" "${_full}"; then
        _ok "gate-${_g} still catches its planted true positive over the full tree"
    else
        _bad "gate-${_g} did NOT catch its planted true positive — got: $(_verdict "${_full}" "${_g}")"
    fi
done

# Full-tree must actually OPEN the manifests rather than diff-scope itself to
# nothing: 62/63 are clean in this fixture, so they must PASS, not SKIP.
for _g in 62 63; do
    _v="$(_verdict "${_full}" "${_g}")"
    if [ "${_v}" = "PASS" ]; then
        _ok "gate-${_g} audited the manifest over the full tree (PASS, not a self-inflicted skip)"
    else
        _bad "gate-${_g} full-tree verdict is '${_v}' — expected PASS over a clean manifest"
    fi
done

# ---------------------------------------------------------------------------
# ARM 2 — an empty scope is a visible SKIP, and it fails --require-full-coverage.
# ---------------------------------------------------------------------------
_scoped="${_tmp}/scoped.txt"
_run "${_scoped}" --scope-to-diff --base HEAD~1 --require-full-coverage
_scoped_rc=$?

for _g in 19 25 62 63; do
    _v="$(_verdict "${_scoped}" "${_g}")"
    case "${_v}" in
        "SKIPPED (structural)")
            _ok "gate-${_g} reports SKIPPED (structural) over an empty scope"
            ;;
        PASS)
            _bad "gate-${_g} reported PASS over a scope it never opened — this is the #242 defect"
            ;;
        *)
            _bad "gate-${_g} empty-scope verdict is '${_v}' — expected SKIPPED (structural)"
            ;;
    esac
done

if [ "${_scoped_rc}" -eq 98 ]; then
    _ok "--require-full-coverage failed the run over the empty scopes (exit 98)"
else
    _bad "--require-full-coverage exited ${_scoped_rc}, expected 98 — the skips are not being counted"
fi

# The skip must carry a REASON. A bare "SKIPPED" is how a gate disappears
# quietly, which is the failure this whole accounting exists to stop.
for _g in 19 25 62 63; do
    if grep -qE "^\[gate-${_g}\][^:]*: SKIPPED \(structural\) — .+UNVERIFIED" "${_scoped}"; then
        _ok "gate-${_g}'s skip states what it left unverified"
    else
        _bad "gate-${_g}'s skip has no reason naming what went unverified"
    fi
done

# ---------------------------------------------------------------------------
# ARM 3 — a NON-empty scope with nothing wrong still passes.
#
# Without this arm, "make every empty scope a skip" could be satisfied by
# skipping unconditionally, and the suite would look fixed while checking
# nothing. The second commit here touches the manifest, so 62/63 have real work.
# ---------------------------------------------------------------------------
(
    cd "${_app}" || exit 1
    printf '{"name":"fx","menu":[],"version":"1.0.1"}\n' > src/manifest.json
    git add src/manifest.json
    git -c user.email=t@t -c user.name=t commit -qm "chore: bump manifest"
) >/dev/null 2>&1

_touched="${_tmp}/touched.txt"
_run "${_touched}" --scope-to-diff --base HEAD~1
for _g in 62 63; do
    _v="$(_verdict "${_touched}" "${_g}")"
    if [ "${_v}" = "PASS" ]; then
        _ok "gate-${_g} PASSes when the diff genuinely contains a clean manifest"
    else
        _bad "gate-${_g} returned '${_v}' for a real, clean, in-scope manifest — the gate has been skipped into uselessness"
    fi
done

echo
if [ "${_failures}" -eq 0 ]; then
    echo "test_gate_empty_scope_never_passes.sh: ALL PASS"
    exit 0
fi
echo "test_gate_empty_scope_never_passes.sh: ${_failures} FAILURE(S)"
exit 1
