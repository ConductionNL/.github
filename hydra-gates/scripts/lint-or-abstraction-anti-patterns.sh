#!/usr/bin/env bash
#
# ShellCheck: 7 x SC2001 (`sed` where `${var//a/b}` would do), all inside the
# pattern-matching itself. Scoped to this file rather than a repo-level
# .shellcheckrc, for the reason spelled out at the top of run-hydra-gates.sh.
# shellcheck disable=SC2001
#
# lint-or-abstraction-anti-patterns.sh — single grep gate backing the seven
# "consume-or-*-fleet-wide" umbrella specs.
#
# Mode: WARN-only for the first 90 days post-acceptance (configured below).
# Switches to BLOCK after BLOCK_AFTER_EPOCH. Returns exit 0 always in WARN
# mode; returns exit 1 when any pattern matches in BLOCK mode.
#
# Patterns covered:
#   - shared-pdok-via-openconnector  → direct api.pdok.nl fetches outside openconnector
#   - consume-or-audit-trail-fleet-wide → app-local *Audit*Listener / *Audit*Validator / *audit*schema
#   - consume-or-approval-workflow-fleet-wide → app-local *ApprovalChain* / *Parafeer* / *SignRequest* schemas
#   - consume-or-tenant-fleet-wide   → app-local Tenant* schemas/services/middleware
#   - consume-or-workflow-engine-fleet-wide → app-local *StatusTransition*Service / *WorkflowEngine*
#   - consume-or-rbac-fleet-wide     → app-local *Permission*Service / *Authorization*Service for OR objects
#   - optional-integration-pattern   → manifest entries without an optionalIntegrations clause where applicable
#
# Plus (ADR-051 §4, exclusivity strengthening of ADR-022): a DATA-DRIVEN
# capability rule table (OR_CAPABILITY_RULES below) — one row per ADR-022
# abstraction-table capability. Detects app-local stacks duplicating an
# OR-owned capability (e.g. lib/Service/Avg/*, *SyncQueue*, Archival*Service,
# Tenant*Middleware, Postgres search_path tenancy). New OR capabilities
# extend the gate by adding a row, not code. Capability rules have their own
# bake-in epoch (HYDRA_OR_CAPABILITY_GATE_BLOCK_AFTER_EPOCH) and honour the
# ADR-022 exception clause: an app-local ADR under openspec/architecture/
# that references ADR-022 and names the affected path suppresses the finding
# for exactly that path.
#
# Run from a Conduction app repo root:
#   bash hydra/scripts/lint-or-abstraction-anti-patterns.sh
#
# License: EUPL-1.2.
# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2024 Conduction B.V. <info@conduction.nl>

set -uo pipefail

# Mode: 0 = WARN, 1 = BLOCK. Switches automatically once BLOCK_AFTER_EPOCH is reached.
# Default: 90 days after the umbrella's acceptance date (2026-05-11 + 90d ≈ 2026-08-09).
BLOCK_AFTER_EPOCH="${HYDRA_OR_GATE_BLOCK_AFTER_EPOCH:-1786636800}"  # 2026-08-09 00:00 UTC
NOW_EPOCH="$(date -u +%s)"
MODE=0
if [ "${NOW_EPOCH}" -ge "${BLOCK_AFTER_EPOCH}" ]; then
    MODE=1
fi

EXIT_CODE=0
FOUND_ANY=0
SEARCH_ROOT="${1:-lib}"

if [ ! -d "${SEARCH_ROOT}" ]; then
    echo "lint-or-abstraction-anti-patterns: search root '${SEARCH_ROOT}' not found; skipping."
    exit 0
fi

