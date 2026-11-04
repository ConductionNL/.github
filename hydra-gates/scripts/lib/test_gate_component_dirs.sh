#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# test_gate_component_dirs.sh — the role gates reach controllers, services and
# background jobs that live in a component directory (lib/<Component>/<Role>/)
# instead of lib/Controller, lib/Service and lib/BackgroundJob.
#
# openregister#5519 moved 63 Search classes to lib/Search/<layer>/. Gates 3,
# 6, 8 and 57 listed only lib/Service and lib/BackgroundJob, and gates 5, 7, 9
# and 14 located controllers in lib/Controller only, so the moved classes were
# no longer opened and the gates still printed PASS. A moved controller keeps
# its route name through appinfo/class-aliases.json, so the route table no
# longer spells where the class lives.
#
# Every fixture below is built in a fresh git repository and carries its
# defects ONLY under lib/Search/: there is no lib/Controller, lib/Service or
# lib/BackgroundJob, so a gate that reads those directories alone finds
# nothing and its assertion fails.
#
# HYDRA_GATES_RUNNER=<path> runs the suite against another runner, which is
# how its failing-first state is shown against the runner before the fix.
#
# Run: bash scripts/lib/test_gate_component_dirs.sh   (exit 0 = all green)
set -uo pipefail

PKG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../.." && pwd)"
RUNNER="${HYDRA_GATES_RUNNER:-${PKG_ROOT}/scripts/run-hydra-gates.sh}"

_fail_n=0
_pass_n=0
_ok()  { _pass_n=$((_pass_n + 1)); printf 'PASS — %s\n' "$1"; }
_bad() { _fail_n=$((_fail_n + 1)); printf 'FAIL — %s\n' "$1"; }

_WORK="$(mktemp -d "${TMPDIR:-/tmp}/hydra-gate-compdirs.XXXXXXXX")"
trap 'rm -rf "${_WORK}"' EXIT

_put() { # <app> <rel> <content>
    mkdir -p "$(dirname "$1/$2")"
    printf '%s' "$3" > "$1/$2"
}

_git() { git -C "$1" -c user.email=fixture@example.invalid -c user.name=Fixture "${@:2}" >/dev/null 2>&1; }

# The controller every scenario routes to. `unguarded` is routed and carries
# no auth attribute (gate 5); `show` is an unguarded #[NoAdminRequired] read
# by id (gate 7); `adminState` says any user and requires an admin (gate 9);
# `orphanReport` returns a Response and has no route (gate 14). The last two
# exist only with <with-unguarded>=1.
_controller() { # <namespace> <with-unguarded:0|1>
    local _unguarded=""
    if [ "$2" = "1" ]; then
        _unguarded='
    /**
     * Builds the orphan report.
     *
     * @NoAdminRequired
     *
     * @return JSONResponse
     */
    public function orphanReport(): JSONResponse
    {
        return new JSONResponse([]);
    }
    /**
     * Returns the export state, with no auth posture declared.
     *
     * @return JSONResponse
     */
    public function unguarded(): JSONResponse
    {
        return new JSONResponse(["state" => "open"]);
    }
'
    fi
    cat <<PHP
<?php
/**
 * @license  EUPL-1.2
 * @copyright 2026 Conduction B.V.
 */

namespace $1;

use OCP\AppFramework\Controller;
use OCP\AppFramework\Http\JSONResponse;

class ThingController extends Controller
{
    /**
     * Reads one object by id with no guard.
     *
     * @NoAdminRequired
     *
     * @return JSONResponse
     */
    public function show(string \$id): JSONResponse
    {
        return new JSONResponse(['id' => \$id, 'secret' => 'exposed']);
    }

    /**
     * Reads admin state behind an annotation that contradicts the body.
     *
     * @NoAdminRequired
     *
     * @return JSONResponse
     */
    public function adminState(): JSONResponse
    {
        \$this->requireAdmin();
        return new JSONResponse(['state' => 'ok']);
    }

${_unguarded}}
PHP
}

_routes() { # <with-unguarded:0|1>
    printf '<?php\nreturn [\n    %s\n' "'routes' => ["
    printf "        ['name' => 'thing#show', 'url' => '/api/things/{id}', 'verb' => 'GET'],\n"
    printf "        ['name' => 'thing#adminState', 'url' => '/api/admin-state', 'verb' => 'GET'],\n"
    [ "$1" = "1" ] && printf "        ['name' => 'thing#unguarded', 'url' => '/api/unguarded', 'verb' => 'GET'],\n"
    printf '    ],\n];\n'
}

_aliases() {
    cat <<'JSON'
{
    "aliases": {
        "OCA\\CompFx\\Controller\\ThingController": {"class": "OCA\\CompFx\\Search\\Controller\\ThingController", "eager": false, "service": true}
    }
}
JSON
}

