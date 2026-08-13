#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# test_gate_45_to_55_acceptance.sh — the acceptance test for gates 45–55:
# each one must FAIL on a planted true positive, PASS on the clean fixture,
# and say NOT APPLICABLE (never PASS) when it inspected nothing.
#
# WHY THIS EXISTS
# ---------------
# On 2026-08-08 one textbook true positive was planted per a11y gate in
# nldesign and ALL THIRTEEN reported PASS: eleven globbed `src/**/*.vue` and
# nldesign ships zero `.vue` files. Every green was a green over nothing, and
# no open issue named any of them — because nobody had ever asked a gate to
# fail on purpose. "No open issue" means nobody looked.
#
# So every arm below plants a defect FIRST and asserts the gate names it.
# An arm that only ever sees clean input proves nothing: a checker that has
# been widened until it catches nothing passes it identically.
#
# THREE FAMILIES OF ARM
# ---------------------
#   A. UNOPENED SCOPE IS NEVER PASS (#242/#240/#258/#268). All eleven gates
#      printed PASS on a README-only diff — a run in which not one of them
#      opened a file. Measured on larpingapp: 11 PASS lines, and the summary
#      then read "53 of 53 applicable gates ran".
#   B. GATE-45's GUARD MUST MIRROR ITS ENUMERATOR (#225/#261). It reads
#      src/ + templates/ + appinfo/templates/ but was gated on `[ -d src ]`,
#      so a templates-only app got NOT APPLICABLE over live markup. A false
#      `na` is worse than the PASS it replaced: `na` removes the gate from the
#      coverage arithmetic, so the run reports "all applicable gates green"
#      with the defect inside it.
#   C. GATE-50 WAS WRONG IN BOTH DIRECTIONS AT ONCE. It could not see a config
#      read whose app id is a class constant (the fleet-standard idiom), and
#      it rejected a correct compound `if ($a === '' || $b === '')` guard.
#      Both arms are here, plus the opencatalogi#86 shape that mixes them:
#      a guarded read and an unguarded one two lines apart.
#
# Run: bash hydra-gates/scripts/lib/test_gate_45_to_55_acceptance.sh
#
# ShellCheck: SC2016 is suppressed for this file only. The PHP and JS fixtures
# below are written as single-quoted heredocs on purpose — `$reg`, `$sch`,
# `$this->appConfig` are PHP variables that must reach the fixture VERBATIM.
# Letting the shell expand them would write `  = ->appConfig->...` into the
# file and silently turn every arm into a test of an empty fixture, which is
# the exact "green over nothing" failure this suite exists to catch.
# shellcheck disable=SC2016

set -u

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_scripts="$(cd "${_here}/.." && pwd)"
_runner="${HYDRA_GATES_RUNNER_UNDER_TEST:-${_scripts}/run-hydra-gates.sh}"

# ---------------------------------------------------------------------------
# PREFLIGHT — ajv must be resolvable, or this suite reports GATE DEFECTS that
# are really a WIRING fault, and one of them is a false pass.
#
# Measured 2026-08-09 on a fresh clone of main (c51a225, zero drift): with ajv
# unresolvable, gate-53 fails closed ("ajv not resolvable ... refusing to run
# fail-open"), and FOUR arms of FAMILY D then read as gate defects —
#   D2  removing component + registry entry together : expected PASS, got FAIL
#   D3  a pre-existing orphan stays advisory         : expected PASS, got FAIL
#   D1b the finding NAMES EventRoster                : name never appears
#   D3b the pre-existing orphan surfaces as a WARN   : WARN never appears
# and this was reported upstream as "the suite expects blocking where the gate
# was deliberately made advisory". It does not. The gate is correct.
#
# 🔑 Worse, arm D1 still printed `ok`. It expects FAIL and got FAIL — for a
# completely unrelated reason. That is a FALSE PASS inside the very suite
# built to catch false passes, and it is why this preflight aborts instead of
# letting the run continue with a warning.
#
# ⚠️ `node -e "require('ajv')"` is NOT a valid check on its own: Node resolves
# UPWARD from the cwd, so it can succeed against a node_modules belonging to
# some ancestor directory rather than to the gates package. Resolve it from
# the helpers' own directory — the same place the runner resolves it from —
# and print the ABSOLUTE PATH, because the path is the evidence and the exit
# code is not.
# ---------------------------------------------------------------------------
if ! command -v node >/dev/null 2>&1; then
    echo "WIRING: node is not on PATH." >&2
    echo "        Every gate in this band that shells out to a JS helper would fail" >&2
    echo "        closed, and this suite would report that as a gate defect." >&2
    exit 2
fi
_ajv_at="$(cd "${_scripts}/lib" && node -e "process.stdout.write(require.resolve('ajv'))" 2>/dev/null || true)"
if [ -z "${_ajv_at}" ]; then
    echo "WIRING: ajv is not resolvable from ${_scripts}/lib." >&2
    echo "        gates 22 and 53 fail CLOSED without it, so this suite would report" >&2
    echo "        four gate-53 defects that do not exist — and arm D1 would print 'ok'" >&2
    echo "        for the wrong reason. Refusing to run rather than emit a false verdict." >&2
    echo "        Fix: NODE_PATH=<dir containing ajv> bash ${BASH_SOURCE[0]}" >&2
    exit 2
fi

_failures=0
_ok()  { echo "  ok   — $1"; }
_bad() { echo "  FAIL — $1"; _failures=$((_failures + 1)); }

echo "test_gate_45_to_55_acceptance.sh"
echo "  preflight — ajv resolves to ${_ajv_at}"

_tmp="$(mktemp -d "${TMPDIR:-/tmp}/hydra-g4555.XXXXXX")"
trap 'rm -rf "${_tmp}"' EXIT

_run() {  # _run <appdir> <outfile> [runner args...]
    local app="$1" out="$2"; shift 2
    local logs="${_tmp}/logs.$$.${RANDOM}"
    mkdir -p "${logs}"
    (
        cd "${app}" || exit 1
        HYDRA_GATE_LOG_DIR="${logs}" bash "${_runner}" "$@" . > "${out}" 2>&1
    )
    return $?
}

# The verdict word is not always one token — "NOT APPLICABLE" is two.
_verdict() { grep -oE "^\[gate-$2\] [^:]+: [A-Z]+( [A-Z]+)*( \([a-z]+\))?" "$1" | head -1 | sed 's/^[^:]*: //'; }

_expect() {  # _expect <outfile> <gate> <expected-verdict> <what>
    local got; got="$(_verdict "$1" "$2")"
    if [ "${got}" = "$3" ]; then
        _ok "gate-$2 $4 → $3"
    else
        _bad "gate-$2 $4 → expected '$3', got '${got:-<no line at all>}'"
    fi
}

_commit() { git -C "$1" add -A >/dev/null 2>&1; git -C "$1" -c user.email=t@t -c user.name=t commit -qm "$2" >/dev/null 2>&1; }

# ===========================================================================
# FAMILY A — an unopened scope must render NOT APPLICABLE, never PASS.
# ===========================================================================
_appA="${_tmp}/appA"
mkdir -p "${_appA}/src" "${_appA}/lib/Controller" "${_appA}/lib/Settings"
cat > "${_appA}/src/manifest.json" <<'JSON'
{ "$schema": "https://codeberg.org/Conduction/nextcloud-vue/raw/branch/main/src/schemas/app-manifest-v2.schema.json", "version": "0.1.0", "menu": [], "pages": [] }
JSON
printf 'export default {}\n' > "${_appA}/src/registry.js"
cat > "${_appA}/lib/Controller/ThingController.php" <<'PHP'
<?php
namespace OCA\Fx\Controller;
class ThingController {
    public function index() { return 1; }
}
PHP
printf '{"components":{"schemas":{}}}\n' > "${_appA}/lib/Settings/fx_register.json"
git -C "${_appA}" init -q .
_commit "${_appA}" init
printf 'docs only\n' > "${_appA}/README.md"
_commit "${_appA}" docs

_base="$(git -C "${_appA}" rev-parse HEAD~1)"
_outA="${_tmp}/a.txt"
_run "${_appA}" "${_outA}" --scope-to-diff --base "${_base}"