flag() {
    local rule="$1"
    local detail="$2"
    if [ "${FOUND_ANY}" -eq 0 ]; then
        if [ "${MODE}" -eq 1 ]; then
            echo "❌ OR-abstraction anti-pattern gate (BLOCK mode after $(date -u -d "@${BLOCK_AFTER_EPOCH}" +%Y-%m-%d)):"
        else
            echo "⚠️  OR-abstraction anti-pattern gate (WARN mode; switches to BLOCK on $(date -u -d "@${BLOCK_AFTER_EPOCH}" +%Y-%m-%d)):"
        fi
    fi
    FOUND_ANY=1
    echo "  [${rule}] ${detail}"
    if [ "${MODE}" -eq 1 ]; then
        EXIT_CODE=1
    fi
}

# 1. shared-pdok-via-openconnector — direct PDOK API calls outside openconnector.
# Scope: lib/ + src/ + frontend js/vue files; skip docs, scripts, and openspec.
if [ "$(basename "$(pwd)")" != "openconnector" ]; then
    matches="$(grep -rln --include='*.php' --include='*.js' --include='*.ts' --include='*.vue' "api\\.pdok\\.nl" "${SEARCH_ROOT}" src 2>/dev/null || true)"
    if [ -n "${matches}" ]; then
        flag "shared-pdok-via-openconnector" "direct api.pdok.nl reference found — route via openconnector PDOK adapter instead"
        echo "${matches}" | sed 's/^/    /'
    fi
fi

# 2. consume-or-audit-trail-fleet-wide — app-local audit listeners/validators/schemas.
matches="$(find "${SEARCH_ROOT}" -type f \( -iname "*Audit*Listener.php" -o -iname "*Audit*Validator.php" -o -iname "*AuditTrail*.php" \) 2>/dev/null | grep -v -i "openregister" || true)"
if [ -n "${matches}" ]; then
    flag "consume-or-audit-trail-fleet-wide" "app-local audit listener/validator found — emit via OR AuditTrailMapper"
    echo "${matches}" | sed 's/^/    /'
fi

# 3. consume-or-approval-workflow-fleet-wide — app-local approval-chain schemas/services.
matches="$(find "${SEARCH_ROOT}" -type f \( -iname "*ApprovalChain*.php" -o -iname "*ApprovalStep*.php" \) 2>/dev/null | grep -v -i "openregister" || true)"
if [ -n "${matches}" ]; then
    flag "consume-or-approval-workflow-fleet-wide" "app-local ApprovalChain/Step class found — consume OR ApprovalService instead"
    echo "${matches}" | sed 's/^/    /'
fi

# 4. consume-or-tenant-fleet-wide — app-local Tenant schemas/services/middleware.
matches="$(find "${SEARCH_ROOT}" -type f -iname "Tenant*.php" 2>/dev/null | grep -v -i "openregister" || true)"
if [ -n "${matches}" ]; then
    flag "consume-or-tenant-fleet-wide" "app-local Tenant class found — consume OR Organisation + TenantLifecycleService"
    echo "${matches}" | sed 's/^/    /'
fi

# 5. consume-or-workflow-engine-fleet-wide — app-local state-machine / workflow-engine services.
matches="$(find "${SEARCH_ROOT}" -type f \( -iname "*StatusTransition*Service.php" -o -iname "*WorkflowEngine*.php" -o -iname "*StateMachine*.php" \) 2>/dev/null | grep -v -i "openregister" || true)"
if [ -n "${matches}" ]; then
    flag "consume-or-workflow-engine-fleet-wide" "app-local state-machine/workflow-engine class found — use x-openregister-lifecycle + WorkflowEngineInterface"
    echo "${matches}" | sed 's/^/    /'
fi

# 6. consume-or-rbac-fleet-wide — app-local permission/authorization services.
matches="$(find "${SEARCH_ROOT}" -type f \( -iname "*Permission*Service.php" -o -iname "*Authorization*Service.php" \) 2>/dev/null | grep -v -i "openregister" | grep -v -i "AuthenticationService" || true)"
if [ -n "${matches}" ]; then
    flag "consume-or-rbac-fleet-wide" "app-local permission/authorization service found — enforce via OR rbac-scopes"
    echo "${matches}" | sed 's/^/    /'
