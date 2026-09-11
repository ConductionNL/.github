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
# The first cut of that fix (#755) suppressed by PATH, across every rule. So
# dossiq ADR-004, written to excuse TenantAuditTrailService under rule 4, also
# hid the same file's rule-7 `search_path` hit: the evidence for dossiq#2470,
# where tenant isolation is inert and the class cites it as isolation evidence.
# Suppression is now per (file, rule). The section headed PER (FILE, RULE)
# below is what ratchets that.
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
#   * an ADR covering a file for rule A still leaves rule B lit on that file,
#     in the same run, and says so next to the finding
#   * an ADR naming NO rules does not blanket-suppress: it is read as rule 7
#     only, the one rule an exception ADR could suppress before 2026-09-11
#   * an explicit rule list works, by number and by printed key, ADR-wide and
#     per path; a per-path list is not widened by the path's prose mentions
#
# Run: bash scripts/lib/test_or_abstraction_exceptions.sh   (exit 0 = pass)
#
# Set GATE=<path> to point the suite at another copy of the gate script. That
# is how these assertions were mutation-checked: run against the pre-change
# script and the suppression, sunset and consumer arms all go red. The
# PER (FILE, RULE) section was checked the same way against #755's script
# (2fd3159): its per-rule arms go red there and green here.
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

# assert_listed <yes|no> <header-regex> <path> <label>
#
# Is <path> in the file list printed DIRECTLY UNDER the finding header that
# matches <header-regex>? A bare "the path appears in the output" cannot tell
# a finding from a suppression line or from the same file listed under a
# different rule, and telling those apart is the whole point of per-rule
# suppression. (ENVIRON, not `awk -v`, so the regex's backslashes survive.)
assert_listed() {
    local want="$1" hdr="$2" path="$3" label="$4" got="no"
    if HDR="${hdr}" ROW="    ${path}" awk '
        $0 ~ ENVIRON["HDR"] { inlist = 1; next }
        inlist && /^    [^ ]/ { if ($0 == ENVIRON["ROW"]) found = 1; next }
        { inlist = 0 }
        END { exit found ? 0 : 1 }
    ' "${WORK}/.out"; then
        got="yes"
    fi
    if [ "${got}" = "${want}" ]; then
        echo "PASS — ${label}"
        return
    fi
    echo "FAIL — ${label} (wanted listed=${want} for ${path} under /${hdr}/)"
    sed 's/^/        /' "${WORK}/.out"
    FAILS=$((FAILS + 1))
}