# The README-only diff opens nothing for any of these. Every one of them used
# to print PASS.
for _g in 45 46 49 50 51 53 54 55; do
    _expect "${_outA}" "${_g}" "NOT APPLICABLE" "on a README-only diff (nothing inspected)"
done

# ⚠️ THIS PAIR ASSERTED THE DEFECT. FLIPPED, DELIBERATELY (.github#401).
#
# It used to read:
#
#   # Gates 47/48 legitimately RAN here — they classified the diff and found no
#   # security change — so PASS is the correct verdict and the arm below is the
#   # anti-widening pair for family A.
#   _expect "${_outA}" 47 "PASS" "classified a real (non-security) diff"
#   _expect "${_outA}" 48 "PASS" "examined a real (no-removal) diff"
#
# The premise is false, and it is false in the same sentence that every other
# gate in family A is being corrected for. **`${_appA}`'s diff is README.md and
# nothing else.** There was no hunk under lib/ or src/ to classify and no
# controller for an attribute to be dropped from — so "they classified the diff
# and found no security change" describes something that did not happen. The
# tree HAS a controller and a registry; the DIFF does not, and these are delta
# gates, so the tree is not their scope.
#
# That is precisely `.github#401(b)`: on this exact shape gates 19, 29 and 61
# declined and named what they had excluded, while 16, 47 and 48 printed a
# green — and that green counted toward "N of N applicable gates ran". Fixing
# 47/48 without flipping this pair is impossible, and flipping it without
# saying so would look like a suite edited to fit a change.
#
# 🔑 Same shape as `#378` being blocked by a required check that asserted the
# contract it superseded: THE ASSERTION WAS THE DEFECT, WRITTEN DOWN.
#
# THE ANTI-WIDENING INTENT IS REAL AND IS NOT LOST — it is rehomed immediately
# below, onto a diff that genuinely contains this gate's subject matter. That
# is what the original pair was reaching for; it was simply attached to an arm
# that could not carry it.
_expect "${_outA}" 47 "NOT APPLICABLE" "on a README-only diff (no lib/ or src/ hunk to classify)"
_expect "${_outA}" 48 "NOT APPLICABLE" "on a README-only diff (no controller to drop an attribute from)"

# THE REHOMED ANTI-WIDENING PAIR. A diff that DOES touch this gate's subject
# matter — a real controller edit, in a real hunk — and is nonetheless not a
# security change and drops no attribute. Both gates must reach a verdict and
# that verdict must be PASS, so the empty-delta guards above cannot have been
# widened into "always decline", which is a strictly worse hole than the PASS
# they replace.
printf '%s\n' '<?php' 'namespace OCA\Fx\Controller;' 'class ThingController {' \
    '    public function index() { return 2; }' \
    '    public function total() { return 3; }' '}' \
    > "${_appA}/lib/Controller/ThingController.php"
_commit "${_appA}" "a real, non-security controller edit"
_outAreal="${_tmp}/a-real.txt"
_run "${_appA}" "${_outAreal}" --scope-to-diff --base "$(git -C "${_appA}" rev-parse HEAD~1)"
_expect "${_outAreal}" 47 "PASS" "classified a REAL controller hunk and found no security change"
_expect "${_outAreal}" 48 "PASS" "examined a REAL controller hunk and found no attribute removal"

# ...and on a run with NO diff at all, 47/48 cannot form a verdict.
_outAfull="${_tmp}/a-full.txt"
_run "${_appA}" "${_outAfull}"
_expect "${_outAfull}" 47 "NOT APPLICABLE" "on a whole-repository run (no change set)"
_expect "${_outAfull}" 48 "NOT APPLICABLE" "on a whole-repository run (no change set)"

# ===========================================================================
# FAMILY B — gate-45 on an app that renders from PHP templates and has no src/.
# ===========================================================================
_appB="${_tmp}/appB"
mkdir -p "${_appB}/templates/settings"
cat > "${_appB}/templates/settings/admin.php" <<'PHP'
<div id="fx-admin">
	<p>Settings</p>
</div>
<style>
.fx-banner { transition: opacity 0.4s ease; }
</style>
PHP
git -C "${_appB}" init -q .
_commit "${_appB}" init

_outB="${_tmp}/b.txt"
_run "${_appB}" "${_outB}"
_expect "${_outB}" 45 "FAIL" "sees a <style> transition in a PHP template with no src/"

# Anti-widening: the same tree with the fallback present must go green, and a
# tree with no motion at all must go green too.
cat > "${_appB}/templates/settings/admin.php" <<'PHP'
<div id="fx-admin">
	<p>Settings</p>
</div>
<style>
.fx-banner { transition: opacity 0.4s ease; }
@media (prefers-reduced-motion: reduce) {
	.fx-banner { transition: none; }
}
</style>
PHP
_commit "${_appB}" "add the reduced-motion fallback"
_outB2="${_tmp}/b2.txt"
_run "${_appB}" "${_outB2}"
_expect "${_outB2}" 45 "PASS" "accepts a template that ships the fallback"

# And a repo that truly renders no markup at all is still NOT APPLICABLE — the
# category must not become unreachable.
_appB3="${_tmp}/appB3"
mkdir -p "${_appB3}/lib"
printf '<?php\n' > "${_appB3}/lib/Nothing.php"
git -C "${_appB3}" init -q .
_commit "${_appB3}" init
_outB3="${_tmp}/b3.txt"
_run "${_appB3}" "${_outB3}"
_expect "${_outB3}" 45 "NOT APPLICABLE" "on a repo with no src/, templates/ or appinfo/templates/"

# ===========================================================================
# FAMILY C — gate-50, both directions.
# ===========================================================================
_appC="${_tmp}/appC"
mkdir -p "${_appC}/lib/Service"

_write_service() {  # _write_service <body>
    cat > "${_appC}/lib/Service/ListingService.php" <<PHP
<?php
namespace OCA\\Fx\\Service;
class ListingService {
$1
}
PHP
}

# C1 — the leak, written with a CLASS CONSTANT app id. This is the shape the
# gate could not see at all: identical code with a quoted 'fx' failed.
_write_service '    public function scope(): string
    {
        $reg = $this->appConfig->getValueString(Application::APP_ID, '"'"'listing_register'"'"', '"'"''"'"');
        return $reg;
    }'
git -C "${_appC}" init -q . 2>/dev/null
_commit "${_appC}" init
_outC1="${_tmp}/c1.txt"
_run "${_appC}" "${_outC1}"
_expect "${_outC1}" 50 "FAIL" "sees an unguarded read whose app id is a class constant"

# C2 — the same leak with a quoted app id. Must still fail (no regression).
_write_service '    public function scope(): string
    {
        $reg = $this->appConfig->getValueString('"'"'fx'"'"', '"'"'listing_register'"'"', '"'"''"'"');
        return $reg;
    }'
_commit "${_appC}" "quoted app id"
_outC2="${_tmp}/c2.txt"
_run "${_appC}" "${_outC2}"
_expect "${_outC2}" 50 "FAIL" "still sees an unguarded read whose app id is a literal"

# C3 — ANTI-WIDENING. A correct COMPOUND guard. The pre-fix regex required a
# closing paren immediately after the empty string, so this shipped as two
# findings and zero defects — and the "fix" it suggested (split into two
# single-key ifs) changes nothing about the code.
_write_service '    public function scope(): array
    {
        $reg = $this->appConfig->getValueString('"'"'fx'"'"', '"'"'listing_register'"'"', '"'"''"'"');
        $sch = $this->appConfig->getValueString('"'"'fx'"'"', '"'"'listing_schema'"'"', '"'"''"'"');
        if ($reg === '"'"''"'"' || $sch === '"'"''"'"') {
            return [];
        }
        return [$reg, $sch];
    }'
_commit "${_appC}" "compound guard"
_outC3="${_tmp}/c3.txt"
_run "${_appC}" "${_outC3}"
_expect "${_outC3}" 50 "PASS" "accepts a correct compound empty-check guard"