# _app <dir> — the app skeleton plus the Search services and job.
_app() {
    local _a="$1"
    mkdir -p "${_a}"
    _git "${_a}" init -q .
    _put "${_a}" appinfo/info.xml '<?xml version="1.0"?>
<info><id>compfx</id><name>Component Fixture</name><namespace>CompFx</namespace><version>1.0.0</version><licence>agpl</licence><author>Conduction</author></info>
'
    _put "${_a}" composer.json '{"name": "conduction/compfx", "autoload": {"psr-4": {"OCA\\CompFx\\": "lib/"}}}
'
    _put "${_a}" lib/AppInfo/Application.php '<?php
namespace OCA\CompFx\AppInfo;

class Application
{
}
'
    _put "${_a}" lib/Search/Service/PermissionHandler.php '<?php
namespace OCA\CompFx\Search\Service;

class PermissionHandler
{
    private function getAuthorizationService(): ?object
    {
        try {
            return \OC::$server->get("OCA\\CompFx\\Search\\Service\\AuthorizationService");
        } catch (\Throwable) {
            return null;
        }
    }

    public function mayWrite(string $userId, string $objectId): bool
    {
        $auth = $this->getAuthorizationService();
        if ($auth !== null) {
            return $auth->check($userId, $objectId);
        }

        return true;
    }
}
'
    _put "${_a}" lib/Search/Service/TransitionGuard.php '<?php
namespace OCA\CompFx\Search\Service;

class TransitionGuard
{
    public function isTransitionAllowed(string $userId, string $state): bool
    {
        return ($userId !== "" && $state !== "");
    }
}
'
    _put "${_a}" lib/Search/Service/LedgerService.php '<?php
namespace OCA\CompFx\Search\Service;

class LedgerService
{
    public function postJournalEntry(array $data): void
    {
        file_put_contents("/tmp/ledger", json_encode($data));
    }
}
'
    _put "${_a}" lib/Search/BackgroundJob/ReindexJob.php '<?php
namespace OCA\CompFx\Search\BackgroundJob;

use OCP\BackgroundJob\TimedJob;

class ReindexJob extends TimedJob
{
    protected function run($argument): void
    {
        // In a complete implementation this would reindex. Nothing happens here.
    }
}
'
}

# _run <app> [runner args...] — the whole run in _OUT, its log dir in _LOGS.
_OUT="" _LOGS=""
_run() {
    local _a="$1"; shift
    _LOGS="$(mktemp -d "${_WORK}/logs.XXXXXXXX")"
    _OUT="$(cd "${_a}" && HYDRA_GATE_LOG_DIR="${_LOGS}" bash "${RUNNER}" "$@" "${_a}" 2>&1 < /dev/null || true)"
    if ! printf '%s' "${_OUT}" | grep -q '^\[hydra-gates\] COVERAGE:'; then
        _bad "run in ${_a} ABORTED before the summary — verdicts above it are not a result"
        printf '%s\n' "${_OUT}" | tail -15 | sed 's/^/       /'
        return 1
    fi
}

_expect_gate() { # <n> <PASS|FAIL> <description>
    local _line
    _line="$(printf '%s' "${_OUT}" | grep -E "^\[gate-$1\] " | head -1)"
    case "${_line}" in
        *": $2"*) _ok "$3 — ${_line:0:160}" ;;
        '') _bad "$3 — gate-$1 emitted no verdict line" ;;
        *) _bad "$3 — wanted $2, got: ${_line:0:240}" ;;
    esac
}

# Some gates write hydra-gate-<name>.log, others a mktemp hydra-gate-<name>.XXXXXX.log.
_logs_of() { cat "${_LOGS}/hydra-gate-$1".log "${_LOGS}/hydra-gate-$1".*.log 2>/dev/null || true; }

_expect_log() { # <log-name> <fixed-string> <description>
    if _logs_of "$1" | grep -qF -- "$2"; then
        _ok "$3"
    else
        _bad "$3 — '$2' not in hydra-gate-$1[.*].log: $(_logs_of "$1" | tr '\n' '|' | cut -c1-300)"
    fi
}

_expect_no_log() { # <log-name> <fixed-string> <description>
    if _logs_of "$1" | grep -qF -- "$2"; then
        _bad "$3 — unexpected: $(_logs_of "$1" | grep -F -- "$2" | head -1)"
    else
        _ok "$3"
    fi
}

echo "== role gates over lib/<Component>/<Role>/ =="

