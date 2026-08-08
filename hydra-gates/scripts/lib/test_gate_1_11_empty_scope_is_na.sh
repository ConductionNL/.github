#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# test_gate_1_11_empty_scope_is_na.sh — gates 1–11 must not report PASS over a
# scope they never opened, and must still catch a planted defect when they do.
#
# WHAT THIS GUARDS (measured 2026-08-08, gate package cdfbd7a)
# ------------------------------------------------------------
# The sibling suite test_gate_empty_scope_never_passes.sh pinned this behaviour
# for gates 19/25/62/63. The SAME hole was open across the whole 1–11 band and
# nothing was watching it. Run against larpingapp with `--scope-to-diff` over a
# README-only commit, the runner printed:
#
#     [gate-1]  spdx-headers:          PASS
#     [gate-2]  forbidden-patterns:    PASS
#     [gate-3]  stub-scan:             PASS
#     [gate-5]  route-auth:            PASS      <- a SECURITY gate
#     [gate-8]  unsafe-auth-resolver:  PASS      <- a SECURITY gate
#     [gate-9]  semantic-auth:         PASS      <- a SECURITY gate
#     [gate-10] initial-state:         PASS
#     [gate-11] admin-router:          PASS      <- a SECURITY gate
#
# Eight greens over zero bytes, four of them on authorization surfaces. Gates
# 4, 6 and 7 already said NOT APPLICABLE for the identical situation, which is
# what made the other eight readable as a real result rather than an absence.
#
# `na`, not `structural`: per #268 an empty ADR-020 diff scope is subject matter
# absent from THIS DIFF, and no change the author could make would put a PHP
# file into a diff that touches none. Categorising it `structural` would exit 98
# on PRs that have nothing to judge.
#
# ARM 2 is the control that keeps ARM 1 honest. A gate can always be made to say
# `na` by never looking at anything; these gates must still FAIL a planted true
# positive when the file IS in scope. Without that arm, "reports na" is
# satisfiable by a gate that has been skipped into uselessness.
#
# Run: bash scripts/lib/test_gate_1_11_empty_scope_is_na.sh   (exit 0 = green)

set -u

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_scripts="$(cd "${_here}/.." && pwd)"
_runner="${HYDRA_GATES_RUNNER_UNDER_TEST:-${_scripts}/run-hydra-gates.sh}"

_failures=0
_ok()  { echo "  ok   — $1"; }
_bad() { echo "  FAIL — $1"; _failures=$((_failures + 1)); }

echo "test_gate_1_11_empty_scope_is_na.sh"

_tmp="$(mktemp -d "${TMPDIR:-/tmp}/hydra-1-11-scope.XXXXXX")"
trap 'rm -rf "${_tmp}"' EXIT

_app="${_tmp}/app"
mkdir -p "${_app}/src" "${_app}/appinfo" "${_app}/lib/Controller" "${_app}/lib/Service"
printf '{"name":"fx","menu":[],"pages":[]}\n' > "${_app}/src/manifest.json"
printf "import { createRouter } from 'vue-router'\nconst router = createRouter({ routes: [] })\nexport default router\n" \
    > "${_app}/src/main.js"
printf "<?php\nreturn ['routes'=>[['name'=>'thing#index','url'=>'/api/thing','verb'=>'GET']]];\n" \
    > "${_app}/appinfo/routes.php"

# A CLEAN controller: correct header, declared auth posture, guarded body.
cat > "${_app}/lib/Controller/ThingController.php" <<'PHP'
<?php

/**
 * @copyright 2026 Conduction B.V.
 * @license   EUPL-1.2 https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12
 */

namespace OCA\Fx\Controller;

class ThingController
{
    /**
     * Read one thing.
     *
     * @NoAdminRequired
     */
    public function index(string $id)
    {
        if ($this->owns($id) === false) {
            return new JSONResponse([], Http::STATUS_FORBIDDEN);
        }

        return new JSONResponse([]);

    }//end index()
}//end class
PHP