fi

# ---------------------------------------------------------------------------
# 7. ADR-051 §4 — OR-owned capability duplication (data-driven).
#
# One row per ADR-022 abstraction-table capability; extend the gate by adding
# a row, NOT code. Seed corpus = the four HEAD violations named in ADR-051 §4
# (pipelinq lib/Service/Avg/*, pipelinq *SyncQueue*, procest Archival*Service,
# procest Tenant*Middleware + search_path tenancy).
#
# WARN-first on the capability rules' own bake-in epoch (they were seeded
# 2026-07-05; ADR-051 acceptance + 90d ≈ 2026-10-03), independent from the
# older umbrella epoch above.
#
# Exception path (ADR-022 exception clause): an app-local ADR under
# openspec/architecture/ that references ADR-022 and literally names the
# affected file path (or its directory) suppresses the finding for exactly
# those paths. Suppressions are printed as info lines so reviewers see them.
# ---------------------------------------------------------------------------
CAP_BLOCK_AFTER_EPOCH="${HYDRA_OR_CAPABILITY_GATE_BLOCK_AFTER_EPOCH:-1790985600}"  # 2026-10-03 00:00 UTC
CAP_MODE=0
if [ "${NOW_EPOCH}" -ge "${CAP_BLOCK_AFTER_EPOCH}" ]; then
    CAP_MODE=1
fi

# Format: <capability-key>|<match-kind>|<pattern>|<guidance>
#   match-kind: path → find -path glob under SEARCH_ROOT
#               name → find -iname glob under SEARCH_ROOT
#               grep → content grep over *.php under SEARCH_ROOT
OR_CAPABILITY_RULES=(
    'avg-dsar-workflow (ADR-047)|path|*/Service/Avg/*.php|app-local AVG/DSAR stack — consume OR lib/Service/Gdpr (DataSubjectRequestService et al.)'
    'mdm-surface (ADR-045)|name|*SyncQueue*.php|app-local MDM sync-queue — consume the OR MDM surface'
    'archival-destruction-workflow|name|Archival*Service.php|app-local archival/e-Depot chain — consume OR archival + destruction workflow'
    'tenant-boundary|name|Tenant*Middleware*.php|app-local tenant middleware — consume the OR tenant boundary'
    'tenant-boundary|grep|search_path|Postgres search_path tenant isolation — consume the OR tenant boundary'
    'semantic-references (ADR-048)|name|*SemanticTypeResolver*.php|app-local semantic-type resolver — consume OR SemanticTypeResolver'
    'semantic-handoffs (ADR-051)|name|*HandoffService*.php|app-local handoff/conversion engine — consume OR HandoffService + the x-openregister-handoff dialect'
)

# Build the exception path-token list once: every path-like token (a token
# containing at least one `/`) mentioned in an app-local ADR
# (openspec/architecture/*.md) that references ADR-022.
CAP_EXCEPTION_PATHS=""
if [ -d openspec/architecture ]; then
    _exception_adrs="$(grep -rl 'ADR-022' openspec/architecture --include='*.md' 2>/dev/null || true)"
    if [ -n "${_exception_adrs}" ]; then
        while IFS= read -r _adr; do
            [ -f "${_adr}" ] || continue
            _adr_paths="$(grep -oE '[A-Za-z0-9_.-]+(/[A-Za-z0-9_.*-]+)+/?' "${_adr}" 2>/dev/null || true)"
            [ -n "${_adr_paths}" ] && CAP_EXCEPTION_PATHS="${CAP_EXCEPTION_PATHS}${_adr_paths}"$'\n'
        done <<< "${_exception_adrs}"
        CAP_EXCEPTION_PATHS="$(printf '%s' "${CAP_EXCEPTION_PATHS}" | sort -u)"
    fi
fi

