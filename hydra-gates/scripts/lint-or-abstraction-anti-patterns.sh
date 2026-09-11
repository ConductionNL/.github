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
# bake-in epoch (HYDRA_OR_CAPABILITY_GATE_BLOCK_AFTER_EPOCH).
#
# THE ADR-022 EXCEPTION CLAUSE APPLIES TO EVERY RULE HERE, not only to the
# capability table. An app-local ADR under openspec/architecture/ that
# references ADR-022, names the affected path AND names the rules it covers
# (a `Gate 23 rules:` line) suppresses the finding for exactly that path under
# exactly those rules; the suppression is printed with the ADR that bought it;
# an ADR with no sunset date is printed as a warning; an ADR whose sunset has
# passed stops suppressing. Rules 2 to 6 gained this on 2026-09-11, and the
# same day it became per (file, rule) instead of per file. The block above
# rule 2 says why, and what leaving each half out cost.
#
# Run from a Conduction app repo root:
#   bash hydra/scripts/lint-or-abstraction-anti-patterns.sh
#
# License: EUPL-1.2.
# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2024 Conduction B.V. <info@conduction.nl>

set -uo pipefail

# Mode: 0 = WARN, 1 = BLOCK. Switches automatically once BLOCK_AFTER_EPOCH is reached.
#
# THIS CONSTANT NEVER MATCHED ITS OWN COMMENT. It was introduced as "90 days
# after the umbrella's acceptance date (2026-05-11 + 90d)", which is
# 2026-08-09 00:00 UTC = 1786233600. The value actually committed, 1786636800,
# is 2026-08-13 16:00 UTC — four days and sixteen hours later, and not even a
# midnight boundary, which is the tell that it was arrived at by hand rather
# than computed. So the switch-over date could be read off neither the code
# nor the comment, and the two answers differed by four days.
#
# The INTENT was the comment's: acceptance + 90 days = 2026-08-09. Taking the
# comment literally would have flipped this gate to BLOCK on the morning the
# discrepancy was found. That was measured before it was decided, and the
# measurement said not to (see below).
#
# RECONCILED 2026-08-09 in favour of neither, DELIBERATELY, for three reasons:
#
#   1. The debt is real and is not four days of work. Measured across all 18
#      Conduction app repositories at origin/development on 2026-08-09,
#      ELEVEN would have started hard-failing: procest carries an entire
#      multi-tenant SaaS stack (26 Tenant* classes, 5 workflow-engine classes)
#      and hermiq a 6-class tenant control plane. Migrating those onto the
#      OpenRegister tenant boundary and lifecycle is an architecture
#      programme, not a deadline.
#
#   2. Blocking on evidence this noisy would have been wrong regardless of
#      time. On that same measurement the MAJORITY of findings were false
#      positives of the rules' own matching (see the rule-1 rewrite below, and
#      the note on rules 2-7): openregister was flagged for a geocoder that
#      routes through OpenConnector exactly as ADR-022 asks, procest for a
#      frontend shim whose docblock CITES this rule, and docudesk for a
#      listener that subscribes to OpenRegister's own ApprovalStep events. A
#      gate must be believable before it is made blocking.
#
#   3. One date instead of two. ADR-022 enforcement previously had two
#      unrelated cliff edges in this one file — the umbrella epoch here and
#      CAP_BLOCK_AFTER_EPOCH for the ADR-051 capability table. Aligning them
#      gives the fleet a single ADR-022 enforcement date to plan against.
#
# The deadline moved on purpose and says so. It was not waived per file and no
# rule was weakened to meet it.
BLOCK_AFTER_EPOCH="${HYDRA_OR_GATE_BLOCK_AFTER_EPOCH:-1790985600}"  # 2026-10-03 00:00 UTC
NOW_EPOCH="$(date -u +%s)"
MODE=0
if [ "${NOW_EPOCH}" -ge "${BLOCK_AFTER_EPOCH}" ]; then
    MODE=1
fi

EXIT_CODE=0
FOUND_ANY=0
# Number of RULES that matched. Reported on the last line so the caller can
# state the size of the evidence even in WARN mode, where the exit status is 0
# either way.
FINDING_COUNT=0
SEARCH_ROOT="${1:-lib}"

if [ ! -d "${SEARCH_ROOT}" ]; then
    echo "lint-or-abstraction-anti-patterns: search root '${SEARCH_ROOT}' not found; skipping."
    exit 0
fi