# ---------------------------------------------------------------------------
# 1. A full run over an app whose controller, services and job all sit under
#    lib/Search/. The controller is reached through its class alias.
# ---------------------------------------------------------------------------
A="${_WORK}/aliased"
_app "${A}"
_put "${A}" appinfo/routes.php "$(_routes 1)"
_put "${A}" appinfo/class-aliases.json "$(_aliases)"
_put "${A}" lib/Search/Controller/ThingController.php "$(_controller 'OCA\CompFx\Search\Controller' 1)"
_git "${A}" add -A && _git "${A}" commit -q -m base
if _run "${A}"; then
    _expect_gate 5 FAIL "gate 5: a routed controller outside lib/Controller without an auth attribute fails"
    _expect_log route-auth "lib/Search/Controller/ThingController.php" "gate 5 judges lib/Search/Controller/ThingController.php"
    _expect_log route-auth "method=unguarded rule=missing-auth-attribute" "gate 5 names the unguarded method"
    _expect_no_log route-auth "method=show " "gate 5 does not flag the annotated show()"
    _expect_log no-admin-idor "lib/Search/Controller/ThingController.php" "gate 7 opens the controller under lib/Search/Controller"
    _expect_log semantic-auth "lib/Search/Controller/ThingController.php" "gate 9 opens the controller under lib/Search/Controller"
    _expect_log route-reachability "method=orphanReport" "gate 14 finds the unrouted method on the moved controller"
    _expect_no_log route-reachability "method=show " "gate 14 sees thing#show as the moved controller's route"
    _expect_log unsafe-auth-resolver "lib/Search/Service/PermissionHandler.php" "gate 8 opens lib/Search/Service"
    _expect_log orphan-auth "lib/Search/Service/TransitionGuard.php" "gate 6 opens lib/Search/Service"
    _expect_log orphaned-write-capability "lib/Search/Service/LedgerService.php" "gate 57 opens lib/Search/Service"
    _expect_log stub-scan "lib/Search/BackgroundJob/ReindexJob.php: run() body" "gate 3 judges the run() body of a job under lib/Search/BackgroundJob"
fi

# ---------------------------------------------------------------------------
# 2. The same controller with the auth attribute in place: gate 5 judges it
#    and passes, instead of parking it as "not judged".
# ---------------------------------------------------------------------------
B="${_WORK}/aliased-clean"
_app "${B}"
_put "${B}" appinfo/routes.php "$(_routes 0)"
_put "${B}" appinfo/class-aliases.json "$(_aliases)"
_put "${B}" lib/Search/Controller/ThingController.php "$(_controller 'OCA\CompFx\Search\Controller' 0)"
_git "${B}" add -A && _git "${B}" commit -q -m base
if _run "${B}"; then
    _expect_gate 5 PASS "gate 5: annotated routed methods on a moved controller pass"
    if [ -s "${_LOGS}/hydra-gate-route-auth-unresolved.log" ]; then
        _bad "gate 5 parked routes as not judged: $(head -1 "${_LOGS}/hydra-gate-route-auth-unresolved.log")"
    else
        _ok "gate 5 judged every route (nothing parked as unresolved)"
    fi
fi

# ---------------------------------------------------------------------------
# 3. The controller moved WITHOUT a class alias: nothing answers to
#    OCA\CompFx\Controller\ThingController, so the routes 500. Gate 5 fails
#    loudly instead of filing the routes as "not judged", and gate 14 fails.
# ---------------------------------------------------------------------------
C="${_WORK}/unaliased"
_app "${C}"
_put "${C}" appinfo/routes.php "$(_routes 0)"
_put "${C}" lib/Search/Controller/ThingController.php "$(_controller 'OCA\CompFx\Search\Controller' 0)"
_git "${C}" add -A && _git "${C}" commit -q -m base
if _run "${C}"; then
    _expect_gate 5 FAIL "gate 5: a routed controller no file declares fails"
    _expect_log route-auth-controller-not-found "thing#show rule=routed-controller-not-found" "gate 5 names the route whose controller is missing"
    _expect_gate 14 FAIL "gate 14: the same route is unreachable"
fi

# ---------------------------------------------------------------------------
# 4. Diff scope: a change that moves the controller out of lib/Controller.
#    With the alias the moved routes are judged (not skipped as out of scope);
#    without it the move fails gate 5 and gate 14.
# ---------------------------------------------------------------------------
for _variant in with-alias without-alias; do
    D="${_WORK}/move-${_variant}"
    _app "${D}"
    _put "${D}" appinfo/routes.php "$(_routes 0)"
    _put "${D}" lib/Controller/ThingController.php "$(_controller 'OCA\CompFx\Controller' 0)"
    _git "${D}" add -A && _git "${D}" commit -q -m base
    _git "${D}" branch -M base
    _git "${D}" checkout -q -b change
    mkdir -p "${D}/lib/Search/Controller"
    _git "${D}" mv lib/Controller/ThingController.php lib/Search/Controller/ThingController.php
    sed -i 's/^namespace OCA\\CompFx\\Controller;/namespace OCA\\CompFx\\Search\\Controller;/' "${D}/lib/Search/Controller/ThingController.php"
    [ "${_variant}" = "with-alias" ] && _put "${D}" appinfo/class-aliases.json "$(_aliases)"
    _git "${D}" add -A && _git "${D}" commit -q -m move
    if _run "${D}" --scope-to-diff --base base; then
        if [ "${_variant}" = "with-alias" ]; then
            _expect_gate 5 PASS "move with alias: gate 5 judges the moved routes and passes"
            _expect_gate 14 PASS "move with alias: gate 14 resolves the moved routes"
        else
            _expect_gate 5 FAIL "move without alias: gate 5 fails on the orphaned routes"
            _expect_gate 14 FAIL "move without alias: gate 14 fails on the orphaned routes"
        fi
    fi
done

echo
echo "test_gate_component_dirs.sh: ${_pass_n} passed, ${_fail_n} failed"
[ "${_fail_n}" -eq 0 ]