# Return 0 (suppressed) when the exception ADRs name the finding's exact
# file path, or a directory the finding lives under (true prefix match on
# whole path segments — naming lib/Service/Avg/ never suppresses a sibling
# like lib/Service/Mdm/, and a bare word in prose never suppresses).
_cap_suppressed() {
    _p="$1"
    [ -z "${CAP_EXCEPTION_PATHS}" ] && return 1
    while IFS= read -r _tok; do
        [ -z "${_tok}" ] && continue
        _tok="${_tok%/\*}"    # lib/Service/Avg/* → lib/Service/Avg
        _tok="${_tok%/}"      # lib/Service/Avg/ → lib/Service/Avg
        [ -z "${_tok}" ] && continue
        [ "${_p}" = "${_tok}" ] && return 0
        case "${_p}" in
            "${_tok}"/*) return 0 ;;
        esac
    done <<< "${CAP_EXCEPTION_PATHS}"
    return 1
}

CAP_FOUND_ANY=0
flag_capability() {
    _cap_rule="$1"
    _cap_detail="$2"
    if [ "${CAP_FOUND_ANY}" -eq 0 ]; then
        if [ "${CAP_MODE}" -eq 1 ]; then
            echo "❌ OR-owned capability duplication (ADR-051 §4; BLOCK mode after $(date -u -d "@${CAP_BLOCK_AFTER_EPOCH}" +%Y-%m-%d)):"
        else
            echo "⚠️  OR-owned capability duplication (ADR-051 §4; WARN mode; switches to BLOCK on $(date -u -d "@${CAP_BLOCK_AFTER_EPOCH}" +%Y-%m-%d)):"
        fi
    fi
    CAP_FOUND_ANY=1
    FOUND_ANY=1
    echo "  [or-capability:${_cap_rule}] ${_cap_detail}"
    if [ "${CAP_MODE}" -eq 1 ]; then
        EXIT_CODE=1
    fi
}

# The OpenRegister engine app IS the owner of these capabilities — skip
# entirely (mirrors the openconnector skip on the PDOK rule above).
if [ "$(basename "$(pwd)")" != "openregister" ]; then
    for _rule_row in "${OR_CAPABILITY_RULES[@]}"; do
        IFS='|' read -r _cap_key _cap_kind _cap_pattern _cap_msg <<< "${_rule_row}"
        case "${_cap_kind}" in
            path) _cap_matches="$(find "${SEARCH_ROOT}" -type f -path "${_cap_pattern}" 2>/dev/null || true)" ;;
            name) _cap_matches="$(find "${SEARCH_ROOT}" -type f -iname "${_cap_pattern}" 2>/dev/null || true)" ;;
            grep) _cap_matches="$(grep -rln --include='*.php' -e "${_cap_pattern}" "${SEARCH_ROOT}" 2>/dev/null || true)" ;;
            *)    _cap_matches="" ;;
        esac
        [ -z "${_cap_matches}" ] && continue
        # OR's own classes vendored/mirrored into an app tree are not
        # app-local duplication.
        _cap_matches="$(echo "${_cap_matches}" | grep -v -i "openregister" || true)"
        [ -z "${_cap_matches}" ] && continue
        _cap_hits=""
        while IFS= read -r _cap_file; do
            [ -z "${_cap_file}" ] && continue
            if _cap_suppressed "${_cap_file}"; then
                echo "  ℹ️  [or-capability:${_cap_key}] suppressed by app-local exception ADR (ADR-022 exception clause): ${_cap_file}"
                continue
            fi
            _cap_hits="${_cap_hits}${_cap_file}"$'\n'
        done <<< "${_cap_matches}"
        _cap_hits="$(printf '%s' "${_cap_hits}")"
        [ -z "${_cap_hits}" ] && continue
        flag_capability "${_cap_key}" "${_cap_msg}"
        echo "${_cap_hits}" | sed 's/^/    /'
    done
fi

if [ "${FOUND_ANY}" -eq 0 ]; then
    echo "✓ OR-abstraction anti-pattern gate clean."
fi

exit "${EXIT_CODE}"