(
    cd "${_app}" || exit 1
    git init -q .
    git add -A
    git -c user.email=t@t -c user.name=t commit -qm init
    # A docs-only second commit — the ordinary shape of a PR that touches no
    # PHP and no frontend. This is the EMPTY SCOPE case.
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

_verdict() { grep -oE "^\[gate-$2\] [^:]+: [A-Z]+( [A-Z]+)*( \([a-z]+\))?" "$1" | head -1 | sed 's/^[^:]*: //'; }

# ---------------------------------------------------------------------------
# ARM 1 — an empty diff scope is NOT APPLICABLE for every gate in the band.
# ---------------------------------------------------------------------------
echo "  -- ARM 1: empty diff scope"
_scoped="${_tmp}/scoped.txt"
_run "${_scoped}" --scope-to-diff --base HEAD~1
for _g in 1 2 3 4 5 6 7 8 9 10 11; do
    _v="$(_verdict "${_scoped}" "${_g}")"
    case "${_v}" in
        "NOT APPLICABLE")
            _ok "gate-${_g} reports NOT APPLICABLE over an empty diff scope" ;;
        PASS)
            _bad "gate-${_g} reported PASS over a scope it never opened" ;;
        "")
            _bad "gate-${_g} emitted NO verdict line at all over an empty diff scope" ;;
        *)
            _bad "gate-${_g} empty-scope verdict is '${_v}' — expected NOT APPLICABLE" ;;
    esac
done

# Every NOT APPLICABLE must carry a reason. A bare category is a skip nobody
# can audit.
for _g in 1 2 3 5 8 9 10 11; do
    if grep -qE "^\[gate-${_g}\][^:]*: NOT APPLICABLE — .{40,}" "${_scoped}"; then
        _ok "gate-${_g} states WHY it was not applicable"
    else
        _bad "gate-${_g}'s NOT APPLICABLE line carries no substantive reason"
    fi
done

# ---------------------------------------------------------------------------
# ARM 2 — THE CONTROL. Saying `na` is free; catching the defect is not.
# Each gate gets one textbook true positive, full-tree, and must FAIL on it.
# ---------------------------------------------------------------------------
echo "  -- ARM 2: planted true positives, full tree"

_full="${_tmp}/full-clean.txt"
_run "${_full}"
for _g in 1 2 3 5 8 9 10 11; do
    _v="$(_verdict "${_full}" "${_g}")"
    if [ "${_v}" = "PASS" ]; then
        _ok "gate-${_g} PASSes the clean fixture (anti-widening control)"
    else
        _bad "gate-${_g} returned '${_v}' on a CLEAN fixture — expected PASS"
    fi
done

# Gates enumerate their surface with `git ls-files` (_enum_tracked), so an
# UNTRACKED plant is invisible and the gate reports PASS — a green that says
# nothing about the gate. Stage every plant before judging it.
_plant_and_check() {  # <gate> <label> <file>
    local _g="$1" _label="$2" _file="$3"
    local _out="${_tmp}/plant-${_g}.txt"
    ( cd "${_app}" && git add -A >/dev/null 2>&1 )
    if ! ( cd "${_app}" && git ls-files --error-unmatch "${_file#${_app}/}" >/dev/null 2>&1 ); then
        _bad "gate-${_g}: the ${_label} plant was NOT staged — the assertion below would prove nothing"
        return
    fi
    _run "${_out}"
    local _v; _v="$(_verdict "${_out}" "${_g}")"
    if [ "${_v}" = "FAIL" ]; then
        _ok "gate-${_g} FAILs its planted true positive (${_label})"
    else
        _bad "gate-${_g} returned '${_v}' for a planted ${_label} — expected FAIL"
    fi
    rm -f "${_file}"
    _restore
}

# Restore the fixture to its COMMITTED state. `git checkout -- .` restores from
# the INDEX, and the plants were staged, so it would hand the plant straight
# back — which is how gate-11 reported residue that did not exist. Each planted
# path is removed by name (never `git clean`, which would take the fixture's
# untracked work with it).
_restore() {
    ( cd "${_app}" \
        && git reset -q HEAD -- . >/dev/null 2>&1 \
        && git checkout -q HEAD -- . >/dev/null 2>&1 )
}

# gate-1: a lib/ PHP file with no @license / @copyright.
printf '<?php\nnamespace OCA\\Fx\\Service;\nclass NoHeader { public function a() { return 1; } }\n' \
    > "${_app}/lib/Service/NoHeader.php"