# C4 — ANTI-WIDENING. A guard that is not an `if` at all. Verbatim shape from
# larpingapp's SetupController::isProvisioned(); it fails closed.
_write_service '    public function isProvisioned(): bool
    {
        $registerId = $this->appConfig->getValueString(Application::APP_ID, '"'"'register'"'"', '"'"''"'"');
        $schemaMarker = $this->appConfig->getValueString(Application::APP_ID, '"'"'schema_marker'"'"', '"'"''"'"');

        return $registerId !== '"'"''"'"' && $schemaMarker !== '"'"''"'"';
    }'
_commit "${_appC}" "boolean-return guard"
_outC4="${_tmp}/c4.txt"
_run "${_appC}" "${_outC4}"
_expect "${_outC4}" 50 "PASS" "accepts a boolean-return empty-check guard"

# C5 — the opencatalogi#86 shape: one read guarded, the next one two lines
# later NOT. The gate must report the second and only the second.
_write_service '    public function scope(): array
    {
        $reg = $this->appConfig->getValueString('"'"'fx'"'"', '"'"'listing_register'"'"', '"'"''"'"');
        if ($reg === '"'"''"'"') {
            return [];
        }
        $sch = $this->appConfig->getValueString('"'"'fx'"'"', '"'"'listing_schema'"'"', '"'"''"'"');
        return [$reg, $sch];
    }'
_commit "${_appC}" "guarded read + leak"
_outC5="${_tmp}/c5.txt"
_run "${_appC}" "${_outC5}"
if grep -qE "^\[gate-50\][^:]*: FAIL — 1 unsafe" "${_outC5}"; then
    _ok "gate-50 reports exactly the unguarded read of the pair, not both"
else
    _bad "gate-50 on a guarded+unguarded pair → $(grep -E '^\[gate-50\]' "${_outC5}" | head -1)"
fi

# C6 — ANTI-WIDENING. A PHPCS-FORMATTED MULTI-LINE READ.
#
# Verbatim shape from procest lib/Service/AiService.php:580 and :967. Two
# five-line calls plus a blank line put the guard on the ELEVENTH line, one
# outside a window that counted from where the call BEGAN. The constant-app-id
# fix (C1) is what made these reads visible at all, so the window bug arrived
# with it: 3 findings on procest, all three textbook `empty()` guards.
_write_service '    public function writeAudit(): void
    {
        $registerId = $this->appConfig->getValueString(
            Application::APP_ID,
            '"'"'register'"'"',
            '"'"''"'"'
        );
        $schemaId   = $this->appConfig->getValueString(
            Application::APP_ID,
            '"'"'ai_audit_entry_schema'"'"',
            '"'"''"'"'
        );

        if (empty($registerId) === true || empty($schemaId) === true) {
            $this->logger->warning('"'"'AI audit: register or schema ID not configured'"'"');
            return;
        }
    }'
_commit "${_appC}" "multi-line reads with a guard below them"
_outC6="${_tmp}/c6.txt"
_run "${_appC}" "${_outC6}"
_expect "${_outC6}" 50 "PASS" "accepts a PHPCS-formatted multi-line read whose guard follows it"

# C7 — ANTI-WIDENING. The guard on the SAME LINE as the read (procest:710).
_write_service '    public function settings(): array
    {
        return [
            '"'"'ai_api_key_set'"'"' => $this->appConfig->getValueString(Application::APP_ID, '"'"'ai_api_key'"'"', '"'"''"'"') !== '"'"''"'"',
        ];
    }'
_commit "${_appC}" "same-line emptiness check"
_outC7="${_tmp}/c7.txt"
_run "${_appC}" "${_outC7}"
_expect "${_outC7}" 50 "PASS" "accepts an emptiness check written on the read's own line"

# C8 — the reverse control for C6/C7: the SAME multi-line shape with the guard
# DELETED must still fail. Without this, C6 and C7 could be satisfied by a
# window so wide the gate can no longer find anything.
_write_service '    public function writeAudit(): void
    {
        $registerId = $this->appConfig->getValueString(
            Application::APP_ID,
            '"'"'register'"'"',
            '"'"''"'"'
        );

        $this->objectService->saveObject($registerId, []);
    }'
_commit "${_appC}" "multi-line read with no guard at all"
_outC8="${_tmp}/c8.txt"
_run "${_appC}" "${_outC8}"
_expect "${_outC8}" 50 "FAIL" "still fails a multi-line read with no guard anywhere"

# C9 — THE BOUNDARY, MOVED DELIBERATELY AND WITH THE NUMBER IN FRONT OF US.
#
# The previous revision of C9/C10 encoded the boundary as the APP ID'S
# SPELLING: a variable app id was a measured blind spot (PASS), a class
# constant was caught (FAIL). C10's own comment named the condition for
# changing it — "if someone later teaches this gate to tell a scope decision
# from a read-out, this is the arm to change" — and that is what happened on
# 2026-08-12.
#
# The old boundary was in the wrong place. Measured over 12 repos, accepting a
# variable app id adds:
#
#     softwarecatalog  +47 new, 47 of 47 in `'key' => ...` position
#     docudesk         + 1 new,  1 of  1 in `'key' => ...` position
#     opencatalogi     +16 new,  0 of 16 in `'key' => ...` position
#
# The noise is not caused by the app id being a variable — it is caused by the
# read sitting in an ARRAY-LITERAL VALUE POSITION, and the two populations
# separate perfectly on that one syntactic fact. Meanwhile the 16 that are NOT
# read-outs are `listing_register` / `listing_schema` / `catalog_register` /
# `publication_schema` read unguarded via `$this->appName` — the exact
# opencatalogi#86 defect this gate was BUILT for, in opencatalogi, reported
# PASS for its whole life.
#
# So the discriminator is now the POSITION, not the spelling, and it applies
# uniformly to every app-id form. C9 and C10 below assert that uniformity;
# C11 asserts the defect the old boundary was hiding.
#
# ⚠️ PRICE OF THIS CHANGE, STATED: 21 findings the fleet reports today stop
# failing (softwarecatalog 17, pipelinq 4). All 21 are `'key' => ...` reads.
# They are not deleted — they are written to <log>.notes, and C10 asserts that.
_write_service '    public function readouts(): array
    {
        $app = '"'"'fx'"'"';
        return [
            '"'"'sendgridApiKey'"'"' => $this->config->getValueString($app, '"'"'email_sendgrid_api_key'"'"', '"'"''"'"'),
            '"'"'mailgunApiKey'"'"'  => $this->config->getValueString($this->appName, '"'"'email_mailgun_api_key'"'"', '"'"''"'"'),
        ];
    }'
_commit "${_appC}" "settings read-outs with a variable app id"
_outC9="${_tmp}/c9.txt"
_run "${_appC}" "${_outC9}"
_expect "${_outC9}" 50 "PASS" "does not fail settings read-outs in array-literal value position (no guard can be written there)"

# C10 — THE EXEMPTION MUST NOT BE A SILENCE, and it must not depend on how the
# app id is spelled. Same read-out written with a CLASS CONSTANT: also demoted
# (uniformity), and BOTH forms must appear in the .notes sidecar by name.
#
# An exemption that produces silence is how a gate's quiet gets believed —
# gate-7 reported 0 IDORs across 18 apps while 167 sat in the tree. So the
# demotion is asserted to be *legible*: file, line and key, in a file a
# reviewer can read.
_g50notes="${_tmp}/g50notes"
mkdir -p "${_g50notes}"
_write_service '    public function readouts(): array
    {
        return [
            '"'"'sendgridApiKey'"'"' => $this->config->getValueString(Application::APP_ID, '"'"'email_sendgrid_api_key'"'"', '"'"''"'"'),
            '"'"'mailgunApiKey'"'"'  => $this->config->getValueString($this->appName, '"'"'email_mailgun_api_key'"'"', '"'"''"'"'),
        ];
    }'
_commit "${_appC}" "same read-out, constant and variable app id side by side"
_outC10="${_tmp}/c10.txt"
(
    cd "${_appC}" || exit 1
    HYDRA_GATE_LOG_DIR="${_g50notes}" bash "${_runner}" . > "${_outC10}" 2>&1
)
_expect "${_outC10}" 50 "PASS" "demotes the read-out identically whether the app id is a constant or a variable"
if [ -s "${_g50notes}/hydra-gate-security-config-fail-mode.log.notes" ] \
   && grep -qF 'email_sendgrid_api_key' "${_g50notes}/hydra-gate-security-config-fail-mode.log.notes" \
   && grep -qF 'email_mailgun_api_key' "${_g50notes}/hydra-gate-security-config-fail-mode.log.notes"; then
    _ok "gate-50 RECORDS both demoted read-outs by key in .notes — demoted, not silent"
