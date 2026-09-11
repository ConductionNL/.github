#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# test_or_abstraction_exceptions.sh — self-test for the ADR-022 exception path
# in scripts/lint-or-abstraction-anti-patterns.sh.
#
# WHY THIS EXISTS
# ---------------
# ADR-022 says an exception applies where it is recorded in an app-local ADR,
# and it ships a worked example. Until 2026-09-11 the gate asked only in rule 7
# (the ADR-051 capability table): `_cap_suppressed()` was defined once, below
# rules 2 to 6, and called from the rule-7 loop alone. Rules 2 to 6 had no
# exception path at all, so the gate was narrower than the ADR it enforces.
#
# Two of those rules match on FILE NAME. In dossiq that flagged
# lib/Service/TenantService.php and lib/Service/TenantAuditTrailService.php —
# the two classes that already consume OpenRegister's OrganisationMapper,
# TenantLifecycleService and AuditTrailMapper. The only way to clear a name
# rule is a rename, which changes nothing. The gate penalised the correct
# architecture and rewarded a cosmetic edit.
#
# WHAT THIS SUITE RATCHETS
# ------------------------
# An exception path is a hole by construction, so every assertion below is
# about the hole's edges:
#
#   * a flagged file with NO ADR still fails       (the positive control)
#   * an ADR that does not cite ADR-022 buys nothing
#   * an ADR naming a SIBLING path buys nothing
#   * every suppression is PRINTED with its ADR    (no silent exceptions)
#   * an ADR with NO sunset suppresses but is PRINTED as a warning, so it
#     cannot become permanent quietly
#   * an ADR whose sunset has PASSED stops suppressing
#   * an audit-trail file that CALLS AuditTrailMapper is compliant and printed;
#     a file that only names it in a COMMENT is not
#
# Run: bash scripts/lib/test_or_abstraction_exceptions.sh   (exit 0 = pass)
#
# Set GATE=<path> to point the suite at another copy of the gate script. That
# is how these assertions were mutation-checked: run against the pre-change
# script and the suppression, sunset and consumer arms all go red.
set -uo pipefail

LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
GATE="${GATE:-${LIB_DIR}/../lint-or-abstraction-anti-patterns.sh}"

if [ ! -f "${GATE}" ]; then
    echo "FAIL — gate script not found at ${GATE}; this suite cannot assert anything."
    echo "Refusing to report passes for a subject that is absent."
    exit 1
fi

FAILS=0
WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT

mkdir -p "${WORK}/lib/Service" "${WORK}/lib/Middleware" "${WORK}/appinfo" "${WORK}/openspec/architecture"
printf '<?xml version="1.0"?>\n<info>\n  <id>fixtureapp</id>\n</info>\n' > "${WORK}/appinfo/info.xml"

FUTURE="$(date -u -d '+180 days' +%Y-%m-%d)"
PAST="$(date -u -d '-2 days' +%Y-%m-%d)"

# Force BOTH epochs so the exit status carries the verdict for the umbrella
# rules AND the capability table. In WARN mode the script returns 0 whether or
# not anything matched, so a suite reading the byte in WARN mode asserts
# nothing — which is how these findings stayed invisible in the first place.
run_gate() (
    cd "${WORK}" \
        && HYDRA_OR_GATE_BLOCK_AFTER_EPOCH=0 \
           HYDRA_OR_CAPABILITY_GATE_BLOCK_AFTER_EPOCH=0 \
           bash "${GATE}" >"${WORK}/.out" 2>&1
    echo $?
)

assert_rc() { # <expected-rc> <label>
    local want="$1" label="$2" got
    got="$(run_gate)"
    if [ "${got}" = "${want}" ]; then
        echo "PASS — ${label}"
    else
        echo "FAIL — ${label} (expected exit ${want}, got ${got})"
        sed 's/^/        /' "${WORK}/.out"
        FAILS=$((FAILS + 1))
    fi
}