_plant_and_check 1 "PHP file with no SPDX header" "${_app}/lib/Service/NoHeader.php"

# gate-2: a debug helper that the OLD grep could not see.
cat > "${_app}/lib/Service/Dbg.php" <<'PHP'
<?php

/**
 * @copyright 2026 Conduction B.V.
 * @license   EUPL-1.2 https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12
 */

namespace OCA\Fx\Service;

class Dbg
{
    public function a(): void
    {
        var_dump ($x);

    }//end a()
}//end class
PHP
_plant_and_check 2 "var_dump WITH A SPACE — invisible to the old grep" "${_app}/lib/Service/Dbg.php"

# gate-3: a service method that accepts a caller identity and ignores it.
cat > "${_app}/lib/Service/Stub.php" <<'PHP'
<?php

/**
 * @copyright 2026 Conduction B.V.
 * @license   EUPL-1.2 https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12
 */

namespace OCA\Fx\Service;

class Stub
{
    public function authorizeRead(string $uid, string $objectId): bool
    {
        $result = true;
        $note = 'not wired yet';
        return $result;

    }//end authorizeRead()
}//end class
PHP
_plant_and_check 3 "caller-identity parameter ignored" "${_app}/lib/Service/Stub.php"

# gate-8: the decidesk#45 fail-open, TAB indented (the shape the old awk
# mis-extracted in both directions).
printf '<?php\n\n/**\n * @copyright 2026 Conduction B.V.\n * @license   EUPL-1.2 x\n */\n\nnamespace OCA\\Fx\\Service;\n\nclass Res\n{\n\tpublic function getAuthorizationService(): ?object\n\t{\n\t\ttry {\n\t\t\treturn $this->c->get("A");\n\t\t} catch (\\Throwable $e) {\n\t\t\treturn null;\n\t\t}\n\t}\n}\n' \
    > "${_app}/lib/Service/Res.php"
_plant_and_check 8 "tab-indented catch(Throwable){return null}" "${_app}/lib/Service/Res.php"

# gate-10: the TWO-STEP DOM read — the form the old single-line grep missed.
printf "const el = document.getElementById('fx-settings')\nexport const v = el.dataset.version\n" \
    > "${_app}/src/probe.js"
_plant_and_check 10 "two-step getElementById -> .dataset read" "${_app}/src/probe.js"

# gate-11: the doriath c7c72e9 defect, in the router the app ACTUALLY uses.
printf "import { createRouter } from 'vue-router'\nimport AdminRoot from './views/AdminRoot.vue'\nconst routes = []\nroutes.push({ path: '/settings', component: AdminRoot })\nconst router = createRouter({ routes })\nexport default router\n" \
    > "${_app}/src/main.js"
( cd "${_app}" && git add -A >/dev/null 2>&1 )
_out="${_tmp}/plant-11.txt"
_run "${_out}"
_v="$(_verdict "${_out}" 11)"
if [ "${_v}" = "FAIL" ]; then
    _ok "gate-11 FAILs its planted true positive (doriath /settings -> AdminRoot in src/main.js)"
else
    _bad "gate-11 returned '${_v}' for the doriath defect in src/main.js — expected FAIL. This is the DEAD-GATE case: fourteen of fifteen fleet apps build their router there."
fi
_restore

# ---------------------------------------------------------------------------
# ARM 3 — removing the plant restores the prior verdict (no residue).
# ---------------------------------------------------------------------------
echo "  -- ARM 3: no residue after the plants are removed"
_after="${_tmp}/after.txt"
_run "${_after}"
for _g in 1 2 3 5 8 9 10 11; do
    _v="$(_verdict "${_after}" "${_g}")"
    if [ "${_v}" = "PASS" ]; then
        _ok "gate-${_g} returned to PASS after its plant was removed"
    else
        _bad "gate-${_g} is '${_v}' after the plants were removed — residue"
    fi
done

echo
if [ "${_failures}" -gt 0 ]; then
    echo "FAILED — ${_failures} assertion(s)"
    exit 1
fi
echo "ALL test_gate_1_11_empty_scope_is_na assertions passed"