else
    _bad "gate-50 demoted the read-outs but left no note: $(wc -c < "${_g50notes}/hydra-gate-security-config-fail-mode.log.notes" 2>/dev/null || echo 'no file')"
fi

# C11 — THE DEFECT THE OLD BOUNDARY HID. Verbatim shape from opencatalogi
# CatalogiService / DirectoryService / PublicationService: the app id is
# `$this->appName`, the value lands in a LOCAL VARIABLE, and nothing guards it.
# Sixteen of these live in opencatalogi today and every one reported PASS.
# This is the arm that must fail, or the whole change bought nothing.
_write_service '    public function scope(): array
    {
        $listingRegister = $this->config->getValueString($this->appName, '"'"'listing_register'"'"', '"'"''"'"');
        $listingSchema   = $this->config->getValueString($this->appName, '"'"'listing_schema'"'"', '"'"''"'"');
        return [$listingRegister, $listingSchema];
    }'
_commit "${_appC}" "opencatalogi#86 shape with a variable app id"
_outC11="${_tmp}/c11.txt"
_run "${_appC}" "${_outC11}"
_expect "${_outC11}" 50 "FAIL" "sees the opencatalogi#86 defect written with a \$this->appName app id"

# C12 — ANTI-WIDENING for C11. The SAME variable-app-id reads, correctly
# guarded, must go green. Widening a matcher is how a gate starts crying wolf;
# this arm proves the new shape does not fire on correct code.
_write_service '    public function scope(): array
    {
        $listingRegister = $this->config->getValueString($this->appName, '"'"'listing_register'"'"', '"'"''"'"');
        $listingSchema   = $this->config->getValueString($this->appName, '"'"'listing_schema'"'"', '"'"''"'"');
        if ($listingRegister === '"'"''"'"' || $listingSchema === '"'"''"'"') {
            return [];
        }
        return [$listingRegister, $listingSchema];
    }'
_commit "${_appC}" "variable app id, correctly guarded"
_outC12="${_tmp}/c12.txt"
_run "${_appC}" "${_outC12}"
_expect "${_outC12}" 50 "PASS" "accepts a correctly-guarded read whose app id is a variable"

# C13 — the exemption is about an ARRAY KEY, not about the `=>` token. A
# single-expression arrow closure has `)` before its `=>`, so it is NOT a
# read-out and stays reported. Pins the exemption's edge so it cannot quietly
# widen into "anything after a fat arrow".
_write_service '    public function lazyScope(): callable
    {
        return fn() => $this->config->getValueString($this->appName, '"'"'listing_register'"'"', '"'"''"'"');
    }'
_commit "${_appC}" "arrow closure returning an unguarded read"
_outC13="${_tmp}/c13.txt"
_run "${_appC}" "${_outC13}"
_expect "${_outC13}" 50 "FAIL" "does not mistake an arrow closure's => for an array key"

# C14 / C15 — A COMMENT MUST NEITHER CONSUME THE WINDOW NOR SATISFY IT (#415).
#
# One cause, two failures pointing opposite ways, so both arms are needed: a
# fix for either one alone can be had by moving the window boundary, and that
# makes the other worse.
#
# C14 (was a FALSE POSITIVE): a textbook guard, reported unsafe because twelve
# lines of ordinary explanation sat between it and the call. 8 of gate-50's 16
# opencatalogi findings were this shape. The gate penalised the DOCUMENTED fix
# and passed the undocumented one — an author who deletes the comment goes
# green having changed nothing about the code's safety.
_write_service '    public function listing(): array
    {
        $reg = $this->config->getValueString(Application::APP_ID, '"'"'listing_register'"'"', '"'"''"'"');
        // We deliberately do not fail hard on a missing register: it is
        // optional in single-tenant installs, the directory sync job re-runs
        // nightly, and a missing value therefore self-heals within a day.
        // See ADR-012 for the full rationale, and the migration plan that
        // removes this branch entirely once the 3.x provisioning path has
        // landed in every deployment we currently support. Until then the
        // empty case must return an empty listing rather than raise, because
        // the public directory endpoint is unauthenticated and a raise there
        // is an information leak of its own. Twelve lines is not an unusual
        // amount of explanation for a decision with that many moving parts,
        // and none of it changes what the code below does.
        //
        // The actual guard follows.
        if ($reg === '"'"''"'"') {
            return [];
        }

        return $this->load($reg);
    }'
_commit "${_appC}" "a guarded read with a long comment between read and guard"
_outC14="${_tmp}/c14.txt"
_run "${_appC}" "${_outC14}"
_expect "${_outC14}" 50 "PASS" "a comment between the read and its guard does not consume the window"

# C15 (was a FALSE NEGATIVE, and the more serious half): an unguarded read of
# an api_token reported CLEAN because the TODO above it happened to contain
# the words the guard regex looks for. A comment STATING THE DEBT satisfied
# the gate that exists to collect it — the same defect gate 19 was fixed for,
# never looked for here. Note the fixture's comment contains BOTH a `throw
# new` and a `=== ''`, so it exercises two of the six guard arms at once.
_write_service '    public function push(): void
    {
        $tok = $this->config->getValueString(Application::APP_ID, '"'"'api_token'"'"', '"'"''"'"');
        // TODO: we should throw new RuntimeException here when this is empty,
        // and compare $tok === '"'"''"'"' before use. Not done yet.
        $this->client->post($tok);
    }'
_commit "${_appC}" "an unguarded read whose TODO names the missing guard"
_outC15="${_tmp}/c15.txt"
_run "${_appC}" "${_outC15}"
_expect "${_outC15}" 50 "FAIL" "a comment naming the missing guard does not satisfy the gate"

# C16 — the string-safety control for C14/C15. Comment stripping must not be a
# naive split: `'https://x'` is a URL inside a string literal, not a comment,
# and `#[PublicPage]` is a PHP 8 attribute. If either is mis-stripped the
# guard on the following line is destroyed and this arm fails, which is how a
# stripper bug shows up as a finding rather than as silence.
_write_service '    #[PublicPage]
    public function docs(): string
    {
        $url = '"'"'https://example.org//docs#anchor'"'"';
        $reg = $this->config->getValueString(Application::APP_ID, '"'"'listing_register'"'"', '"'"''"'"');
        if ($reg === '"'"''"'"') {
            return $url;
        }

        return $this->load($reg);
    }'
_commit "${_appC}" "a guarded read alongside a URL literal and an attribute"
_outC16="${_tmp}/c16.txt"
_run "${_appC}" "${_outC16}"
_expect "${_outC16}" 50 "PASS" "a // inside a string literal and a #[Attribute] are not comments"

# ===========================================================================
# FAMILY D — gate-53 must block the PR that CREATES larpingapp#286.
#
# `EventRoster` was registered in src/registry.js, resolvable, and named by no
# manifest position, so the event check-in surface had no entry point. When
# that defect was reintroduced exactly, gate-53 printed PASS. Direction 1 of
# the registry cross-reference stays advisory for LEGACY orphans — the gate
# cannot tell "wire it" from "delete it" — but when the DIFF ITSELF removed
# the last reference, it can, and that is the case worth blocking.
# ===========================================================================
_appD="${_tmp}/appD"
mkdir -p "${_appD}/src"
cat > "${_appD}/src/manifest.json" <<'JSON'
{
  "$schema": "https://codeberg.org/Conduction/nextcloud-vue/raw/branch/main/src/schemas/app-manifest-v2.schema.json",
  "version": "0.1.0",
  "menu": [{ "id": "EventDetail", "label": "Events", "icon": "Calendar", "route": "EventDetail", "order": 10 }],
  "pages": [
    {
      "id": "EventDetail",
      "type": "detail",
      "route": "/events/:id",
      "title": "Event",
      "config": { "sidebar": { "tabs": [
        { "id": "checkin", "label": "Check-in", "icon": "AccountCheck", "component": "EventRoster" }
      ] } }
    }
  ]
}
JSON
cat > "${_appD}/src/registry.js" <<'JS'
import EventRoster from './views/EventRoster.vue'