assert_out() { # <yes|no> <regex> <label>   (asserts on the LAST run's output)
    local want="$1" rx="$2" label="$3"
    if grep -qE -- "${rx}" "${WORK}/.out"; then
        if [ "${want}" = "yes" ]; then echo "PASS — ${label}"; return; fi
    elif [ "${want}" = "no" ]; then
        echo "PASS — ${label}"; return
    fi
    echo "FAIL — ${label} (wanted match=${want} for /${rx}/)"
    sed 's/^/        /' "${WORK}/.out"
    FAILS=$((FAILS + 1))
}

reset_tree() {
    rm -f "${WORK}"/lib/Service/*.php "${WORK}"/lib/Middleware/*.php 2>/dev/null || true
    rm -rf "${WORK}"/lib/Service/Sub 2>/dev/null || true
    rm -f "${WORK}"/openspec/architecture/*.md 2>/dev/null || true
}

# write_adr <file> <cites-adr-022: yes|no> <sunset: none|DATE> <path...>
write_adr() {
    local f="$1" cites="$2" sunset="$3"; shift 3
    {
        echo "# ADR-900: fixture exception"
        echo
        echo "- **Status:** Accepted"
        if [ "${cites}" = "yes" ]; then
            echo "- **References:** hydra ADR-022 (Apps consume OpenRegister abstractions), exception clause"
        else
            echo "- **References:** nothing in particular"
        fi
        echo
        echo "## Covered paths"
        echo
        for p in "$@"; do echo "- \`${p}\`"; done
        echo
        if [ "${sunset}" != "none" ]; then
            echo "## Sunset"
            echo
            echo "Sunset: ${sunset}. Retired by change \`fixture-retiring-change\`."
        fi
    } > "${WORK}/openspec/architecture/${f}"
}

# --- guard the guard --------------------------------------------------------
# An empty tree must be clean, or every "did not fire" assertion below passes
# for the wrong reason.
reset_tree
assert_rc 0 "control: empty tree is clean (so the silence assertions mean something)"

# --- POSITIVE CONTROL: no ADR, still fails ----------------------------------
reset_tree
cat > "${WORK}/lib/Service/TenantThingService.php" <<'PHPEOF'
<?php
class TenantThingService { public function go(): void {} }
PHPEOF
assert_rc 1 "positive control: a Tenant* file with NO exception ADR still fails (rule 4)"
assert_out yes 'consume-or-tenant-fleet-wide' "positive control: the rule is named in the output"

# --- an ADR that does not cite ADR-022 buys nothing --------------------------
write_adr "adr-900-no-citation.md" no "${FUTURE}" "lib/Service/TenantThingService.php"
assert_rc 1 "an ADR that never references ADR-022 does not suppress"
rm -f "${WORK}/openspec/architecture/adr-900-no-citation.md"

# --- an ADR naming a SIBLING buys nothing -----------------------------------
write_adr "adr-900-sibling.md" yes "${FUTURE}" "lib/Service/TenantOtherService.php"
assert_rc 1 "an ADR naming a SIBLING path does not suppress the flagged file"
rm -f "${WORK}/openspec/architecture/adr-900-sibling.md"

# --- NEGATIVE CONTROL: the named path is suppressed, and printed -------------
write_adr "adr-900-tenant.md" yes "${FUTURE}" "lib/Service/TenantThingService.php"
assert_rc 0 "an ADR citing ADR-022 and naming the path suppresses rule 4"
assert_out yes 'suppressed by app-local exception ADR' "the suppression is PRINTED, not silent"
assert_out yes 'openspec/architecture/adr-900-tenant\.md' "the printed suppression names the ADR that bought it"
assert_out yes "sunset ${FUTURE}" "the printed suppression names the sunset date"

# --- a directory token suppresses what lives under it, not a sibling ---------
reset_tree
mkdir -p "${WORK}/lib/Service/Sub"
cat > "${WORK}/lib/Service/Sub/TenantInnerService.php" <<'PHPEOF'
<?php
class TenantInnerService {}
PHPEOF
cat > "${WORK}/lib/Service/TenantOutsideService.php" <<'PHPEOF'
<?php
class TenantOutsideService {}
PHPEOF
write_adr "adr-900-dir.md" yes "${FUTURE}" "lib/Service/Sub/"
assert_rc 1 "a directory exception does NOT cover a file outside that directory"
assert_out yes 'suppressed by app-local exception ADR.*lib/Service/Sub/TenantInnerService\.php' "the file inside the named directory IS suppressed"
assert_out yes '^    lib/Service/TenantOutsideService\.php$' "the sibling outside it is still listed as a finding"

# --- an ADR with NO sunset suppresses, but says so every run -----------------
reset_tree
cat > "${WORK}/lib/Service/TenantThingService.php" <<'PHPEOF'
<?php
class TenantThingService {}
PHPEOF
write_adr "adr-900-no-sunset.md" yes none "lib/Service/TenantThingService.php"
assert_rc 0 "an ADR with no sunset still suppresses (this change may not newly fail a repo)"
assert_out yes 'names NO sunset date' "an ADR with no sunset does NOT silently pass — the gate warns on every run"
assert_out yes 'adr-900-no-sunset\.md names NO sunset' "the sunset warning names the offending ADR"

# --- an EXPIRED sunset stops suppressing -------------------------------------
rm -f "${WORK}/openspec/architecture/adr-900-no-sunset.md"
write_adr "adr-900-expired.md" yes "${PAST}" "lib/Service/TenantThingService.php"
assert_rc 1 "an exception ADR whose sunset has PASSED no longer suppresses"
assert_out yes 'EXPIRED, so it counts again' "the expired exception explains itself in the output"
assert_out yes "sunset ${PAST}" "the expired notice names the date the author chose"

# --- rules 2, 3, 5 and 6 each honour the clause ------------------------------
reset_tree
cat > "${WORK}/lib/Service/ThingAuditTrail.php" <<'PHPEOF'
<?php
class ThingAuditTrail {
    public function append(array $e): void { $this->obj['auditTrail'][] = $e; }
}
PHPEOF
assert_rc 1 "rule 2 fires on an app-local audit trail with no ADR"
write_adr "adr-900-audit.md" yes "${FUTURE}" "lib/Service/ThingAuditTrail.php"
assert_rc 0 "rule 2 honours the exception clause"
assert_out yes 'consume-or-audit-trail-fleet-wide\] suppressed by app-local exception ADR' "rule 2 prints its suppression"

reset_tree
cat > "${WORK}/lib/Service/ApprovalChainService.php" <<'PHPEOF'
<?php
class ApprovalChainService {}
PHPEOF
assert_rc 1 "rule 3 fires on an app-local approval chain with no ADR"
write_adr "adr-900-approval.md" yes "${FUTURE}" "lib/Service/ApprovalChainService.php"
assert_rc 0 "rule 3 honours the exception clause"

reset_tree
cat > "${WORK}/lib/Service/CaseStateMachine.php" <<'PHPEOF'
<?php
class CaseStateMachine {}
PHPEOF
assert_rc 1 "rule 5 fires on an app-local state machine with no ADR"
write_adr "adr-900-workflow.md" yes "${FUTURE}" "lib/Service/CaseStateMachine.php"
assert_rc 0 "rule 5 honours the exception clause"
assert_out yes 'consume-or-workflow-engine-fleet-wide\] suppressed by app-local exception ADR' "rule 5 prints its suppression"

reset_tree
cat > "${WORK}/lib/Service/DossierPermissionService.php" <<'PHPEOF'
<?php
class DossierPermissionService {}
PHPEOF
assert_rc 1 "rule 6 fires on an app-local permission service with no ADR"
write_adr "adr-900-rbac.md" yes "${FUTURE}" "lib/Service/DossierPermissionService.php"
assert_rc 0 "rule 6 honours the exception clause"

# --- rule 7 (capability table) must still honour it, unchanged ---------------
reset_tree
cat > "${WORK}/lib/Middleware/TenantScopeMiddleware.php" <<'PHPEOF'
<?php
class TenantScopeMiddleware {}
PHPEOF
assert_rc 1 "regression: rule 7 still fires on a tenant middleware with no ADR"
write_adr "adr-900-cap.md" yes "${FUTURE}" "lib/Middleware/TenantScopeMiddleware.php"
assert_rc 0 "regression: rule 7 still honours the exception clause it has always had"
assert_out yes 'or-capability:tenant-boundary\] suppressed by app-local exception ADR' "rule 7 prints its suppression"

# --- the audit-trail CONSUMER is compliant, not a finding --------------------
#
# This is the half that needs no ADR at all. A file matching rule 2's name
# pattern that WRITES THROUGH OpenRegister's AuditTrailMapper is doing exactly
# what the rule asks for.
reset_tree
cat > "${WORK}/lib/Service/CaseAuditTrailService.php" <<'PHPEOF'
<?php
use OCA\OpenRegister\Db\AuditTrailMapper;

class CaseAuditTrailService {
    public function __construct(private readonly AuditTrailMapper $auditTrailMapper) {}

    public function record(object $o, string $action, array $ctx): void {
        $this->auditTrailMapper->createAuditTrailEntry($o, $action, $ctx);
    }
}
PHPEOF
assert_rc 0 "a *AuditTrail* file that calls OR's AuditTrailMapper is compliant without any ADR"
assert_out yes "writes through OpenRegister's AuditTrailMapper — compliant, not counted" "the compliant consumer is PRINTED, so the reader can audit the decision"
assert_out no 'consume-or-audit-trail-fleet-wide\] app-local audit listener' "the consumer is not also reported as a violation"

# The consumer check clears RULE 2 ONLY. dossiq's real file is called
# TenantAuditTrailService.php, so rule 4 still matches it on the Tenant
# prefix — which is precisely why an app-local exception ADR is needed on top
# of the consumer check, and why this suite asserts the residue rather than
# letting a reader assume the content check cleared everything.
reset_tree
cat > "${WORK}/lib/Service/TenantAuditTrailService.php" <<'PHPEOF'
<?php
use OCA\OpenRegister\Db\AuditTrailMapper;

class TenantAuditTrailService {
    public function __construct(private readonly AuditTrailMapper $auditTrailMapper) {}

    public function record(object $o, string $action, array $ctx): void {
        $this->auditTrailMapper->createAuditTrailEntry($o, $action, $ctx);
    }
}
PHPEOF
assert_rc 1 "an OR consumer NAMED Tenant* still trips rule 4 — the content check clears rule 2 only"
assert_out yes "writes through OpenRegister's AuditTrailMapper — compliant, not counted" "rule 2 clears it even while rule 4 holds it"
assert_out yes 'consume-or-tenant-fleet-wide' "rule 4 is the one still lit, by file name"
write_adr "adr-900-consumer.md" yes "${FUTURE}" "lib/Service/TenantAuditTrailService.php"
assert_rc 0 "with the exception ADR on top, the OR consumer is finally clean"

# The suppression may not be bought with a comment. Same ratchet as rule 1's.
reset_tree
cat > "${WORK}/lib/Service/FakeAuditTrail.php" <<'PHPEOF'
<?php
/**
 * One day this will go through OpenRegister's AuditTrailMapper and call
 * createAuditTrailEntry(). It does not yet.
 */
class FakeAuditTrail {
    public function append(array $e): void { $this->rows[] = $e; }
}
PHPEOF
assert_rc 1 "a COMMENT naming AuditTrailMapper does not make a file a consumer"

# --- the file list a rule prints must shrink by the suppressed file only -----
reset_tree
cat > "${WORK}/lib/Service/TenantOneService.php" <<'PHPEOF'
<?php
class TenantOneService {}
PHPEOF
cat > "${WORK}/lib/Service/TenantTwoService.php" <<'PHPEOF'
<?php
class TenantTwoService {}
PHPEOF
write_adr "adr-900-one.md" yes "${FUTURE}" "lib/Service/TenantOneService.php"
assert_rc 1 "a partial exception leaves the rule lit for the files it does not name"
assert_out no '^    lib/Service/TenantOneService\.php$' "the suppressed file is gone from the finding list"
assert_out yes '^    lib/Service/TenantTwoService\.php$' "the unnamed file is still in the finding list"

echo
if [ "${FAILS}" -eq 0 ]; then
    echo "ALL assertions passed."
    exit 0
fi
echo "${FAILS} assertion(s) FAILED."
exit 1