# ---------------------------------------------------------------------------
# WHICH APP IS THIS?  (and why `basename $(pwd)` is not the answer)
#
# Rule 1 already needed to exempt one app from its own rule — openconnector
# owns the PDOK adapter, so "do not call api.pdok.nl" cannot apply to it — and
# it asked `basename $(pwd)`. That is the checkout DIRECTORY, which in CI is
# whatever `actions/checkout` was told to call it, and in a git worktree is a
# branch-shaped name. `appinfo/info.xml`'s `<id>` is the app's actual identity
# and is what Nextcloud itself uses.
#
# THIS MATTERS BEYOND TIDINESS. Every rule below is an ADR-022 "consume the
# OpenRegister abstraction instead of growing your own" rule, and each one
# tries to exclude OpenRegister's own implementation with `grep -v -i
# openregister`. That filter reads the FILE PATH — and when the linter runs
# inside the openregister repository the paths are `lib/Db/AuditTrail.php`,
# `lib/Db/ApprovalChain.php`, `lib/Service/Geo/PdokGeocoder.php`: not one of
# them contains the string "openregister", so not one is excluded. Measured
# 2026-08-08 on openregister at 28c5d19: 33 findings, every single one a
# canonical OpenRegister implementation being told to consume itself. The gate
# is in WARN mode until 2026-08-13; on that date it starts hard-failing the
# foundation repository over its own source.
#
# So the exemption is expressed once, by app id, for the provider of each
# abstraction — and it is PRINTED, never silent.
_app_id() {
    local _id=""
    if [ -f appinfo/info.xml ]; then
        _id=$(sed -n 's/.*<id>\([^<]*\)<\/id>.*/\1/p' appinfo/info.xml 2>/dev/null | head -1)
    fi
    [ -z "${_id}" ] && _id="$(basename "$(pwd)")"
    printf '%s' "${_id}"
}
APP_ID="$(_app_id)"

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
    FINDING_COUNT=$((FINDING_COUNT + 1))
    echo "  [${rule}] ${detail}"
    if [ "${MODE}" -eq 1 ]; then
        EXIT_CODE=1
    fi
}

# Rules 2-7 all say "consume the OpenRegister abstraction". OpenRegister IS the
# abstraction; running them against it asks the provider to consume itself, and
# every one of its canonical classes matches (see the _app_id block above).
# The exemption is announced, so a reader can never mistake this run's silence
# for a clean leaf app.
IS_OR=0
if [ "${APP_ID}" = "openregister" ]; then
    IS_OR=1
    echo "i lint-or-abstraction-anti-patterns: app id is 'openregister' — the ADR-022"
    echo "  'consume the OR abstraction' rules (audit-trail, approval-chain, tenant,"
    echo "  workflow-engine, rbac, and the ADR-051 capability table) do NOT apply to the"
    echo "  repository that PROVIDES those abstractions and are not evaluated here."
    echo "  They remain in force for every leaf app."
fi

# ---------------------------------------------------------------------------
# 1. shared-pdok-via-openconnector — direct PDOK API calls outside openconnector.
# Scope: lib/ + src/ + frontend js/vue files; skip docs, scripts, and openspec.
#
# WHY THIS IS NOT `grep -l api.pdok.nl` ANY MORE.
#
# It was, and on 2026-08-09 that spelling produced three findings fleet-wide of
# which TWO were the opposite of a violation:
#
#   * procest src/services/pdokService.js — the file is the openconnector-routed
#     shim itself (`generateUrl('/apps/openconnector/api/pdok')`); it never
#     contacts PDOK. Its only match was a docblock line reading "Direct browser
#     calls to api.pdok.nl are NOT permitted from this app — see Hydra umbrella
#     `shared-pdok-via-openconnector` (ADR-022)". The gate reported a file as
#     violating the rule because it contains a sentence CITING the rule.
#
#   * openregister lib/Service/Geo/PdokGeocoder.php — matched on a `const`
#     holding the Locatieserver base URL. That URL is the argument handed to
#     OpenConnector's CallService; the class has no HTTP client of its own and
#     returns null when OpenConnector is absent. It is the pattern ADR-022
#     prescribes, reported as the thing ADR-022 forbids.
#
# Only procest's PdokLocatieserverService was real: it fopen()s the endpoint
# directly whenever the `pdok_locatieserver_source` config key is empty, which
# is its default.
#
# A hostname in a comment cannot make an HTTP request, and a hostname handed to
# the shared adapter is the fix, not the defect. So the rule now asks the two
# questions that actually distinguish them:
#   (a) does the host appear on a line of CODE (comments stripped)?  and
#   (b) does the file carry its own HTTP transport, or does it dispatch through
#       OpenConnector?
# Routed files are PRINTED as info, never silently dropped.
#
# This is strictly narrower on prose and NOT narrower on code: a bare URL with
# no OpenConnector reference anywhere in the file still fires, so a file that
# gains a direct fetch cannot slip through by omitting a known transport name.
# ---------------------------------------------------------------------------