export default {
	EventRoster: { kind: 'section', component: EventRoster },
}
JS
mkdir -p "${_appD}/src/views"
printf '<template><div /></template>\n' > "${_appD}/src/views/EventRoster.vue"
git -C "${_appD}" init -q .
_commit "${_appD}" init
_baseD="$(git -C "${_appD}" rev-parse HEAD)"

# D1 — remove the ONLY reference, keep the registry entry. This is #286.
python3 - "${_appD}/src/manifest.json" <<'PY'
import json, sys
p = sys.argv[1]
raw = open(p).read()
old = '        { "id": "checkin", "label": "Check-in", "icon": "AccountCheck", "component": "EventRoster" }\n'
assert old in raw, "PLANT ANCHOR MISSING — the fixture changed, fix the test not the anchor"
open(p, 'w').write(raw.replace(old, '', 1))
json.load(open(p))
PY
_commit "${_appD}" "drop the check-in tab"
_outD1="${_tmp}/d1.txt"
_run "${_appD}" "${_outD1}" --scope-to-diff --base "${_baseD}"
_expect "${_outD1}" 53 "FAIL" "blocks the PR that removes the last reference to a registered component"
if grep -q "EventRoster" "${_outD1}"; then
    _ok "gate-53 NAMES the orphaned component"
else
    _bad "gate-53 failed without naming EventRoster"
fi

# D2 — ANTI-WIDENING. Removing BOTH sides is a legitimate retirement.
git -C "${_appD}" checkout -q -B d2 "${_baseD}"
python3 - "${_appD}/src/manifest.json" "${_appD}/src/registry.js" <<'PY'
import json, sys
m, r = sys.argv[1], sys.argv[2]
raw = open(m).read()
old = '        { "id": "checkin", "label": "Check-in", "icon": "AccountCheck", "component": "EventRoster" }\n'
assert old in raw, "PLANT ANCHOR MISSING (manifest)"
open(m, 'w').write(raw.replace(old, '', 1))
json.load(open(m))
js = open(r).read()
oldj = "\tEventRoster: { kind: 'section', component: EventRoster },\n"
assert oldj in js, "PLANT ANCHOR MISSING (registry)"
open(r, 'w').write(js.replace(oldj, '', 1))
PY
_commit "${_appD}" "retire the check-in surface entirely"
_outD2="${_tmp}/d2.txt"
_run "${_appD}" "${_outD2}" --scope-to-diff --base "${_baseD}"
_expect "${_outD2}" 53 "PASS" "accepts removing the component and its registry entry together"

# D3 — ANTI-WIDENING. A pre-existing orphan is still advisory, not blocking.
# Without this arm the fix would be indistinguishable from promoting
# direction 1 wholesale, which would light up every app carrying legacy debt.
_appD3="${_tmp}/appD3"
mkdir -p "${_appD3}/src/views"
cat > "${_appD3}/src/manifest.json" <<'JSON'
{ "$schema": "https://codeberg.org/Conduction/nextcloud-vue/raw/branch/main/src/schemas/app-manifest-v2.schema.json", "version": "0.1.0", "menu": [], "pages": [] }
JSON
cat > "${_appD3}/src/registry.js" <<'JS'
import Orphan from './views/Orphan.vue'

export default {
	Orphan: { kind: 'section', component: Orphan },
}
JS
printf '<template><div /></template>\n' > "${_appD3}/src/views/Orphan.vue"
git -C "${_appD3}" init -q .
_commit "${_appD3}" init
_outD3="${_tmp}/d3.txt"
_run "${_appD3}" "${_outD3}"
_expect "${_outD3}" 53 "PASS" "leaves a PRE-EXISTING orphan advisory (WARN), not blocking"
if grep -qE '^\[gate-53\].*WARN finding' "${_outD3}"; then
    _ok "gate-53 still SURFACES the pre-existing orphan as a WARN"
else
    _bad "gate-53 swallowed the pre-existing orphan entirely"
fi

# ===========================================================================
# FAMILY E — gate-52: a crashed helper is WIRING, never a finding.
#
# The runner read `_cwr_fail=$?` straight off the helper. An exit status is one
# byte and it is also how Python reports a traceback, so a dead checker
# reported `FAIL — 1 custom-widget finding(s)` — an actionable-looking finding
# with nothing behind it, pointing at a widget that does not exist. Same
# lossy-channel shape as #209, where 266 findings were reported as 10.
#
# Driven by copying the package and injecting a `raise` into the helper's
# main(), then pointing the runner-under-test at the copy. The copy is why
# this arm can exist at all: the shipped helper must not be edited to test it.
# ===========================================================================
_pkg="${_tmp}/pkg"
mkdir -p "${_pkg}"
cp -R "${_scripts}" "${_pkg}/scripts"
_broken="${_pkg}/scripts/lib/check_custom_widget_ratchet.py"
python3 - "${_broken}" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
old = "def main(argv):"
assert old in s, "MUTATION ANCHOR MISSING — check_custom_widget_ratchet.py no longer defines main(argv)"
s = s.replace(old, 'def main(argv):\n    raise RuntimeError("simulated helper crash")\n\n\ndef _unreachable_main(argv):', 1)
open(p, "w").write(s)
PY

_appE="${_tmp}/appE"
mkdir -p "${_appE}/src"
printf "export default {\n\tThing: { kind: 'widget', component: 1 },\n}\n" > "${_appE}/src/registry.js"
git -C "${_appE}" init -q .
_commit "${_appE}" init

_outE="${_tmp}/e.txt"
_saved_runner="${_runner}"
_runner="${_pkg}/scripts/run-hydra-gates.sh"
_run "${_appE}" "${_outE}"
_runner="${_saved_runner}"

_expect "${_outE}" 52 "SKIPPED (wiring)" "reports a crashed helper as wiring, not as a finding"
if grep -qE '^\[gate-52\][^:]*: FAIL' "${_outE}"; then
    _bad "gate-52 turned a helper crash into a FAIL with a fabricated finding count"
else
    _ok "gate-52 invents no finding count when the helper did not finish"
fi

# ANTI-WIDENING for family E: the SAME fixture with the real helper must still
# catch its planted true positive (a kind:"widget" entry with no _note).
_outE2="${_tmp}/e2.txt"
_run "${_appE}" "${_outE2}"
_expect "${_outE2}" 52 "FAIL" "still catches a kind:\"widget\" entry with no _note"

# ===========================================================================
# FAMILY F — A CRASHED INTERPRETER MUST NOT PRODUCE A VERDICT.
#
# A planted true positive only fires WHEN THE GATE RUNS, so no arm above can
# see this. Measured 2026-08-08 on a tree carrying real findings, with a
# `python3` on PATH that exits 1 on every call: EIGHT of these eleven gates
# printed PASS. The worst was gate-46, which reported PASS over the 277
# unresolved @spec findings — 104 distinct targets — it had reported one run
# earlier on the same files. Gates 45/49/50 discarded the status with
# `2>/dev/null`; gates 47/51/54/55 with `|| true`; gate-52 read the count off
# the exit byte, so a traceback became `FAIL — 1 custom-widget finding(s)`.
#
# `_a` is a fake `python3` earlier on PATH. Both directions are asserted: the
# same fixture with a working interpreter must produce real verdicts, or this
# family would be satisfied by a runner that skipped everything always.
# ===========================================================================
_appF="${_tmp}/appF"
mkdir -p "${_appF}/src/manifest.d" "${_appF}/lib/Controller" "${_appF}/lib/Service" \
         "${_appF}/lib/Settings" "${_appF}/templates"
cat > "${_appF}/src/manifest.json" <<'JSON'
{ "$schema": "https://codeberg.org/Conduction/nextcloud-vue/raw/branch/main/src/schemas/app-manifest-v2.schema.json",
  "version": "0.1.0", "menu": [], "pages": [] }