reset_tree() {
    rm -f "${WORK}"/lib/Service/*.php "${WORK}"/lib/Middleware/*.php 2>/dev/null || true
    rm -rf "${WORK}"/lib/Service/Sub 2>/dev/null || true
    rm -f "${WORK}"/openspec/architecture/*.md 2>/dev/null || true
}

# write_adr <file> <cites-adr-022: yes|no> <sunset: none|DATE> <path...>
#
# Set ADR_RULES to add an ADR-wide `- **Gate 23 rules:** <list>` line beside
# the sunset, in the metadata-bullet shape real ADRs use. Leave it unset for an
# ADR written before that line existed.
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
        if [ -n "${ADR_RULES:-}" ]; then
            echo "- **Gate 23 rules:** ${ADR_RULES}"
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

# The two refusals below declare rule 4, so that what they test is the
# citation and the path. Without it they would pass on the rule list alone.
# --- an ADR that does not cite ADR-022 buys nothing --------------------------
ADR_RULES=4 write_adr "adr-900-no-citation.md" no "${FUTURE}" "lib/Service/TenantThingService.php"
assert_rc 1 "an ADR that never references ADR-022 does not suppress"
rm -f "${WORK}/openspec/architecture/adr-900-no-citation.md"

# --- an ADR naming a SIBLING buys nothing -----------------------------------
ADR_RULES=4 write_adr "adr-900-sibling.md" yes "${FUTURE}" "lib/Service/TenantOtherService.php"
assert_rc 1 "an ADR naming a SIBLING path does not suppress the flagged file"
rm -f "${WORK}/openspec/architecture/adr-900-sibling.md"

# --- NEGATIVE CONTROL: the named path is suppressed, and printed -------------
ADR_RULES=4 write_adr "adr-900-tenant.md" yes "${FUTURE}" "lib/Service/TenantThingService.php"
assert_rc 0 "an ADR citing ADR-022, naming the path and covering rule 4 suppresses rule 4"
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
ADR_RULES=4 write_adr "adr-900-dir.md" yes "${FUTURE}" "lib/Service/Sub/"
assert_rc 1 "a directory exception does NOT cover a file outside that directory"
assert_out yes 'suppressed by app-local exception ADR.*lib/Service/Sub/TenantInnerService\.php' "the file inside the named directory IS suppressed"
assert_out yes '^    lib/Service/TenantOutsideService\.php$' "the sibling outside it is still listed as a finding"

# --- an ADR with NO sunset suppresses, but says so every run -----------------
reset_tree
cat > "${WORK}/lib/Service/TenantThingService.php" <<'PHPEOF'
<?php
class TenantThingService {}
PHPEOF
ADR_RULES=4 write_adr "adr-900-no-sunset.md" yes none "lib/Service/TenantThingService.php"
assert_rc 0 "an ADR with no sunset still suppresses (this change may not newly fail a repo)"
assert_out yes 'names NO sunset date' "an ADR with no sunset does NOT silently pass — the gate warns on every run"
assert_out yes 'adr-900-no-sunset\.md names NO sunset' "the sunset warning names the offending ADR"

# --- an EXPIRED sunset stops suppressing -------------------------------------
rm -f "${WORK}/openspec/architecture/adr-900-no-sunset.md"
ADR_RULES=4 write_adr "adr-900-expired.md" yes "${PAST}" "lib/Service/TenantThingService.php"
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
ADR_RULES=2 write_adr "adr-900-audit.md" yes "${FUTURE}" "lib/Service/ThingAuditTrail.php"
assert_rc 0 "rule 2 honours the exception clause"
assert_out yes 'consume-or-audit-trail-fleet-wide\] suppressed by app-local exception ADR' "rule 2 prints its suppression"

reset_tree
cat > "${WORK}/lib/Service/ApprovalChainService.php" <<'PHPEOF'
<?php
class ApprovalChainService {}
PHPEOF
assert_rc 1 "rule 3 fires on an app-local approval chain with no ADR"
ADR_RULES=3 write_adr "adr-900-approval.md" yes "${FUTURE}" "lib/Service/ApprovalChainService.php"
assert_rc 0 "rule 3 honours the exception clause"

reset_tree
cat > "${WORK}/lib/Service/CaseStateMachine.php" <<'PHPEOF'
<?php
class CaseStateMachine {}
PHPEOF
assert_rc 1 "rule 5 fires on an app-local state machine with no ADR"
ADR_RULES=5 write_adr "adr-900-workflow.md" yes "${FUTURE}" "lib/Service/CaseStateMachine.php"
assert_rc 0 "rule 5 honours the exception clause"
assert_out yes 'consume-or-workflow-engine-fleet-wide\] suppressed by app-local exception ADR' "rule 5 prints its suppression"

reset_tree
cat > "${WORK}/lib/Service/DossierPermissionService.php" <<'PHPEOF'
<?php
class DossierPermissionService {}
PHPEOF
assert_rc 1 "rule 6 fires on an app-local permission service with no ADR"
ADR_RULES=6 write_adr "adr-900-rbac.md" yes "${FUTURE}" "lib/Service/DossierPermissionService.php"
assert_rc 0 "rule 6 honours the exception clause"

# --- rule 7 (capability table) must still honour it, unchanged ---------------
#
# Deliberately an ADR with NO rule list: this is the backwards-compatible arm.
# Before 2026-09-11 rule 7 was the only rule an exception ADR could suppress,
# so an ADR written then still covers rule 7, and is told to say so.
reset_tree
cat > "${WORK}/lib/Middleware/TenantScopeMiddleware.php" <<'PHPEOF'
<?php
class TenantScopeMiddleware {}
PHPEOF
assert_rc 1 "regression: rule 7 still fires on a tenant middleware with no ADR"
write_adr "adr-900-cap.md" yes "${FUTURE}" "lib/Middleware/TenantScopeMiddleware.php"
# The file is ALSO a rule-4 match (Tenant*.php). A rule-less ADR does not
# cover rule 4, so the run still fails; rule 7 alone is asserted here.
assert_rc 1 "a rule-less ADR on a tenant middleware covers rule 7 but not rule 4"
assert_listed yes '^  \[consume-or-tenant-fleet-wide\] app-local Tenant class' "lib/Middleware/TenantScopeMiddleware.php" "the middleware's rule-4 finding is still listed"
assert_out yes 'or-capability:tenant-boundary\] suppressed by app-local exception ADR' "regression: a rule-less ADR still suppresses rule 7, as it always has"
assert_out yes 'adr-900-cap\.md names no gate 23 rules, so it is read as covering rule 7 only' "a rule-less ADR is told, on the suppression itself, to name its rules"
rm -f "${WORK}/openspec/architecture/adr-900-cap.md"
ADR_RULES="4, 7" write_adr "adr-900-cap.md" yes "${FUTURE}" "lib/Middleware/TenantScopeMiddleware.php"
assert_rc 0 "rule 7 honours an explicit rule list that names it"

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
ADR_RULES=4 write_adr "adr-900-consumer.md" yes "${FUTURE}" "lib/Service/TenantAuditTrailService.php"
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
ADR_RULES=4 write_adr "adr-900-one.md" yes "${FUTURE}" "lib/Service/TenantOneService.php"
assert_rc 1 "a partial exception leaves the rule lit for the files it does not name"
assert_out no '^    lib/Service/TenantOneService\.php$' "the suppressed file is gone from the finding list"
assert_out yes '^    lib/Service/TenantTwoService\.php$' "the unnamed file is still in the finding list"

# =============================================================================
# PER (FILE, RULE)
# =============================================================================
#
# The fixture is dossiq's TenantAuditTrailService in miniature: a Tenant*
# file (rule 4, on its name) that also carries `search_path` on a CODE line
# (rule 7, tenant-boundary). In dossiq that string is a hardening checklist
# citing the inert isolation middleware as evidence, dossiq#2470.
TENANT_HDR='^  \[consume-or-tenant-fleet-wide\] app-local Tenant class'
SEARCH_HDR='^  \[or-capability:tenant-boundary\] Postgres search_path'
write_scope_fixture() {
    cat > "${WORK}/lib/Service/TenantScopeService.php" <<'PHPEOF'
<?php
class TenantScopeService {
    public function hardeningChecklist(): array {
        return ['evidence' => 'TenantIsolationMiddleware sets the Postgres search_path'];
    }
}
PHPEOF
}

# --- control: with no ADR, the fixture lights BOTH rules ---------------------
reset_tree
write_scope_fixture
assert_rc 1 "per-rule control: the two-rule fixture fails with no ADR"
assert_listed yes "${TENANT_HDR}" "lib/Service/TenantScopeService.php" "per-rule control: rule 4 lists the fixture"
assert_listed yes "${SEARCH_HDR}" "lib/Service/TenantScopeService.php" "per-rule control: rule 7 search_path lists the fixture (so the arms below mean something)"

# --- an ADR for rule A suppresses A and leaves B lit, in the SAME run ---------
ADR_RULES=4 write_adr "adr-900-rule-a.md" yes "${FUTURE}" "lib/Service/TenantScopeService.php"
assert_rc 1 "an ADR covering rule 4 does NOT clear the same file's rule-7 finding"
assert_out yes 'consume-or-tenant-fleet-wide\] suppressed by app-local exception ADR.*TenantScopeService\.php' "rule A (4) IS suppressed for the file, and printed"
assert_listed no "${TENANT_HDR}" "lib/Service/TenantScopeService.php" "rule A (4) no longer lists the file"
assert_listed yes "${SEARCH_HDR}" "lib/Service/TenantScopeService.php" "rule B (7, search_path) STILL lists the file as a finding in that same run"
assert_out no 'or-capability:tenant-boundary\] suppressed by app-local exception ADR' "rule B is not in the suppression list at all"
assert_out yes 'or-capability:tenant-boundary\] still counted: lib/Service/TenantScopeService\.php is named by openspec/architecture/adr-900-rule-a\.md .*covers it for rules: 4\. Not this one' "the surviving finding says which ADR named it and which rules that ADR covers"
assert_out yes '^or_abstraction_findings=1 ' "exactly one rule is left lit: the one the ADR does not cover"

# --- an ADR naming NO rules does not blanket-suppress ------------------------
reset_tree
write_scope_fixture
write_adr "adr-900-rule-less.md" yes "${FUTURE}" "lib/Service/TenantScopeService.php"
assert_rc 1 "an ADR naming no rules does NOT suppress the file under every rule"
assert_listed yes "${TENANT_HDR}" "lib/Service/TenantScopeService.php" "a rule-less ADR leaves rule 4 lit on the path it names"
assert_out yes 'consume-or-tenant-fleet-wide\] still counted: lib/Service/TenantScopeService\.php is named by openspec/architecture/adr-900-rule-less\.md .*names no gate 23 rules and is read as covering rule 7 only' "the rule-4 finding explains the rule-less ADR it was not bought by"
assert_out yes 'or-capability:tenant-boundary\] suppressed by app-local exception ADR.*TenantScopeService\.php' "a rule-less ADR still covers rule 7, the only rule it can have been written against"
assert_out yes 'adr-900-rule-less\.md names no gate 23 rules' "and that rule-7 suppression asks for an explicit list"

# An ADR that cites ADR-022 in passing and says `lib/Service/` in prose is
# keepiq's and hermiq's shape: #755 read that as an exception for every
# rule-2 to rule-6 file under lib/Service. It is not one.
reset_tree
cat > "${WORK}/lib/Service/TenantThingService.php" <<'PHPEOF'
<?php
class TenantThingService {}
PHPEOF
cat > "${WORK}/openspec/architecture/adr-900-prose.md" <<'ADREOF'
# ADR-900: where secrets live

Per ADR-022 we consume OpenRegister where we can. The vault services in
`lib/Service/` keep their own tables, because OpenRegister stores plaintext.
ADREOF
assert_rc 1 "a prose directory mention in an ADR that cites ADR-022 does not suppress rule 4"
assert_listed yes "${TENANT_HDR}" "lib/Service/TenantThingService.php" "the file under the prose directory is still a rule-4 finding"

# A References line that NAMES rules in a sentence is prose, not a list.
# dossiq ADR-004 had exactly this line before it gained a real one.
reset_tree
write_scope_fixture
cat > "${WORK}/openspec/architecture/adr-900-references.md" <<'ADREOF'
# ADR-900: tenant exception

- **Status:** Accepted
- **References:** hydra ADR-022, exception clause. Hydra gate 23, `or-abstraction-anti-patterns`, rules 2, 4 and 7.

- `lib/Service/TenantScopeService.php`
ADREOF
assert_rc 1 "'gate 23, rules 2, 4 and 7' in a References sentence declares nothing"
assert_listed yes "${TENANT_HDR}" "lib/Service/TenantScopeService.php" "rule 4 is still lit when the rules are only mentioned in prose"

# --- an explicit rule list works ---------------------------------------------
reset_tree
write_scope_fixture
ADR_RULES="4, 7" write_adr "adr-900-both.md" yes "${FUTURE}" "lib/Service/TenantScopeService.php"
assert_rc 0 "an explicit list naming 4 and 7 clears both"
assert_out yes 'consume-or-tenant-fleet-wide\] suppressed by app-local exception ADR.*TenantScopeService\.php' "explicit list: rule 4 suppressed and printed"
assert_out yes 'or-capability:tenant-boundary\] suppressed by app-local exception ADR.*TenantScopeService\.php' "explicit list: rule 7 suppressed and printed"
assert_out no 'names no gate 23 rules' "an ADR with an explicit list is not nagged to add one"

rm -f "${WORK}/openspec/architecture/adr-900-both.md"
ADR_RULES="consume-or-tenant-fleet-wide and or-capability:tenant-boundary" write_adr "adr-900-keys.md" yes "${FUTURE}" "lib/Service/TenantScopeService.php"
assert_rc 0 "the list also accepts the keys the gate prints, not only rule numbers"

# A per-path list REPLACES the ADR-wide one for that path, and the path's
# later prose mentions do not widen it again. This is dossiq ADR-004's shape:
# the file is listed for rule 4, then discussed further down.
reset_tree
write_scope_fixture
cat > "${WORK}/lib/Service/TenantOtherService.php" <<'PHPEOF'
<?php
class TenantOtherService {}
PHPEOF
cat > "${WORK}/openspec/architecture/adr-900-per-path.md" <<ADREOF
# ADR-900: tenant exception

- **References:** hydra ADR-022, exception clause.
- **Sunset:** ${FUTURE}
- **Gate 23 rules:** 4, 7

- \`lib/Service/TenantScopeService.php\` (gate 23 rules: 4)
- \`lib/Service/TenantOtherService.php\`

## One suppression we do not want

The search_path string in \`lib/Service/TenantScopeService.php\` is real, and
this ADR does not license it.
ADREOF
assert_rc 1 "a per-path list naming only rule 4 leaves that file's rule 7 lit, whatever the ADR-wide line says"
assert_listed yes "${SEARCH_HDR}" "lib/Service/TenantScopeService.php" "the per-path list is not widened by the path's later prose mention"
assert_out yes 'consume-or-tenant-fleet-wide\] suppressed by app-local exception ADR.*TenantOtherService\.php' "an un-annotated path in the same ADR gets the ADR-wide list"
assert_listed no "${TENANT_HDR}" "lib/Service/TenantScopeService.php" "the annotated path is still covered for the rule its own list names"

# The list ends at the first word that is not a rule, so the prose after it
# cannot add one.
reset_tree
write_scope_fixture
ADR_RULES="4 (the name rule). Rule 7 stays counted until the isolation code is gone" write_adr "adr-900-prose-tail.md" yes "${FUTURE}" "lib/Service/TenantScopeService.php"
assert_rc 1 "prose after the rule list does not add the rule it mentions"
assert_listed yes "${SEARCH_HDR}" "lib/Service/TenantScopeService.php" "rule 7 stays lit when only the prose after the list names it"

# `or-capability:<key>` covers that capability row and no other row.
reset_tree
cat > "${WORK}/lib/Middleware/TenantSyncQueueMiddleware.php" <<'PHPEOF'
<?php
class TenantSyncQueueMiddleware {}
PHPEOF
ADR_RULES="4, or-capability:tenant-boundary" write_adr "adr-900-row.md" yes "${FUTURE}" "lib/Middleware/TenantSyncQueueMiddleware.php"
assert_rc 1 "covering or-capability:tenant-boundary does not cover or-capability:mdm-surface on the same file"
assert_listed yes '^  \[or-capability:mdm-surface' "lib/Middleware/TenantSyncQueueMiddleware.php" "the uncovered capability row still lists the file"
assert_out yes 'or-capability:tenant-boundary\] suppressed by app-local exception ADR' "the covered capability row is suppressed"

# A declaration the gate cannot read covers nothing, not even rule 7. It does
# not fall back to the rule-less reading, because its author meant to declare.
reset_tree
cat > "${WORK}/lib/Middleware/TenantScopeMiddleware.php" <<'PHPEOF'
<?php
class TenantScopeMiddleware {}
PHPEOF
ADR_RULES="tenant" write_adr "adr-900-unreadable.md" yes "${FUTURE}" "lib/Middleware/TenantScopeMiddleware.php"
assert_rc 1 "an unreadable rule list covers nothing"
assert_out yes 'covers it for rules: none\. Not this one' "the finding says the ADR's list is empty, so the typo is visible"

echo
if [ "${FAILS}" -eq 0 ]; then
    echo "ALL assertions passed."
    exit 0
fi
echo "${FAILS} assertion(s) FAILED."
exit 1