# Echo a file with comment-only lines removed. `https://` must survive, so a
# `//` is treated as a comment ONLY when it opens the line; `#` likewise, and
# never for a PHP `#[Attribute]`. Trailing comments are deliberately left in
# place — keeping them can only cause the gate to fire, never to stay silent.
_code_lines() {
    awk '
        BEGIN { inblk = 0 }
        {
            t = $0
            sub(/^[ \t]+/, "", t)
            if (inblk == 1) { if (t ~ /\*\//) { inblk = 0 } ; next }
            if (t ~ /^\/\*/) { if (t !~ /\*\//) { inblk = 1 } ; next }
            if (t ~ /^\/\//) { next }
            if (t ~ /^\*/)   { next }
            if (t ~ /^#/ && t !~ /^#\[/) { next }
            print $0
        }
    ' "$1" 2>/dev/null
}

# Tokens that mean "this file performs its own HTTP call".
_PDOK_DIRECT_TRANSPORT='file_get_contents|fopen[[:space:]]*\(|stream_context_create|curl_init|curl_exec|curl_setopt|GuzzleHttp|HttpClient|XMLHttpRequest|fetch[[:space:]]*\(|axios\.(get|post|put|request)|\$\.ajax'

# The provider's app id MOVED. `openconnector` was renamed to `integriq` in the
# 2026-08 fleet rename and shipped the new `<id>` in appinfo/info.xml, so this
# exemption stopped matching the app it exists for. Measured 2026-09-05 on
# integriq at 835d0d5d: four findings, every one a canonical PDOK
# implementation (lib/Sources/Pdok/PdokGeocodingClient.php,
# lib/Adapters/Pdok/PdokGeocodingClientHttp.php, lib/Connectors/PdokConnector.php,
# lib/Service/CatalogRegistryService.php) being told to route through itself.
# The rule is WARN until 2026-10-03 and hard-fails the provider on that date.
#
# BOTH ids are accepted rather than swapped: the rename is per app and the old
# id is still what some checkouts and every stored flow carry, so a swap would
# just move the same breakage to whichever side is measured next.
if [ "${APP_ID}" != "openconnector" ] && [ "${APP_ID}" != "integriq" ]; then
    _pdok_candidates="$(grep -rl --include='*.php' --include='*.js' --include='*.ts' --include='*.vue' "api\\.pdok\\.nl" "${SEARCH_ROOT}" src 2>/dev/null || true)"
    _pdok_direct=""
    _pdok_routed=""
    _pdok_prose=""
    while IFS= read -r _pf; do
        [ -z "${_pf}" ] && continue
        _pf_code="$(_code_lines "${_pf}")"
        # (a) host mentioned only in prose → not a call site.
        if ! printf '%s\n' "${_pf_code}" | grep -q "api\\.pdok\\.nl"; then
            _pdok_prose="${_pdok_prose}${_pf}"$'\n'
            continue
        fi
        # (b) own transport alongside the host → direct call.
        if printf '%s\n' "${_pf_code}" | grep -qE "${_PDOK_DIRECT_TRANSPORT}"; then
            _pdok_direct="${_pdok_direct}${_pf}"$'\n'
            continue
        fi
        # No transport of its own AND it names the provider → routed.
        # BOTH provider ids: a leaf app repointed at `/apps/integriq/api/pdok`
        # after the rename is routing correctly, and matching only the old name
        # would read that as a direct call and flag it.
        if printf '%s\n' "${_pf_code}" | grep -qiE 'openconnector|integriq'; then
            _pdok_routed="${_pdok_routed}${_pf}"$'\n'
            continue
        fi
        # Host on a code line, no transport named, no OpenConnector anywhere:
        # routing cannot be demonstrated, so this counts against the app.
        _pdok_direct="${_pdok_direct}${_pf}"$'\n'
    done <<< "${_pdok_candidates}"

    _pdok_direct="$(printf '%s' "${_pdok_direct}")"
    _pdok_routed="$(printf '%s' "${_pdok_routed}")"
    _pdok_prose="$(printf '%s' "${_pdok_prose}")"

    if [ -n "${_pdok_direct}" ]; then
        flag "shared-pdok-via-openconnector" "api.pdok.nl contacted with the file's own HTTP transport — route via the openconnector PDOK adapter instead"
        echo "${_pdok_direct}" | sed 's/^/    /'
    fi
    if [ -n "${_pdok_routed}" ]; then
        echo "  ℹ️  [shared-pdok-via-openconnector] references api.pdok.nl but dispatches through OpenConnector — compliant, not counted:"
        echo "${_pdok_routed}" | sed 's/^/      /'
    fi
    if [ -n "${_pdok_prose}" ]; then
        echo "  ℹ️  [shared-pdok-via-openconnector] names api.pdok.nl in comments only — no call site, not counted:"
        echo "${_pdok_prose}" | sed 's/^/      /'
    fi
fi

# ---------------------------------------------------------------------------
# THE ADR-022 EXCEPTION CLAUSE, FOR EVERY RULE IN THIS FILE.
#
# ADR-022 says in its own text that an exception applies where it is recorded
# in an app-local ADR, and it ships a worked example. Until 2026-09-11 only
# rule 7 (the ADR-051 capability table) ever asked: `_cap_suppressed()` was
# defined once, below, and called from the rule-7 loop alone. Rules 2 to 6 had
# NO exception path. The gate was narrower than the ADR it enforces.
#
# That is not a theoretical gap, and it is not fixed by asking apps to try
# harder. Rules 2 and 4 match on FILE NAME. Two of the files they flag in
# dossiq are the OpenRegister CONSUMERS ADR-022 asks for:
#
#   lib/Service/TenantService.php           calls OR's OrganisationMapper and
#                                           TenantLifecycleService::provision()
#   lib/Service/TenantAuditTrailService.php writes through OR's
#                                           AuditTrailMapper::createAuditTrailEntry()
#
# Neither can clear a name rule except by being renamed, and a rename changes
# no behaviour at all. So the gate as written penalised the correct
# architecture and rewarded a cosmetic edit. The decided dossiq tenancy
# migration deliberately KEEPS five Tenant-named satellite services, which
# means the approved migration could not clear this gate however much of it
# was built. That is the defect fixed here.
#
# One mechanism now, used by every rule:
#
#   * an app-local ADR under openspec/architecture/ that references ADR-022 and
#     literally names the path (or a directory the path lives under) suppresses
#     the finding for exactly that path,
#   * EVERY suppression is PRINTED, with the file and the ADR that bought it. A
#     silent exception is how a gate becomes decorative, and this repository has
#     been bitten by exactly that,
#   * an exception ADR that names no sunset date still suppresses, but prints a
#     warning naming the ADR on every single run, so it cannot become permanent
#     quietly,
#   * an exception ADR whose sunset date has PASSED stops suppressing, and the
#     finding says so. The author picks the date; the gate holds them to it.
#
# Direction of travel: this only ever removes findings from what rules 2 to 6
# already reported, so no repository can newly fail because of it. The
# expired-sunset arm is the single ratchet, and on the day this landed no ADR
# in the fleet carried a sunset date at all, so it fired for nobody.
#
# SUPPRESSION IS PER (FILE, RULE), NOT PER FILE.
#
# The first cut of the above (ConductionNL/.github#755) matched on path alone,
# across every rule at once. So an ADR written to excuse a file under ONE rule
# silenced that file under every OTHER rule too. The worked example is the one
# that mattered most: dossiq ADR-004 covers lib/Service/TenantAuditTrailService.php
# for rule 4 (a correct OpenRegister consumer flagged on its Tenant* name), and
# that also hid the file's rule-7 `search_path` hit. That hit is the evidence
# for dossiq#2470: the class's hardening checklist cites a search_path
# middleware as tenant-isolation evidence, and the schema it switches to is
# never created. The suppression printed, so nothing vanished outright. But a
# finding a reader has to go looking for in a suppression list is a finding
# that gets ignored.
#
# #755 had a second blast radius nobody measured. ANY ADR under
# openspec/architecture/ that mentions ADR-022 counts as an exception ADR, and
# ANY path-shaped token in it counts as a covered path, directories included.
# Measured on development 2026-09-11: keepiq's secrets ADR says `lib/Service/`
# in prose, which suppressed five audit-trail classes and an authorization
# service; hermiq's agent-boundary ADR did the same for three Tenant*
# services; shillinq's data-model ADR for an audit-trail guard. None of those
# ADRs was written as a gate-23 exception, and none could have been: rules 2
# to 6 had no exception path until that morning.
#
# THE GRAMMAR. It extends the two conventions #755 reads, the path tokens and
# the `Sunset:` line, and adds one keyword-anchored line of the same shape:
#
#   ADR-wide, as a metadata bullet beside `- **Sunset:**`:
#       - **Gate 23 rules:** 4, 7
#   Per path, after the path on the same line:
#       - `lib/Service/TenantAuditTrailService.php` (gate 23 rules: 4)
#
# A rule is named by its number in this file (2 to 7) or by the key the gate
# prints (`consume-or-tenant-fleet-wide`, `or-capability:tenant-boundary`).
# `7` covers every capability row; `or-capability:<row>` covers that row only.
# A per-path list REPLACES the ADR-wide one for that path, everywhere in the
# ADR: repeating the path in prose further down does not widen it. Once an ADR
# declares rules anywhere, a path it mentions without a rule list is covered
# for the ADR-wide rules only, and for nothing if it has none.
#
# AN ADR THAT NAMES NO RULES is read as covering RULE 7 ONLY, and says so on
# every suppression. Rule 7 is the only rule that honoured an exception ADR
# before 2026-09-11, so it is the only rule an ADR written without this grammar
# can have been written against. That makes the fallback exactly the gate's
# behaviour before #755: no repository can fail on it that did not already,
# and nothing #755 accidentally hid under rules 2 to 6 stays hidden. When a
# rule-less ADR names a path that is still counted under rules 2 to 6, the
# gate prints which ADR and which token, so the author can add the line.
#
# Direction of travel: this TIGHTENS. Findings #755 hid come back. Measured on
# all 21 core apps before it merged; see the PR for the per-repo table.
# ---------------------------------------------------------------------------

# One record per (path token, ADR), five fields:
#
#   <token>|<adr path>|<none|YYYY-MM-DD|expired:YYYY-MM-DD>|<rules>|<source>
#
# <rules> is a space-padded set, " 4 7 " or " 4 or-capability:tenant-boundary ",
# so membership is a plain `case` glob. <source> says where the set came from:
#   path    a per-path `(gate 23 rules: ...)` on the line naming the path
#   adr     the ADR-wide `Gate 23 rules:` line
#   legacy  the ADR names no rules anywhere, so it is read as " 7 "
#
# The parse is one awk pass per ADR, not a shell loop per line: shillinq's
# data-model ADR alone is 8,600 lines. Only POSIX awk is used (match, substr,
# split, gsub, tolower), because the CI runner's awk is mawk.
#
# The path token regex is #755's, unchanged, so every path that was a candidate
# before is a candidate now. What changed is which RULES each one buys.
# shellcheck disable=SC2016  # the awk program is single-quoted on purpose
_EXCEPTION_AWK='
function ruleset(s,    n, i, w, out, words) {
    out = ""
    n = split(s, words, /[ \t,;&]+/)
    for (i = 1; i <= n; i++) {
        w = words[i]
        gsub(/^[(]+/, "", w)
        gsub(/[).:]+$/, "", w)
        if (w == "" || w == "and" || w == "rule" || w == "rules") continue
        if (w ~ /^[0-9]+$/ || w ~ /^consume-or-[a-z-]+-fleet-wide$/ || w ~ /^or-capability:[a-z0-9-]+$/) {
            out = out " " w
            continue
        }
        # The list ends at the first word that is not a rule, so prose after
        # it ("4 (the name rule). Rule 7 stays counted") cannot add a rule.
        break
    }
    return out
}
{
    line = $0
    gsub(/\r/, "", line)
    # Emphasis and code marks become spaces, not nothing, so a position in
    # `plain` is the same position in `line`.
    plain = tolower(line)
    gsub(/[*`_]/, " ", plain)

    ntok = 0
    rest = line
    off = 0
    while (match(rest, /[A-Za-z0-9_.-]+(\/[A-Za-z0-9_.*-]+)+\/?/)) {
        ntok++
        tok[ntok] = substr(rest, RSTART, RLENGTH)
        tpos[ntok] = off + RSTART
        off += RSTART + RLENGTH - 1
        rest = substr(rest, RSTART + RLENGTH)
    }

    # ADR-wide: the line OPENS with the keyword, after any list or quote mark.
    # Anchored on purpose: "gate 23, rules 2, 4 and 7" in a References line is
    # prose and must not declare anything.
    if (match(plain, /^[ \t>+-]*gate[ -]*23 +rules? *:/)) {
        declared = 1
        adrwide = adrwide ruleset(substr(plain, RSTART + RLENGTH))
        next
    }

    # Per path: the keyword FOLLOWS a path on the same line, and the list
    # applies to the paths before it.
    m = 0
    rs = ""
    if (match(plain, /gate[ -]*23 +rules? *:/)) {
        m = RSTART
        rs = ruleset(substr(plain, RSTART + RLENGTH))
    }
    for (i = 1; i <= ntok; i++) {
        if (m > 0 && tpos[i] < m) {
            declared = 1
            annotated[tok[i]] = annotated[tok[i]] rs
        } else {
            plaintok[tok[i]] = 1
        }
    }
}
END {
    for (t in annotated) print t "|" adr "|" state "|" annotated[t] " |path"
    for (t in plaintok) {
        if (t in annotated) continue
        if (declared) print t "|" adr "|" state "|" adrwide " |adr"
        else print t "|" adr "|" state "| 7 |legacy"
    }
}
'

EXCEPTION_RECORDS=""
if [ -d openspec/architecture ]; then
    _exception_adrs="$(grep -rl 'ADR-022' openspec/architecture --include='*.md' 2>/dev/null || true)"
    while IFS= read -r _adr; do
        [ -f "${_adr}" ] || continue
        # The sunset is the LATEST ISO date on a line that says "sunset" —
        # latest, because an ADR may recount a date it has already moved, and
        # the superseded one must not shorten the exception by accident.
        _sunset="$(grep -iE 'sunset' "${_adr}" 2>/dev/null | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | sort | tail -1)"
        _state="none"
        if [ -n "${_sunset}" ]; then
            _sun_epoch="$(date -u -d "${_sunset} 00:00:00" +%s 2>/dev/null || echo 0)"
            if [ "${_sun_epoch}" -gt 0 ] && [ "${NOW_EPOCH}" -ge "${_sun_epoch}" ]; then
                _state="expired:${_sunset}"
            else
                _state="${_sunset}"
            fi
        fi
        # A parse that fails must say so. An empty record set suppresses
        # nothing, which fails closed, but a reader should not have to work
        # out why an exception they wrote stopped counting.
        if ! _adr_recs="$(awk -v adr="${_adr}" -v state="${_state}" "${_EXCEPTION_AWK}" "${_adr}")"; then
            echo "  ⚠️  could not parse exception ADR ${_adr}; it suppresses nothing this run."
            continue
        fi
        EXCEPTION_RECORDS="${EXCEPTION_RECORDS}${_adr_recs}"$'\n'
    done <<< "${_exception_adrs}"
    EXCEPTION_RECORDS="$(printf '%s' "${EXCEPTION_RECORDS}" | sort -u)"
fi

# The names a finding answers to in an ADR's rule list: its number in this
# file, and the key the gate prints for it. A rule-7 finding also answers to
# its own capability row, so an ADR can cover `or-capability:tenant-boundary`
# without covering `or-capability:mdm-surface` on the same file.
_rule_aliases() {  # <rule-key> -> " <n> <key> "
    case "$1" in
        consume-or-audit-trail-fleet-wide)       printf ' 2 %s ' "$1" ;;
        consume-or-approval-workflow-fleet-wide) printf ' 3 %s ' "$1" ;;
        consume-or-tenant-fleet-wide)            printf ' 4 %s ' "$1" ;;
        consume-or-workflow-engine-fleet-wide)   printf ' 5 %s ' "$1" ;;
        consume-or-rbac-fleet-wide)              printf ' 6 %s ' "$1" ;;
        # "or-capability:avg-dsar-workflow (ADR-047)" answers to the key
        # without its parenthetical.
        or-capability:*)                         printf ' 7 %s ' "${1%% (*}" ;;
        *)                                       printf ' %s ' "$1" ;;
    esac
}

_rules_cover() {  # <rule set> <aliases> -> 0 when any alias is in the set
    for _rc_alias in $2; do
        case "$1" in
            *" ${_rc_alias} "*) return 0 ;;
        esac
    done
    return 1
}

# Return 0 (suppressed) when an exception ADR names the finding's exact file
# path, or a directory the finding lives under (true prefix match on whole
# path segments — naming lib/Service/Avg/ never suppresses a sibling like
# lib/Service/Mdm/, and a bare word in prose never suppresses), AND that ADR
# covers the finding's RULE for that path. Sets _SUPP_ADR, _SUPP_SUNSET and
# _SUPP_SOURCE on a hit. Returns 1 otherwise, and says why: _SUPP_EXPIRED when
# an ADR covering this rule has run out of time, _SUPP_UNCOVERED (one line
# per ADR) when an ADR names the path but not this rule.
_SUPP_ADR=""
_SUPP_SUNSET=""
_SUPP_SOURCE=""
_SUPP_EXPIRED=""
_SUPP_UNCOVERED=""
_cap_suppressed() {  # <path> <rule-key>
    _p="$1"
    _x_aliases="$(_rule_aliases "$2")"
    _SUPP_ADR=""
    _SUPP_SUNSET=""
    _SUPP_SOURCE=""
    _SUPP_EXPIRED=""
    _SUPP_UNCOVERED=""
    [ -z "${EXCEPTION_RECORDS}" ] && return 1
    while IFS= read -r _rec; do
        [ -z "${_rec}" ] && continue
        IFS='|' read -r _x_raw _x_adr _x_state _x_rules _x_src <<< "${_rec}"
        _x_tok="${_x_raw%/\*}"    # lib/Service/Avg/* → lib/Service/Avg
        _x_tok="${_x_tok%/}"      # lib/Service/Avg/ → lib/Service/Avg
        [ -z "${_x_tok}" ] && continue
        _x_hit=1
        [ "${_p}" = "${_x_tok}" ] && _x_hit=0
        case "${_p}" in
            "${_x_tok}"/*) _x_hit=0 ;;
        esac
        [ "${_x_hit}" -eq 0 ] || continue
        if ! _rules_cover "${_x_rules}" "${_x_aliases}"; then
            case $'\n'"${_SUPP_UNCOVERED}" in
                *$'\n'"${_x_adr}|"*) ;;
                *) _SUPP_UNCOVERED="${_SUPP_UNCOVERED}${_x_adr}|${_x_raw}|${_x_rules}|${_x_src}"$'\n' ;;
            esac
            continue
        fi
        case "${_x_state}" in
            expired:*)
                _SUPP_EXPIRED="${_x_adr} (sunset ${_x_state#expired:})"
                continue
                ;;
        esac
        _SUPP_ADR="${_x_adr}"
        _SUPP_SUNSET="${_x_state}"
        _SUPP_SOURCE="${_x_src}"
        return 0
    done <<< "${EXCEPTION_RECORDS}"
    return 1
}

# Print the exception verdict for one file. Returns 0 when the file SURVIVES
# (still a finding), 1 when it was suppressed. Every outcome prints.
_report_exception() {  # <rule-key> <path>
    if _cap_suppressed "$2" "$1"; then
        echo "  ℹ️  [$1] suppressed by app-local exception ADR (ADR-022 exception clause): $2"
        if [ "${_SUPP_SUNSET}" = "none" ]; then
            echo "      ⚠️  ${_SUPP_ADR} names NO sunset date. An exception with no end date is a permanent one; add a 'Sunset: YYYY-MM-DD' line."
        else
            echo "      by ${_SUPP_ADR}, sunset ${_SUPP_SUNSET}"
        fi
        if [ "${_SUPP_SOURCE}" = "legacy" ]; then
            echo "      ⚠️  ${_SUPP_ADR} names no gate 23 rules, so it is read as covering rule 7 only, the one rule an exception ADR could suppress before 2026-09-11. Add a 'Gate 23 rules:' line naming the rules it covers."
        fi
        return 1
    fi
    if [ -n "${_SUPP_EXPIRED}" ]; then
        echo "  ⌛ [$1] the exception ADR naming this path has EXPIRED, so it counts again: $2"
        echo "      ${_SUPP_EXPIRED}"
    fi
    # An ADR that names the path but not this rule. Printed next to the
    # finding, so the reader sees the exception was considered and does not
    # reach this rule, instead of inferring it from a suppression list.
    if [ -n "${_SUPP_UNCOVERED}" ]; then
        while IFS='|' read -r _u_adr _u_tok _u_rules _u_src; do
            [ -z "${_u_adr}" ] && continue
            if [ "${_u_src}" = "legacy" ]; then
                echo "  ℹ️  [$1] still counted: $2 is named by ${_u_adr} (as ${_u_tok}), which names no gate 23 rules and is read as covering rule 7 only."
            else
                _u_list="${_u_rules# }"
                _u_list="${_u_list% }"
                _u_list="${_u_list// /, }"
                echo "  ℹ️  [$1] still counted: $2 is named by ${_u_adr} (as ${_u_tok}), which covers it for rules: ${_u_list:-none}. Not this one."
            fi
        done <<< "${_SUPP_UNCOVERED}"
    fi
    return 0
}

# Filter a newline-separated file list through the exception clause. Survivors
# land in _SURVIVORS; suppressions are printed by _report_exception.
_filter_exceptions() {  # <rule-key> <file-list>
    _fx_keep=""
    while IFS= read -r _fx_file; do
        [ -z "${_fx_file}" ] && continue
        if _report_exception "$1" "${_fx_file}"; then
            _fx_keep="${_fx_keep}${_fx_file}"$'\n'
        fi
    done <<< "$2"
    _SURVIVORS="$(printf '%s' "${_fx_keep}")"
}

# Rule 2 asks an app to "emit via OR AuditTrailMapper". A file that DOES that
# is the compliant case, and it was being counted as the violation — on its
# name, with its own consumer call sitting in the body. dossiq
# lib/Service/TenantAuditTrailService.php is the worked example: it calls
# OR's createAuditTrailEntry() at lines 139 to 196 and was still flagged.
#
# So the name check now asks a second question, the way rule 1 does for PDOK:
# does this file actually consume OR's audit trail? Compliant files are
# PRINTED, never silently dropped, and the question is asked of CODE lines, so
# a docblock naming the mapper buys nothing.
_or_audit_consumer() {  # <path> -> 0 when the file writes through OR's audit trail
    _code_lines "$1" | grep -qE 'AuditTrailMapper|createAuditTrailEntry'
}

if [ "${IS_OR}" -eq 0 ]; then
# 2. consume-or-audit-trail-fleet-wide — app-local audit listeners/validators/schemas.
matches="$(find "${SEARCH_ROOT}" -type f \( -iname "*Audit*Listener.php" -o -iname "*Audit*Validator.php" -o -iname "*AuditTrail*.php" \) 2>/dev/null | grep -v -i "openregister" || true)"
_audit_keep=""
while IFS= read -r _audit_file; do
    [ -z "${_audit_file}" ] && continue
    if _or_audit_consumer "${_audit_file}"; then
        echo "  ℹ️  [consume-or-audit-trail-fleet-wide] writes through OpenRegister's AuditTrailMapper — compliant, not counted:"
        echo "      ${_audit_file}"
        continue
    fi
    _audit_keep="${_audit_keep}${_audit_file}"$'\n'
done <<< "${matches}"
matches="$(printf '%s' "${_audit_keep}")"
_filter_exceptions "consume-or-audit-trail-fleet-wide" "${matches}"
matches="${_SURVIVORS}"
if [ -n "${matches}" ]; then
    flag "consume-or-audit-trail-fleet-wide" "app-local audit listener/validator found — emit via OR AuditTrailMapper"
    echo "${matches}" | sed 's/^/    /'
fi

# 3. consume-or-approval-workflow-fleet-wide — app-local approval-chain schemas/services.
matches="$(find "${SEARCH_ROOT}" -type f \( -iname "*ApprovalChain*.php" -o -iname "*ApprovalStep*.php" \) 2>/dev/null | grep -v -i "openregister" || true)"
_filter_exceptions "consume-or-approval-workflow-fleet-wide" "${matches}"
matches="${_SURVIVORS}"
if [ -n "${matches}" ]; then
    flag "consume-or-approval-workflow-fleet-wide" "app-local ApprovalChain/Step class found — consume OR ApprovalService instead"
    echo "${matches}" | sed 's/^/    /'
fi

# 4. consume-or-tenant-fleet-wide — app-local Tenant schemas/services/middleware.
matches="$(find "${SEARCH_ROOT}" -type f -iname "Tenant*.php" 2>/dev/null | grep -v -i "openregister" || true)"
_filter_exceptions "consume-or-tenant-fleet-wide" "${matches}"
matches="${_SURVIVORS}"
if [ -n "${matches}" ]; then
    flag "consume-or-tenant-fleet-wide" "app-local Tenant class found — consume OR Organisation + TenantLifecycleService"
    echo "${matches}" | sed 's/^/    /'
fi

# 5. consume-or-workflow-engine-fleet-wide — app-local state-machine / workflow-engine services.
matches="$(find "${SEARCH_ROOT}" -type f \( -iname "*StatusTransition*Service.php" -o -iname "*WorkflowEngine*.php" -o -iname "*StateMachine*.php" \) 2>/dev/null | grep -v -i "openregister" || true)"
_filter_exceptions "consume-or-workflow-engine-fleet-wide" "${matches}"
matches="${_SURVIVORS}"
if [ -n "${matches}" ]; then
    flag "consume-or-workflow-engine-fleet-wide" "app-local state-machine/workflow-engine class found — use x-openregister-lifecycle + WorkflowEngineInterface"
    echo "${matches}" | sed 's/^/    /'
fi

# 6. consume-or-rbac-fleet-wide — app-local permission/authorization services.
matches="$(find "${SEARCH_ROOT}" -type f \( -iname "*Permission*Service.php" -o -iname "*Authorization*Service.php" \) 2>/dev/null | grep -v -i "openregister" | grep -v -i "AuthenticationService" || true)"
_filter_exceptions "consume-or-rbac-fleet-wide" "${matches}"
matches="${_SURVIVORS}"
if [ -n "${matches}" ]; then
    flag "consume-or-rbac-fleet-wide" "app-local permission/authorization service found — enforce via OR rbac-scopes"
    echo "${matches}" | sed 's/^/    /'
fi
fi  # IS_OR == 0

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
# openspec/architecture/ that references ADR-022, literally names the
# affected file path (or its directory) and covers rule 7 for it suppresses
# the finding for exactly those paths. `7` covers every row below;
# `or-capability:<key>` covers the rows sharing that key, so the two
# tenant-boundary rows (the middleware name and the search_path grep) are
# covered together or not at all. An ADR naming no rules is read as rule 7
# only. Suppressions are printed as info lines so reviewers see them.
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

# The exception-ADR index (EXCEPTION_RECORDS) and `_cap_suppressed()` USED TO
# BE DEFINED HERE, immediately above the only loop that called them. That
# placement is why rules 2 to 6 had no exception path: they run earlier in the
# file. Both now live above rule 2 and serve every rule. For this rule the
# behaviour of an ADR without a `Gate 23 rules:` line is unchanged: it still
# covers rule 7, and is now told on every run to say so explicitly.

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
    FINDING_COUNT=$((FINDING_COUNT + 1))
    echo "  [or-capability:${_cap_rule}] ${_cap_detail}"
    if [ "${CAP_MODE}" -eq 1 ]; then
        EXIT_CODE=1
    fi
}

# The OpenRegister engine app IS the owner of these capabilities — skip
# entirely (mirrors the openconnector skip on the PDOK rule above).
if [ "${IS_OR}" -eq 0 ]; then
    for _rule_row in "${OR_CAPABILITY_RULES[@]}"; do
        IFS='|' read -r _cap_key _cap_kind _cap_pattern _cap_msg <<< "${_rule_row}"
        case "${_cap_kind}" in
            path) _cap_matches="$(find "${SEARCH_ROOT}" -type f -path "${_cap_pattern}" 2>/dev/null || true)" ;;
            name) _cap_matches="$(find "${SEARCH_ROOT}" -type f -iname "${_cap_pattern}" 2>/dev/null || true)" ;;
            grep)
                # A COMMENT MUST NOT MANUFACTURE A FINDING (#415/#423).
                #
                # This row is the only `grep`-kind rule in the table, and it
                # ran over the RAW file. A docblock reading
                #
                #     We deliberately do NOT set a Postgres search_path here
                #     — tenant isolation is OpenRegister's job (ADR-022).
                #
                # produced `[or-capability:tenant-boundary]` against a file
                # that does exactly what the ADR asks. The cheapest fix
                # available to the author is to delete the paragraph that
                # records the decision.
                #
                # The PDOK rule in this same file has routed through
                # `_code_lines` since it was written; the capability rows
                # never got it. `grep -rln` is kept as the CANDIDATE finder
                # (it is fast and it opens the whole tree), and each
                # candidate is then re-asked on its code lines only.
                #
                # ⚠️ `_code_lines` strips WHOLE-LINE comments only — its own
                # docstring says trailing comments are left in place because
                # keeping them "can only cause the gate to fire, never to
                # stay silent". So a trailing `// no search_path here` still
                # produces a finding. Narrowing that is a change to a helper
                # the PDOK rule shares, and it is not made here.
                _cap_raw="$(grep -rln --include='*.php' -e "${_cap_pattern}" "${SEARCH_ROOT}" 2>/dev/null || true)"
                _cap_matches=""
                while IFS= read -r _cap_cand; do
                    [ -z "${_cap_cand}" ] && continue
                    if _code_lines "${_cap_cand}" | grep -q -e "${_cap_pattern}"; then
                        _cap_matches="${_cap_matches}${_cap_cand}"$'\n'
                    fi
                done <<< "${_cap_raw}"
                _cap_matches="$(printf '%s' "${_cap_matches}")"
                ;;
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
            if ! _report_exception "or-capability:${_cap_key}" "${_cap_file}"; then
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

# A MACHINE-READABLE TALLY, because in WARN mode the exit status is 0 whether
# or not anything was found — so the caller cannot tell "clean" from "found
# things and chose not to block" by the byte, which is exactly what gate-23 was
# doing (it printed PASS over 33 findings on openregister and 1 on doriath).
# The caller greps this line and states the number in its verdict.
echo "or_abstraction_findings=${FINDING_COUNT} app_id=${APP_ID} mode=$([ "${MODE}" -eq 1 ] && echo BLOCK || echo WARN)"

exit "${EXIT_CODE}"