JSON
printf "export default {}\n" > "${_appF}/src/registry.js"
printf '<template><div /></template>\n<style scoped>\n.x { transition: all .3s; }\n</style>\n' \
    > "${_appF}/src/Thing.vue"
cat > "${_appF}/lib/Controller/ThingController.php" <<'PHP'
<?php
namespace OCA\Fx\Controller;
class ThingController {
    /** @spec openspec/specs/no-such-thing/spec.md#requirement-nope */
    public function destroy(string $id) {
        $this->objectService->deleteObject($id);
        return 1;
    }
}
PHP
cat > "${_appF}/lib/Service/ListingService.php" <<'PHP'
<?php
namespace OCA\Fx\Service;
class ListingService {
    public function scope(): string
    {
        return $this->appConfig->getValueString('fx', 'listing_register', '');
    }
}
PHP
cat > "${_appF}/lib/Settings/fx_register.json" <<'JSON'
{ "components": { "schemas": { "thing": { "properties": {
  "bare": { "type": "string" },
  "rel": { "type": "string", "format": "uuid", "title": "Rel", "description": "Reference to the related thing object" }
} } } } }
JSON
git -C "${_appF}" init -q .
_commit "${_appF}" init

# Working interpreter: these gates must produce REAL verdicts on this tree.
_outF="${_tmp}/f.txt"
_run "${_appF}" "${_outF}"
_real=0
for _g in 45 46 49 50 51 54; do
    grep -qE "^\[gate-${_g}\][^:]*: FAIL" "${_outF}" && _real=$((_real + 1))
done
if [ "${_real}" -ge 5 ]; then
    _ok "with a working interpreter the fixture yields ${_real} real FAIL verdicts (the thing a crash must not erase)"
else
    _bad "fixture produced only ${_real} FAIL verdicts — family F would prove nothing"
fi

# Broken interpreter: every one of them must say WIRING, and none may PASS.
_fakebin="${_tmp}/fakebin"
mkdir -p "${_fakebin}"
printf '#!/bin/sh\necho "python3: simulated interpreter failure" >&2\nexit 1\n' > "${_fakebin}/python3"
chmod +x "${_fakebin}/python3"
_outF2="${_tmp}/f2.txt"
(
    cd "${_appF}" || exit 1
    _l="${_tmp}/logs.crash"; mkdir -p "${_l}"
    PATH="${_fakebin}:${PATH}" HYDRA_GATE_LOG_DIR="${_l}" bash "${_runner}" . > "${_outF2}" 2>&1
)
_green_over_crash=""
for _g in 45 46 47 48 49 50 51 52 54 55; do
    if grep -qE "^\[gate-${_g}\][^:]*: (PASS|FAIL)" "${_outF2}"; then
        _green_over_crash="${_green_over_crash} ${_g}"
    fi
done
if [ -z "${_green_over_crash}" ]; then
    _ok "with python3 exiting 1, no gate in the band produced a verdict — all reported wiring or na"
else
    _bad "gate(s)${_green_over_crash} produced a PASS/FAIL verdict although their checker never ran"
fi
if grep -qE "^\[gate-46\][^:]*: SKIPPED \(wiring\)" "${_outF2}"; then
    _ok "gate-46 says SKIPPED (wiring) rather than PASS over findings it cannot see"
else
    _bad "gate-46 on a dead interpreter → $(grep -E '^\[gate-46\]' "${_outF2}" | head -1)"
fi

# ===========================================================================
# FAMILY G — gate-49, the SAME defect family C caught in gate-50 (#415).
#
# gate-50's window was raw file text. gate-49's method BODY was raw file text.
# Different mechanism, one cause: prose is made of the same bytes as code, so
# a comment answered both of gate-49's questions — "is there a catch of a
# tracked exception?" and "does this method call a risky service method?".
#
# Four arms, because a fix for either direction alone is available by
# loosening or tightening the regex, and each of those makes the other worse.
# G1 is the POSITIVE CONTROL and it is not decoration: it is the arm that
# proves the other three are measuring a live gate rather than a silent one.
# ===========================================================================
_appG="${_tmp}/appG"
mkdir -p "${_appG}/lib/Controller"

_write_controller() {  # _write_controller <body>
    cat > "${_appG}/lib/Controller/ThingController.php" <<PHP
<?php
namespace OCA\\Fx\\Controller;
class ThingController
{
$1
}
PHP
}

# G1 — POSITIVE CONTROL. An unhandled call to a known-throwy service method.
# If this arm ever prints PASS, every arm below it is measuring nothing and
# their greens are green over a dead gate.
_write_controller '    public function destroy(int $id)
    {
        return $this->objectService->deleteObject($id);
    }'
git -C "${_appG}" init -q . 2>/dev/null
_commit "${_appG}" "an unhandled call to a throwy service method"
_outG1="${_tmp}/g1.txt"
_run "${_appG}" "${_outG1}"
_expect "${_outG1}" 49 "FAIL" "POSITIVE CONTROL — an unhandled throwy service call is a finding"

# G2 — THE FALSE NEGATIVE, and the serious half. The identical unhandled call,
# with a TODO above it naming the catch that is missing. The gate matched
# `catch\s*\(\s*…DoesNotExistException` against the raw body and accepted the
# comment as the handler. A comment STATING THE DEBT satisfied the gate that
# exists to collect it — the shape gate 19 was fixed for, and gate 50 in #415.
_write_controller '    public function destroy(int $id)
    {
        // TODO: we should catch (DoesNotExistException $e) here and translate
        // it to a 404 JSONResponse. Not done yet — tracked separately.
        return $this->objectService->deleteObject($id);
    }'
_commit "${_appG}" "the same unhandled call, with a TODO naming the missing catch"
_outG2="${_tmp}/g2.txt"
_run "${_appG}" "${_outG2}"
_expect "${_outG2}" 49 "FAIL" "a comment naming the missing catch does not satisfy the gate"

# G3 — THE FALSE POSITIVE, and the one that erodes the gate. A method that
# calls nothing riskier than a renderer, carrying a note about the call it no
# longer makes. `$this->objectService->deleteObject(` was collected from the
# comment, so the REMOVAL NOTE scored as the removed call: the better the
# documentation, the redder the repo (#230's shape, one gate over).
_write_controller '    public function index()
    {
        // This endpoint used to call $this->objectService->deleteObject($id)
        // directly. It no longer does; deletion moved to destroy().
        return $this->renderer->toArray();
    }'
_commit "${_appG}" "a method whose comment describes a call it does not make"
_outG3="${_tmp}/g3.txt"
_run "${_appG}" "${_outG3}"
_expect "${_outG3}" 49 "PASS" "a comment describing a removed call is not that call"

# G4 — THE ANTI-WIDENING PAIR, and the reason the mask keeps the docblock.
# `@throws` lives in a comment BY DESIGN: it is the author's declaration, not
# incidental prose. A fix that masked the docblock along with everything else
# would close G2 and turn every intentionally-propagating method in the fleet
# into a finding — trading a false negative for a fleet of false positives.
# Both suppressions must survive.
_write_controller '    /**
     * @throws \\OCP\\AppFramework\\Db\\DoesNotExistException
     */
    public function destroy(int $id)
    {
        return $this->objectService->deleteObject($id);
    }

    public function purge(int $id)
    {
        try {
            return $this->objectService->deleteObject($id);
        } catch (\\OCP\\AppFramework\\Db\\DoesNotExistException $e) {
            return 404;
        }
    }'
_commit "${_appG}" "a real @throws and a real try/catch"
_outG4="${_tmp}/g4.txt"
_run "${_appG}" "${_outG4}"
_expect "${_outG4}" 49 "PASS" "a real @throws docblock and a real catch still suppress"

# G5 — the brace-walk control. The body span is now measured on the mask, so a
# `{` inside a string literal cannot mis-balance the walk and hand the method
# a span of code it does not contain. The call here is genuinely unhandled, so
# the arm asserts the finding SURVIVES the mask rather than being eaten by it
# — a stripper that swallows code shows up here as a PASS.
_write_controller '    public function destroy(int $id)
    {
        $fmt = '"'"'{ unbalanced'"'"';
        return $this->objectService->deleteObject($id);
    }'
_commit "${_appG}" "an unhandled call below a brace inside a string literal"
_outG5="${_tmp}/g5.txt"
_run "${_appG}" "${_outG5}"
_expect "${_outG5}" 49 "FAIL" "a { inside a string literal does not derail the body walk"

# ===========================================================================
# FAMILY H — gate-48: a comment is not a CSRF token (#415).
#
# This file already predicted the defect and filed it as a hypothetical. The
# runner's own note above `_csrf_callers_helper` reads:
#
#     "the cheapest way to green would have been a cosmetic edit under src/
#      containing the word `requesttoken`: exactly the prose-satisfaction
#      #191 warns against."
#
# It was not a hypothetical. And it is worse than one missed finding: the
# signal count SHORT-CIRCUITS the caller-state check built as the mitigation
# for this exact shape, so one comment skips the guard AND its backup.
#
# ⚠️ THE FIXTURE FILE MUST NOT SIT DIRECTLY IN src/. The gate's pathspec is
# `src/**/*.vue`, and a plain git pathspec's `*` matches `/` too — so the
# glob requires a SECOND slash and `src/Del.vue` is invisible to it. The
# first cut of this family put the file there, and both arms printed FAIL:
# the "before" and "after" agreed, for the reason that neither had measured
# anything. A component directory is also what real apps ship.
# ===========================================================================
_appH="${_tmp}/appH"
mkdir -p "${_appH}/lib/Controller" "${_appH}/src/components"

cat > "${_appH}/lib/Controller/ThingController.php" <<'PHP'
<?php
namespace OCA\Fx\Controller;
class ThingController
{
    /**
     * @NoCSRFRequired
     */
    public function create() { return 1; }
}
PHP
# An UNPROTECTED mutating caller, so the caller-state branch has something to
# find. Without this the fixture passes for a legitimate reason and the arm
# below cannot tell a repaired gate from a satisfied one.
cat > "${_appH}/src/components/Del.vue" <<'VUE'
<script>
export default { methods: { async del(id) {
  await fetch(`/api/things/${id}`, { method: 'DELETE', headers: {} })
} } }
</script>
VUE
git -C "${_appH}" init -q . 2>/dev/null
_commit "${_appH}" "a controller with @NoCSRFRequired and an unprotected caller"
_baseH="$(git -C "${_appH}" rev-parse HEAD)"

# H1 — THE FALSE NEGATIVE. Drop the annotation; the ONLY frontend change is a
# comment saying the token has NOT been added.
cat > "${_appH}/lib/Controller/ThingController.php" <<'PHP'
<?php
namespace OCA\Fx\Controller;
class ThingController
{
    public function create() { return 1; }
}
PHP
cat > "${_appH}/src/components/Del.vue" <<'VUE'
<script>
export default { methods: { async del(id) {
  // TODO: this call still needs a requesttoken header. Not done yet.
  await fetch(`/api/things/${id}`, { method: 'DELETE', headers: {} })
} } }
</script>
VUE
_commit "${_appH}" "drop @NoCSRFRequired; add only a TODO naming the missing header"
_outH1="${_tmp}/h1.txt"
_run "${_appH}" "${_outH1}" --scope-to-diff --base "${_baseH}"
_expect "${_outH1}" 48 "FAIL" "a comment naming the missing token is not a CSRF co-change"

# H2 — THE ANTI-WIDENING PAIR. The same removal, with a REAL header added.
# A fix that counted no added line at all would close H1 and fail here.
cat > "${_appH}/src/components/Del.vue" <<'VUE'
<script>
export default { methods: { async del(id) {
  await fetch(`/api/things/${id}`, { method: 'DELETE', headers: { requesttoken: OC.requestToken } })
} } }
</script>
VUE
_commit "${_appH}" "the same removal, with a real requesttoken header added"
_outH2="${_tmp}/h2.txt"
_run "${_appH}" "${_outH2}" --scope-to-diff --base "${_baseH}"
_expect "${_outH2}" 48 "PASS" "a real added requesttoken header is still a co-change signal"

# ===========================================================================
# FAMILY I — gate-48: `src/**/*.js` CANNOT SEE `src/thing.js` (#428).
#
# FAMILY H's own header warns about this and works AROUND it ("the fixture
# file must not sit directly in src/"). The workaround was correct and the
# blind spot was left in the gate. This family removes it.
#
# In a PLAIN git pathspec there is no `**` operator — it is two ordinary
# `*`s, and a plain `*` matches `/`. `src/**/*.js` therefore REQUIRES a
# second slash, and every file at `src/foo.js` was invisible to the signal
# scan. Reproduced 2026-08-13 on c26f9a3:
#
#   git diff --name-only HEAD~1...HEAD -- 'src/**/*.js'          -> (empty)
#   git diff --name-only HEAD~1...HEAD -- ':(glob)src/**/*.js'   -> src/thing.js
#
# DIRECTION. A missed signal makes the count 0, which routes to the
# caller-state check — the conservative branch. So this was never letting a
# CSRF removal through; it made the count a FLOOR rather than a count, and
# the NOTE gate-48 prints about the frontend diff could be wrong about what
# it had read. Fixing it therefore REMOVES a finding in I1, and the arm is
# built so that the removal is unambiguous: the diff really does add a real
# `requesttoken` header, which is exactly the co-change this gate asks for.
#
# I1 is the evidence arm (FAIL on origin/main, PASS here).
# I2 and I3 are CONTROLS: they hold the same verdict before and after.
# ===========================================================================
_appI="${_tmp}/appI"
mkdir -p "${_appI}/lib/Controller" "${_appI}/src/components" "${_appI}/src/sub"

cat > "${_appI}/lib/Controller/ThingController.php" <<'PHP'
<?php
namespace OCA\Fx\Controller;
class ThingController
{
    /**
     * @NoCSRFRequired
     */
    public function create() { return 1; }
}
PHP
# The same unprotected mutating caller FAMILY H uses, and for the same reason:
# without it the fallback branch has nothing to find and every arm below
# passes for a legitimate reason, which cannot distinguish a repaired gate
# from a satisfied one.
cat > "${_appI}/src/components/Del.vue" <<'VUE'
<script>
export default { methods: { async del(id) {
  await fetch(`/api/things/${id}`, { method: 'DELETE', headers: {} })
} } }
</script>
VUE
printf '// placeholder\n' > "${_appI}/src/thing.js"
printf '// placeholder\n' > "${_appI}/src/sub/thing.js"
git -C "${_appI}" init -q . 2>/dev/null
_commit "${_appI}" "a controller with @NoCSRFRequired and an unprotected caller"
_baseI="$(git -C "${_appI}" rev-parse HEAD)"

cat > "${_appI}/lib/Controller/ThingController.php" <<'PHP'
<?php
namespace OCA\Fx\Controller;
class ThingController
{
    public function create() { return 1; }
}
PHP

# I1 — THE DEFECT. The added signal sits DIRECTLY under src/.
cat > "${_appI}/src/thing.js" <<'JS'
import axios from '@nextcloud/axios'
export const create = (b) => axios.post('/api/things', b, { headers: { requesttoken: OC.requestToken } })
JS
_commit "${_appI}" "drop @NoCSRFRequired; add a real requesttoken in src/thing.js"
_outI1="${_tmp}/i1.txt"
_run "${_appI}" "${_outI1}" --scope-to-diff --base "${_baseI}"
_expect "${_outI1}" 48 "PASS" "a CSRF signal added DIRECTLY under src/ is seen (src/thing.js)"

# I2 — CONTROL. The identical signal one directory down. This is the arm the
# old pathspec could already see, so it holds its verdict across the fix; it
# is here so that a fix which handled ONLY the top level would be visible.
git -C "${_appI}" checkout -q "${_baseI}" -- src/thing.js
cat > "${_appI}/src/sub/thing.js" <<'JS'
import axios from '@nextcloud/axios'
export const create = (b) => axios.post('/api/things', b, { headers: { requesttoken: OC.requestToken } })
JS
_commit "${_appI}" "the same signal, one directory down"
_outI2="${_tmp}/i2.txt"
_run "${_appI}" "${_outI2}" --scope-to-diff --base "${_baseI}"
_expect "${_outI2}" 48 "PASS" "control: the same signal in src/sub/thing.js is still seen"

# I3 — ANTI-WIDENING CONTROL. A top-level src/ file that is touched but adds
# NO signal must not satisfy the gate. Without this arm, "make the top level
# visible" is indistinguishable from "count any top-level edit".
git -C "${_appI}" checkout -q "${_baseI}" -- src/sub/thing.js
cat > "${_appI}/src/thing.js" <<'JS'
// TODO: this call still needs a requesttoken header. Not done yet.
export const create = (b) => fetch('/api/things', { method: 'POST', body: b, headers: {} })
JS
_commit "${_appI}" "drop @NoCSRFRequired; a top-level src/ edit with no signal"
_outI3="${_tmp}/i3.txt"
_run "${_appI}" "${_outI3}" --scope-to-diff --base "${_baseI}"
_expect "${_outI3}" 48 "FAIL" "anti-widening: a top-level src/ edit carrying NO signal is not a co-change"

# FAMILY J — gate-50: THE GUARD WINDOW MUST NOT CROSS A METHOD BOUNDARY (#429).
#
# The window was "eleven lines of code following the read", counted over the
# FILE, with no notion of where the method ends. A guard belonging to a
# DIFFERENT method therefore cleared an unguarded read in the method above it.
#
# Measured 2026-08-13 on c26f9a3, one file, one variable:
#   both methods present                 PASS                   <- the defect
#   delete the next method, nothing else FAIL — 1, naming api_token
#
# #420 changed the window's BUDGET (comments no longer spend it) but not its
# EXTENT, so that fix moved this defect closer rather than away.
#
# J1 is the evidence arm (PASS on origin/main, FAIL here). J2–J5 hold their
# verdict in BOTH arms and are CONTROLS:
#   J2  the issue's own positive control — the unguarded read on its own
#   J3  a guard genuinely in the SAME method, inside budget, must still PASS,
#       or the clip is a new false-positive engine
#   J4  the SAME method, one code line OUTSIDE budget, must still FAIL — the
#       clip must not have quietly shrunk the budget it clips
#   J5  a `}` inside a string literal AND inside a heredoc body must not
#       truncate the method span. Load-bearing: walking the un-blanked text
#       computes readToken() as ending on its second line, which clips the
#       real guard out and invents a finding. (Measured directly on the
#       helper: spans (4,6) un-blanked vs (4,15) blanked.)
# ===========================================================================
_appJ="${_tmp}/appJ"
mkdir -p "${_appJ}/lib/Controller"
git -C "${_appJ}" init -q . 2>/dev/null

_write_j() {  # _write_j <heredoc-on-stdin> — writes lib/Controller/JController.php
    cat > "${_appJ}/lib/Controller/JController.php"
}

# J1 — THE DEFECT. The guard five code lines below belongs to another method.
_write_j <<'PHP'
<?php
namespace OCA\Fx\Controller;
class JController
{
    // UNGUARDED: this read has no fail-mode handling of its own.
    public function readToken()
    {
        $tok = $this->config->getValueString($this->appName, 'api_token', '');
        return $this->render($tok);
    }

    // A DIFFERENT METHOD. Its guard is 5 code lines below the read above.
    public function readRegister()
    {
        $reg = $this->config->getValueString($this->appName, 'register_key', '');
        if ($reg === '') {
            return $this->render('');
        }
        return $this->lookup($reg);
    }
}
PHP
_commit "${_appJ}" "an unguarded read whose only guard lives in the next method"
_g50j="${_tmp}/g50j"
mkdir -p "${_g50j}"
_outJ1="${_tmp}/j1.txt"
(
    cd "${_appJ}" || exit 1
    HYDRA_GATE_LOG_DIR="${_g50j}" bash "${_runner}" . > "${_outJ1}" 2>&1
)
_expect "${_outJ1}" 50 "FAIL" "a guard in the NEXT method does not clear a read in this one"
if grep -q 'readToken()' "${_g50j}/hydra-gate-security-config-fail-mode.log" 2>/dev/null \
   && grep -q 'api_token' "${_g50j}/hydra-gate-security-config-fail-mode.log" 2>/dev/null; then
    _ok "gate-50 NAMES the method the window was clipped to (readToken)"
else
    _bad "gate-50 finding does not name readToken(): $(cat "${_g50j}/hydra-gate-security-config-fail-mode.log" 2>/dev/null | head -2)"
fi

# J2 — CONTROL. The issue's positive control: delete readRegister() and
# nothing else. FAILs before and after.
_write_j <<'PHP'
<?php
namespace OCA\Fx\Controller;
class JController
{
    // UNGUARDED: this read has no fail-mode handling of its own.
    public function readToken()
    {
        $tok = $this->config->getValueString($this->appName, 'api_token', '');
        return $this->render($tok);
    }
}
PHP
_commit "${_appJ}" "control: the unrelated next method deleted"
_outJ2="${_tmp}/j2.txt"
_run "${_appJ}" "${_outJ2}"
_expect "${_outJ2}" 50 "FAIL" "control: the same read alone is still a finding"

# J3 — CONTROL, ANTI-FALSE-POSITIVE. The guard is genuinely in this method,
# nine code lines of filler below the read (the 11th code line of the window).
_write_j <<'PHP'
<?php
namespace OCA\Fx\Controller;
class JController
{
    public function readToken()
    {
        $tok = $this->config->getValueString($this->appName, 'api_token', '');
        $v1 = 1;
        $v2 = 2;
        $v3 = 3;
        $v4 = 4;
        $v5 = 5;
        $v6 = 6;
        $v7 = 7;
        $v8 = 8;
        $v9 = 9;
        if ($tok === '') {
            return $this->render('');
        }
        return $this->render($tok);
    }

    public function unrelated()
    {
        return 2;
    }
}
PHP
_commit "${_appJ}" "the guard is in the same method, inside budget"
_outJ3="${_tmp}/j3.txt"
_run "${_appJ}" "${_outJ3}"
_expect "${_outJ3}" 50 "PASS" "control: a guard in the SAME method inside budget still PASSes"

# J4 — CONTROL, BUDGET. One more filler line and the guard is out of budget.
# This is what makes J3 mean something: it shows the budget is still being
# spent, so J3's PASS is "the guard was in range", not "the window is now
# unbounded inside a method".
_write_j <<'PHP'
<?php
namespace OCA\Fx\Controller;
class JController
{
    public function readToken()
    {
        $tok = $this->config->getValueString($this->appName, 'api_token', '');
        $v1 = 1;
        $v2 = 2;
        $v3 = 3;
        $v4 = 4;
        $v5 = 5;
        $v6 = 6;
        $v7 = 7;
        $v8 = 8;
        $v9 = 9;
        $v10 = 10;
        if ($tok === '') {
            return $this->render('');
        }
        return $this->render($tok);
    }
}
PHP
_commit "${_appJ}" "the guard is in the same method, one code line outside budget"
_outJ4="${_tmp}/j4.txt"
_run "${_appJ}" "${_outJ4}"
_expect "${_outJ4}" 50 "FAIL" "control: the 11-code-line budget is unchanged by the clip"

# J5 — CONTROL, ROBUSTNESS. Braces inside a string literal and inside a
# heredoc body must not truncate the method span.
_write_j <<'PHP'
<?php
namespace OCA\Fx\Controller;
class JController
{
    public function readToken()
    {
        $tok = $this->config->getValueString($this->appName, 'api_token', '');
        $fmt = '}';
        $q = <<<SQL
            SELECT } FROM t
SQL;
        $other = "}}}";
        if ($tok === '') {
            return $this->render('');
        }
        return $this->render($tok);
    }

    public function unrelated()
    {
        return 2;
    }
}
PHP
_commit "${_appJ}" "braces inside a string literal and a heredoc body"
_outJ5="${_tmp}/j5.txt"
_run "${_appJ}" "${_outJ5}"
_expect "${_outJ5}" 50 "PASS" "control: a } in a string or heredoc does not truncate the method span"

echo ""
if [ "${_failures}" -eq 0 ]; then
    echo "test_gate_45_to_55_acceptance.sh: ALL GREEN"
    exit 0
fi
echo "test_gate_45_to_55_acceptance.sh: ${_failures} failure(s)"
exit 1
