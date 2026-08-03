#!/bin/bash
# SPDX-License-Identifier: EUPL-1.2
#
# ---------------------------------------------------------------------------
# ShellCheck: scoped, deliberate suppressions for this file only.
#
# This runner spent its whole life in ConductionNL/hydra, which has NO GitHub
# Actions — so it had never been ShellChecked until it moved here. Landing it
# in a repository that does run ShellCheck surfaced 22 findings at note and
# warning level. None are errors, and none change what a gate decides:
#
#   SC2001  `sed` where `${var//a/b}` would do — 11 sites, all inside gate
#           logic. Rewriting them is a behaviour change to the gates for a
#           style point, in code with no unit tests of its own.
#   SC2221/SC2222  overlapping `case` globs (e.g. `tests/*` before `*.spec.js`,
#           where `tests/x.spec.js` legitimately matches the first). Both arms
#           set the same variable, so the overlap is intended and inert.
#   SC2162  `read` without -r, SC1003, SC2016, SC2086, SC2295 — long-standing
#           idioms in the file's own parsing helpers.
#
# Suppressed HERE rather than in a repo-level .shellcheckrc on purpose: a
# root-level disable would have switched these checks off for every script in
# this repository, including ones written after this. This directive covers
# exactly one file. Anything newly added to it still gets checked, and clearing
# these findings is worth doing on its own, with the gate output diffed before
# and after.
# ---------------------------------------------------------------------------
# shellcheck disable=SC1003,SC2001,SC2016,SC2086,SC2162,SC2221,SC2222,SC2295
#
# run-hydra-gates.sh — single source of truth for all 61 Hydra mechanical
# quality gates. Exit 0 on all-green; non-zero on any FAIL.
#
# Invoked from:
#   - images/builder/entrypoint.sh       (Rule 0b iteration — mechanical enforcement)
#   - images/reviewer + security         (mandatory first step — via the skill wrapper)
#   - .claude/skills/hydra-gates/SKILL.md (documents + describes invocation)
#   - humans, locally                     (./scripts/run-hydra-gates.sh [options] [app-dir])
#
# Runs against the CURRENT WORKING DIRECTORY unless a path is given. Designed
# for apps following the standard Conduction NC app layout: lib/ + appinfo/
# + optional src/ + tests/.
#
# Options:
#   --scope-to-diff [BASE]   — Phase G: only scan files changed vs BASE
#                              (default origin/development). Inherited debt
#                              in unchanged files is ignored. Required for
#                              reviewer/security post-flight enforcement;
#                              optional for builder (build mode runs full).
#   --base BRANCH            — override the diff base (default origin/development)
#
# Output shape (stdout):
#   [gate-N] <gate-name>: PASS | FAIL[<reasons>]
# Gates that FAIL write details to /tmp/hydra-gate-<name>.log for debugging;
# a short summary is emitted on stdout so the wrapper can relay it to the
# builder's focused fix pass.
#
# Exit code is the number of failing gates. Zero when all green.

set -u

# Resolve this script's own directory ONCE, as an absolute path, BEFORE any
# `cd` into the app dir below. Gates that shell out to co-located Python
# helpers (scripts/lib/*.py) must use ${SCRIPT_DIR} — resolving via
# `dirname "${BASH_SOURCE[0]}"` AFTER the `cd "${APP_DIR}"` breaks whenever the
# script was invoked by a relative path (e.g. `bash scripts/run-hydra-gates.sh
# /some/app`), because the relative script path no longer resolves from inside
# the app dir.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"

SCOPE_TO_DIFF=0
BASE_REF="origin/development"
APP_DIR=""
while [ $# -gt 0 ]; do
    case "$1" in
        --scope-to-diff) SCOPE_TO_DIFF=1; shift ;;
        --base) BASE_REF="$2"; shift 2 ;;
        --base=*) BASE_REF="${1#--base=}"; shift ;;
        *) APP_DIR="$1"; shift ;;
    esac
done
APP_DIR="${APP_DIR:-$(pwd)}"
cd "${APP_DIR}" 2>/dev/null || { echo "[hydra-gates] ERROR: ${APP_DIR} not accessible" >&2; exit 99; }

# When scope-to-diff is requested, derive the changed-files set once.
# Non-diff branches that need the set: each gate below filters its
# file-iteration based on this variable. Empty set = no scoped files =
# nothing to scan = all gates pass (a scoped run only makes sense when
# the caller knows what the PR changed; an empty diff = no PR work =
# nothing to enforce).
CHANGED_FILES=""
if [ "${SCOPE_TO_DIFF}" = "1" ]; then
    # FAIL CLOSED WHEN THE BASE REF DOES NOT EXIST (hydra#399).
    #
    # The diff below used to swallow a bad base with `2>/dev/null || … || true`,
    # leaving CHANGED_FILES empty. Every gate then iterated an empty set and the
    # suite reported "0 failing gates" — indistinguishable from a suite that had
    # actually inspected the PR. Found on design-system#38: that repo's mainline
    # is `main`, the default base `origin/development` does not exist there, and
    # the pre-flight therefore passed having checked nothing. Re-scoped by hand
    # to origin/main it was 29 files and 57 real gates.
    #
    # A base that cannot be resolved is a configuration error, not an empty PR.
    # Refusing is the only safe reading: an unverifiable scope must never be
    # reported as a clean one.
    if ! git -c safe.directory='*' rev-parse --verify --quiet "${BASE_REF}^{commit}" > /dev/null 2>&1; then
        # Try the remote's own default branch before giving up — most repos that
        # trip this simply call their mainline something else.
        _auto_base=$(git -c safe.directory='*' symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)
        if [ -n "${_auto_base}" ] \
            && git -c safe.directory='*' rev-parse --verify --quiet "${_auto_base}^{commit}" > /dev/null 2>&1; then
            echo "[hydra-gates] Base '${BASE_REF}' does not exist — using the remote default '${_auto_base}' instead."
            BASE_REF="${_auto_base}"
        else
            echo "[hydra-gates] ERROR: diff base '${BASE_REF}' does not resolve in this repository." >&2
            echo "[hydra-gates] Scoping to an unresolvable base yields an EMPTY changed-file set," >&2
            echo "[hydra-gates] which would let every gate pass without inspecting anything." >&2
            echo "[hydra-gates] Set --base <ref> or HYDRA_GATE_BASE_REF (e.g. origin/main)." >&2
            exit 99
        fi
    fi

    CHANGED_FILES=$(git -c safe.directory='*' diff --name-only \
        --diff-filter=ACMR "${BASE_REF}...HEAD" 2>/dev/null \
        || git -c safe.directory='*' diff --name-only \
            --diff-filter=ACMR "${BASE_REF}" 2>/dev/null \
        || true)
    _cf_count=$(printf '%s' "${CHANGED_FILES}" | grep -c . 2>/dev/null || true)
    if [ "${_cf_count:-0}" = "0" ]; then
        # Genuinely zero changed files is a legitimate outcome, but it must be
        # stated as such rather than looking like a scoped run that found nothing.
        echo "[hydra-gates] Scope: diff vs ${BASE_REF} — 0 changed file(s). Base resolves; this PR changes nothing."
    else
        echo "[hydra-gates] Scope: diff vs ${BASE_REF} — ${_cf_count} changed file(s)"
    fi
else
    echo "[hydra-gates] Scope: full repo"
fi

# Helper — return 0 if $1 (a file path) is in scope (i.e. either we're
# running full-repo OR the file appears in CHANGED_FILES). Used inside
# every gate's file loop to filter out untouched files when
# --scope-to-diff is active.
_in_scope() {
    [ "${SCOPE_TO_DIFF}" = "0" ] && return 0
    [ -z "${CHANGED_FILES}" ] && return 1
    echo "${CHANGED_FILES}" | grep -qxF "$1"
}

# Filter a newline-separated list of file paths (one per line) on stdin,
# writing to stdout only those in scope. No-op if SCOPE_TO_DIFF=0.
_filter_files_by_scope() {
    if [ "${SCOPE_TO_DIFF}" = "0" ]; then cat; return; fi
    while IFS= read -r _f; do
        [ -z "${_f}" ] && continue
        _in_scope "${_f}" && echo "${_f}"
    done
}

# Filter a newline-separated list of "file:line:..." (grep -n format) on
# stdin, writing to stdout only those whose file part is in scope.
_filter_grep_by_scope() {
    if [ "${SCOPE_TO_DIFF}" = "0" ]; then cat; return; fi
    while IFS= read -r _line; do
        [ -z "${_line}" ] && continue
        _f="${_line%%:*}"
        _in_scope "${_f}" && echo "${_line}"
    done
}

# ---------------------------------------------------------------------------
# _enum_tracked <basename-regex> <dir> [<dir>...]
#
# Enumerate the files a gate is meant to judge, RECURSIVELY and completely.
#
# Why this exists: several gates enumerated their surface with a NON-RECURSIVE
# shell glob (`for f in lib/Service/*.php`). That silently skipped every file
# in a sub-namespace — so the DEEPER a class sat, the LESS likely it was
# checked, exactly backwards for security-critical code. Measured on
# openregister, gate-8 (unsafe-auth-resolver) read 227 of 607 Service+Controller
# files (37%) and therefore MISSED a live CWE-863 fail-open in
# lib/Service/Object/PermissionHandler.php. The detection logic was correct; the
# gate simply never opened the file.
#
# Why `git ls-files` and not `find`:
#   - `find` walks untracked and ignored trees. A nested `custom_apps/` inside a
#     working dir MASKS the repo's own files and pulls in a vendored copy of a
#     DIFFERENT app; `vendor/`, `node_modules/`, `dist/` do the same at smaller
#     scale. Measured: `find lib -name '*.php'` on openregister returns 1242
#     paths vs 1218 tracked — 24 phantom files that gates then judge.
#   - Tracked-ness is the correct definition of "code this repo ships".
#
# Falls back to `find` (with explicit prunes) only when the app dir is not a git
# work tree, so container/tarball invocations still scan something.
#
# NB: this is about WHICH FILES EXIST for a gate to consider. It does not
# bypass ADR-020 diff-scoping — every caller still filters through `_in_scope` /
# `_filter_files_by_scope`, which decides which of those files to JUDGE.
# ---------------------------------------------------------------------------
_enum_tracked() {
    local _re="$1"; shift
    [ "$#" -gt 0 ] || return 0
    local _out=""
    if git -c safe.directory='*' rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        _out=$(git -c safe.directory='*' ls-files -z -- "$@" 2>/dev/null | tr '\0' '\n' || true)
    else
        local _d _hit
        for _d in "$@"; do
            [ -d "${_d}" ] || continue
            _hit=$(find "${_d}" \
                \( -path '*/vendor/*' -o -path '*/node_modules/*' \
                   -o -path '*/dist/*' -o -path '*/build/*' \
                   -o -path '*/custom_apps/*' \) -prune -o \
                -type f -print 2>/dev/null || true)
            [ -n "${_hit}" ] && _out="${_out}${_out:+
}${_hit}"
        done
    fi
    [ -n "${_out}" ] || return 0
    printf '%s\n' "${_out}" \
        | grep -E "${_re}" 2>/dev/null \
        | grep -vE '(^|/)(vendor|node_modules|dist|build|custom_apps)/' \
        | sort -u || true
}

_FAILED=0
_fail() { echo "[gate-$1] $2: FAIL${3:+ — $3}"; _FAILED=$((_FAILED + 1)); }
_pass() { echo "[gate-$1] $2: PASS"; }

# An abort before the summary (set -e / set -u, a helper blowing up, ...) used
# to be indistinguishable from a completed run: the per-gate PASS lines were
# already on stdout, the summary simply never printed, and readers concluded
# "all gates passed". Observed 2026-07-24 — an unguarded ${HYDRA_GATE_PR_BODY}
# under `set -u` killed the run at gate-49, and the remaining gates were
# reported as green because nobody noticed the summary was missing.
# Make that failure mode impossible to misread.
_SUMMARY_REACHED=0
trap '_rc=$?; if [ "${_SUMMARY_REACHED}" -eq 0 ]; then
        echo "" >&2
        echo "[hydra-gates] ABORTED before the summary (exit ${_rc}) — GATE COVERAGE IS INCOMPLETE." >&2
        echo "[hydra-gates] The PASS lines above cover only the gates that ran; the rest never executed." >&2
        echo "[hydra-gates] Do NOT treat this run as green." >&2
    fi' EXIT

# Resolve the lib/ dir that ships the gate helpers. Local repo layout is
# scripts/run-hydra-gates.sh + scripts/lib/*.py; container layout flattens
# everything into /usr/local/lib/hydra/. Probe both.
_gate_helper_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/lib" 2>/dev/null && pwd || true)"
if [ ! -f "${_gate_helper_dir}/filter_preexisting_methods.py" ]; then
    _gate_helper_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"
fi

# Provenance filter — for method-based gates, distinguish PR-introduced
# findings from pre-existing methods that happen to live in files the PR
# touched. Only runs when --scope-to-diff is active and the helper is
# present. Mutates the log in place; pre-existing entries move to a
# `<log>.preexisting` sibling for the reviewer to surface as informational.
# Argument: the log path(s) to filter. Safe no-op on missing files / missing
# base ref / parse failures.
_filter_preexisting() {
    [ "${SCOPE_TO_DIFF}" = "1" ] || return 0
    [ -f "${_gate_helper_dir}/filter_preexisting_methods.py" ] || return 0
    python3 "${_gate_helper_dir}/filter_preexisting_methods.py" "${BASE_REF}" "$@" 2>&1 \
        | grep -E '^\[filter-preexisting\]' >&2 || true
}

# ---------------------------------------------------------------------------
# Gate 1: SPDX / license headers on every lib/**/*.php
# ---------------------------------------------------------------------------
if [ -d lib ]; then
    # `grep -r lib/` is recursive but walks UNTRACKED and ignored trees too:
    # on openregister it saw 1242 .php paths vs 1218 tracked, i.e. 24 files the
    # repo does not ship were being judged for SPDX headers. Enumerate the
    # tracked surface instead; the header check itself is unchanged.
    _spdx_files=$(_enum_tracked '\.php$' lib)
    _missing_license=$(printf '%s\n' "${_spdx_files}" | grep . \
        | xargs -r -d '\n' grep -LE '^[[:space:]]*\*[[:space:]]*@license[[:space:]]' 2>/dev/null \
        | _filter_files_by_scope)
    _missing_copyright=$(printf '%s\n' "${_spdx_files}" | grep . \
        | xargs -r -d '\n' grep -LE '^[[:space:]]*\*[[:space:]]*@copyright[[:space:]]' 2>/dev/null \
        | _filter_files_by_scope)
    _ml=$(echo -n "${_missing_license}" | grep -c . || true)
    _mc=$(echo -n "${_missing_copyright}" | grep -c . || true)
    if [ "$((_ml + _mc))" -eq 0 ]; then
        _pass 1 "spdx-headers"
    else
        {
            [ "${_ml}" -gt 0 ] && { echo "Missing @license:"; echo "${_missing_license}" | sed 's/^/  /'; }
            [ "${_mc}" -gt 0 ] && { echo "Missing @copyright:"; echo "${_missing_copyright}" | sed 's/^/  /'; }
        } > /tmp/hydra-gate-spdx-headers.log
        _fail 1 "spdx-headers" "${_ml} missing @license, ${_mc} missing @copyright"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 2: Forbidden debug helpers in lib/
# ---------------------------------------------------------------------------
if [ -d lib ]; then
    : > /tmp/hydra-gate-forbidden-patterns.log
    _forbidden=0
    for pattern in var_dump die error_log print_r dd dump; do
        _hits=$(grep -rnE "\\b${pattern}\\(" lib/ 2>/dev/null | grep -v 'vendor/' | _filter_grep_by_scope || true)
        if [ -n "${_hits}" ]; then
            _n=$(echo "${_hits}" | wc -l)
            echo "${_n}x ${pattern}(" >> /tmp/hydra-gate-forbidden-patterns.log
            echo "${_hits}" | head -3 | sed 's/^/  /' >> /tmp/hydra-gate-forbidden-patterns.log
            _forbidden=$((_forbidden + _n))
        fi
    done
    if [ "${_forbidden}" -eq 0 ]; then
        _pass 2 "forbidden-patterns"
    else
        _fail 2 "forbidden-patterns" "${_forbidden} forbidden calls"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 3: Stub scan
# ---------------------------------------------------------------------------
_stub_log=/tmp/hydra-gate-stub-scan.log
: > "${_stub_log}"
grep -rn "In a complete implementation" lib/ src/ 2>/dev/null | _filter_grep_by_scope | head -5 >> "${_stub_log}" || true
if [ -d lib/BackgroundJob ]; then
    while IFS= read -r job; do
        [ -f "${job}" ] || continue
        _in_scope "${job}" || continue
        _body=$(awk '/function run\(/,/^    }/' "${job}" | grep -vE '^\s*(//|\*|\s*\{|\s*\}|\s*$)' | grep -vE 'function run|logger->(info|warning|debug|error|notice)|try\s*\{|\}\s*catch|return;?$' || true)
        _lc=$(echo "${_body}" | grep -cE '\S' || true)
        [ "${_lc}" -lt 2 ] && echo "${job}: run() body has no non-logger statements (stub)" >> "${_stub_log}"
    done < <(_enum_tracked '\.php$' lib/BackgroundJob)
fi
if [ -d src ]; then
    while IFS= read -r vue; do
        _in_scope "${vue}" || continue
        if grep -qE 'fetch[A-Z][A-Za-z]*\s*\(\s*\)\s*\{' "${vue}" \
           && grep -qE "return\s*\[\s*\{\s*label:\s*'(Default|Personal|Test|Demo)" "${vue}"; then
            echo "${vue}: fetch*() returns hard-coded single-entry stub" >> "${_stub_log}"
        fi
    done < <(find src -name '*.vue' 2>/dev/null)
fi
# Stub auth / ignored caller-identity parameter — decidesk#45 pattern
# (2026-04-22). The builder's fix-mode created empty-stub authorize*()
# methods that accept $uid but never reference it; gate-7 passed (regex
# saw the method call exist) but Clyde's semantic review correctly
# flagged them. This check closes that loop: any public method in a
# service/controller that declares a caller-identity parameter
# ($uid / $callerUid / $userId / $caller) but never references it in
# its body is an unfinished stub and fails gate-3. See ADR-021.
while IFS= read -r f; do
    [ -f "$f" ] || continue
    _in_scope "$f" || continue
    grep -nE '^\s*public\s+function\s+\w+\s*\([^)]*\$(uid|callerUid|userId|caller)\b' "$f" \
        | while IFS=: read -r _line_no _; do
            _sig=$(sed -n "${_line_no}p" "$f")
            _method=$(echo "$_sig" | grep -oE 'function\s+\w+' | awk '{print $2}')
            _param=$(echo "$_sig" | grep -oE '\$(uid|callerUid|userId|caller)\b' | head -1)
            [ -z "$_method" ] || [ -z "$_param" ] && continue
            _body=$(awk -v start="${_line_no}" 'NR >= start { print; if (NR > start && /^    \}/) exit }' "$f")
            _body_lines=$(echo "${_body}" | wc -l)
            # A legitimate ≥3-line method that accepts a caller-identity
            # param and never references it is a stub. Skip very short
            # methods (likely abstract/interface forwards).
            [ "${_body_lines}" -lt 4 ] && continue
            # Count lines matching the param — signature line always has it,
            # so <2 means body never references it.
            _count=$(echo "${_body}" | grep -cF "${_param}")
            if [ "${_count}" -lt 2 ]; then
                echo "${f}:${_line_no} method=${_method} rule=caller-identity-ignored param=${_param}" >> "${_stub_log}"
            fi
        done
done < <(_enum_tracked '\.php$' lib/Service lib/Controller)
if [ -s "${_stub_log}" ]; then
    _fail 3 "stub-scan" "$(wc -l < "${_stub_log}") finding(s) — see ${_stub_log}"
else
    _pass 3 "stub-scan"
fi

# ---------------------------------------------------------------------------
# Gate 4: Composer audit
# ---------------------------------------------------------------------------
if [ -f composer.json ] && command -v composer >/dev/null 2>&1; then
    _run_audit=1
    if [ "${SCOPE_TO_DIFF}" = "1" ]; then
        _in_scope "composer.json" || _in_scope "composer.lock" || _run_audit=0
    fi
    if [ "${_run_audit}" = "1" ]; then
        if composer audit --format=plain >/tmp/hydra-gate-composer-audit.log 2>&1; then
            _pass 4 "composer-audit"
        else
            _fail 4 "composer-audit" "CVEs or advisories — see /tmp/hydra-gate-composer-audit.log"
        fi
    fi
fi

# ---------------------------------------------------------------------------
# Gate 5: Route-auth — every method registered in appinfo/routes.php has
# an NC middleware attribute (#[PublicPage] / #[NoAdminRequired] /
# #[NoCSRFRequired] / #[AuthorizedAdminSetting]) or legacy docblock tag.
# ---------------------------------------------------------------------------
if [ -f appinfo/routes.php ]; then
    _ra_fail=0 _ra_log=/tmp/hydra-gate-route-auth.log
    : > "${_ra_log}"
    grep -oE "'name'\s*=>\s*'[a-z_]+#[a-zA-Z0-9_]+'" appinfo/routes.php \
        | grep -oE "[a-z_]+#[a-zA-Z0-9_]+" | sort -u \
        | while IFS='#' read ctrl method; do
            class=$(echo "$ctrl" | awk -F'_' '{for(i=1;i<=NF;i++) printf toupper(substr($i,1,1)) substr($i,2); print ""}')
            path="lib/Controller/${class}Controller.php"
            if [ ! -f "$path" ]; then
                echo "${ctrl}#${method} — ${path} missing" >> "${_ra_log}"
                continue
            fi
            _in_scope "$path" || continue
            def_line=$(grep -nE "^\s*public\s+function\s+${method}\s*\(" "$path" | head -1 | cut -d: -f1)
            if [ -z "$def_line" ]; then
                echo "${path}: no method ${method}" >> "${_ra_log}"
                continue
            fi
            start=$((def_line > 20 ? def_line - 20 : 1))
            head_block=$(sed -n "${start},${def_line}p" "$path")
            if ! echo "$head_block" | grep -qE '#\[(PublicPage|NoAdminRequired|NoCSRFRequired|AuthorizedAdminSetting)\b|@(PublicPage|NoAdminRequired|NoCSRFRequired)\b'; then
                echo "${path}:${def_line} method=${method} rule=missing-auth-attribute" >> "${_ra_log}"
            fi
        done
    _ra_fail=$(wc -l < "${_ra_log}" 2>/dev/null || echo 0)
    if [ "${_ra_fail}" -eq 0 ]; then
        _pass 5 "route-auth"
    else
        _fail 5 "route-auth" "${_ra_fail} routed method(s) missing auth attribute — see ${_ra_log}"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 6: Orphan-auth — public is*/requires?*/validate*/authorize*/check*/
# ensure*/verify*/assert* methods in services + controllers must have at
# least one external caller — BUT only when the method is a genuine
# ACCESS CONTROL, not a generic boolean predicate.
#
# The verb prefix alone over-matches: reference-data lookups
# (Iv3TaakveldList::isValidCode / isDeprecated), SLA queries
# (Kcc\SlaCalculator::isBreached), and UI-availability flags
# (WOOAnonymisationAssistService::isLlmAssistAvailable) are all boolean
# predicates that are NOT authorization. Flagging them inflated the fleet
# "dead auth" count with noise, and a noisy security gate gets ignored —
# the exact failure that cost us with gates 56/57.
#
# The detection now lives in scripts/lib/check_orphan_auth.py, which keeps
# the verb prefix as the candidate filter but requires an authorization-
# domain signal (subject param / permission-denial throw / authz-service
# touch / authz name token / @authorization marker) before a method counts
# as access control. A verb-prefixed method with a real auth signal and
# zero callers anywhere in lib/ or src/ is still flagged (the decidesk
# isTransitionAllowed/requiresChairAuthorization/validateQuorum trio and
# the shillinq segregation guard stay caught). Same-file callers still
# count (a public helper called from a sibling method is legit).
#
# The findings log uses a mktemp path (not the fixed
# /tmp/hydra-gate-orphan-auth.log) so parallel gate runs across multiple
# apps can't clobber each other's counts. See hydra#110.
# ---------------------------------------------------------------------------
_oa_log="$(mktemp "${TMPDIR:-/tmp}/hydra-gate-orphan-auth.XXXXXX.log")"
: > "${_oa_log}"
_oa_files=()
while IFS= read -r f; do
    [ -f "$f" ] || continue
    _in_scope "$f" || continue
    _oa_files+=("$f")
done < <(_enum_tracked '\.php$' lib/Service lib/Controller)
if [ "${#_oa_files[@]}" -gt 0 ]; then
    _oa_lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/lib" 2>/dev/null && pwd)"
    if [ ! -f "${_oa_lib_dir}/check_orphan_auth.py" ]; then
        _oa_lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)/lib"
    fi
    if [ -f "${_oa_lib_dir}/check_orphan_auth.py" ]; then
        python3 "${_oa_lib_dir}/check_orphan_auth.py" "${_oa_files[@]}" \
            >> "${_oa_log}" 2>/dev/null || true
    else
        echo "[gate-6] WARN: check_orphan_auth.py not found at ${_oa_lib_dir} — gate-6 skipped" >&2
    fi
fi
_filter_preexisting "${_oa_log}"
_oa_fail=$(wc -l < "${_oa_log}" 2>/dev/null || echo 0)
if [ "${_oa_fail}" -eq 0 ]; then
    _pass 6 "orphan-auth"
else
    _fail 6 "orphan-auth" "${_oa_fail} orphan method(s) — see ${_oa_log}"
fi

# ---------------------------------------------------------------------------
# Gate 7: No-admin-IDOR — every controller method with #[NoAdminRequired]
# / @NoAdminRequired must contain an authorization guard in the body.
# Recognized guard patterns:
#   - OCSForbiddenException thrown
#   - isAdmin( check
#   - ->authorize*/require*/ensure* service call
#   - #[PublicPage] / @PublicPage (explicit public endpoint)
#   - Http::STATUS_(UNAUTHORIZED|FORBIDDEN) response (or numeric 401/403 in
#     response-construction position)
#   - a deny response routed through a helper — ::forbidden( /
#     ->unauthorized( / ::accessDenied( (call position only, so
#     ->forbiddenWords( is not a false guard)
#   - TemplateResponse return type / instantiation — SPA page renderers
#   - (delegated guards, see check_no_admin_idor.py: Pattern 1 same-class
#     guard-helper; Pattern 2 OpenRegister ObjectService/*Mapper RBAC)
#
# Exemptions (never IDOR vectors):
#   - __construct — not a routed action endpoint
#   - Session-scoped endpoint with no caller-supplied object reference
#     (Pattern 3): zero parameters + no request reads + a session-derived
#     identity ($this->userId / getUID()) — there is no direct object
#     reference to substitute, so IDOR is not structurally possible. Fails
#     closed on an unparseable signature.
#   - Methods carrying @no-admin-idor-exempt <reason> (reason required)
#   - Methods whose name starts with preflightedCors (case-insensitive) —
#     Nextcloud OCS/CORS preflight handlers; OPTIONS requests are sent by
#     browsers without credentials so an auth guard would break CORS.
#     Fleet convention: preflightedCors / preflightedCorsItem / etc.
#     (false positives confirmed: opencatalogi 8x, openconnector 3x, 2026-05-27)
#   - Methods whose body only sets Access-Control-* headers (no data access)
#
# The gate is implemented in scripts/lib/check_no_admin_idor.py, a
# brace-aware Python helper (mirrors gate-9's check_semantic_auth.py).
# The Python implementation correctly handles the function-signature
# return-type hint (e.g. TemplateResponse in ": TemplateResponse") and
# properly scopes @NoAdminRequired look-back to the current method's
# docblock — avoiding false positives from preceding method annotations.
# ---------------------------------------------------------------------------
_idor_log=/tmp/hydra-gate-no-admin-idor.log
: > "${_idor_log}"
_idor_files=()
while IFS= read -r f; do
    [ -f "$f" ] || continue
    _in_scope "$f" || continue
    _idor_files+=("$f")
done < <(_enum_tracked '\.php$' lib/Controller)
if [ "${#_idor_files[@]}" -gt 0 ]; then
    _gate_lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/lib" 2>/dev/null && pwd)"
    if [ ! -f "${_gate_lib_dir}/check_no_admin_idor.py" ]; then
        _gate_lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)/lib"
    fi
    if [ -f "${_gate_lib_dir}/check_no_admin_idor.py" ]; then
        python3 "${_gate_lib_dir}/check_no_admin_idor.py" "${_idor_files[@]}" \
            >> "${_idor_log}" 2>/dev/null || true
    else
        echo "[gate-7] WARN: check_no_admin_idor.py not found at ${_gate_lib_dir} — gate-7 skipped" >&2
    fi
fi
_filter_preexisting "${_idor_log}"
_idor_fail=$(wc -l < "${_idor_log}" 2>/dev/null || echo 0)
if [ "${_idor_fail}" -eq 0 ]; then
    _pass 7 "no-admin-idor"
else
    _fail 7 "no-admin-idor" "${_idor_fail} method(s) with NoAdminRequired + no guard — see ${_idor_log}"
fi

# ---------------------------------------------------------------------------
# Gate 8: Unsafe-auth-resolver — no `catch (\Throwable) { return null; }`
# in methods whose name contains Auth/Authorization/Permission/Role/Guard.
# ---------------------------------------------------------------------------
_uar_log=/tmp/hydra-gate-unsafe-auth-resolver.log
: > "${_uar_log}"
while IFS= read -r f; do
    [ -f "$f" ] || continue
    _in_scope "$f" || continue
    grep -nE "^\s*(public|private|protected)\s+function\s+[a-zA-Z0-9_]*([Aa]uthori[sz]ation|[Aa]uth|[Pp]ermission|[Rr]ole|[Gg]uard)[a-zA-Z0-9_]*\s*\(" "$f" \
        | while IFS=: read _line_no _; do
            _method=$(sed -n "${_line_no}p" "$f" | grep -oE 'function\s+[a-zA-Z0-9_]+' | awk '{print $2}')
            [ -z "$_method" ] && continue
            _body=$(awk -v start="${_line_no}" 'NR >= start { print; if (NR > start && /^    \}/) exit }' "$f")
            # Only flag when the `return null` is INSIDE the catch(\Throwable)
            # block itself — that is the actual fail-open. Methods whose catch
            # returns an error/deny value while a NORMAL (non-catch) path returns
            # null are NOT fail-open and must not be flagged. Two real-world
            # false positives this clears (procest ZgwService, 2026-05-26):
            #   - validateJwtAuth(): catch returns a 403 JSONResponse, the
            #     trailing `return null` is the success path → fail-closed.
            #   - getConsumerAuthorisaties(): catch returns []; the normal-path
            #     `return null` legitimately means "unrestricted".
            # Extract the catch block (from the `catch (\Throwable` line to its
            # closing brace at the method's inner indent) and check only that.
            # NB: the catch line is `} catch (\Throwable $e) {` — it begins with
            # the try's closing brace, so we capture it then only test the
            # block-closing brace on SUBSEQUENT lines (else we'd exit on the
            # catch line itself and miss its body).
            _catch_block=$(echo "$_body" | awk '
                /catch[[:space:]]*\([[:space:]]*\\?Throwable/ { inblk=1; print; next }
                inblk && /^        \}/ { exit }
                inblk { print }
            ')
            if [ -n "$_catch_block" ] && echo "$_catch_block" | grep -qE 'return\s+null\s*;'; then
                echo "${f}:${_line_no} method=${_method} rule=throwable-caught-returns-null" >> "${_uar_log}"
            fi
        done
done < <(_enum_tracked '\.php$' lib/Service lib/Controller)
_filter_preexisting "${_uar_log}"
_uar_fail=$(wc -l < "${_uar_log}" 2>/dev/null || echo 0)
if [ "${_uar_fail}" -eq 0 ]; then
    _pass 8 "unsafe-auth-resolver"
else
    _fail 8 "unsafe-auth-resolver" "${_uar_fail} fail-open pattern(s) — see ${_uar_log}"
fi

# ---------------------------------------------------------------------------
# Gate 9: Semantic-auth — annotation must match the method body's actual
# authorization requirement. Observed on decidesk#44 (2026-04-23): builder
# satisfied gate-5 (route-auth) by adding `#[NoAdminRequired]` to load()
# even though the method body calls `requireAdmin()`. Gate-5 accepted any
# auth attribute; this gate catches the semantic mismatch.
#
# Checks:
#  1. #[NoAdminRequired] / @NoAdminRequired with requireAdmin() / isAdmin()
#     in body → mismatch. Use #[AuthorizedAdminSetting(Application::APP_ID)]
#     instead (declaratively admin-only, matches the body's check).
#  2. #[PublicPage] / @PublicPage with requireAdmin() / isAdmin() / userSession
#     getUser() null-check in body → mismatch. Public means no auth; having
#     body checks means the annotation lies to routers and reviewers.
#
# See ADR-005 (security — attribute must match actual requirement) and
# ADR-016 (routes — gate-5 syntactic, gate-9 semantic).
# ---------------------------------------------------------------------------
_sem_log=/tmp/hydra-gate-semantic-auth.log
: > "${_sem_log}"

# W28 (2026-04-24 warnings list) — gate-9 was a flat-regex implementation
# that broke on nested `}` inside the if-body (closures, array literals,
# match-expressions). The current implementation delegates to a brace-
# aware Python helper that walks the PHP source with proper string +
# comment + heredoc skipping. The bash side just feeds it the in-scope
# files and counts the printed violations.
_sem_files=()
while IFS= read -r f; do
    [ -f "$f" ] || continue
    _in_scope "$f" || continue
    _sem_files+=("$f")
done < <(_enum_tracked '\.php$' lib/Controller)
if [ "${#_sem_files[@]}" -gt 0 ]; then
    # The helper script is co-located with the gate runner. Two layouts:
    #   local repo: scripts/run-hydra-gates.sh + scripts/lib/check_semantic_auth.py
    #   container:  /usr/local/lib/hydra/run-hydra-gates.sh + /usr/local/lib/hydra/check_semantic_auth.py
    # Probe both — the flat container layout was previously a silent skip
    # because the path resolution only checked the lib/ subdir variant.
    _sem_helper=""
    for _candidate in \
        "$(dirname "${BASH_SOURCE[0]:-$0}")/lib/check_semantic_auth.py" \
        "$(dirname "${BASH_SOURCE[0]:-$0}")/check_semantic_auth.py"; do
        if [ -f "${_candidate}" ]; then
            _sem_helper="${_candidate}"
            break
        fi
    done
    if [ -n "${_sem_helper}" ]; then
        python3 "${_sem_helper}" "${_sem_files[@]}" \
            >> "${_sem_log}" 2>/dev/null || true
    else
        echo "[gate-9] WARN: check_semantic_auth.py not found near $(dirname "${BASH_SOURCE[0]:-$0}") — gate-9 skipped" >&2
    fi
fi
_sem_fail=$(wc -l < "${_sem_log}" 2>/dev/null || echo 0)
if [ "${_sem_fail}" -eq 0 ]; then
    _pass 9 "semantic-auth"
else
    _fail 9 "semantic-auth" "${_sem_fail} attribute-vs-body mismatch(es) — see ${_sem_log}"
fi

# ---------------------------------------------------------------------------
# Gate 10: Initial-state — frontend reads of `getElementById(...).dataset.*`
# in .vue/.js/.ts files. Server-side data must travel via IInitialState
# (PHP) + loadState() from @nextcloud/initial-state. Observed 2026-04-30
# on doriath where AdminRoot.vue read `dataset.version` instead of
# `loadState('doriath', 'version', 'Unknown')`. ADR-004 hard rule.
# ---------------------------------------------------------------------------
if [ -d src ]; then
    _is_log=/tmp/hydra-gate-initial-state.log
    : > "${_is_log}"
    grep -rnE "getElementById\s*\([^)]+\)[^.]*\.dataset\b" src/ \
        --include='*.vue' --include='*.js' --include='*.ts' 2>/dev/null \
        | _filter_grep_by_scope >> "${_is_log}" || true
    _is_fail=$(wc -l < "${_is_log}" 2>/dev/null || echo 0)
    if [ "${_is_fail}" -eq 0 ]; then
        _pass 10 "initial-state"
    else
        _fail 10 "initial-state" "${_is_fail} DOM dataset read(s) — use loadState()/IInitialState — see ${_is_log}"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 11: Admin-router — admin settings Vue components must NOT be
# registered as vue-router routes; doing so makes them publicly reachable
# as a frontend URL, bypassing the admin check that Nextcloud's settings
# framework enforces. ADR-004 hard rule. Observed 2026-04-30 on doriath
# (commit c7c72e9 removed the dangerous /settings → AdminRoot route).
# ---------------------------------------------------------------------------
_ar_log=/tmp/hydra-gate-admin-router.log
: > "${_ar_log}"
for f in src/router/index.js src/router/index.ts src/router.js src/router.ts; do
    [ -f "$f" ] || continue
    _in_scope "$f" || continue
    # Imports of admin-prefixed components or anything from views/settings/
    grep -nE "from\s+['\"][^'\"]*(/Admin[A-Z][A-Za-z]*\.vue|views/settings/)" "$f" 2>/dev/null \
        | sed "s|^|${f}:import:|" >> "${_ar_log}" || true
    # Routes whose path is /settings or /admin
    grep -nE "path\s*:\s*['\"]/(settings|admin)\b" "$f" 2>/dev/null \
        | sed "s|^|${f}:path:|" >> "${_ar_log}" || true
done
_ar_fail=$(wc -l < "${_ar_log}" 2>/dev/null || echo 0)
if [ "${_ar_fail}" -eq 0 ]; then
    _pass 11 "admin-router"
else
    _fail 11 "admin-router" "${_ar_fail} admin route/import — register via AdminSettings.php instead — see ${_ar_log}"
fi

# ---------------------------------------------------------------------------
# Gate 12: NC-input-labels — every <NcSelect> tag must declare an
# inputLabel (or ariaLabelCombobox). Manual <label> elements break the
# component's internal a11y wiring (WCAG 1.3.1 / 4.1.2). ADR-004 hard
# rule. Observed 2026-04-30 on doriath.
# ---------------------------------------------------------------------------
if [ -d src ]; then
    _il_log=/tmp/hydra-gate-nc-input-labels.log
    : > "${_il_log}"
    while IFS= read -r vue; do
        _in_scope "${vue}" || continue
        _flat=$(tr '\n' ' ' < "${vue}")
        echo "${_flat}" \
            | grep -oE '<NcSelect[^>]*>' 2>/dev/null \
            | while IFS= read -r tag; do
                [ -z "${tag}" ] && continue
                if ! echo "${tag}" | grep -qE "(input-label|inputLabel|aria-label-combobox|ariaLabelCombobox)"; then
                    echo "${vue}: ${tag}" >> "${_il_log}"
                fi
            done
    done < <(find src -name '*.vue' 2>/dev/null)
    _il_fail=$(wc -l < "${_il_log}" 2>/dev/null || echo 0)
    if [ "${_il_fail}" -eq 0 ]; then
        _pass 12 "nc-input-labels"
    else
        _fail 12 "nc-input-labels" "${_il_fail} NcSelect without inputLabel/ariaLabelCombobox — see ${_il_log}"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 13: Modal-isolation — <NcModal> / <NcDialog> markup must live in
# its own file under src/modals/ or src/dialogs/, not inline in parent
# components. ADR-004 hard rule. Observed 2026-04-30 on doriath.
# ---------------------------------------------------------------------------
if [ -d src ]; then
    _mi_log=/tmp/hydra-gate-modal-isolation.log
    : > "${_mi_log}"
    while IFS= read -r vue; do
        case "${vue}" in
            src/modals/*|src/dialogs/*) continue ;;
        esac
        _in_scope "${vue}" || continue
        if grep -qE '<NcModal[ \t>/]|<NcDialog[ \t>/]' "${vue}" 2>/dev/null; then
            echo "${vue}: inline NcModal/NcDialog — extract to src/modals/ or src/dialogs/" >> "${_mi_log}"
        fi
    done < <(find src -name '*.vue' 2>/dev/null)
    _mi_fail=$(wc -l < "${_mi_log}" 2>/dev/null || echo 0)
    if [ "${_mi_fail}" -eq 0 ]; then
        _pass 13 "modal-isolation"
    else
        _fail 13 "modal-isolation" "${_mi_fail} file(s) with inline modal/dialog — see ${_mi_log}"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 14: Route reachability — every Controller method that returns a
# Response type is registered in appinfo/routes.php, and every routed
# entry resolves to a method that actually exists on the named class.
# Catches the two pre-runtime bug classes documented in ADR-029:
#
#   1. Controller method exists, no route registered → router 404
#      (caught 41 instances on openregister 2026-05-01: profile-actions
#       /tmlo-metadata phantom-ticked `[x] Register route` boxes,
#       file-actions / workflow-operations / nextcloud-entity-relations
#       all shipped controllers + tests with no routes.)
#   2. Route exists, the controller class doesn't expose the method
#      (typically because the method moved during a namespace refactor)
#      → ReflectionException 500. Caught 4 instances on openregister
#      2026-05-01: Settings\SolrManagement#getObjectCollectionFields
#      etc. — methods actually live on Settings\ConfigurationSettings.
#
# Out of scope: cross-request persistence (per-instance state where
# operators expect cross-request behaviour, e.g. FileLockHandler
# pre-22c5625ef). That requires semantic understanding beyond static
# analysis; owned by code-review runtime semantics + ADR-005.
# ---------------------------------------------------------------------------
if [ -d lib/Controller ] && [ -f appinfo/routes.php ]; then
    _rr_log=/tmp/hydra-gate-route-reachability.log
    : > "${_rr_log}"

    # Resource auto-routes (entries inside the top-level `'resources' => [...]`
    # block) generate index/show/create/update/destroy on the named
    # controller; methods on those auto-routes are excluded from invariant 1.
    # The block's keys are PascalCase (e.g. `'Registers'`, `'Configurations'`),
    # which we lowercase-first-char to match the route-slug convention used
    # everywhere else in this gate.
    _rr_auto_resources=$(awk '
        /^[[:space:]]*.resources.[[:space:]]*=>[[:space:]]*\[/ { in_block=1; next }
        in_block && /^[[:space:]]*\][[:space:]]*,[[:space:]]*$/ { in_block=0; next }
        in_block && /^[[:space:]]*.[A-Za-z][A-Za-z0-9_]*.[[:space:]]*=>/ {
            match($0, /[A-Za-z][A-Za-z0-9_]*/); key=substr($0, RSTART, RLENGTH)
            print tolower(substr(key,1,1)) substr(key,2)
        }
    ' appinfo/routes.php | sort -u)

    # ---- Invariant 1: every Response-returning controller method has a route
    # Iterate Controller files. For each public method whose return type is
    # a Response shape, derive the expected `controller#method` name and
    # confirm a route entry exists in appinfo/routes.php.
    # SC2044: while-read instead of for-find so paths with whitespace /
    # newlines are handled safely. Process substitution keeps the loop in
    # the current shell so variable updates survive.
    while IFS= read -r _ctrl_path; do
        [ -n "${_ctrl_path}" ] || continue
        _in_scope "${_ctrl_path}" || continue

        # Derive the controller route slug — strip lib/Controller/ prefix +
        # Controller.php suffix, lowercase the first character. Settings/
        # subnamespace becomes `Settings\Foo`.
        _ctrl_short=$(echo "${_ctrl_path}" | sed -e 's|^lib/Controller/||' -e 's|Controller\.php$||')
        case "${_ctrl_short}" in
            Settings/*) _ctrl_slug="Settings\\$(echo "${_ctrl_short}" | sed 's|^Settings/||')";;
            */*)        _ctrl_slug=$(echo "${_ctrl_short}" | sed 's|/|\\|g'); _ctrl_slug=$(echo "${_ctrl_slug}" | awk -F'\\\\' '{for(i=1;i<NF;i++) printf "%s\\\\", $i; sub(/^./,tolower(substr($NF,1,1)),$NF); print $NF}');;
            *)          _ctrl_slug=$(echo "${_ctrl_short}" | awk '{print tolower(substr($0,1,1)) substr($0,2)}');;
        esac

        # Skip resource-routed controllers — their CRUD quintet is auto-generated.
        # Match against both the slug and a snake_case variant of the short name.
        _ctrl_resource=$(echo "${_ctrl_short}" | awk '{name=tolower(substr($0,1,1)) substr($0,2); print name}')
        if echo "${_rr_auto_resources}" | grep -qxF "${_ctrl_resource}"; then continue; fi

        # Each public method that returns a Response-shaped type.
        # Strategy: pcregrep-style multiline pull — for every `public function
        # X(` at the start of a line, capture the next 0-12 lines until the
        # opening `{`, and grep that buffer for any `): ...Response` return
        # type. Done in plain awk for portability (no pcregrep dependency).
        # Helper-prefixed names are excluded by the gate convention.
        _methods=$(awk -v RESPONSE_RX='Response[ |\\{]' '
            /^[[:space:]]*public[[:space:]]+function[[:space:]]+[a-zA-Z_][a-zA-Z0-9_]*[[:space:]]*\(/ {
                method = $0
                sub(/^[[:space:]]*public[[:space:]]+function[[:space:]]+/, "", method)
                sub(/[[:space:]]*\(.*$/, "", method)
                if (method ~ /^(helper|assert|validate|guard|ensure|prepare|format|render)/) next
                buf = $0
                n = 0
                while (n < 12) {
                    if ((getline nxt) <= 0) break
                    buf = buf "\n" nxt
                    n++
                    if (nxt ~ /\{[[:space:]]*$/) break
                    if (nxt ~ /:[[:space:]]*[A-Za-z\\\\|]+[[:space:]]*\{/) break
                }
                if (buf ~ /:[[:space:]]*[A-Za-z\\\\|]*Response/) print method
            }
        ' "${_ctrl_path}" | sort -u)

        for _m in ${_methods}; do
            [ -z "${_m}" ] && continue
            # Use grep -F (fixed string) on the literal `'controller#method'`
            # phrase. Avoids the `\S`-as-regex-metachar trap that hits any
            # `Settings\Foo` slug under grep -E. The narrower phrase
            # (single-quoted controller#method) is unique enough in the file
            # that false positives from comments / docstrings are vanishingly
            # rare.
            if ! grep -qF "'${_ctrl_slug}#${_m}'" appinfo/routes.php; then
                echo "${_ctrl_path} method=${_m} expected_route='${_ctrl_slug}#${_m}' rule=missing-route" >> "${_rr_log}"
            fi
        done
    done < <(_enum_tracked 'Controller\.php$' lib/Controller)

    # ---- Invariant 2: every routed entry resolves to a method that exists.
    grep -oE "'name'\s*=>\s*'[A-Za-z][A-Za-z0-9_\\]*#[a-zA-Z0-9_]+'" appinfo/routes.php \
        | grep -oE "[A-Za-z][A-Za-z0-9_\\]*#[a-zA-Z0-9_]+" | sort -u \
        | while IFS='#' read _ctrl _method; do
            # Resolve controller name → file path. Settings\Foo → Settings/FooController.php.
            # snake_case → camelCase + Controller.php.
            _ctrl_path_from_name() {
                local _name="$1"
                case "${_name}" in
                    *\\*)
                        # Settings\Foo → Settings/FooController.php
                        local _last="${_name##*\\}"
                        local _ns="${_name%\\*}"
                        # SC2155: declare and assign separately so awk's exit
                        # code isn't masked by `local`.
                        local _last_cap
                        _last_cap="$(printf '%s' "${_last}" | awk '{print toupper(substr($0,1,1)) substr($0,2)}')"
                        echo "lib/Controller/${_ns}/${_last_cap}Controller.php"
                        ;;
                    *_*)
                        # snake_case → CamelCase
                        local _camel
                        _camel=$(echo "${_name}" | awk -F'_' '{for(i=1;i<=NF;i++) printf toupper(substr($i,1,1)) substr($i,2); print ""}')
                        echo "lib/Controller/${_camel}Controller.php"
                        ;;
                    *)
                        local _cap
                        _cap=$(printf '%s' "${_name}" | awk '{print toupper(substr($0,1,1)) substr($0,2)}')
                        echo "lib/Controller/${_cap}Controller.php"
                        ;;
                esac
            }
            _path=$(_ctrl_path_from_name "${_ctrl}")
            if [ ! -f "${_path}" ]; then
                # Treat missing controller file as out of this gate's scope —
                # gate-5 (route-auth) already flags this. Skip to avoid duplicates.
                continue
            fi
            # Diff scope: only enforce on changed files so inherited debt
            # doesn't bounce unrelated PRs (per ADR-020).
            _in_scope "${_path}" || continue
            if ! grep -qE "^[[:space:]]*public function ${_method}[[:space:]]*\(" "${_path}"; then
                echo "${_path} route='${_ctrl}#${_method}' rule=method-not-found-on-target-controller" >> "${_rr_log}"
            fi
        done

    _rr_fail=$(wc -l < "${_rr_log}" 2>/dev/null || echo 0)
    if [ "${_rr_fail}" -eq 0 ]; then
        _pass 14 "route-reachability"
    else
        _fail 14 "route-reachability" "${_rr_fail} unrouted method(s) or wrong-target route(s) — see ${_rr_log}"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 15: Dashboard-antipattern — `type:"dashboard"` page whose custom
# widget body slot template renders `<CnDashboardPage>` (= dashboard-in-
# widget-of-dashboard), or `type:"custom"` page whose component renders
# `<CnDashboardPage>` AND is also referenced as a widget body elsewhere.
# Catches the pipelinq triple-"Dashboard" heading cascade documented in
# hydra#316. Static-grep over src/manifest.json + .vue files; runs in
# under a second on the largest apps. See
# scripts/lib/check_dashboard_antipattern.py for the brace-aware slot
# slicer + manifest walker.
# ---------------------------------------------------------------------------
if [ -f src/manifest.json ]; then
    _da_log=/tmp/hydra-gate-dashboard-antipattern.log
    : > "${_da_log}"
    _da_lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/lib" 2>/dev/null && pwd)"
    if [ ! -f "${_da_lib_dir}/check_dashboard_antipattern.py" ]; then
        _da_lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)/lib"
    fi
    if [ -f "${_da_lib_dir}/check_dashboard_antipattern.py" ]; then
        # The helper exits with the number of violations and prints one
        # "<file>:<line> ..." per finding; capture both into the log.
        python3 "${_da_lib_dir}/check_dashboard_antipattern.py" . \
            >> "${_da_log}" 2>/dev/null || true
        # Filter to scope when --scope-to-diff is set — the helper reports
        # absolute paths, so strip the app-dir prefix before comparing.
        if [ "${SCOPE_TO_DIFF}" = "1" ]; then
            _da_tmp=$(mktemp)
            while IFS= read -r _line; do
                [ -z "${_line}" ] && continue
                _f="${_line%%:*}"
                # Convert absolute path back to repo-relative if it lives
                # under the current pwd.
                _rel="${_f#${APP_DIR}/}"
                _in_scope "${_rel}" && echo "${_line}" >> "${_da_tmp}"
            done < "${_da_log}"
            mv "${_da_tmp}" "${_da_log}"
        fi
        _da_fail=$(wc -l < "${_da_log}" 2>/dev/null || echo 0)
    else
        _da_fail=0
        echo "[gate-15] WARN: check_dashboard_antipattern.py not found at ${_da_lib_dir} — gate-15 skipped" >&2
    fi
    if [ "${_da_fail}" -eq 0 ]; then
        _pass 15 "dashboard-antipattern"
    else
        _fail 15 "dashboard-antipattern" "${_da_fail} nested-dashboard pattern(s) — see ${_da_log}"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 16: Spec-coverage — every backend (public/protected) + frontend method
# ADDED or MODIFIED in this PR must carry an `@spec openspec/...` tag in its
# docblock / JSDoc (ADR-003 spec traceability). Diff-scoped at the METHOD
# level (ADR-020): the helper derives the changed-line set itself via
# `git diff -U0` against HYDRA_GATE_BASE_REF, so pre-existing untagged legacy
# methods never block a PR — coverage is enforced going forward only.
# Plumbing (constructors, magic methods, simple accessors, lib/Db, lib/
# Migration, lifecycle hooks, test files, main.js/bootstrap.js) is exempt.
# See scripts/lib/check_spec_coverage.py for the parse + scope logic.
# ---------------------------------------------------------------------------
if [ -d lib ] || [ -d src ]; then
    _sc_log=/tmp/hydra-gate-spec-coverage.log
    : > "${_sc_log}"
    _sc_lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/lib" 2>/dev/null && pwd)"
    if [ ! -f "${_sc_lib_dir}/check_spec_coverage.py" ]; then
        _sc_lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)/lib"
    fi
    if [ -f "${_sc_lib_dir}/check_spec_coverage.py" ]; then
        # The helper self-scopes to the PR diff; feed it our --base so a
        # non-default mainline (e.g. --base main) is honoured. Always diff-
        # scoped — a full-repo @spec sweep would flag the entire legacy
        # surface, which is the wrong contract (ADR-020).
        HYDRA_GATE_BASE_REF="${BASE_REF}" \
            python3 "${_sc_lib_dir}/check_spec_coverage.py" . \
            >> "${_sc_log}" 2>/dev/null || true
        _sc_fail=$(wc -l < "${_sc_log}" 2>/dev/null || echo 0)
    else
        _sc_fail=0
        echo "[gate-16] WARN: check_spec_coverage.py not found at ${_sc_lib_dir} — gate-16 skipped" >&2
    fi
    if [ "${_sc_fail}" -eq 0 ]; then
        _pass 16 "spec-coverage"
    else
        _fail 16 "spec-coverage" "${_sc_fail} changed method(s) missing @spec — see ${_sc_log}"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 17: Redundant CRUD controllers / services (ADR-022)
# ---------------------------------------------------------------------------
# Per ADR-022 (apps-consume-or-abstractions), a controller method or service
# method whose body is a literal pass-through to OpenRegister's ObjectService
# is dead code — the frontend already hits /apps/openregister/api/objects via
# `useObjectStore` from @conduction/nextcloud-vue. Wrapping it in a
# per-schema `MeetingController::index/create/show/update/destroy` plus a
# parallel `MeetingService::create/read/update/delete` ships ~250 lines per
# schema with zero callers.
#
# This gate flags only methods whose NAME shapes like CRUD (index/show/
# create/update/delete/save/find/etc.) AND whose body's effective work is
# one ObjectService call. Domain methods named after the action (publishX,
# transitionY, generateZ, reviseAgenda) escape the filter even when their
# body is short, so state-machine wrappers that just toggle one field
# don't false-positive.
#
# Observed on decidesk#60 (2026-04-19): 5 MeetingController CRUD methods +
# 4 MeetingService CRUD methods, ~260 lines, never called from the
# frontend. Deleted in 2026-04-28 retrofit. This gate prevents the same
# pattern from recurring.
_redundant_log=/tmp/hydra-gate-redundant-controller.log
SCRIPT_DIR_REDUNDANT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Use a bash array so the multi-line `${CHANGED_FILES}` (newline-separated by
# `git diff --name-only`) stays a single argument. Previously the unquoted
# `${_changed_files_arg}` expansion word-split on newlines/spaces, causing
# argparse to reject every file after the first as "unrecognized arguments"
# and the gate to fail spuriously. Observed 2026-05-27 on PR #739 canary.
_redundant_args=()
if [ "${SCOPE_TO_DIFF}" = "1" ] && [ -n "${CHANGED_FILES}" ]; then
    _redundant_args+=("--changed-files=${CHANGED_FILES}")
fi
_redundant_args+=("${APP_DIR}")
if python3 "${SCRIPT_DIR_REDUNDANT}/lib/detect-redundant-controllers.py" \
        "${_redundant_args[@]}" > "${_redundant_log}" 2>&1; then
    _pass 17 "redundant-controller"
elif grep -q '^# count=0$' "${_redundant_log}" 2>/dev/null; then
    # The python script ran cleanly and printed its terminal `# count=0`
    # line — it found zero pass-through controllers. The non-zero exit
    # came from somewhere else (log file permission collision when the
    # same path was first written by a different uid/umask, transient
    # PHP parser error on an unrelated stub, etc.) — NOT from a real
    # finding. Treating as fail would trip Rule 0b's retry loop into
    # 40-turn-per-iter Claude sessions trying to fix code that is by
    # the script's own measure already clean. Observed 2026-05-27 on
    # pipelinq #561 canary-5: builder produced a clean leaf migration
    # (349/349 tests pass, all 19 gates green per its own self-report)
    # but Rule 0b's re-run hit the script's zero-finding non-zero exit
    # and burned 40 turns + $1+ on a fix loop with no fixable code.
    _pass 17 "redundant-controller"
else
    # `grep -c` prints the count (0 on no match); the old `|| echo 0`
    # appended a second "0" on the zero-match exit-1, so the failure
    # message read "0\n0 pass-through method(s)". Drop the fallback.
    _redundant_count=$(grep -c '^lib/' "${_redundant_log}" 2>/dev/null)
    _fail 17 "redundant-controller" "${_redundant_count:-0} pass-through method(s) — see ${_redundant_log}"
fi

# ---------------------------------------------------------------------------
# Gate 18: Notification-dialect — guard the canonical
# x-openregister-notifications dialect (ADR-031). Two checks:
#
#   (a) HARD FAIL — legacy dialect in any lib/Settings/*register*.json. The
#       obsolete dialect (singular `channel`/`recipient`, `lifecycleEnter`,
#       `trigger.calculated`, `idempotencyKey`, `alsoDispatchLifecycle`,
#       `@self.` recipient refs) was migrated off the fleet (scholiq was the
#       last holdout, since-migrated 2026-05-26). The canonical dialect uses
#       plural `channels`/`recipients` arrays, `trigger.type`, and a
#       per-locale `subject` map. Detection is scoped to the
#       x-openregister-notifications block via a JSON-parsing helper —
#       NOT a whole-file grep — because registers legitimately carry `@self.`
#       in aggregation filters and a `channel` property on unrelated schemas;
#       a whole-file grep false-positives on decidesk + scholiq (verified
#       2026-05-26) and a gate that false-positives gets disabled.
#
#   (b) WARNING (non-failing) — imperative object-notification dispatch in a
#       LEAF app: a class whose name ends `NotificationService`, a
#       `createNotification()` + `->notify(` usage, or `implements INotifier`
#       under lib/. ADR-031 says declare x-openregister-notifications instead
#       of hand-rolling an IManager::notify() dispatcher. This is a WARNING,
#       not a FAIL: decidesk (DecisionNotificationService, mid-migration) and
#       launchpad (DashboardShareService + Notification/Notifier) both carry
#       legitimate transitional/non-object-event dispatch, so a hard fail
#       would false-positive. The OpenRegister engine app itself is skipped
#       entirely (it owns lib/Service/Notification/AnnotationNotificationDispatcher.php
#       and legitimately uses IManager::notify()). The warning prints advisory
#       lines for reviewer attention but does NOT increment the failure count.
#
# See ADR-031 "The x-openregister-notifications dialect (canonical)".
# ---------------------------------------------------------------------------
_nd_log=/tmp/hydra-gate-notification-dialect.log
: > "${_nd_log}"
# OpenRegister engine marker — only the engine app ships this dispatcher.
# Its presence suppresses check (b) entirely (the engine legitimately calls
# IManager::notify()).
_nd_is_engine=0
[ -f lib/Service/Notification/AnnotationNotificationDispatcher.php ] && _nd_is_engine=1

# ---- (a) Legacy dialect in register files — HARD FAIL.
# Enumerate the SAME register-JSON surface as gates 51/54/56: `*register*.json`
# anywhere under lib/Settings PLUS every register.d/ fragment (fragments are
# named by topic — `10-bookings-*.json` — so a `*register*` name filter alone
# never sees them). The previous `-maxdepth 1 -name '*register*.json'` read 1 of
# shillinq's 147 register files (0.7%) and 2 of procest's 20 (10%): the legacy
# notification dialect was effectively unpoliced in every fragment-based app.
_nd_register_files=$(_enum_tracked '(register[^/]*\.json|/register\.d/[^/]*\.json)$' lib/Settings | _filter_files_by_scope || true)
if [ -n "${_nd_register_files}" ]; then
    _nd_lib_dir="${SCRIPT_DIR}/lib"
    if [ -f "${_nd_lib_dir}/check_notification_dialect.py" ]; then
        # shellcheck disable=SC2086
        echo "${_nd_register_files}" | while IFS= read -r _rf; do
            [ -n "${_rf}" ] || continue
            python3 "${_nd_lib_dir}/check_notification_dialect.py" "${_rf}" >> "${_nd_log}" 2>/dev/null || true
        done
    else
        echo "[gate-18] WARN: check_notification_dialect.py not found at ${_nd_lib_dir} — legacy-dialect check skipped" >&2
    fi
fi
_nd_fail=$(wc -l < "${_nd_log}" 2>/dev/null || echo 0)

# ---- (b) Imperative dispatch in a leaf app — WARNING only (not a failure).
_nd_warn_log=/tmp/hydra-gate-notification-dialect-warn.log
: > "${_nd_warn_log}"
if [ "${_nd_is_engine}" = "0" ] && [ -d lib ]; then
    # NotificationService-named classes.
    grep -rlE 'class\s+[A-Za-z0-9_]*NotificationService\b' lib/ --include='*.php' 2>/dev/null \
        | _filter_files_by_scope \
        | sed 's/$/: class named *NotificationService (declare x-openregister-notifications instead of imperative dispatch — ADR-031)/' \
        >> "${_nd_warn_log}" || true
    # implements INotifier.
    grep -rlE 'implements\s+[A-Za-z0-9_,\ ]*\bINotifier\b' lib/ --include='*.php' 2>/dev/null \
        | _filter_files_by_scope \
        | sed 's/$/: implements INotifier (declare x-openregister-notifications instead of imperative dispatch — ADR-031)/' \
        >> "${_nd_warn_log}" || true
    # createNotification() + ->notify( in the same file.
    for _pf in $(grep -rlE 'createNotification\s*\(' lib/ --include='*.php' 2>/dev/null | _filter_files_by_scope || true); do
        [ -f "${_pf}" ] || continue
        if grep -qE '->notify\s*\(' "${_pf}" 2>/dev/null; then
            echo "${_pf}: createNotification() + ->notify() dispatch (declare x-openregister-notifications instead of imperative dispatch — ADR-031)" >> "${_nd_warn_log}"
        fi
    done
fi
_nd_warn=$(wc -l < "${_nd_warn_log}" 2>/dev/null || echo 0)

if [ "${_nd_fail}" -eq 0 ]; then
    _pass 18 "notification-dialect"
else
    _fail 18 "notification-dialect" "${_nd_fail} legacy-dialect token(s) in register file(s) — see ${_nd_log}"
fi
if [ "${_nd_warn}" -gt 0 ]; then
    echo "[gate-18] notification-dialect: WARNING — ${_nd_warn} imperative-dispatch site(s) (advisory, non-blocking) — see ${_nd_warn_log}"
fi

# ---------------------------------------------------------------------------
# Gate 19: E2e-coverage — every #### Scenario: in an openspec spec file that
# is ADDED or MODIFIED in a PR must be referenced by at least one Playwright
# e2e test file under tests/e2e/** via an @e2e annotation, OR must carry a
# reason-bearing `@e2e exclude <reason>` in its spec block. A bare
# `@e2e exclude` (no reason) is treated as non-compliant, mirroring gate-16's
# `@spec exclude` rule.
#
# Diff-scoped (ADR-020): only spec files touched by the PR are checked.
# Untouched legacy scenarios in unchanged spec files are never flagged.
#
# A whole spec can be excluded (e.g. pure-backend API contracts covered by
# Newman) by placing `@e2e exclude <reason>` after the spec's ## Purpose
# heading, which suppresses all its scenarios without per-scenario markers.
#
# See scripts/lib/check_e2e_coverage.py for the parse + annotation logic.
# See .claude/skills/hydra-gate-e2e-coverage/SKILL.md for the fix action.
# ---------------------------------------------------------------------------
if [ -d openspec/specs ] || [ -d tests/e2e ]; then
    _e2e_log=/tmp/hydra-gate-e2e-coverage.log
    : > "${_e2e_log}"
    _e2e_lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/lib" 2>/dev/null && pwd)"
    if [ ! -f "${_e2e_lib_dir}/check_e2e_coverage.py" ]; then
        _e2e_lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)/lib"
    fi
    if [ -f "${_e2e_lib_dir}/check_e2e_coverage.py" ]; then
        # check_e2e_coverage.py exits with the uncovered-scenario count (0 = PASS).
        # Capture exit code directly — avoids the grep -c bug where grep exits 1
        # on zero matches, causing "|| echo 0" to append a second "0", leaving
        # _e2e_fail="0\n0" which fails the subsequent -eq integer comparison.
        set +e
        HYDRA_GATE_BASE_REF="${BASE_REF}" \
            python3 "${_e2e_lib_dir}/check_e2e_coverage.py" . \
            >> "${_e2e_log}" 2>/dev/null
        _e2e_fail=$?
        set -e
    else
        _e2e_fail=0
        echo "[gate-19] WARN: check_e2e_coverage.py not found at ${_e2e_lib_dir} — gate-19 skipped" >&2
    fi
    if [ "${_e2e_fail}" -eq 0 ]; then
        _pass 19 "e2e-coverage"
    else
        _fail 19 "e2e-coverage" "${_e2e_fail} scenario(s) missing @e2e — see ${_e2e_log}"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 20: OR ObjectService API — catch calls to fabricated methods that
# don't exist on OpenRegister's ObjectService. The four offenders observed
# in the wild are `findObjects(` (plural — real API is `findAll`),
# `findObject(` (singular — real API is `find`), `createFromArray(`,
# and `deleteFromId(`. PHPStan misses these because OR is baseline-
# suppressed in app repos, so they ship green and only blow up at runtime
# with `BadMethodCallException`. Observed 2026-06-06 on shillinq#123
# (PR #229 SettingsService::seedDimensions invoked `findObjects(...)`
# which would have 500'd on first import) and previously documented in
# the [[or-objectservice-api]] memory note.
#
# Real ObjectService surface (from openregister): find / findAll /
# saveObject / createObject / updateObject / deleteObject. Anything else
# named like an OR call is fabricated.
#
# Scoped to PHP files under lib/, diff-aware when --scope-to-diff is on.
# ---------------------------------------------------------------------------
if [ -d lib ]; then
    _or_log=/tmp/hydra-gate-or-objectservice-api.log
    : > "${_or_log}"
    _or_hits=0
    # Method-call style only — `->findObjects(` etc — to avoid matching
    # legitimately-named methods on other services (notably $context->
    # findObject in plugin code, which doesn't use OR's ObjectService).
    # The leading `->` requires the call to be on an object, which the
    # ObjectService usage always is.
    for _pat in 'findObjects(' 'findObject(' 'createFromArray(' 'deleteFromId('; do
        while IFS= read -r _file; do
            [ -z "${_file}" ] && continue
            _in_scope "${_file}" || continue
            _hits=$(grep -nE "->${_pat//(/\\(}" "${_file}" 2>/dev/null || true)
            [ -z "${_hits}" ] && continue
            # Only flag when the call appears to be on an ObjectService
            # instance — heuristic: the same file references
            # ObjectService\>|objectService\> somewhere. If not, the
            # method name is presumably legitimate on a different class.
            if grep -qE 'ObjectService|objectService' "${_file}" 2>/dev/null; then
                while IFS= read -r _line; do
                    echo "${_file}:${_line}  rule=or-objectservice-fabricated-method (${_pat})" >> "${_or_log}"
                    _or_hits=$((_or_hits + 1))
                done <<< "${_hits}"
            fi
        done < <(_enum_tracked '\.php$' lib)
    done
    if [ "${_or_hits}" -eq 0 ]; then
        _pass 20 "or-objectservice-api"
    else
        _fail 20 "or-objectservice-api" "${_or_hits} call(s) to fabricated OR ObjectService methods (use find / findAll / saveObject / createObject / updateObject / deleteObject) — see ${_or_log}"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 21: conflict-marker scan — catch un-resolved `<<<<<<<` / `=======` /
# `>>>>>>>` markers in tracked source. Observed 2026-06-06 on procest
# #17 (PR #46 DSOIntakeController.php), #12 (PR #41 appinfo/routes.php),
# #10 (PR #42 package.json + l10n/{en,nl}.{js,json}): the Builder's
# `fix(code-review bounded): Juan post-run mechanical commit` step
# committed raw conflict markers without resolving them, producing
# branches that no longer parsed PHP/JSON. The Codeberg "mergeable:
# true" flag is not a reliable proxy because that check only inspects
# diff base, not file syntax.
#
# This gate fails fast at build/review time, BEFORE the orchestrator
# flips a label, so the orphaned-merge state never reaches review.
#
# Scope: all PHP/JS/TS/Vue/JSON/MD files in repo (or diff-scoped when
# --scope-to-diff is on). The marker pattern is anchored to start-of-
# line + at least 7 chars + space, which is git's canonical conflict
# marker shape and unlikely to collide with prose / code.
# ---------------------------------------------------------------------------
_cm_log=/tmp/hydra-gate-conflict-markers.log
: > "${_cm_log}"
_cm_hits=0
# Match git's exact marker shapes: `<<<<<<< ` / `======= ` (end of line OK) / `>>>>>>> `
# at the start of a line. Length is exactly 7 chars of the marker glyph; the
# trailing content for << / >> is a ref name, ======= can be bare.
while IFS= read -r _file; do
    [ -z "${_file}" ] && continue
    [ ! -f "${_file}" ] && continue
    _in_scope "${_file}" || continue
    # grep -l would short-circuit but we want a line count for the log.
    _matches=$(grep -nE '^(<{7}[[:space:]]|>{7}[[:space:]]|={7}$)' "${_file}" 2>/dev/null || true)
    [ -z "${_matches}" ] && continue
    echo "${_file}:" >> "${_cm_log}"
    echo "${_matches}" | head -5 | sed 's/^/  /' >> "${_cm_log}"
    _cm_hits=$((_cm_hits + 1))
done < <(find lib appinfo src tests openspec l10n appinfo \
            \( -name '*.php' -o -name '*.js' -o -name '*.ts' \
             -o -name '*.vue' -o -name '*.json' -o -name '*.md' \
             -o -name '*.yaml' -o -name '*.yml' -o -name '*.xml' \) \
             2>/dev/null)
if [ "${_cm_hits}" -eq 0 ]; then
    _pass 21 "conflict-markers"
else
    _fail 21 "conflict-markers" "${_cm_hits} file(s) with unresolved conflict markers — see ${_cm_log}"
fi

# ---------------------------------------------------------------------------
# Gate 22: manifest-validation — every app that ships src/manifest.json must
# validate it against the canonical @conduction/nextcloud-vue schema. Per
# ADR-024 (app-manifest fleet-wide adoption) and openspec/changes/
# adopt-app-manifest. Apps without a manifest (Tier 0) are silently skipped.
#
# Behavior:
#   - No src/manifest.json   → skip (PASS quietly, no log line)
#   - Has src/manifest.json:
#       * Run `npm run check:manifest` if defined in package.json
#       * Otherwise fall back to a thin Node one-liner that imports
#         validateManifest from @conduction/nextcloud-vue and runs it
#       * If the library is missing from node_modules → log warning + PASS
#         (fail-open per spec — apps mid-migration may not have installed
#         the renderer yet)
#       * If validateManifest reports errors → FAIL with error count
#
# Skill: .claude/skills/hydra-gate-manifest-validation/SKILL.md
# Spec: openspec/changes/adopt-app-manifest/specs/adopt-app-manifest/spec.md
# ---------------------------------------------------------------------------
if [ -f src/manifest.json ]; then
    _mv_log=/tmp/hydra-gate-manifest-validation.log
    : > "${_mv_log}"
    _mv_fail=0
    # Diff-scope: when --scope-to-diff is set and src/manifest.json was NOT
    # touched in this PR, the gate runs informationally (PASS without
    # spending time on a clean manifest the PR didn't touch).
    if [ "${SCOPE_TO_DIFF}" = "1" ] && ! _in_scope "src/manifest.json"; then
        _pass 22 "manifest-validation"
    else
        # Prefer the package.json `check:manifest` script — apps adopting
        # the convention add it per ADR-024.
        if [ -f package.json ] && grep -q '"check:manifest"' package.json 2>/dev/null; then
            if npm run --silent check:manifest >> "${_mv_log}" 2>&1; then
                _pass 22 "manifest-validation"
            else
                _mv_fail=$(grep -cE 'at /|error:|ERROR' "${_mv_log}" 2>/dev/null || echo 1)
                [ "${_mv_fail}" -eq 0 ] && _mv_fail=1
                _fail 22 "manifest-validation" "${_mv_fail} schema violation(s) in src/manifest.json — see ${_mv_log}"
            fi
        elif [ -f node_modules/@conduction/nextcloud-vue/src/utils/validateManifest.js ] \
          || [ -f node_modules/@conduction/nextcloud-vue/dist/utils/validateManifest.js ]; then
            # Fallback: invoke validateManifest directly via node one-liner.
            # Apps that haven't wired `check:manifest` into package.json yet
            # still get gated, as long as the library is installed.
            node -e "
                const fs = require('fs');
                const path = require('path');
                let validateManifest;
                try {
                    validateManifest = require('@conduction/nextcloud-vue/utils/validateManifest').validateManifest
                        || require('@conduction/nextcloud-vue').validateManifest;
                } catch (e) {
                    console.error('validateManifest library not installed; skipping');
                    process.exit(0);
                }
                if (typeof validateManifest !== 'function') {
                    console.error('validateManifest export missing — library version mismatch; skipping');
                    process.exit(0);
                }
                const manifest = JSON.parse(fs.readFileSync('src/manifest.json', 'utf8'));
                const result = validateManifest(manifest);
                if (result && result.valid === false) {
                    for (const err of (result.errors || [])) {
                        console.error('at ' + (err.instancePath || err.dataPath || '/') + ': ' + (err.message || JSON.stringify(err)));
                    }
                    process.exit(1);
                }
                process.exit(0);
            " >> "${_mv_log}" 2>&1
            _rc=$?
            if [ "${_rc}" -eq 0 ]; then
                _pass 22 "manifest-validation"
            else
                _mv_fail=$(grep -cE '^at /' "${_mv_log}" 2>/dev/null || echo 1)
                [ "${_mv_fail}" -eq 0 ] && _mv_fail=1
                _fail 22 "manifest-validation" "${_mv_fail} schema violation(s) in src/manifest.json — see ${_mv_log}"
            fi
        else
            # Fail-open per spec: missing library is treated as warning + PASS.
            echo "validateManifest library not installed; skipping" >> "${_mv_log}"
            _pass 22 "manifest-validation"
        fi
    fi
fi

# ---------------------------------------------------------------------------
# Gate 23: OR abstraction anti-patterns — single shared grep gate backing the
# seven `consume-or-*-fleet-wide` umbrellas + `optional-integration-pattern`.
# Per ADR-022 (apps-consume-or-abstractions): apps must not re-grow approval
# chains, audit-trail listeners, tenant middleware, RBAC services, workflow
# engines, or hit shared-PDOK directly — those live in OpenRegister /
# openconnector. Script ships in WARN mode for the first 90 days post-
# acceptance, then auto-switches to BLOCK on the bake-in epoch.
#
# Source-of-truth script: scripts/lint-or-abstraction-anti-patterns.sh
# (covers the seven anti-pattern families; exit code 0 in WARN mode, 1 in
# BLOCK mode when any match is found).
#
# Spec refs:
#   - openspec/changes/consume-or-approval-workflow-fleet-wide/tasks.md HYDRA-1.2
#   - openspec/changes/consume-or-audit-trail-fleet-wide/tasks.md HYDRA-1.2
#   - openspec/changes/consume-or-rbac-fleet-wide/tasks.md HYDRA-1.2
#   - openspec/changes/consume-or-tenant-fleet-wide/tasks.md HYDRA-1.2
#   - openspec/changes/consume-or-workflow-engine-fleet-wide/tasks.md HYDRA-1.2
#   - openspec/changes/shared-pdok-via-openconnector/tasks.md
# ---------------------------------------------------------------------------
_or_abs_log=/tmp/hydra-gate-or-abstraction-anti-patterns.log
: > "${_or_abs_log}"
# Skip when lib/ is absent (frontend-only repo).
if [ -d lib ]; then
    _or_abs_script=""
    # Prefer the colocated script from SCRIPT_DIR so the gate runs even when
    # invoked against an app dir (the script lives in hydra/scripts/, not
    # the app dir).
    if [ -f "${SCRIPT_DIR}/lint-or-abstraction-anti-patterns.sh" ]; then
        _or_abs_script="${SCRIPT_DIR}/lint-or-abstraction-anti-patterns.sh"
    elif [ -f scripts/lint-or-abstraction-anti-patterns.sh ]; then
        _or_abs_script="scripts/lint-or-abstraction-anti-patterns.sh"
    fi
    if [ -n "${_or_abs_script}" ]; then
        # Script defaults its search root to `lib` when no arg is passed.
        if bash "${_or_abs_script}" lib >> "${_or_abs_log}" 2>&1; then
            _pass 23 "or-abstraction-anti-patterns"
        else
            # In BLOCK mode (post bake-in epoch) the script exits 1 on any
            # match. Count the per-rule lines in the log.
            _or_abs_hits=$(grep -cE '^\s+\[' "${_or_abs_log}" 2>/dev/null || echo 0)
            [ "${_or_abs_hits}" -eq 0 ] && _or_abs_hits=1
            _fail 23 "or-abstraction-anti-patterns" "${_or_abs_hits} OR-abstraction match(es) — see ${_or_abs_log}"
        fi
    else
        # Script missing — fail-open (don't block CI when the gate's own
        # helper is unavailable; the umbrella-spec retro-fit will land it).
        echo "lint-or-abstraction-anti-patterns.sh helper not found; skipping gate" >> "${_or_abs_log}"
        _pass 23 "or-abstraction-anti-patterns"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 24: ADR-019 integration parity — every registered render-surface
# integration in @conduction/nextcloud-vue MUST declare a COMPLETE render pair
# for its declared `renderMode` (AD-11/AD-13, extended by ADR-066 decision #7):
#   * renderMode: 'component' (default) → a sidebar `tab` AND a `widget` SFC
#     pair, exactly as before (unchanged behaviour, backward compatible).
#   * renderMode: 'mount'              → a `mount(el, props)` AND an `unmount(el)`
#     function pair instead — a cross-Vue-major leaf ships no SFC tab/widget and
#     satisfies parity with the mount pair.
# The parity contract therefore moved from the literal "tab AND widget" to "a
# complete render pair for the declared renderMode", keeping the AD-11/AD-13
# guarantee that a render-surface leaf can actually render while admitting the
# mount shape. The canonical Node check ships in nextcloud-vue
# (`scripts/check-integration-parity.js`); openregister carries a thin bash
# wrapper at `scripts/check-integration-parity.sh` that locates the JS check
# (env override / installed dep / sibling checkout) and exits 0-skip when
# neither is available.
#
# This gate looks for the wrapper in the app dir; when absent (app has no
# integration descriptors of its own), it skips silently. When present, the
# wrapper's own resolution logic decides between RUN (JS check found) and
# SKIP (JS check absent — authoritative gate runs in nextcloud-vue CI). The
# orchestrator gate is the "additional safety net" called out in
# `openregister/openspec/changes/pluggable-integration-registry/tasks.md`.
#
# ADR-066 (cross-app-leaf-registration) Decision 4 — extended by Decision 7 —
# adds a server↔JS descriptor↔`id` correlation for `render-surface` leaves that
# also asserts renderMode AGREEMENT: the server `LeafDescriptor.renderMode` MUST
# equal the JS registration's `renderMode` under the shared `id`. The
# nextcloud-vue check (`scripts/check-integration-parity.js`) runs a WARN-only
# cross-reference against the repo it executes in (process.cwd() — which is the
# app dir here, since this gate cd's into it): it correlates server-side
# render-surface `LeafDescriptor` ids + renderMode (scanned from lib/**.php
# `new LeafDescriptor(...)`) against JS `registerIntegration({ id, renderMode })`
# call sites (src/**), flagging BOTH ways — a phantom render surface (a
# descriptor discoverable in the `openregister.integrations.leaves` capability
# whose JS pair never registered), an orphan JS registration (a pair with no
# server descriptor), and a renderMode MISMATCH under a shared id (server says
# 'component' while JS registered 'mount', or vice-versa). It is WARN-first per
# the fleet's gate bake-in pattern: the cross-ref NEVER changes the JS check's
# exit code, so it cannot fail this gate — advisory `⚠` lines are surfaced below
# on PASS for the bake-in epoch. Only the HARD render-pair-for-renderMode parity
# check (AD-11/AD-13, renderMode-aware per Decision 7) can fail gate-24 today,
# and only when it already hard-fails — this extension does NOT tighten the
# gate's fail posture. Promotion of the cross-ref to a blocking check, plus the
# deferred cross-repo join (this library's own builtins ↔ each consuming app's
# PHP, and a live capability-payload assertion), is tracked as an ADR-066
# follow-up.
#
# Spec ref: openspec/changes/pluggable-integration-registry/tasks.md
#           (hydra-side bullet "Add parity check to hydra quality gate");
#           openspec/architecture/adr-066-cross-app-leaf-registration.md
#           (Decision 4 — parity correlation is a gate-24 concern; Decision 7 —
#           renderMode-keyed render pair + server↔JS renderMode agreement).
# ---------------------------------------------------------------------------
_parity_log=/tmp/hydra-gate-integration-parity.log
: > "${_parity_log}"
if [ -f scripts/check-integration-parity.sh ]; then
    if bash scripts/check-integration-parity.sh >> "${_parity_log}" 2>&1; then
        # The WARN-only ADR-066 cross-ref advisory lines start with `⚠`/its
        # bullets; surface them on PASS so a phantom/orphan leaf is visible in
        # CI during the bake-in epoch (they never fail the gate).
        if grep -q '⚠ server↔JS leaf parity' "${_parity_log}" 2>/dev/null; then
            echo "  [gate-24] ADR-066 server↔JS leaf parity — advisory warnings (WARN-only):"
            grep -E '^(⚠|  - )' "${_parity_log}" 2>/dev/null | sed 's/^/    /'
        fi
        _pass 24 "integration-parity"
    else
        # WARN-only advisory lines carry "phantom"/"orphan"/"NO matching" and a
        # `⚠` header — never "missing"/"mismatch"/`^✗` — so this hard-failure
        # count excludes them by construction.
        _parity_hits=$(grep -cE '^✗|missing|mismatch' "${_parity_log}" 2>/dev/null || echo 0)
        [ "${_parity_hits}" -eq 0 ] && _parity_hits=1
        _fail 24 "integration-parity" "${_parity_hits} parity violation(s) — see ${_parity_log}"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 25: Contract-coverage — every controller method ADDED in this PR that is
# registered in appinfo/routes.php AND publicly reachable (#[PublicPage] /
# #[NoAdminRequired]) is a new network-facing endpoint and MUST be covered by an
# automated contract test: a Newman/Postman collection assertion under
# tests/integration/*.postman_collection.json that hits its URL, OR a PHPUnit
# controller test under tests/** that exercises the method, OR a reason-bearing
# `@contract exclude <reason>` in its docblock. A bare `@contract exclude` is
# non-compliant (mirrors gate-16/gate-19's exclude rule).
#
# API-layer companion to gate-19 (UI e2e) + gate-16 (spec). Closes the loop so a
# newly-exposed endpoint can never merge without a wire-contract proof. Diff-
# scoped (ADR-020): only methods whose declaration line was ADDED are checked, so
# pre-existing endpoints (legacy debt) never block a PR.
#
# See scripts/lib/check_contract_coverage.py for the route-table + diff logic.
# See .claude/skills/hydra-gate-contract-coverage/SKILL.md for the fix action.
# ---------------------------------------------------------------------------
if [ -f appinfo/routes.php ]; then
    _cc_log=/tmp/hydra-gate-contract-coverage.log
    : > "${_cc_log}"
    _cc_lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/lib" 2>/dev/null && pwd)"
    if [ ! -f "${_cc_lib_dir}/check_contract_coverage.py" ]; then
        _cc_lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)/lib"
    fi
    if [ -f "${_cc_lib_dir}/check_contract_coverage.py" ]; then
        # The helper exits with the uncovered-endpoint count (0 = PASS). Capture
        # the exit code directly — avoids the grep -c double-zero bug.
        set +e
        HYDRA_GATE_BASE_REF="${BASE_REF}" \
            python3 "${_cc_lib_dir}/check_contract_coverage.py" . \
            >> "${_cc_log}" 2>/dev/null
        _cc_fail=$?
        set -e
    else
        _cc_fail=0
        echo "[gate-25] WARN: check_contract_coverage.py not found at ${_cc_lib_dir} — gate-25 skipped" >&2
    fi
    if [ "${_cc_fail}" -eq 0 ]; then
        _pass 25 "contract-coverage"
    else
        _fail 25 "contract-coverage" "${_cc_fail} new public endpoint(s) missing a contract test — see ${_cc_log}"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 26: Visual-coverage — every new Vue page/view component ADDED in this PR
# (a .vue file added under src/views/ | src/pages/, OR a component referenced as
# a manifest `"type":"page"` entry whose file was added) MUST have a visual-
# regression proof: a spec/baseline under tests/e2e/visual/** referencing it, OR
# an e2e workflow test under tests/e2e/** that drives it, OR a reason-bearing
# `@visual exclude <reason>` marker inside the .vue file. A bare `@visual
# exclude` is non-compliant (mirrors gate-16/gate-19/gate-25's exclude rule).
#
# Visual-layer companion to gate-19 (behavioural e2e) + gate-25 (API contract).
# New screens cannot merge without a pixel/structural baseline or an audited
# waiver. Diff-scoped (ADR-020): only ADDED page components are checked, so
# untouched legacy pages never block a PR.
#
# See scripts/lib/check_visual_coverage.py for the page discovery + diff logic.
# See .claude/skills/hydra-gate-visual-coverage/SKILL.md for the fix action.
# ---------------------------------------------------------------------------
if [ -d src ]; then
    _vc_log=/tmp/hydra-gate-visual-coverage.log
    : > "${_vc_log}"
    _vc_lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/lib" 2>/dev/null && pwd)"
    if [ ! -f "${_vc_lib_dir}/check_visual_coverage.py" ]; then
        _vc_lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)/lib"
    fi
    if [ -f "${_vc_lib_dir}/check_visual_coverage.py" ]; then
        set +e
        HYDRA_GATE_BASE_REF="${BASE_REF}" \
            python3 "${_vc_lib_dir}/check_visual_coverage.py" . \
            >> "${_vc_log}" 2>/dev/null
        _vc_fail=$?
        set -e
    else
        _vc_fail=0
        echo "[gate-26] WARN: check_visual_coverage.py not found at ${_vc_lib_dir} — gate-26 skipped" >&2
    fi
    if [ "${_vc_fail}" -eq 0 ]; then
        _pass 26 "visual-coverage"
    else
        _fail 26 "visual-coverage" "${_vc_fail} new page component(s) missing a visual baseline — see ${_vc_log}"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 27: No-phantom-cross-app-rpc — forbid the phantom cross-app *RPC*
# patterns ADR-041 (decision #2) bans. A cross-app *command* (one app
# invoking another Conduction NC app's business action) MUST use a typed
# IEventDispatcher event (the RequestedEvent + synchronous result-slot +
# ConcludedEvent recipe in ADR-041), NOT the OpenRegister integration
# registry, NOT a non-existent integration service, NOT a server-side HTTP
# call to a sibling app's REST route. Every historical cross-app delegation
# built this way was a phantom no-op (failed closed, never reached the
# target). This gate stops the pattern recurring.
#
# Four rules (see scripts/lib/check_phantom_cross_app_rpc.py):
#   A  ->getLeaf(           — registry has no getLeaf; always phantom
#   B  ->call('<appId>',…)  — quoted FLEET app id as 1st arg = registry RPC
#                             (legit dispatchers take an OBJECT 1st arg, so
#                              OpenConnector external-source dispatch never
#                              matches)
#   C  OCA\OpenRegister\Service\IntegrationService — class does not exist
#                             (real classes live under …\Service\Integration\,
#                              app-local *IntegrationService classes excluded)
#   D  IClientService ->post/->get to a SIBLING app's linkToRoute('<app>.…')
#                             WITHOUT session-forwarding (Cookie / OCS-
#                             APIRequest / requesttoken / allow_local_address).
#                             Session-forwarding in-cluster delegation is
#                             RBAC-respecting and is NOT flagged.
#
# Diff-scoped (ADR-020): only files changed vs BASE are scanned, so legacy
# debt in untouched files never blocks an unrelated PR. The canonical
# replacement recipe is in the change spec + ADR-041.
#
# See .claude/skills/hydra-gate-no-phantom-cross-app-rpc/SKILL.md for the
# detection algorithm and the fix action (the event-contract recipe).
# ---------------------------------------------------------------------------
_pcar_log=/tmp/hydra-gate-no-phantom-cross-app-rpc.log
: > "${_pcar_log}"
_pcar_files=()
# Audit lib/ PHP (the command-dispatch site) and src/ JS/Vue/TS (a phantom
# getLeaf could also live in a frontend store calling an OR endpoint).
while IFS= read -r f; do
    [ -f "$f" ] || continue
    _in_scope "$f" || continue
    _pcar_files+=("$f")
done < <(find lib src \( -name '*.php' -o -name '*.vue' -o -name '*.js' -o -name '*.ts' \) \
    -not -path '*/vendor/*' -not -path '*/node_modules/*' \
    -not -path '*/dist/*' -not -path '*/build/*' 2>/dev/null)
if [ "${#_pcar_files[@]}" -gt 0 ]; then
    _pcar_lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/lib" 2>/dev/null && pwd)"
    if [ ! -f "${_pcar_lib_dir}/check_phantom_cross_app_rpc.py" ]; then
        _pcar_lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)/lib"
    fi
    if [ -f "${_pcar_lib_dir}/check_phantom_cross_app_rpc.py" ]; then
        python3 "${_pcar_lib_dir}/check_phantom_cross_app_rpc.py" "${_pcar_files[@]}" \
            >> "${_pcar_log}" 2>/dev/null || true
    else
        echo "[gate-27] WARN: check_phantom_cross_app_rpc.py not found at ${_pcar_lib_dir} — gate-27 skipped" >&2
    fi
fi
# Count findings. NOTE: gates 25/26 above leave `set -e` ENABLED, so a
# `grep -c .` on an empty log (exit 1, no matches) would kill the script
# here. Disable errexit for the count, then restore. wc -l avoids the
# grep -c double-zero bug entirely (always exits 0, prints the line count).
set +e
_pcar_fail=$(wc -l < "${_pcar_log}" 2>/dev/null | tr -d ' ')
set -e
[ -z "${_pcar_fail}" ] && _pcar_fail=0
if [ "${_pcar_fail}" -eq 0 ]; then
    _pass 27 "no-phantom-cross-app-rpc"
else
    _fail 27 "no-phantom-cross-app-rpc" "${_pcar_fail} phantom cross-app RPC pattern(s) — use the ADR-041 event recipe; see ${_pcar_log}"
fi

# ---------------------------------------------------------------------------
# Gate 28: License triangle — every per-file `@license` PHPDoc tag in lib/ + the
# `license` field in composer.json MUST agree (Conduction convention: EUPL-1.2).
# Gate-1 (SPDX) only checks PRESENCE of the @license tag; this gate checks the
# VALUES line up across the three locations a Conduction app declares its
# license: composer.json (.license), appinfo/info.xml (<licence>), per-file
# @license PHPDoc tags.
#
# Exception: appinfo/info.xml's <licence>agpl</licence> is the legacy Nextcloud
# appstore signal that the app is published under EUPL-1.2 (the appstore taxonomy
# pre-dates EUPL); per ADR-014 we accept that drift on info.xml ONLY. composer
# .json and per-file headers must agree.
# ---------------------------------------------------------------------------
_lt_log=/tmp/hydra-gate-license-triangle.log
: > "${_lt_log}"
_composer_lic=""
if [ -f composer.json ]; then
    # composer.json's `license` may be a string ("EUPL-1.2") or an array of
    # SPDX identifiers (`["EUPL-1.2", "MIT"]` for dual-licensed projects).
    # Emit pipe-joined so the bash check can match a file's @license value
    # against ANY entry in the set.
    _composer_lic=$(python3 -c "
import json, sys
try:
    v = json.load(open('composer.json')).get('license', '')
    if isinstance(v, list):
        print('|'.join(str(x) for x in v))
    else:
        print(v)
except Exception:
    print('')
" 2>/dev/null)
fi
if [ -n "${_composer_lic}" ] && [ -d lib ]; then
    # Collect every distinct @license value in lib/**/*.php files in scope
    while IFS= read -r _php; do
        [ -z "${_php}" ] && continue
        _in_scope "${_php}" || continue
        _file_lic=$(grep -oE '^[[:space:]]*\*[[:space:]]*@license[[:space:]]+[^[:space:]*]+' "${_php}" 2>/dev/null \
            | head -1 | awk '{print $3}')
        if [ -z "${_file_lic}" ]; then continue; fi
        # Member-of check against the pipe-joined composer license set.
        case "|${_composer_lic}|" in
            *"|${_file_lic}|"*) ;;   # file license is in the allowed set
            *)
                echo "${_php} file_license=${_file_lic} composer_license=${_composer_lic} rule=license-triangle-drift" >> "${_lt_log}"
                ;;
        esac
    done < <(_enum_tracked '\.php$' lib)
fi
_lt_fail=$(wc -l < "${_lt_log}" 2>/dev/null || echo 0)
if [ "${_lt_fail}" -eq 0 ]; then
    _pass 28 "license-triangle"
else
    _fail 28 "license-triangle" "${_lt_fail} file(s) with @license != composer.json — see ${_lt_log}"
fi

# ---------------------------------------------------------------------------
# Gate 29: Gitignore-then-commit oversight — the PR adds a path to .gitignore
# AND has tracked files at exactly that path. The ignore rule only prevents
# future re-adds; existing tracked files persist until `git rm --cached <path>`.
# Observed: opencatalogi#539 (116 .phpunit.cache/ files shipped to main
# alongside a new .phpunit.cache/ ignore rule). Only fires under --scope-to-diff
# because the check is intrinsically diff-relative.
# ---------------------------------------------------------------------------
_gi_log=/tmp/hydra-gate-gitignore-then-commit.log
: > "${_gi_log}"
if [ "${SCOPE_TO_DIFF}" = "1" ] && [ -f .gitignore ]; then
    # Lines newly added to .gitignore in this PR (excluding blanks + comments)
    _new_ignores=$(git -c safe.directory='*' diff "${BASE_REF}...HEAD" -- .gitignore 2>/dev/null \
        | grep -E '^\+[^+]' | sed 's/^+//' | grep -vE '^\s*(#|$)' || true)
    if [ -n "${_new_ignores}" ]; then
        while IFS= read -r _pat; do
            [ -z "${_pat}" ] && continue
            # Strip leading slash + trailing slash to get the directory/file
            # prefix to match against `git ls-files` output.
            _prefix=$(echo "${_pat}" | sed -E 's|^/||; s|/$||; s|^\!||')
            [ -z "${_prefix}" ] && continue
            # Skip wildcard-only entries (e.g. "*.log") — they'd match too broadly
            # in `git ls-files` and the real signal is path-prefix shape.
            case "${_prefix}" in
                \**|*\*\**) continue ;;
            esac
            # Find tracked files whose path starts with the prefix (cap at 5)
            git ls-files 2>/dev/null | grep -E "^${_prefix}(/|$)" | head -5 \
                | while IFS= read -r _tracked; do
                    [ -z "${_tracked}" ] && continue
                    echo "ignore_pattern=${_pat} tracked_file=${_tracked} rule=gitignore-then-commit-oversight" >> "${_gi_log}"
                done
        done <<< "${_new_ignores}"
    fi
fi
_gi_fail=$(wc -l < "${_gi_log}" 2>/dev/null || echo 0)
if [ "${_gi_fail}" -eq 0 ]; then
    _pass 29 "gitignore-then-commit"
else
    _fail 29 "gitignore-then-commit" "${_gi_fail} tracked file(s) at newly-ignored path(s) — see ${_gi_log}"
fi

# ---------------------------------------------------------------------------
# Gate 30: Public-monitoring — controllers with monitoring-shaped route names
# (metrics, health, liveness, readiness, probe) MUST be annotated `#[PublicPage]`
# / `@PublicPage`. Without it, NC middleware defaults to admin-login-required
# and the route silently 401s/redirects to /login for the actual consumer
# (Prometheus scraper, kubelet, external uptime monitor). Gate-5 (route-auth)
# only verifies SOME annotation is present — this gate verifies the right one
# is present for monitoring callers.
# ---------------------------------------------------------------------------
_pm_log=/tmp/hydra-gate-public-monitoring.log
: > "${_pm_log}"
if [ -f appinfo/routes.php ] && [ -d lib/Controller ]; then
    # Find route entries whose `name` looks like `<monitoring-word>#<method>`
    grep -oE "['\"]\s*name['\"]\s*=>\s*['\"][a-zA-Z0-9_\\\\]*(metrics|health|liveness|readiness|probe)[a-zA-Z0-9_]*#[a-zA-Z0-9_]+['\"]" appinfo/routes.php 2>/dev/null \
        | grep -oE "[a-zA-Z0-9_\\\\]*(metrics|health|liveness|readiness|probe)[a-zA-Z0-9_]*#[a-zA-Z0-9_]+" | sort -u \
        | while IFS='#' read _ctrl _method; do
            [ -z "${_ctrl}" ] && continue
            [ -z "${_method}" ] && continue
            # Map snake_case route slug → PascalCase file basename. Real apps
            # use `metrics_internal#index` (route) → `MetricsInternalController.php`.
            # The single-char `toupper(substr(...,1,1))` form preserves underscores
            # → `Metrics_internal` which doesn't exist on disk → silent skip.
            # Gate-5 already uses the awk -F'_' pattern; copy it verbatim.
            _ctrl_cap=$(printf '%s' "${_ctrl}" | awk -F'_' '{for(i=1;i<=NF;i++) printf toupper(substr($i,1,1)) substr($i,2); print ""}')
            _ctrl_path="lib/Controller/${_ctrl_cap}Controller.php"
            [ ! -f "${_ctrl_path}" ] && continue
            _in_scope "${_ctrl_path}" || continue
            _method_line=$(grep -nE "^[[:space:]]*public function ${_method}[[:space:]]*\(" "${_ctrl_path}" | head -1 | cut -d: -f1)
            [ -z "${_method_line}" ] && continue
            # Inspect annotations above the method declaration (up to 20 lines back)
            _ann_start=$((_method_line > 20 ? _method_line - 20 : 1))
            _annotations=$(sed -n "${_ann_start},${_method_line}p" "${_ctrl_path}")
            if ! echo "${_annotations}" | grep -qE '#\[PublicPage\]|@PublicPage\b'; then
                echo "${_ctrl_path}:${_method_line} method=${_method} rule=monitoring-endpoint-missing-public-page" >> "${_pm_log}"
            fi
        done
fi
_filter_preexisting "${_pm_log}"
_pm_fail=$(wc -l < "${_pm_log}" 2>/dev/null || echo 0)
if [ "${_pm_fail}" -eq 0 ]; then
    _pass 30 "public-monitoring"
else
    _fail 30 "public-monitoring" "${_pm_fail} monitoring endpoint(s) missing @PublicPage — see ${_pm_log}"
fi
# ---------------------------------------------------------------------------
# Gate 31: Img-alt — every `<img>` tag in .vue files must declare an `alt` /
# `:alt` / `v-bind:alt` attribute. Per WCAG 2.2 AA SC 1.1.1 (Non-text Content),
# `<img>` elements need a text alternative; decorative images get `alt=""`.
# Without it, screen-reader users hear the image filename or nothing.
#
# Scope: literal `<img ...>` tags in template/SFC sections of `.vue` files.
# Excludes `<NcAvatarMenu>` / `<NcUserBubble>` / other component wrappers —
# those handle accessibility internally per their own component contract.
#
# References:
#   - ADR-010 (NL Design — WCAG 2.2 AA)
#   - openspec/architecture/wcag-coverage.md SC 1.1.1
# ---------------------------------------------------------------------------
if [ -d src ]; then
    _ia_log=/tmp/hydra-gate-img-alt.log
    : > "${_ia_log}"
    while IFS= read -r vue; do
        _in_scope "${vue}" || continue
        # Flatten multi-line attribute lists so a single grep can match the
        # opening tag including all its attributes.
        _flat=$(tr '\n' ' ' < "${vue}")
        echo "${_flat}" \
            | grep -oE '<img\b[^>]*>' 2>/dev/null \
            | while IFS= read -r tag; do
                [ -z "${tag}" ] && continue
                # Any of: `alt=`, `:alt=`, `v-bind:alt=`, `alt-text=` (some
                # Conduction components proxy the prop under this name).
                if ! echo "${tag}" | grep -qE '(^|[[:space:]])(:?alt|v-bind:alt|alt-text)='; then
                    echo "${vue}: ${tag}" >> "${_ia_log}"
                fi
            done
    done < <(find src -name '*.vue' 2>/dev/null)
    _ia_fail=$(wc -l < "${_ia_log}" 2>/dev/null || echo 0)
    if [ "${_ia_fail}" -eq 0 ]; then
        _pass 31 "img-alt"
    else
        _fail 31 "img-alt" "${_ia_fail} <img> tag(s) without alt attribute — see ${_ia_log}"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 32: Semantic-controls — `<div>` / `<span>` / `<a>` (without href) /
# generic block elements carrying a `@click` (or `v-on:click`) handler MUST
# also declare `role="button"` (or another interactive role) AND a `tabindex`
# AND a keyboard handler (`@keydown` / `@keyup` / `@keypress`). Without all
# three, the control is mouse-only — fails WCAG 2.2 AA SC 2.1.1 (Keyboard)
# and 4.1.2 (Name, Role, Value) because screen readers see a non-interactive
# element with a click handler.
#
# The right fix is almost always to use `<NcButton>` / `<button>` / `<a href>`
# — built-in keyboard handling, focus styling, and correct role.
#
# Scope: literal HTML tags in `.vue` templates. Component wrappers
# (`<NcButton>`, `<NcActionButton>`, `<NcListItem>`, etc.) handle this
# internally and are not in scope. `<a href="...">` is excluded because a
# real anchor is keyboard-accessible by default.
#
# References:
#   - ADR-010 (NL Design — WCAG 2.2 AA)
#   - openspec/architecture/wcag-coverage.md SC 2.1.1, 4.1.2
# ---------------------------------------------------------------------------
if [ -d src ]; then
    _sc_log=/tmp/hydra-gate-semantic-controls.log
    : > "${_sc_log}"
    while IFS= read -r vue; do
        _in_scope "${vue}" || continue
        _flat=$(tr '\n' ' ' < "${vue}")
        # Match opening tags of non-semantic block/inline elements that have
        # a click binding. `<a` is included but filtered below if `href` is
        # also present.
        echo "${_flat}" \
            | grep -oE '<(div|span|a|p|li|article|section|header|footer|aside|main|nav)\b[^>]*(@click|v-on:click)[^>]*>' 2>/dev/null \
            | while IFS= read -r tag; do
                [ -z "${tag}" ] && continue
                # Real anchor with href = native keyboard-accessible; skip.
                if echo "${tag}" | grep -qE '^<a\b[^>]*\bhref='; then
                    continue
                fi
                # Event-management-only handlers don't represent user
                # interactions and shouldn't trigger the gate:
                #   - `@click.stop` with no value     — pure event stop-propagation
                #   - `@click.stop=""`                — same, explicit empty
                # Only skip when the click is .stop AND there's no other
                # `@click` (i.e. no real action handler on the tag). This
                # closes the false-positive observed on opencatalogi
                # PublicationCard.vue `<div @click.stop>` wrappers.
                _stop_only=0
                if echo "${tag}" | grep -qE '@click\.stop(\s|>|=("\s*"|'\''\s*'\''))'; then
                    # Any `@click` outside the .stop form? If not, this is
                    # event-mgmt-only.
                    if ! echo "${tag}" | grep -qE '@click(\.[a-z]+)*\s*=\s*"[^"]+"' \
                       || ! echo "${tag}" | grep -qE '@click(\.[a-z]+)*\s*=\s*"[^"]+"' | grep -qv '@click\.stop\s*=\s*""'; then
                        _stop_only=1
                    fi
                fi
                if [ "${_stop_only}" -eq 1 ]; then continue; fi
                # Required trio: role= , tabindex= , and a key handler
                _has_role=0
                _has_tabindex=0
                _has_keyhandler=0
                echo "${tag}" | grep -qE '(^|[[:space:]])(:?role|v-bind:role)=' && _has_role=1
                echo "${tag}" | grep -qE '(^|[[:space:]])(:?tabindex|v-bind:tabindex)=' && _has_tabindex=1
                echo "${tag}" | grep -qE '(@keydown|@keyup|@keypress|v-on:keydown|v-on:keyup|v-on:keypress)' && _has_keyhandler=1
                if [ "${_has_role}" -eq 0 ] || [ "${_has_tabindex}" -eq 0 ] || [ "${_has_keyhandler}" -eq 0 ]; then
                    _missing=""
                    [ "${_has_role}" -eq 0 ] && _missing="${_missing}role="
                    [ "${_has_tabindex}" -eq 0 ] && _missing="${_missing}${_missing:+,}tabindex="
                    [ "${_has_keyhandler}" -eq 0 ] && _missing="${_missing}${_missing:+,}@keydown"
                    echo "${vue}: ${tag} rule=missing[${_missing}]" >> "${_sc_log}"
                fi
            done
    done < <(find src -name '*.vue' 2>/dev/null)
    _sc_fail=$(wc -l < "${_sc_log}" 2>/dev/null || echo 0)
    if [ "${_sc_fail}" -eq 0 ]; then
        _pass 32 "semantic-controls"
    else
        _fail 32 "semantic-controls" "${_sc_fail} non-semantic element(s) with @click but missing role/tabindex/keyboard handler — use <NcButton> or <button> — see ${_sc_log}"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 33: Axe-core report — consume the axe-core violations JSON produced by
# `scripts/run-browser-tests.sh`. Static gates can only catch AST-visible
# issues; axe-core runs against the rendered DOM and catches contrast,
# landmark structure, ARIA validity, and live-region issues that no regex
# can reliably detect. See WCAG 2.2 AA SC 1.4.3, 1.4.11, 1.3.1, 4.1.2, 4.1.3.
#
# Contract: if `tests/axe/report.json` exists, parse its `violations` array
# and fail on any entry with `impact` of `serious` or `critical`. If the
# report file does not exist, the gate SKIPS silently — the test runner
# either didn't run axe yet, or this app doesn't have a browser-test stage.
# This mirrors gate-4 (composer-audit) which skips when composer.json is
# absent.
#
# To produce the report, add an axe-core invocation to the Playwright
# session inside `scripts/run-browser-tests.sh`. See the `hydra-gate-axe`
# skill for the canonical Playwright snippet.
#
# References:
#   - ADR-010 (NL Design — WCAG 2.2 AA)
#   - openspec/architecture/wcag-coverage.md (axe column)
#   - .claude/skills/hydra-gate-axe/SKILL.md (how the report is produced)
# ---------------------------------------------------------------------------
_axe_report="tests/axe/report.json"
if [ -f "${_axe_report}" ]; then
    _axe_log=/tmp/hydra-gate-axe.log
    : > "${_axe_log}"
    # Parse with python so we don't add a jq dependency. Counts violations
    # by impact and emits one line per serious/critical violation for the
    # detail log. Exit code 0 if zero serious-or-critical; 1 otherwise.
    python3 - "${_axe_report}" "${_axe_log}" <<'PYAXE' || _axe_fail_count=$?
import json, sys
path, log = sys.argv[1], sys.argv[2]
try:
    with open(path) as f:
        data = json.load(f)
except Exception as e:
    print(f"axe-report-unreadable: {e}", file=open(log, 'w'))
    sys.exit(1)
violations = data.get('violations', []) if isinstance(data, dict) else []
blocking = [v for v in violations if v.get('impact') in ('serious', 'critical')]
with open(log, 'w') as f:
    for v in blocking:
        rule = v.get('id', '?')
        impact = v.get('impact', '?')
        help_url = v.get('helpUrl', '')
        targets = []
        for n in v.get('nodes', [])[:3]:
            t = n.get('target', [])
            targets.append(' > '.join(t) if isinstance(t, list) else str(t))
        f.write(f"axe-rule={rule} impact={impact} nodes={len(v.get('nodes', []))} help={help_url} targets={targets}\n")
sys.exit(0 if not blocking else 1)
PYAXE
    _axe_fail=$(wc -l < "${_axe_log}" 2>/dev/null || echo 0)
    if [ "${_axe_fail}" -eq 0 ]; then
        _pass 33 "axe-core"
    else
        _fail 33 "axe-core" "${_axe_fail} serious/critical axe violation(s) — see ${_axe_log}"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 34: Window-confirm — flag literal `window.confirm(` / `window.alert(`
# / `window.prompt(` calls in `.vue` / `.js` / `.ts` files. ADR-004 hard
# rule: native browser dialogs break Nextcloud's theming + WCAG. Use
# `NcDialog` or `CnFormDialog` instead. References WCAG 2.2 SC 3.3.4
# (Error Prevention) for destructive-action confirmations and SC 4.1.2
# (Name, Role, Value) — native window dialogs don't expose a queryable
# role to assistive tech that matches the surrounding NC shell.
# ---------------------------------------------------------------------------
if [ -d src ]; then
    _wc_log=/tmp/hydra-gate-window-confirm.log
    : > "${_wc_log}"
    grep -rnE '\bwindow\.(confirm|alert|prompt)\s*\(' src/ \
        --include='*.vue' --include='*.js' --include='*.ts' 2>/dev/null \
        | _filter_grep_by_scope >> "${_wc_log}" || true
    _wc_fail=$(wc -l < "${_wc_log}" 2>/dev/null || echo 0)
    if [ "${_wc_fail}" -eq 0 ]; then
        _pass 34 "window-confirm"
    else
        _fail 34 "window-confirm" "${_wc_fail} native dialog call(s) — use NcDialog / CnFormDialog — see ${_wc_log}"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 35: Img-alt-empty-only — escalates gate 31. Detects `<img alt="">`
# (literal empty alt — i.e. "explicitly decorative") paired with a `:src`
# / `v-bind:src` whose bound expression contains a semantic noun
# (`avatar`, `photo`, `thumbnail`, `picture`, `headshot`, `portrait`,
# `profilePicture`). These are content images by name — silencing gate 31
# with `alt=""` is the "I made the gate green by lying" anti-pattern.
#
# Decorative images that are decorative-by-shape still pass (e.g. a static
# `<img src="img/decoration.svg" alt="">`). The gate only fires when the
# bound src name explicitly signals dynamic user content.
#
# References:
#   - ADR-010 (NL Design — WCAG 2.2 AA)
#   - openspec/architecture/wcag-coverage.md SC 1.1.1 (Non-text Content)
# ---------------------------------------------------------------------------
if [ -d src ]; then
    _iae_log=/tmp/hydra-gate-img-alt-empty-only.log
    : > "${_iae_log}"
    while IFS= read -r vue; do
        _in_scope "${vue}" || continue
        _flat=$(tr '\n' ' ' < "${vue}")
        echo "${_flat}" \
            | grep -oE '<img\b[^>]*>' 2>/dev/null \
            | while IFS= read -r tag; do
                [ -z "${tag}" ] && continue
                # Must have literal alt="" (not bound `:alt=""` — bound expressions
                # with computed-default-empty are out of scope; the developer there
                # at least went through a prop pipeline).
                echo "${tag}" | grep -qE 'alt\s*=\s*"\s*"' || continue
                # Must have a bound :src or v-bind:src that names a semantic noun.
                # We match the BINDING expression body — substring search inside
                # the :src="..." quotes for the semantic noun list.
                _src_expr=$(echo "${tag}" | grep -oE '(:src|v-bind:src)\s*=\s*"[^"]*"' | head -1 || true)
                [ -z "${_src_expr}" ] && continue
                if echo "${_src_expr}" | grep -qiE '\b(avatar|photo|thumbnail|picture|headshot|portrait|profilePicture)\b'; then
                    echo "${vue}: ${tag} rule=empty-alt-on-semantic-bound-src" >> "${_iae_log}"
                fi
            done
    done < <(find src -name '*.vue' 2>/dev/null)
    _iae_fail=$(wc -l < "${_iae_log}" 2>/dev/null || echo 0)
    if [ "${_iae_fail}" -eq 0 ]; then
        _pass 35 "img-alt-empty-only"
    else
        _fail 35 "img-alt-empty-only" "${_iae_fail} <img alt=\"\"> on semantic-bound src — see ${_iae_log}"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 36: Tabindex-positive — flag any `tabindex="N"` with N ≥ 1 (positive
# tabindex). Per WCAG 2.2 AA SC 2.4.3 (Focus Order), positive tabindex
# values pull the element out of natural document order and into a
# parallel "tab sequence" that almost never matches user expectations.
# The only correct values are `tabindex="0"` (in natural order) or
# `tabindex="-1"` (programmatically focusable, not in tab order).
#
# References:
#   - openspec/architecture/wcag-coverage.md SC 2.4.3 (Focus Order)
#   - WHATWG / W3C: "Authors should generally use `tabindex='0'` or
#     `tabindex='-1'`. Positive integer values are very rarely useful."
# ---------------------------------------------------------------------------
if [ -d src ]; then
    _tp_log=/tmp/hydra-gate-tabindex-positive.log
    : > "${_tp_log}"
    # Match tabindex with quoted positive integer. Allow whitespace
    # inside the quotes. Excludes tabindex="0", tabindex="-1", and any
    # form where the value is bound (`:tabindex="..."` is reviewer-judgment).
    grep -rnE 'tabindex[[:space:]]*=[[:space:]]*"[[:space:]]*[1-9][0-9]*[[:space:]]*"' src/ \
        --include='*.vue' --include='*.js' --include='*.ts' 2>/dev/null \
        | _filter_grep_by_scope >> "${_tp_log}" || true
    _tp_fail=$(wc -l < "${_tp_log}" 2>/dev/null || echo 0)
    if [ "${_tp_fail}" -eq 0 ]; then
        _pass 36 "tabindex-positive"
    else
        _fail 36 "tabindex-positive" "${_tp_fail} positive tabindex value(s) — use \"0\" or \"-1\" — see ${_tp_log}"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 37: Aria-hidden-focusable — flag elements with `aria-hidden="true"`
# that ALSO declare a focusable mechanism (`tabindex` with any value,
# `role="button|link|menuitem|tab|..."`, or a native focusable tag like
# `<a href>` / `<button>` / `<input>` / `<select>` / `<textarea>`).
#
# This is one of the most-cited axe-core violations: the element is
# hidden from assistive tech but still in the tab order, so keyboard
# users land on a control that screen readers don't announce. Result:
# focus lands on "nothing" — confusing and disorienting. WCAG 2.2 AA
# SC 4.1.2 (Name, Role, Value).
#
# References:
#   - openspec/architecture/wcag-coverage.md SC 4.1.2 (Name, Role, Value)
#   - axe-core rule `aria-hidden-focus` (impact: serious)
# ---------------------------------------------------------------------------
if [ -d src ]; then
    _ahf_log=/tmp/hydra-gate-aria-hidden-focusable.log
    : > "${_ahf_log}"
    while IFS= read -r vue; do
        _in_scope "${vue}" || continue
        _flat=$(tr '\n' ' ' < "${vue}")
        # Match every opening HTML tag that contains aria-hidden="true".
        # We grep with -oE for the full tag including all attributes.
        echo "${_flat}" \
            | grep -oE '<[a-zA-Z][a-zA-Z0-9-]*\b[^>]*aria-hidden[[:space:]]*=[[:space:]]*"true"[^>]*>' 2>/dev/null \
            | while IFS= read -r tag; do
                [ -z "${tag}" ] && continue
                # Extract the element name (between < and the first space-or->).
                _elem=$(echo "${tag}" | sed -nE 's|^<([a-zA-Z][a-zA-Z0-9-]*)\b.*|\1|p')
                [ -z "${_elem}" ] && continue
                # Vue/NC component shells like <NcAvatar> or <RouterLink>
                # are component invocations; their internal a11y wiring is
                # the component's problem, not the consumer's. Skip
                # PascalCase tags (starts with uppercase).
                case "${_elem}" in
                    [A-Z]*) continue ;;
                esac
                # Focusable signals:
                #   1. native focusable tag
                #   2. tabindex= attribute (any value)
                #   3. interactive role=
                _focusable=0
                case "${_elem}" in
                    a|button|input|select|textarea|details|summary|iframe|audio|video)
                        # `<a>` is only focusable when href is set.
                        if [ "${_elem}" = "a" ]; then
                            echo "${tag}" | grep -qE '\bhref[[:space:]]*=' && _focusable=1
                        else
                            _focusable=1
                        fi
                        ;;
                esac
                if [ "${_focusable}" -eq 0 ]; then
                    echo "${tag}" | grep -qE '(^|[[:space:]])(:?tabindex|v-bind:tabindex)[[:space:]]*=' && _focusable=1
                fi
                if [ "${_focusable}" -eq 0 ]; then
                    echo "${tag}" | grep -qE 'role[[:space:]]*=[[:space:]]*"(button|link|menuitem|tab|checkbox|radio|switch|option|treeitem|gridcell|columnheader|rowheader|slider|spinbutton|searchbox|combobox|textbox)"' && _focusable=1
                fi
                if [ "${_focusable}" -eq 1 ]; then
                    echo "${vue}: ${tag} rule=aria-hidden-on-focusable-element" >> "${_ahf_log}"
                fi
            done
    done < <(find src -name '*.vue' 2>/dev/null)
    _ahf_fail=$(wc -l < "${_ahf_log}" 2>/dev/null || echo 0)
    if [ "${_ahf_fail}" -eq 0 ]; then
        _pass 37 "aria-hidden-focusable"
    else
        _fail 37 "aria-hidden-focusable" "${_ahf_fail} aria-hidden=true on focusable element(s) — remove aria-hidden OR remove the focusable mechanism — see ${_ahf_log}"
    fi
fi


# ---------------------------------------------------------------------------
# Gate 38: Skip-link — every app entry-point Vue (App.vue / *Root.vue) or
# admin/settings PHP template must include a skip-to-content affordance,
# either via NC's shell (typically inherited by mounting under <NcContent>)
# or via an explicit `<a href="#main">` / `<a href="#content">` link as
# the first focusable element. Per WCAG 2.2 AA SC 2.4.1 (Bypass Blocks).
#
# Heuristic: a file is in scope if it's a top-level Vue mount root (App.vue
# / **/AdminRoot.vue / **/Root.vue) OR a settings admin template
# (templates/settings/*.php). We pass if the file either renders
# `<NcContent>` / `<NcAppContent>` (which inherits NC's skip-link) OR
# contains a literal `skip-` link / `skip-to-content` reference.
#
# References:
#   - openspec/architecture/wcag-coverage.md SC 2.4.1
# ---------------------------------------------------------------------------
if [ -d src ] || [ -d templates ]; then
    _sl_log=/tmp/hydra-gate-skip-link.log
    : > "${_sl_log}"
    _sl_check() {
        local _f="$1"
        _in_scope "$_f" || return 0
        if grep -qE '<NcContent\b|<NcAppContent\b|<NcAppContentList\b' "$_f" 2>/dev/null; then return 0; fi
        # The skip-link affordance must be an actual anchor or marked
        # element — not just a stray mention of the words. Accept:
        #   - <a ... class="skip-link" ...> or class containing skip-link / skip-nav
        #   - <a href="#main"> / <a href="#content"> / <a href="#main-content">
        #   - id="skip-link" / id="skip-to-content" on any element
        if grep -qE '<a\b[^>]*(class\s*=\s*"[^"]*skip-(link|nav|to-content)|href\s*=\s*"#(main|content|main-content)")' "$_f" 2>/dev/null; then return 0; fi
        if grep -qE 'id\s*=\s*"skip-(link|to-content|nav)"' "$_f" 2>/dev/null; then return 0; fi
        echo "${_f}: no <NcContent> shell, no skip-link affordance" >> "${_sl_log}"
    }
    for _f in src/App.vue src/views/App.vue; do
        [ -f "$_f" ] && _sl_check "$_f"
    done
    while IFS= read -r _f; do
        [ -z "$_f" ] && continue
        _sl_check "$_f"
    done < <(_enum_tracked 'Root\.vue$' src)
    if [ -d templates/settings ]; then
        while IFS= read -r _f; do
            [ -z "$_f" ] && continue
            _sl_check "$_f"
        done < <(find templates/settings -name '*.php' 2>/dev/null)
    fi
    _sl_fail=$(wc -l < "${_sl_log}" 2>/dev/null || echo 0)
    if [ "${_sl_fail}" -eq 0 ]; then
        _pass 38 "skip-link"
    else
        _fail 38 "skip-link" "${_sl_fail} root component(s) without skip-link / <NcContent> — see ${_sl_log}"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 39: Button-name — `<NcButton>` / `<button>` tags with NO text content
# AND no `aria-label` / `aria-labelledby` / `title` are invisible to screen
# readers (announced as just "button"). Common shape: icon-only buttons
# like `<NcButton><CloseIcon /></NcButton>`. Per WCAG 2.2 AA SC 4.1.2
# (Name, Role, Value).
#
# Pass conditions for a button tag:
#   (a) has aria-label / :aria-label / aria-labelledby attribute, OR
#   (b) has a title attribute, OR
#   (c) has non-trivial text content (not just an icon-component child) OR
#       a Vue interpolation {{ ... }} indicating dynamic text.
#
# References:
#   - openspec/architecture/wcag-coverage.md SC 4.1.2
# ---------------------------------------------------------------------------
if [ -d src ]; then
    _bn_log=/tmp/hydra-gate-button-name.log
    : > "${_bn_log}"
    while IFS= read -r vue; do
        _in_scope "${vue}" || continue
        python3 - "$vue" <<'PYBN' >> "${_bn_log}" 2>/dev/null
import re, sys
fname = sys.argv[1]
try:
    src = open(fname).read()
except Exception:
    sys.exit(0)
txt = src.replace('\n', ' ')
for tag_re in (r'<NcButton\b([^>]*)>(.*?)</NcButton>', r'<button\b([^>]*)>(.*?)</button>'):
    for m in re.finditer(tag_re, txt, re.IGNORECASE):
        attrs = m.group(1) or ''
        body = m.group(2) or ''
        if re.search(r'(^|\s)(:?aria-label|aria-labelledby|v-bind:aria-label|title)\s*=', attrs):
            continue
        if '{{' in body and '}}' in body:
            continue
        body_text = re.sub(r'<[^>]+>', '', body)
        body_text = re.sub(r'\s+', '', body_text)
        if len(body_text) >= 2:
            continue
        opening = m.group(0).split('>')[0] + '>'
        print(f'{fname}: {opening} rule=icon-only-button-without-accessible-name')
PYBN
    done < <(find src -name '*.vue' 2>/dev/null)
    _bn_fail=$(wc -l < "${_bn_log}" 2>/dev/null || echo 0)
    if [ "${_bn_fail}" -eq 0 ]; then
        _pass 39 "button-name"
    else
        _fail 39 "button-name" "${_bn_fail} icon-only button(s) without aria-label — see ${_bn_log}"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 40: Form-label-association — generalises gate 12 (NcSelect-only) to
# every form input shape: `<input>`, `<textarea>`, `<NcTextField>`,
# `<NcCheckboxRadioSwitch>`, `<NcRichContenteditable>`, `<NcInputField>`.
# Per WCAG 2.2 AA SC 1.3.1 (Info and Relationships) and 3.3.2 (Labels or
# Instructions).
#
# Pass conditions for an input element:
#   (a) has aria-label / :aria-label / aria-labelledby, OR
#   (b) has an `id=` attribute paired with some `<label for=>` in the file
#       referencing the same id (heuristic), OR
#   (c) for the NC* components: has a `label` / `:label` / `inputLabel`
#       prop (their published API), OR
#   (d) input `type` is `hidden` / `submit` / `button` / `reset` / `image`.
#
# References:
#   - openspec/architecture/wcag-coverage.md SC 1.3.1, 3.3.2
# ---------------------------------------------------------------------------
if [ -d src ]; then
    _fl_log=/tmp/hydra-gate-form-label-association.log
    : > "${_fl_log}"
    while IFS= read -r vue; do
        _in_scope "${vue}" || continue
        python3 - "$vue" <<'PYFL' >> "${_fl_log}" 2>/dev/null
import re, sys
fname = sys.argv[1]
try:
    src = open(fname).read()
except Exception:
    sys.exit(0)
txt = src.replace('\n', ' ')
labelled_for = set(m.group(1) for m in re.finditer(r'<label\b[^>]*\bfor\s*=\s*"([^"]+)"', txt, re.IGNORECASE))

def has_aria(attrs):
    return bool(re.search(r'(^|\s)(:?aria-label|aria-labelledby|v-bind:aria-label)\s*=', attrs))

def has_for_match(attrs):
    m = re.search(r'(^|\s)id\s*=\s*"([^"]+)"', attrs)
    return m and m.group(2) in labelled_for

def has_nc_label_prop(attrs):
    return bool(re.search(r'(^|\s)(:?label|input-label|:input-label|inputLabel)\s*=', attrs))

for m in re.finditer(r'<input\b([^>]*)>', txt, re.IGNORECASE):
    attrs = m.group(1) or ''
    type_m = re.search(r'(^|\s)type\s*=\s*"(hidden|submit|button|reset|image)"', attrs, re.IGNORECASE)
    if type_m: continue
    if has_aria(attrs): continue
    if has_for_match(attrs): continue
    print(f'{fname}: {m.group(0)} rule=input-without-label')

for m in re.finditer(r'<(NcTextField|NcCheckboxRadioSwitch|NcRichContenteditable|NcInputField)\b([^>]*)/?>', txt, re.IGNORECASE):
    tag = m.group(1)
    attrs = m.group(2) or ''
    if has_aria(attrs): continue
    if has_nc_label_prop(attrs): continue
    print(f'{fname}: <{tag} ...> rule={tag.lower()}-without-label-prop')

for m in re.finditer(r'<textarea\b([^>]*)>', txt, re.IGNORECASE):
    attrs = m.group(1) or ''
    if has_aria(attrs): continue
    if has_for_match(attrs): continue
    print(f'{fname}: <textarea ...> rule=textarea-without-label')
PYFL
    done < <(find src -name '*.vue' 2>/dev/null)
    _fl_fail=$(wc -l < "${_fl_log}" 2>/dev/null || echo 0)
    if [ "${_fl_fail}" -eq 0 ]; then
        _pass 40 "form-label-association"
    else
        _fail 40 "form-label-association" "${_fl_fail} form input(s) without an associated label — see ${_fl_log}"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 41: Html-lang — Nextcloud's shell sets `<html lang>` from user locale
# for app routes, but app-owned PHP templates under `appinfo/templates/` and
# `templates/` (admin/settings + public PublicPage routes) sometimes don't
# inherit it. Detect templates that emit an `<html>` element without a `lang`
# attribute. Per WCAG 2.2 AA SC 3.1.1 (Language of Page).
#
# Heuristic: PHP template files containing `<html>` (opening tag) must also
# carry `lang=` on that tag. Pure partial templates that never render
# `<html>` are skipped.
#
# References:
#   - openspec/architecture/wcag-coverage.md SC 3.1.1
# ---------------------------------------------------------------------------
if [ -d templates ] || [ -d appinfo/templates ]; then
    _hl_log=/tmp/hydra-gate-html-lang.log
    : > "${_hl_log}"
    while IFS= read -r _f; do
        [ -z "$_f" ] && continue
        _in_scope "$_f" || continue
        python3 - "$_f" <<'PYHL' >> "${_hl_log}" 2>/dev/null
import re, sys
fname = sys.argv[1]
try:
    txt = open(fname).read()
except Exception:
    sys.exit(0)
m = re.search(r'<html\b([^>]*)>', txt, re.IGNORECASE)
if not m: sys.exit(0)
if not re.search(r'(^|\s)lang\s*=', m.group(1) or ''):
    print(f'{fname}: <html> rule=html-tag-without-lang')
PYHL
    done < <(find templates appinfo/templates -name '*.php' 2>/dev/null)
    _hl_fail=$(wc -l < "${_hl_log}" 2>/dev/null || echo 0)
    if [ "${_hl_fail}" -eq 0 ]; then
        _pass 41 "html-lang"
    else
        _fail 41 "html-lang" "${_hl_fail} <html> tag(s) without lang= — see ${_hl_log}"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 42: Link-text-quality — flag links with low-quality text that
# doesn't describe the destination. Pattern-match known anti-patterns:
# "Click here", "Read more", "Learn more", "Here", "More", "Details", and
# empty link bodies. Per WCAG 2.2 AA SC 2.4.4 (Link Purpose — In Context).
#
# Higher false-positive risk than the AST gates — surrounding context can
# make "Read more" accessible-in-context. Links with aria-label or Vue
# interpolations are accepted unconditionally.
#
# References:
#   - openspec/architecture/wcag-coverage.md SC 2.4.4
# ---------------------------------------------------------------------------
if [ -d src ]; then
    _lq_log=/tmp/hydra-gate-link-text-quality.log
    : > "${_lq_log}"
    while IFS= read -r vue; do
        _in_scope "${vue}" || continue
        python3 - "$vue" <<'PYLQ' >> "${_lq_log}" 2>/dev/null
import re, sys
fname = sys.argv[1]
try:
    src = open(fname).read()
except Exception:
    sys.exit(0)
txt = src.replace('\n', ' ')
patterns = [
    (r'<a\b([^>]*)>(.*?)</a>', 'a'),
    (r'<router-link\b([^>]*)>(.*?)</router-link>', 'router-link'),
    (r'<RouterLink\b([^>]*)>(.*?)</RouterLink>', 'RouterLink'),
]
BAD = re.compile(r'^(click\s*here|here|read\s*more|learn\s*more|more|continue|see\s*more|details)\.?$', re.IGNORECASE)
for pat, tagname in patterns:
    for m in re.finditer(pat, txt, re.IGNORECASE | re.DOTALL):
        attrs = m.group(1) or ''
        body = m.group(2) or ''
        if re.search(r'(:?aria-label|aria-labelledby)\s*=', attrs): continue
        if '{{' in body and '}}' in body: continue
        body_text = re.sub(r'<[^>]+>', '', body)
        body_text = re.sub(r'\s+', ' ', body_text).strip()
        if not body_text or BAD.match(body_text):
            print(f'{fname}: <{tagname}> body="{body_text}" rule=link-text-not-descriptive')
PYLQ
    done < <(find src -name '*.vue' 2>/dev/null)
    _lq_fail=$(wc -l < "${_lq_log}" 2>/dev/null || echo 0)
    if [ "${_lq_fail}" -eq 0 ]; then
        _pass 42 "link-text-quality"
    else
        _fail 42 "link-text-quality" "${_lq_fail} link(s) with non-descriptive text — see ${_lq_log}"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 43: Table-headers — every `<table>` in `.vue` templates must have at
# least one `<th>` with a `scope="col"` / `scope="row"` attribute. Without
# it, screen readers can't associate data cells with their headers. Per
# WCAG 2.2 AA SC 1.3.1 (Info and Relationships).
#
# Two failure shapes:
#   - rule=th-without-scope: <table> has <th> but no scope=
#   - rule=table-without-th: <table> with <td> rows but no <th> at all
#
# Wrapper components (<CnDataTable>, <NcTable>) are not in scope.
#
# References:
#   - openspec/architecture/wcag-coverage.md SC 1.3.1
# ---------------------------------------------------------------------------
if [ -d src ]; then
    _th_log=/tmp/hydra-gate-table-headers.log
    : > "${_th_log}"
    while IFS= read -r vue; do
        _in_scope "${vue}" || continue
        python3 - "$vue" <<'PYTH' >> "${_th_log}" 2>/dev/null
import re, sys
fname = sys.argv[1]
try:
    src = open(fname).read()
except Exception:
    sys.exit(0)
txt = src.replace('\n', ' ')
for m in re.finditer(r'<table\b([^>]*)>(.*?)</table>', txt, re.IGNORECASE | re.DOTALL):
    body = m.group(2) or ''
    if re.search(r'<th\b[^>]*\bscope\s*=', body, re.IGNORECASE):
        continue
    if re.search(r'<th\b', body, re.IGNORECASE):
        print(f'{fname}: <table> rule=th-without-scope')
    elif re.search(r'<td\b', body, re.IGNORECASE):
        print(f'{fname}: <table> rule=table-without-th')
PYTH
    done < <(find src -name '*.vue' 2>/dev/null)
    _th_fail=$(wc -l < "${_th_log}" 2>/dev/null || echo 0)
    if [ "${_th_fail}" -eq 0 ]; then
        _pass 43 "table-headers"
    else
        _fail 43 "table-headers" "${_th_fail} <table>(s) missing <th scope=> — see ${_th_log}"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 44: Autocomplete-attr — `<input>` with name attributes / ids that
# match well-known autofill categories MUST declare an `autocomplete=`
# attribute so password managers + browser autofill work. Per WCAG 2.2 AA
# SC 1.3.5 (Identify Input Purpose).
#
# References:
#   - openspec/architecture/wcag-coverage.md SC 1.3.5
# ---------------------------------------------------------------------------
if [ -d src ]; then
    _ac_log=/tmp/hydra-gate-autocomplete-attr.log
    : > "${_ac_log}"
    while IFS= read -r vue; do
        _in_scope "${vue}" || continue
        python3 - "$vue" <<'PYAC' >> "${_ac_log}" 2>/dev/null
import re, sys
fname = sys.argv[1]
try:
    src = open(fname).read()
except Exception:
    sys.exit(0)
txt = src.replace('\n', ' ')
SEM_RE = re.compile(r'(email|tel(?:ephone)?|phone|firstname|lastname|fullname|address|street|city|postal|postcode|zip|country|password|username|organization|birthday|dob)', re.IGNORECASE)
for m in re.finditer(r'<input\b([^>]*)>', txt, re.IGNORECASE):
    attrs = m.group(1) or ''
    type_m = re.search(r'(^|\s)type\s*=\s*"(hidden|submit|button|reset|image|file|checkbox|radio|color|range)"', attrs, re.IGNORECASE)
    if type_m: continue
    if re.search(r'(^|\s)(:?autocomplete|v-bind:autocomplete)\s*=', attrs): continue
    name_m = re.search(r'(^|\s)(?:name|id|:name|:id|v-model)\s*=\s*"([^"]+)"', attrs)
    if not name_m: continue
    val = name_m.group(2)
    if SEM_RE.search(val):
        print(f'{fname}: <input name/id="{val}" ...> rule=semantic-input-without-autocomplete')
PYAC
    done < <(find src -name '*.vue' 2>/dev/null)
    _ac_fail=$(wc -l < "${_ac_log}" 2>/dev/null || echo 0)
    if [ "${_ac_fail}" -eq 0 ]; then
        _pass 44 "autocomplete-attr"
    else
        _fail 44 "autocomplete-attr" "${_ac_fail} semantic input(s) without autocomplete= — see ${_ac_log}"
    fi
fi

# ---------------------------------------------------------------------------
# Gate 45: Prefers-reduced-motion — every `<style>` block in `.vue` files
# that declares `transition:` or `animation:` properties MUST also contain
# a `@media (prefers-reduced-motion: reduce)` block that disables or
# shortens motion. Per WCAG 2.2 SC 2.3.3 (Animation from Interactions —
# AAA, but a common Dutch toegankelijkheidsverklaring audit checkpoint).
#
# References:
#   - openspec/architecture/wcag-coverage.md SC 2.3.3 (AAA, audit-common)
# ---------------------------------------------------------------------------
if [ -d src ]; then
    _rm_log=/tmp/hydra-gate-prefers-reduced-motion.log
    : > "${_rm_log}"
    while IFS= read -r vue; do
        _in_scope "${vue}" || continue
        python3 - "$vue" <<'PYRM' >> "${_rm_log}" 2>/dev/null
import re, sys
fname = sys.argv[1]
try:
    src = open(fname).read()
except Exception:
    sys.exit(0)
for m in re.finditer(r'<style\b[^>]*>(.*?)</style>', src, re.IGNORECASE | re.DOTALL):
    block = m.group(1)
    if not re.search(r'\b(transition|animation)\s*:', block):
        continue
    if re.search(r'@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)', block, re.IGNORECASE):
        continue
    print(f'{fname}: <style> rule=motion-without-reduced-motion-fallback')
PYRM
    done < <(find src -name '*.vue' 2>/dev/null)
    _rm_fail=$(wc -l < "${_rm_log}" 2>/dev/null || echo 0)
    if [ "${_rm_fail}" -eq 0 ]; then
        _pass 45 "prefers-reduced-motion"
    else
        _fail 45 "prefers-reduced-motion" "${_rm_fail} <style> block(s) with motion but no reduced-motion fallback — see ${_rm_log}"
    fi
fi


# ---------------------------------------------------------------------------
# Gate 46: Spec-anchor-existence — every `@spec openspec/...` PHPDoc/JSDoc
# tag in a changed file must resolve to an existing file AND (when a
# `#fragment` is present) an existing section anchor. Gate-16 checks the
# tag EXISTS; this gate checks its TARGET resolves. Observed 2026-07-03
# on opencatalogi#85 where `@spec openspec/specs/federation/spec.md
# #requirement-directory-self-detection` pointed at a non-existent
# requirement — gate-16 accepted the tag because it was present.
#
# Skill: .claude/skills/hydra-gate-spec-anchor-existence/SKILL.md
# ---------------------------------------------------------------------------
_sae_log=/tmp/hydra-gate-spec-anchor-existence.log
: > "${_sae_log}"
_sae_files=()
while IFS= read -r f; do
    [ -f "$f" ] || continue
    _in_scope "$f" || continue
    _sae_files+=("$f")
done < <(find lib src \( -name '*.php' -o -name '*.vue' -o -name '*.js' -o -name '*.ts' -o -name '*.md' \) \
    -not -path '*/vendor/*' -not -path '*/node_modules/*' \
    -not -path '*/dist/*' -not -path '*/build/*' 2>/dev/null)
if [ "${#_sae_files[@]}" -gt 0 ]; then
    python3 - "${_sae_log}" "${_sae_files[@]}" << 'PY'
import glob, os, re, sys
log_path = sys.argv[1]
files = sys.argv[2:]
# Match `@spec openspec/...` but NOT `@spec exclude ...`
TAG = re.compile(r'@spec\s+(openspec/[^\s`\'"]+)')
DATE = re.compile(r'\b\d{4}-\d{2}-\d{2}\b')
def slugify(text):
    # kebab-case the visible-heading text so #requirement-foo-bar matches "## Requirement: Foo Bar"
    t = text.strip().lower()
    t = re.sub(r'[^a-z0-9]+', '-', t).strip('-')
    return t
def dedate(name):
    # `retrofit-2026-04-28-b2b-crossrefs` and `retrofit-b2b-crossrefs-2026-04-28`
    # both normalise to `retrofit-b2b-crossrefs`: archiving moves the date token.
    return re.sub(r'-+', '-', DATE.sub('', name)).strip('-')
def has_anchor(md_path, fragment):
    # A fragment resolves when it matches (kebab-cased) a heading, a heading's
    # leading token (`#### 5.2 Foo` ← `#5.2`), a task-list item id
    # (`- [x] task-18: ...` ← `#task-18`, `- [x] 5.2 Add ...` ← `#5.2`,
    # optionally with a `task-` prefix in the tag), or — for `#task-N` /
    # `#N` on files whose checkbox items carry no ids — the Nth top-level
    # checkbox item (positional convention used by reverse-spec retrofits).
    frag_slug = slugify(fragment)
    frag_alt = slugify(re.sub(r'^task-', '', fragment))
    pos_m = re.fullmatch(r'(?:task-)?(\d+)', fragment)
    positional = int(pos_m.group(1)) if pos_m else None
    item_count = 0
    try:
        with open(md_path, encoding='utf-8', errors='replace') as f:
            for line in f:
                m = re.match(r'^\s*#{1,6}\s+(.+?)\s*$', line)
                if m:
                    head = m.group(1)
                    hslug = slugify(head)
                    frags = (frag_slug, frag_alt)
                    if hslug in frags:
                        return True
                    # `### Task 8 — long title` resolves `#task-8`; the `-`
                    # boundary keeps `#task-8` from matching `Task 89`.
                    if any(hslug.startswith(f + '-') for f in frags if f):
                        return True
                    # `### Requirement: Foo bar` resolves `#foo-bar` (tags
                    # often omit the `requirement-`/`scenario-` prefix).
                    if ':' in head and slugify(head.split(':', 1)[1]) in frags:
                        return True
                    lead = head.split()[0].rstrip('.:') if head.split() else ''
                    if lead and slugify(lead) in frags:
                        return True
                    continue
                if re.match(r'^-\s*\[[ xX]\]', line):
                    item_count += 1
                    if positional is not None and item_count == positional:
                        return True
                t = re.match(r'^\s*-\s*\[[ xX]\]\s*(?:\*\*)?([A-Za-z0-9][A-Za-z0-9.\-]*)', line)
                if t and slugify(t.group(1).rstrip('.:')) in (frag_slug, frag_alt):
                    return True
        return False
    except OSError:
        return False
def find_repo_root():
    p = os.getcwd()
    while p and p != '/':
        if os.path.isdir(os.path.join(p, 'openspec')):
            return p
        p = os.path.dirname(p)
    return None
root = find_repo_root() or os.getcwd()
# Archived-change index: archiving moves `openspec/changes/<name>/` to
# `openspec/changes/archive/<date>-<name>/` (or legacy `openspec/archive/<name>`,
# sometimes with the date token reshuffled). Tags keep pointing at the original
# path; resolve them through this index instead of forcing a repo-wide retag.
archive_index = {}
for pattern in ('openspec/changes/archive/*', 'openspec/archive/*'):
    for d in glob.glob(os.path.join(root, pattern)):
        if os.path.isdir(d):
            archive_index.setdefault(dedate(os.path.basename(d)), []).append(d)
def resolve(path):
    # Returns the list of existing candidate files for the tag path: the
    # literal path plus archived counterparts. Several archived dirs can
    # share a de-dated key (e.g. two annotate-openregister retrofits from
    # different dates), so candidates carrying the tag's own date token are
    # tried first and ALL existing candidates are returned — the anchor
    # check accepts a fragment found in any of them.
    cands = []
    abs_path = os.path.join(root, path)
    if os.path.exists(abs_path):
        cands.append(abs_path)
    m = re.match(r'openspec/(?:changes|archive)/([^/]+)/(.*)$', path)
    if m and m.group(1) != 'archive':
        name = m.group(1)
        dates = DATE.findall(name)
        dirs = archive_index.get(dedate(name), [])
        dirs = sorted(dirs, key=lambda d: 0 if any(t in os.path.basename(d) for t in dates) else 1)
        for d in dirs:
            cand = os.path.join(d, m.group(2))
            if os.path.exists(cand) and cand not in cands:
                cands.append(cand)
    return cands
for fp in files:
    try:
        with open(fp, encoding='utf-8', errors='replace') as f:
            src = f.read()
    except OSError:
        continue
    for m in TAG.finditer(src):
        target = m.group(1)
        # Split path#fragment
        if '#' in target:
            path, frag = target.split('#', 1)
        else:
            path, frag = target, None
        candidates = resolve(path)
        if not candidates:
            with open(log_path, 'a', encoding='utf-8') as g:
                g.write(f"{fp}: @spec target file not found → {target}\n")
            continue
        if frag and path.endswith('.md'):
            if not any(has_anchor(c, frag) for c in candidates):
                with open(log_path, 'a', encoding='utf-8') as g:
                    g.write(f"{fp}: @spec anchor not found in {path} → #{frag}\n")
PY
fi
set +e
_sae_fail=$(wc -l < "${_sae_log}" 2>/dev/null | tr -d ' ')
set -e
[ -z "${_sae_fail}" ] && _sae_fail=0
if [ "${_sae_fail}" -eq 0 ]; then
    _pass 46 "spec-anchor-existence"
else
    _fail 46 "spec-anchor-existence" "${_sae_fail} unresolved @spec target(s) — see ${_sae_log}"
fi

# ---------------------------------------------------------------------------
# Gate 47: Security-change-has-tests — any PR touching security-sensitive
# code (auth annotations, CSRF, session, URL parsing, permission checks)
# must ALSO touch at least one file under tests/. Observed 2026-07-03 on
# opencatalogi#85 (SSRF hardening) and opencatalogi#86 (DELETE scope) —
# both shipped security-adjacent changes with zero test files touched and
# both had blockers surface only via manual review.
#
# Opt-out: `[hydra-gate-security-change-has-tests exclude] <reason>` in
# the PR body or head commit message (≥ 20 chars).
#
# Skill: .claude/skills/hydra-gate-security-change-has-tests/SKILL.md
# ---------------------------------------------------------------------------
_scht_log=/tmp/hydra-gate-security-change-has-tests.log
: > "${_scht_log}"
if [ "${SCOPE_TO_DIFF}" = "1" ] && [ -n "${BASE_REF}" ]; then
    _scht_changed=$(git diff --name-only "${BASE_REF}...HEAD" 2>/dev/null || true)
    _scht_sec=""
    _scht_has_test=""
    while IFS= read -r f; do
        [ -z "$f" ] && continue
        case "$f" in
            tests/*|*/tests/*|*.spec.js|*.spec.ts|*.spec.vue) _scht_has_test="1" ;;
        esac
        case "$f" in
            lib/*Auth*|lib/*Csrf*|lib/*Session*|lib/*/Auth/*|lib/*/Session/*|lib/*/Csrf/*|lib/*/Rbac/*|lib/*/Permission/*|lib/*/Authorization/*)
                _scht_sec="${_scht_sec}${f}\n" ;;
            lib/*.php|src/*.vue|src/*.js|src/*.ts)
                # content-based classification
                if [ -f "$f" ] && grep -qE "(#\[NoAdminRequired\]|#\[AuthorizedAdminSetting\(|@NoAdminRequired|@NoCSRFRequired|#\[PublicPage\]|parse_url|hash_equals|password_verify|IUserSession|getSecureRandom|requesttoken)" "$f" 2>/dev/null; then
                    _scht_sec="${_scht_sec}${f}\n"
                fi
                ;;
        esac
    done <<< "${_scht_changed}"
    if [ -n "${_scht_sec}" ] && [ -z "${_scht_has_test}" ]; then
        # Check for opt-out in PR body or head commit message
        _scht_optout_re='\[hydra-gate-security-change-has-tests exclude\][[:space:]]+.{20,}'
        _scht_optout=""
        [ -n "${HYDRA_GATE_PR_BODY:-}" ] && echo "${HYDRA_GATE_PR_BODY:-}" | grep -qE "${_scht_optout_re}" && _scht_optout="1"
        [ -z "${_scht_optout}" ] && git log -1 --pretty=%B 2>/dev/null | grep -qE "${_scht_optout_re}" && _scht_optout="1"
        if [ -z "${_scht_optout}" ]; then
            printf "%b" "${_scht_sec}" >> "${_scht_log}"
        fi
    fi
fi
set +e
_scht_fail=$(wc -l < "${_scht_log}" 2>/dev/null | tr -d ' ')
set -e
[ -z "${_scht_fail}" ] && _scht_fail=0
if [ "${_scht_fail}" -eq 0 ]; then
    _pass 47 "security-change-has-tests"
else
    _fail 47 "security-change-has-tests" "${_scht_fail} security-touching change(s) without a test co-change — see ${_scht_log}"
fi

# ---------------------------------------------------------------------------
# Gate 48: CSRF-cochange — when the diff REMOVES @NoCSRFRequired /
# #[NoCSRFRequired] from a controller method, the SAME diff must touch
# every frontend caller of that endpoint so it sends a CSRF-satisfying
# header (`OCS-APIRequest: true`, `requesttoken`, or `@nextcloud/axios`).
# Observed 2026-07-03 on opencatalogi#79 — @NoCSRFRequired removed on
# destroy(), delete-modal fetch() still had no CSRF header.
#
# Skill: .claude/skills/hydra-gate-csrf-cochange/SKILL.md
# ---------------------------------------------------------------------------
_csrf_log=/tmp/hydra-gate-csrf-cochange.log
: > "${_csrf_log}"
if [ "${SCOPE_TO_DIFF}" = "1" ] && [ -n "${BASE_REF}" ]; then
    # Find removed @NoCSRFRequired lines in changed PHP files
    _csrf_removed=$(git diff -U0 "${BASE_REF}...HEAD" -- 'lib/Controller/*.php' 2>/dev/null \
        | grep -E '^-.*(@NoCSRFRequired|#\[NoCSRFRequired\])' || true)
    if [ -n "${_csrf_removed}" ]; then
        # Look for frontend co-change signals in the diff
        _csrf_fe_signals=$(git diff "${BASE_REF}...HEAD" -- 'src/**/*.vue' 'src/**/*.js' 'src/**/*.ts' 2>/dev/null \
            | grep -cE '^\+.*(OCS-APIRequest|requesttoken|@nextcloud/axios|getRequestToken)' 2>/dev/null || echo 0)
        if [ "${_csrf_fe_signals}" -eq 0 ]; then
            # Check for opt-out
            _csrf_optout_re='\[hydra-gate-csrf-cochange exclude\][[:space:]]+.{20,}'
            _csrf_optout=""
            [ -n "${HYDRA_GATE_PR_BODY:-}" ] && echo "${HYDRA_GATE_PR_BODY:-}" | grep -qE "${_csrf_optout_re}" && _csrf_optout="1"
            [ -z "${_csrf_optout}" ] && git log -1 --pretty=%B 2>/dev/null | grep -qE "${_csrf_optout_re}" && _csrf_optout="1"
            if [ -z "${_csrf_optout}" ]; then
                echo "@NoCSRFRequired removed but no frontend CSRF-signal added in diff:" >> "${_csrf_log}"
                echo "${_csrf_removed}" >> "${_csrf_log}"
            fi
        fi
    fi
fi
set +e
_csrf_fail=$(wc -l < "${_csrf_log}" 2>/dev/null | tr -d ' ')
set -e
[ -z "${_csrf_fail}" ] && _csrf_fail=0
if [ "${_csrf_fail}" -eq 0 ]; then
    _pass 48 "csrf-cochange"
else
    _fail 48 "csrf-cochange" "@NoCSRFRequired dropped without frontend CSRF co-change — see ${_csrf_log}"
fi

# ---------------------------------------------------------------------------
# Gate 49: Controller-exception-translation — a controller method that
# calls a service function with documented `@throws DoesNotExistException`
# (or NotFoundException, PermissionException, ValidationException, ...)
# must either wrap the call in try/catch translating to JSONResponse, OR
# declare the same @throws in its own docblock so propagation is
# intentional. Observed 2026-07-03 on opencatalogi#86 — destroy() called
# ObjectService::deleteObject() which re-throws DoesNotExistException on
# scope-mismatch, but destroy() had no try/catch → HTTP 500 on the exact
# defended path.
#
# Skill: .claude/skills/hydra-gate-controller-exception-translation/SKILL.md
# ---------------------------------------------------------------------------
_cxt_log=/tmp/hydra-gate-controller-exception-translation.log
: > "${_cxt_log}"
_cxt_files=()
while IFS= read -r f; do
    [ -f "$f" ] || continue
    _in_scope "$f" || continue
    _cxt_files+=("$f")
done < <(_enum_tracked '\.php$' lib/Controller)
if [ "${#_cxt_files[@]}" -gt 0 ]; then
    python3 - "${_cxt_log}" "${_cxt_files[@]}" << 'PY'
import re, sys, os
log_path = sys.argv[1]
files = sys.argv[2:]
# Documented-throw shapes we track — these are known-not-auto-translated by NC's dispatcher.
TRACKED = [
    'DoesNotExistException',
    'MultipleObjectsReturnedException',
    'NotFoundException',
    'PermissionException',
    'ValidationException',
    'ForbiddenException',
    'CustomValidationException',
    'AppendOnlyException',
    'ArchivalImmutableException',
]
METHOD_RE = re.compile(
    r'(/\*\*[\s\S]*?\*/)?\s*'                    # optional preceding docblock
    r'(public|protected|private)\s+function\s+'
    r'(?P<name>\w+)\s*\([^)]*\)[^{]*\{',
    re.MULTILINE,
)
def _method_bodies(src):
    out = []
    for m in METHOD_RE.finditer(src):
        start = m.end() - 1  # position of the `{`
        depth = 0
        p = start
        while p < len(src):
            c = src[p]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    out.append({
                        'name': m.group('name'),
                        'docblock': m.group(1) or '',
                        'body': src[start+1:p],
                        'start_line': src[:m.start()].count('\n') + 1,
                    })
                    break
            p += 1
    return out
for fp in files:
    try:
        with open(fp, encoding='utf-8', errors='replace') as f:
            src = f.read()
    except OSError:
        continue
    methods = _method_bodies(src)
    for m in methods:
        body = m['body']
        # Find calls of shape $this->prop->method(...) which is a proxy for "calls a service"
        service_calls = re.findall(r'\$this->\w+->(\w+)\s*\(', body)
        if not service_calls:
            continue
        # Heuristic: if the method body ALREADY has try/catch of one of the tracked exceptions,
        # or its docblock declares @throws for one of them, accept it as intentionally handled.
        try_ok = re.search(r'catch\s*\(\s*[\\\w]*(' + '|'.join(TRACKED) + r')\b', body)
        throws_ok = any(x in (m['docblock'] or '') for x in TRACKED)
        if try_ok or throws_ok:
            continue
        # Otherwise: if any service call inside the body invokes a known-throwy shape,
        # log the method. Restricted to OR-specific suffixed names to keep false
        # positives low; full symbol resolution is out of scope for this gate.
        risky = re.search(r'\b(deleteObject|findObject|saveObject|updateObject|loadObject|get(One|Object|Register|Schema))\b', body)
        if risky:
            with open(log_path, 'a', encoding='utf-8') as g:
                g.write(f"{fp}:{m['start_line']}: {m['name']}() calls a service method that may throw a tracked exception, "
                        f"but has no matching try/catch and no @throws declaration\n")
PY
fi
# Opt-out: `[hydra-gate-controller-exception-translation exclude] <reason>` in
# the PR body or head commit message (≥ 20 chars).
if [ -s "${_cxt_log}" ]; then
    _cxt_optout_re='\[hydra-gate-controller-exception-translation exclude\][[:space:]]+.{20,}'
    _cxt_optout=""
    [ -n "${HYDRA_GATE_PR_BODY:-}" ] && echo "${HYDRA_GATE_PR_BODY:-}" | grep -qE "${_cxt_optout_re}" && _cxt_optout="1"
    [ -z "${_cxt_optout}" ] && git log -1 --pretty=%B 2>/dev/null | grep -qE "${_cxt_optout_re}" && _cxt_optout="1"
    [ -n "${_cxt_optout}" ] && : > "${_cxt_log}"
fi
set +e
_cxt_fail=$(wc -l < "${_cxt_log}" 2>/dev/null | tr -d ' ')
set -e
[ -z "${_cxt_fail}" ] && _cxt_fail=0
if [ "${_cxt_fail}" -eq 0 ]; then
    _pass 49 "controller-exception-translation"
else
    _fail 49 "controller-exception-translation" "${_cxt_fail} controller method(s) missing try/catch or @throws — see ${_cxt_log}"
fi

# ---------------------------------------------------------------------------
# Gate 50: Security-config-fail-mode — controllers/services reading a
# security-relevant config key via `$this->config->getValueString(...)`
# must handle the empty-default explicitly (fail closed, log-warn, or
# guard). Silent fallback on empty deactivates the defense. Observed
# 2026-07-03 on opencatalogi#86 — empty `listing_register` OR
# `listing_schema` silently deactivated WOO-515's scope-DELETE guard.
#
# Skill: .claude/skills/hydra-gate-security-config-fail-mode/SKILL.md
# ---------------------------------------------------------------------------
_scfm_log=/tmp/hydra-gate-security-config-fail-mode.log
: > "${_scfm_log}"
_scfm_files=()
while IFS= read -r f; do
    [ -f "$f" ] || continue
    _in_scope "$f" || continue
    _scfm_files+=("$f")
done < <(_enum_tracked '(Controller|Service)[^/]*\.php$' lib)
if [ "${#_scfm_files[@]}" -gt 0 ]; then
    python3 - "${_scfm_log}" "${_scfm_files[@]}" << 'PY'
import re, sys
log_path = sys.argv[1]
files = sys.argv[2:]
SEC_KEY = re.compile(
    r"getValue(?:String|Bool|Int)\s*\(\s*['\"][^'\"]+['\"]\s*,\s*['\"]"
    r"(?P<key>[^'\"]*"
    r"(?:register|schema|allow[_-]?list|allow_?list|whitelist|blocklist|"
    # Quote-or-underscore-anchored short tokens so `author_name`,
    # `authenticate`, `oauth_client_id` don't spuriously match, while
    # bare `auth`/`rbac`/`permission` and long-form suffixed keys
    # (auth_key, basic_auth, rbac_scope, permission_check) do. Uses
    # lookaround so neither anchor consumes the closing key-quote —
    # a consuming form corrupts the outer capture and would fail on
    # `basic_auth` etc. because it eats the trailing `'`.
    r"csrf|(?<=['\"]|_)rbac(?=['\"]|_)|(?<=['\"]|_)permission(?=['\"]|_)|(?<=['\"]|_)auth(?=['\"]|_)|"
    r"_secret|_key|_token|instance_aliases|trusted_domains|trusted_proxies)"
    r"[^'\"]*)"
    r"['\"]",
    re.IGNORECASE,
)
for fp in files:
    try:
        with open(fp, encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except OSError:
        continue
    src = ''.join(lines)
    for m in SEC_KEY.finditer(src):
        # Find the line number of the match
        lineno = src[:m.start()].count('\n') + 1
        # Window: 10 lines after the config read
        window = ''.join(lines[lineno:lineno+10])
        # Look for fail-mode signals
        has_guard = re.search(
            r"if\s*\(\s*[\$\w\-\>]+\s*(===|!==|==|!=)\s*['\"]{2}\s*\)"       # empty-string compare
            r"|if\s*\(\s*empty\s*\("                                          # empty()
            r"|->logger->(warning|error|critical|alert)"                      # log-warn
            r"|throw\s+new\s+"                                                # throw
            r"|return\s+new\s+(JSONResponse|Response|DataResponse)",          # early return
            window,
        )
        if not has_guard:
            with open(log_path, 'a', encoding='utf-8') as g:
                g.write(f"{fp}:{lineno}: security-relevant config read of \"{m.group('key')}\" has no fail-mode guard within 10 lines\n")
PY
fi
set +e
_scfm_fail=$(wc -l < "${_scfm_log}" 2>/dev/null | tr -d ' ')
set -e
[ -z "${_scfm_fail}" ] && _scfm_fail=0
if [ "${_scfm_fail}" -eq 0 ]; then
    _pass 50 "security-config-fail-mode"
else
    _fail 50 "security-config-fail-mode" "${_scfm_fail} unsafe security-config read(s) — see ${_scfm_log}"
fi

# ---------------------------------------------------------------------------
# Gate 51: Schema-property-titles — every property of every schema in a
# changed OpenRegister register MUST carry a human-friendly English `title`
# and a `description`. The nextcloud-vue form renderer uses
# `label: prop.title || key` (fieldsFromSchema), so a property without a
# `title` shows its raw technical key (`governanceBody`, `closedAt`) to end
# users. ADR-011 (schema standards). Reference exemplars: docudesk,
# softwarecatalog.
#
# Diff-scoped at the PROPERTY level (ADR-020): under --scope-to-diff the
# helper self-scopes to lines changed vs BASE (via HYDRA_GATE_BASE_REF +
# `git diff -U0`), so only properties ADDED or MODIFIED in the PR are checked
# — legacy title debt in a TOUCHED register never blocks an unrelated PR
# (titles enforced going forward only, exactly like gate-16). Builder
# full-repo runs leave the env unset and ratchet every property. The helper
# recurses into nested object `properties` and array `items.properties`.
#
# Skill: .claude/skills/hydra-gate-schema-property-titles/SKILL.md
# ---------------------------------------------------------------------------
_spt_log=/tmp/hydra-gate-schema-property-titles.log
: > "${_spt_log}"
_spt_files=()
while IFS= read -r f; do
    [ -f "$f" ] || continue
    _in_scope "$f" || continue
    _spt_files+=("$f")
done < <(_enum_tracked '(register[^/]*\.json|/register\.d/[^/]*\.json)$' lib/Settings)
if [ "${#_spt_files[@]}" -gt 0 ]; then
    _spt_helper="${SCRIPT_DIR}/lib/check_schema_property_meta.py"
    if [ -f "${_spt_helper}" ]; then
        # Diff-scoped at the PROPERTY level (ADR-020) when --scope-to-diff is
        # set: the helper self-scopes to lines changed vs BASE_REF, so legacy
        # title debt in a touched register never blocks an unrelated PR —
        # titles are enforced going forward only (mirrors gate-16). Builder
        # full-repo runs leave HYDRA_GATE_BASE_REF unset → ratchet every prop.
        if [ "${SCOPE_TO_DIFF}" = "1" ]; then
            HYDRA_GATE_BASE_REF="${BASE_REF}" \
                python3 "${_spt_helper}" "${_spt_files[@]}" >> "${_spt_log}" 2>/dev/null || true
        else
            python3 "${_spt_helper}" "${_spt_files[@]}" >> "${_spt_log}" 2>/dev/null || true
        fi
    else
        echo "[gate-51] WARN: check_schema_property_meta.py not found at ${_spt_helper} — gate-51 skipped" >&2
    fi
fi
set +e
_spt_fail=$(wc -l < "${_spt_log}" 2>/dev/null | tr -d ' ')
set -e
[ -z "${_spt_fail}" ] && _spt_fail=0
if [ "${_spt_fail}" -eq 0 ]; then
    _pass 51 "schema-property-titles"
else
    _fail 51 "schema-property-titles" "${_spt_fail} schema property(ies) missing a human-friendly title/description — see ${_spt_log}"
fi

# ---------------------------------------------------------------------------
# Gate 52: Custom-widget-ratchet — govern the growth of custom kind:"widget"
# component-registry entries (the ADR-036 five-kind registry passed to
# CnAppRoot) per ADR-049 Decision 1 (built-in-first rule for widgets). Two
# mechanics, both in scripts/lib/check_custom_widget_ratchet.py:
#
#   Justification — any kind:"widget" entry ADDED or MODIFIED in the PR diff
#   without a `_note` field fails with the canonical message from the
#   hydra-gate-custom-widget-ratchet spec. Untouched legacy entries never
#   block a PR (ADR-020) — they are burned down by migrations.
#
#   Ratchet — the app's total custom-widget count on the PR head MUST NOT
#   exceed the count on BASE_REF. Growth fails even when every new entry
#   carries a `_note`, unless an in-scope entry carries the documented
#   exception marker `@custom-widget-ratchet exclude <reason>` (the
#   gate-16/19 exclude-reason convention). Counts (base/head/delta) are
#   always reported so migrations can demonstrate the count shrinking.
#
# Library built-in widget keys (object-table, card-grid, form-renderer,
# map-viewer, chart, stats-block, wiki-renderer) are not custom entries and
# are never counted. The helper receives ALL src/**/*.{js,ts,vue} candidates
# (NOT pre-filtered by _in_scope) because the ratchet count is app-wide; it
# self-scopes the justification check to changed entries via
# HYDRA_GATE_BASE_REF + git diff -U0, exactly like gate-51. When no changed
# file declares a kind:"widget" entry the helper prints nothing and exits 0
# (no-op pass — the ratchet is not computed for that PR). Builder full-repo
# runs leave the env unset: every custom entry needs a `_note`; no ratchet.
#
# Skill: .claude/skills/hydra-gate-custom-widget-ratchet/SKILL.md
# ---------------------------------------------------------------------------
_cwr_log=/tmp/hydra-gate-custom-widget-ratchet.log
: > "${_cwr_log}"
_cwr_files=()
while IFS= read -r f; do
    [ -f "$f" ] || continue
    _cwr_files+=("$f")
done < <(find src \( -name '*.js' -o -name '*.ts' -o -name '*.vue' \) \
    -not -path '*/node_modules/*' -not -path '*/dist/*' \
    -not -path '*/build/*' 2>/dev/null)
_cwr_fail=0
if [ "${#_cwr_files[@]}" -gt 0 ]; then
    _cwr_helper="${SCRIPT_DIR}/lib/check_custom_widget_ratchet.py"
    if [ -f "${_cwr_helper}" ]; then
        # Helper exit code = number of findings (capped at 99); stdout gets
        # the finding blocks + the always-on counts report line.
        set +e
        if [ "${SCOPE_TO_DIFF}" = "1" ]; then
            HYDRA_GATE_BASE_REF="${BASE_REF}" \
                python3 "${_cwr_helper}" "${_cwr_files[@]}" >> "${_cwr_log}" 2>&1
        else
            python3 "${_cwr_helper}" "${_cwr_files[@]}" >> "${_cwr_log}" 2>&1
        fi
        _cwr_fail=$?
        set -e
    else
        echo "[gate-52] WARN: check_custom_widget_ratchet.py not found at ${_cwr_helper} — gate-52 skipped" >&2
    fi
fi
# Surface the base/head/delta report on stdout (spec: the counts are always
# reported so migrations can show the number shrinking).
_cwr_counts=$(grep -m1 -o 'base=[0-9]* head=[0-9]* delta=[+-]*[0-9]*.*' "${_cwr_log}" 2>/dev/null || true)
[ -n "${_cwr_counts}" ] && echo "[gate-52] custom-widget-ratchet: ${_cwr_counts}"
if [ "${_cwr_fail}" -eq 0 ]; then
    _pass 52 "custom-widget-ratchet"
else
    _fail 52 "custom-widget-ratchet" "${_cwr_fail} custom-widget finding(s)${_cwr_counts:+ (${_cwr_counts})} — see ${_cwr_log}"
fi

# ---------------------------------------------------------------------------
# Gate 53: effective-manifest-crossref — build the EFFECTIVE manifest exactly
# as the lib bootstrap does (base src/manifest.json + src/manifest.d/*.json
# fragments in ascending filename order (ADR-037) + src/menu-layout.json
# relocations → removals → settingsSection (ADR-044)), then:
#   1. validate the ASSEMBLED result through the canonical gate-22 validator
#      (scripts/lib/check_manifest.js — canonical schema + semantic checks);
#      a fragment-introduced violation fails even when the base alone passes;
#   2. run the cross-reference joins JSON Schema cannot express
#      (scripts/lib/check_manifest_crossref.js): menu-route → page-id,
#      open-page action targets (open-modal degrades to WARN — the modal
#      registry is app code), register/schema slug resolution against
#      lib/Settings/*register*.json (+ register.d/*.json; no register JSON
#      in-repo → WARN, runtime-bound registers), deepLink route
#      correspondence, and the ADR-044 no-functionality-loss removals
#      invariant (a removal must never orphan its route).
#
# Why (2026-07-06 audit item 19): gate-22 validates ONLY the base manifest.
# shillinq ships 75+ fragments gate-22 never sees; the 2026-07-06 live e2e
# caught zaakafhandelapp detail widgets referencing besluit/resultaat schemas
# absent from any register declaration — OpenRegister 404s rendered raw
# "Request failed with status code 404" to end users.
#
# Assembly is the hydra-VENDORED buildManifest pipeline
# (scripts/lib/build_effective_manifest.js, sync-noted to
# nextcloud-vue/src/utils/buildManifest.js) — one deterministic merge
# generation fleet-wide, never the app's pinned lib copy.
#
# Diff-scope (ADR-020): with --scope-to-diff, the gate runs only when the PR
# touches src/manifest.json, src/manifest.d/**, src/menu-layout.json, or
# lib/Settings/*register*.json; otherwise it PASSes informationally. Full
# runs (builder, fleet sweep) always run. Tier 0 (no manifest) skips quietly.
#
# Fail-closed (mirrors scripts/fleet-manifest-sweep.sh): a missing helper or
# unresolvable Ajv FAILs the gate — never a silent pass.
#
# NOTE: `set -e` is still enabled at this point in the script (gates 25/26
# leave it on, see the gate-27 comment) — every command below is guarded.
#
# Skill: .claude/skills/hydra-gate-effective-manifest-crossref/SKILL.md
# Spec:  openspec/changes/gate-53-effective-manifest-crossref/specs/gate-effective-manifest-crossref/spec.md
# ---------------------------------------------------------------------------
if [ -f src/manifest.json ]; then
    _em_log=/tmp/hydra-gate-effective-manifest-crossref.log
    : > "${_em_log}"
    _em_builder="${SCRIPT_DIR}/lib/build_effective_manifest.js"
    _em_crossref="${SCRIPT_DIR}/lib/check_manifest_crossref.js"
    _em_validator="${SCRIPT_DIR}/lib/check_manifest.js"
    # Diff-scope trigger set: any manifest input touched → run for real.
    _em_touched=0
    if [ "${SCOPE_TO_DIFF}" = "1" ]; then
        while IFS= read -r _em_f; do
            [ -z "${_em_f}" ] && continue
            case "${_em_f}" in
                src/manifest.json|src/manifest.d/*|src/menu-layout.json|lib/Settings/*register*.json)
                    _em_touched=1 ;;
            esac
        done <<< "${CHANGED_FILES}"
    else
        _em_touched=1
    fi
    if [ "${_em_touched}" -eq 0 ]; then
        # PR touches no manifest input — informational pass (ADR-020).
        _pass 53 "effective-manifest-crossref"
    elif [ ! -f "${_em_builder}" ] || [ ! -f "${_em_crossref}" ] || [ ! -f "${_em_validator}" ]; then
        # Gate misconfiguration — a vendored helper is missing. Fail-closed.
        _fail 53 "effective-manifest-crossref" "vendored helper missing under ${SCRIPT_DIR}/lib (need build_effective_manifest.js + check_manifest_crossref.js + check_manifest.js) — fail-closed"
    elif ! node -e "require('ajv/dist/2020')" >/dev/null 2>&1 \
        && ! node -e "require.resolve('ajv/dist/2020', { paths: ['${SCRIPT_DIR}/lib'] })" >/dev/null 2>&1; then
        # Without Ajv the structural stage cannot validate the assembled
        # manifest for real — refuse to run fail-open (fleet-sweep guard).
        _fail 53 "effective-manifest-crossref" "ajv not resolvable from ${SCRIPT_DIR}/lib — refusing to run fail-open (set NODE_PATH or install ajv)"
    else
        _em_tmp=$(mktemp /tmp/hydra-gate53-effective.XXXXXX.json 2>/dev/null || true)
        _em_reason=""
        if [ -z "${_em_tmp}" ]; then
            # Temp-file handoff failed — fail-closed, never skipped.
            _em_reason="mktemp failed — cannot write the assembled manifest (fail-closed)"
        elif ! node "${_em_builder}" --app-dir . --out "${_em_tmp}" >> "${_em_log}" 2>&1; then
            _em_reason="effective manifest could not be assembled (bad JSON input?) — see ${_em_log}"
        elif ! node "${_em_validator}" "${_em_tmp}" >> "${_em_log}" 2>&1; then
            _em_n=$(grep -cE '^at ' "${_em_log}" 2>/dev/null || true)
            { [ -z "${_em_n}" ] || [ "${_em_n}" -eq 0 ]; } && _em_n=1
            _em_reason="${_em_n} structural violation(s) in the ASSEMBLED manifest (base+fragments+menu-layout) — see ${_em_log}"
        elif ! node "${_em_crossref}" --app-dir . --manifest "${_em_tmp}" >> "${_em_log}" 2>&1; then
            # Count error-severity findings only — WARN lines never fail.
            _em_n=$(grep -E '^at ' "${_em_log}" 2>/dev/null | grep -cv ': WARN ' || true)
            { [ -z "${_em_n}" ] || [ "${_em_n}" -eq 0 ]; } && _em_n=1
            _em_reason="${_em_n} cross-reference failure(s) in the effective manifest — see ${_em_log}"
        fi
        [ -n "${_em_tmp}" ] && rm -f "${_em_tmp}"
        # Surface WARN-severity findings on stdout even on a pass (they never
        # set the exit code, but they must not vanish either).
        _em_warns=$(grep -cE '^at .*: WARN ' "${_em_log}" 2>/dev/null || true)
        [ -n "${_em_warns}" ] && [ "${_em_warns}" -gt 0 ] && echo "[gate-53] effective-manifest-crossref: ${_em_warns} WARN finding(s) (non-blocking) — see ${_em_log}"
        if [ -z "${_em_reason}" ]; then
            _pass 53 "effective-manifest-crossref"
        else
            _fail 53 "effective-manifest-crossref" "${_em_reason}"
        fi
    fi
fi

# ---------------------------------------------------------------------------
# Gate 54: relation-dialect — enforce the ONE canonical OpenRegister relation
# dialect (ADR-062 rules 6/7/10) across changed register files
# (lib/Settings/*register*.json + lib/Settings/register.d/*.json). A relation
# is a schema PROPERTY carrying type:string (or array items), format:uuid and
# $ref:<schemaKey> (same register set); x-relation-filter rides on that same
# property. Bespoke per-schema dialects are banned. Observed 2026-07-08 across
# the fleet detail-page redesign: decidesk's per-schema x-openregister-
# relations blocks (nothing consumed them — retired) and scholiq's bare-string
# FKs-by-convention (85 converted); procest's case.status proved the rule-10
# lifecycle carve-out.
#
# The helper checks: (a) banned x-openregister-relations dialect; (b) relation-
# shaped property (format:uuid + relation description, no $ref) — property-level
# diff-scoped like gate-51; (c) x-relation-filter misplacement / filter-on-non-
# relation; (d) filter tokens (@objectId / @object.<field>, no two-hop, no
# unknown/nonexistent field); (e) rule-10 frozen-lifecycle readOnly; (f) $ref
# targets resolve to a schema key in the register set (numeric $ref → WARN).
#
# Diff-scoped (ADR-020): only the changed register files are inspected, so
# legacy debt in an untouched register never blocks an unrelated PR. WARN-
# prefixed lines are advisory and never fail the gate.
#
# Skill: .claude/skills/hydra-gate-relation-dialect/SKILL.md
# ---------------------------------------------------------------------------
_rd_log=/tmp/hydra-gate-relation-dialect.log
: > "${_rd_log}"
_rd_files=()
while IFS= read -r f; do
    [ -f "$f" ] || continue
    _in_scope "$f" || continue
    _rd_files+=("$f")
done < <(_enum_tracked '(register[^/]*\.json|/register\.d/[^/]*\.json)$' lib/Settings)
if [ "${#_rd_files[@]}" -gt 0 ]; then
    _rd_helper="${SCRIPT_DIR}/lib/check_relation_dialect.py"
    if [ -f "${_rd_helper}" ]; then
        # Property-level diff-scoping for the relation-shape check when
        # --scope-to-diff is set (mirrors gate-51); other checks scope to the
        # changed file set. Builder full-repo runs leave the env unset.
        if [ "${SCOPE_TO_DIFF}" = "1" ]; then
            HYDRA_GATE_BASE_REF="${BASE_REF}" \
                python3 "${_rd_helper}" "${_rd_log}" "${_rd_files[@]}" >/dev/null 2>&1 || true
        else
            python3 "${_rd_helper}" "${_rd_log}" "${_rd_files[@]}" >/dev/null 2>&1 || true
        fi
    else
        echo "[gate-54] WARN: check_relation_dialect.py not found at ${_rd_helper} — gate-54 skipped" >&2
    fi
fi
set +e
_rd_fail=$(grep -cv '^WARN:' "${_rd_log}" 2>/dev/null | tr -d ' ')
_rd_warn=$(grep -c '^WARN:' "${_rd_log}" 2>/dev/null | tr -d ' ')
set -e
[ -z "${_rd_fail}" ] && _rd_fail=0
[ -z "${_rd_warn}" ] && _rd_warn=0
[ "${_rd_warn}" -gt 0 ] && echo "[gate-54] relation-dialect: ${_rd_warn} WARN finding(s) (non-blocking) — see ${_rd_log}"
if [ "${_rd_fail}" -eq 0 ]; then
    _pass 54 "relation-dialect"
else
    _fail 54 "relation-dialect" "${_rd_fail} non-canonical relation dialect finding(s) — see ${_rd_log}"
fi

# ---------------------------------------------------------------------------
# Gate 55: detail-page-discipline — enforce the manifest side of the ADR-062
# detail-page grid discipline (rules 1/2/5/8/9) on changed manifests
# (src/manifest.json + src/manifest.d/*.json). For every type:"detail" page
# the diff TOUCHES: (a) page-level widgets[] AND config.widgets both present
# (render-path shadowing); (b) config.summaryAggregates present (deprecated,
# rule 2); (c) widgets↔layout integrity (1:1 id↔widgetId + no 12-col overlap);
# (d) sidebar CnAuditTrailTab / audit-trail (use widgets:[{type:'audit'}]);
# (e) widget icons in the shared registry (rule 8); (f) viewAllRoute/rowRoute
# resolve to a page id in the merged manifest.
#
# Diff-scoped (ADR-020): only changed manifest files, and within them only the
# detail pages the diff touches (page object line-span). Complements gate-53
# (menu/deeplink route crossref) — gate-53 does NOT look at widget
# rowRoute/viewAllRoute, so there is no overlap.
#
# Skill: .claude/skills/hydra-gate-detail-page-discipline/SKILL.md
# ---------------------------------------------------------------------------
_dpd_log=/tmp/hydra-gate-detail-page-discipline.log
: > "${_dpd_log}"
_dpd_files=()
while IFS= read -r f; do
    [ -f "$f" ] || continue
    _in_scope "$f" || continue
    _dpd_files+=("$f")
done < <(find src -maxdepth 1 -name 'manifest.json' 2>/dev/null; \
    find src/manifest.d -name '*.json' 2>/dev/null)
if [ "${#_dpd_files[@]}" -gt 0 ]; then
    _dpd_helper="${SCRIPT_DIR}/lib/check_detail_page_discipline.py"
    if [ -f "${_dpd_helper}" ]; then
        # Page-level diff-scoping when --scope-to-diff is set: only detail pages
        # the PR touches are checked. Builder full-repo runs leave the env unset
        # → every detail page in a changed manifest is checked.
        if [ "${SCOPE_TO_DIFF}" = "1" ]; then
            HYDRA_GATE_BASE_REF="${BASE_REF}" \
                python3 "${_dpd_helper}" "${_dpd_log}" "${_dpd_files[@]}" >/dev/null 2>&1 || true
        else
            python3 "${_dpd_helper}" "${_dpd_log}" "${_dpd_files[@]}" >/dev/null 2>&1 || true
        fi
    else
        echo "[gate-55] WARN: check_detail_page_discipline.py not found at ${_dpd_helper} — gate-55 skipped" >&2
    fi
fi
set +e
_dpd_fail=$(wc -l < "${_dpd_log}" 2>/dev/null | tr -d ' ')
set -e
[ -z "${_dpd_fail}" ] && _dpd_fail=0
if [ "${_dpd_fail}" -eq 0 ]; then
    _pass 55 "detail-page-discipline"
else
    _fail 55 "detail-page-discipline" "${_dpd_fail} detail-page discipline finding(s) — see ${_dpd_log}"
fi

# ---------------------------------------------------------------------------
# Gate 56: register-handler-resolution — every class/FQCN + method
# referenced from an OpenRegister register JSON (lib/Settings/*register*.json
# + lib/Settings/register.d/*.json) — lifecycle guards (requires/guard/save/
# fallbackGuard/preconditions) and calculation/aggregation/notification
# `handler` entries — MUST resolve to a class that actually exists in the
# repo AND, when a `::method` suffix is present, a method that exists on it.
#
# Observed 2026-07-13 on shillinq (orphan-capability-sweep, issue #425): 17
# guard classes referenced from register.d requires/guard/save/fallbackGuard
# entries did not exist at all, and PeriodCloseGuard::trialBalanceVerifies
# referenced a real class but a method that was never written. OpenRegister's
# LifecycleGuardRegistry::resolve() throws uncaught in
# LifecycleValidationListener, so every one of those lifecycle transitions
# hard-fails (HTTP 500) at runtime while the spec/tests/PHPCS/PHPStan all stay
# green — nothing else in the fleet's tooling ever inspects the JSON STRING.
#
# Diff-scoped (ADR-020): under --scope-to-diff only changed register files
# are inspected — legacy debt in an untouched register never blocks an
# unrelated PR.
#
# Skill: .claude/skills/hydra-gate-register-handler-resolution/SKILL.md
# ---------------------------------------------------------------------------
_rhr_log=/tmp/hydra-gate-register-handler-resolution.log
: > "${_rhr_log}"
_rhr_files=()
while IFS= read -r f; do
    [ -f "$f" ] || continue
    _in_scope "$f" || continue
    _rhr_files+=("$f")
done < <(find lib/Settings -name '*register*.json' \
    -not -path '*/vendor/*' -not -path '*/node_modules/*' 2>/dev/null; \
    find lib/Settings/register.d -name '*.json' 2>/dev/null)
if [ "${#_rhr_files[@]}" -gt 0 ]; then
    _rhr_helper="${SCRIPT_DIR}/lib/check_register_handler_resolution.py"
    if [ -f "${_rhr_helper}" ]; then
        python3 "${_rhr_helper}" "${_rhr_files[@]}" >> "${_rhr_log}" 2>/dev/null || true
    else
        echo "[gate-56] WARN: check_register_handler_resolution.py not found at ${_rhr_helper} — gate-56 skipped" >&2
    fi
fi
set +e
_rhr_fail=$(wc -l < "${_rhr_log}" 2>/dev/null | tr -d ' ')
set -e
[ -z "${_rhr_fail}" ] && _rhr_fail=0
if [ "${_rhr_fail}" -eq 0 ]; then
    _pass 56 "register-handler-resolution"
else
    _fail 56 "register-handler-resolution" "${_rhr_fail} unresolved register-handler reference(s) — see ${_rhr_log}"
fi

# ---------------------------------------------------------------------------
# Gate 57: orphaned-write-capability — every PUBLIC side-effecting method on
# lib/Service/** (name starting with post/create/save/emit/dispatch/notify/
# write/export/generate/submit/record/settle/clear/reconcile/seed/publish/
# issue) MUST have at least one non-test production caller, OR be invoked
# through a recognised indirect seam: a register.d handler/guard/requires/
# save/fallbackGuard/preconditions entry, an event listener registered in
# lib/AppInfo/Application.php, a background job registered in
# appinfo/info.xml, or a documented Log*Adapter intentional log-only seam.
#
# Observed 2026-07-13 on shillinq (orphan-capability-sweep, 13 filed
# issues): DisposalJournalEmitter::emit(), IntercompanyJournalService, the
# inventory-cogs-posting.json declarative posting path, five
# Payroll*HandoffService classes, and OssInvoiceRouter::route() were all
# fully implemented and unit-tested by calling the class directly, spec'd
# "done", with ZERO production callers — 100% dead while every prior gate
# and the test suite stayed green.
#
# Diff-scoped (ADR-020): under --scope-to-diff only changed Service files
# are inspected — legacy dead code in an untouched file never blocks an
# unrelated PR.
#
# Skill: .claude/skills/hydra-gate-orphaned-write-capability/SKILL.md
# ---------------------------------------------------------------------------
_owc_log=/tmp/hydra-gate-orphaned-write-capability.log
: > "${_owc_log}"
_owc_files=()
while IFS= read -r f; do
    [ -f "$f" ] || continue
    _in_scope "$f" || continue
    _owc_files+=("$f")
done < <(_enum_tracked '\.php$' lib/Service | grep -v '/tests/')
if [ "${#_owc_files[@]}" -gt 0 ]; then
    _owc_helper="${SCRIPT_DIR}/lib/check_orphaned_write_capability.py"
    if [ -f "${_owc_helper}" ]; then
        python3 "${_owc_helper}" "${_owc_files[@]}" >> "${_owc_log}" 2>/dev/null || true
    else
        echo "[gate-57] WARN: check_orphaned_write_capability.py not found at ${_owc_helper} — gate-57 skipped" >&2
    fi
fi
set +e
_owc_fail=$(wc -l < "${_owc_log}" 2>/dev/null | tr -d ' ')
set -e
[ -z "${_owc_fail}" ] && _owc_fail=0
if [ "${_owc_fail}" -eq 0 ]; then
    _pass 57 "orphaned-write-capability"
else
    _fail 57 "orphaned-write-capability" "${_owc_fail} orphaned write-capability method(s) — see ${_owc_log}"
fi

# ---------------------------------------------------------------------------
# Gate 58: e2e-networkidle — `networkidle` NEVER settles on Nextcloud.
# NC's notification poll keeps at least one request in flight for the whole
# session, so `page.waitForLoadState('networkidle')` and
# `goto(..., { waitUntil: 'networkidle' })` can never resolve: each call
# silently burns its ENTIRE timeout budget. The customary
# `.catch(() => {})` swallows the throw while still paying the full cost,
# so the symptom is a bare "Test timeout of Nms exceeded" that is
# indistinguishable from an app outage.
#
# Observed 2026-07-27 on larpingapp: two such waits inside
# `tests/e2e/spec-coverage/index-pages.spec.ts::freshNav()` made EVERY
# index-pages test time out at 90s on a fully idle host. The fleet sweep
# then found 278 call-sites across 128 files in 20 apps (scholiq 26 files,
# docudesk 22, nldesign 17, openconnector 14, larpingapp 9, openbuild 9…)
# — the single largest source of slow/flaky e2e in the fleet.
#
# Canonical fix: `waitUntil: 'domcontentloaded'` + explicit element
# assertions as the readiness signal (openconnector documents this in
# tests/e2e/regression/manifest-pages.spec.ts). ADR-074 rule 4.
#
# Diff-scoped per ADR-020 so the 278-site legacy backlog never blocks an
# unrelated PR — only e2e files the PR touches are checked. Suppress a
# justified single use with an `e2e-networkidle exclude <reason>` comment
# on the same line.
#
# Skill: .claude/skills/hydra-gate-e2e-networkidle/SKILL.md
# ---------------------------------------------------------------------------
_nwi_log=/tmp/hydra-gate-e2e-networkidle.log
: > "${_nwi_log}"
while IFS= read -r f; do
    [ -f "$f" ] || continue
    _in_scope "$f" || continue
    grep -nE "waitForLoadState\([[:space:]]*['\"]networkidle['\"]|waitUntil:[[:space:]]*['\"]networkidle['\"]" "$f" 2>/dev/null \
        | grep -v "e2e-networkidle exclude" \
        | while IFS= read -r hit; do
            echo "${f}:${hit}" >> "${_nwi_log}"
        done
done < <(find tests/e2e -type f \( -name '*.ts' -o -name '*.js' \) 2>/dev/null)
set +e
_nwi_fail=$(wc -l < "${_nwi_log}" 2>/dev/null | tr -d ' ')
set -e
[ -z "${_nwi_fail}" ] && _nwi_fail=0
if [ "${_nwi_fail}" -eq 0 ]; then
    _pass 58 "e2e-networkidle"
else
    _fail 58 "e2e-networkidle" "${_nwi_fail} networkidle wait(s) in changed e2e file(s) — never settles on Nextcloud, use waitUntil:'domcontentloaded' (ADR-074 rule 4); see ${_nwi_log}"
fi

# ---------------------------------------------------------------------------
# Gate 59: unclosable-gate — a version/state config key that is READ but never
# WRITTEN is not a gate. It sits at its default forever, the comparison never
# short-circuits, and the expensive setup it guards (config import, register
# bootstrap, schema seeding) runs on EVERY call. Because these guards live in
# Application::boot() or a service reached from it, that is every request to the
# whole instance.
#
# Observed 2026-07-29 on docudesk: SettingsInitializer::initialize() read
# `configuration_version` to decide whether its OpenRegister configuration was
# imported. Nothing wrote it, so importFromApp() ran every request —
# 354ms -> 255ms median once set (~28% of every request) and 14 schema lookups
# per object create. ADR-076 rule 3.
#
# Diff-scoped per ADR-020: only runs when lib/ changed.
# Suppress with a comment containing `unclosable-gate exclude <reason>`.
# Skill: .claude/skills/hydra-gate-unclosable-gate/SKILL.md
# ---------------------------------------------------------------------------
_ucg_log=/tmp/hydra-gate-unclosable-gate.log
: > "${_ucg_log}"
if [ -d lib ] && printf '%s\n' "${CHANGED_FILES}" | grep -qE '^lib/.*\.php$'; then
    set +e
    python3 "${SCRIPT_DIR}/lib/check_unclosable_gate.py" . > "${_ucg_log}" 2>&1
    _ucg_rc=$?
    set -e
    if [ "${_ucg_rc}" -eq 0 ]; then
        _pass 59 "unclosable-gate"
    else
        _fail 59 "unclosable-gate" "config gate(s) read but never written — guarded setup runs on every request (ADR-076 rule 3); see ${_ucg_log}"
    fi
else
    _pass 59 "unclosable-gate"
fi

# ---------------------------------------------------------------------------
# Gate 60: icon-vocabulary — every manifest menu `icon` must come from the
# canonical semantic icon vocabulary (ADR-077), so a glyph reads the same way in
# every Conduction app. Validated against the HYDRA-VENDORED table in
# scripts/schemas/semantic-icons.json, not whatever version the app has pinned
# (same rule as gate 22's schema).
#
# HARD FAILS:
#   - an MDI-style name that exists neither in the vocabulary nor in the app's
#     installed vue-material-design-icons (shillinq shipped `LedgerOutline` and
#     `FileSignOutline` — names with no upstream existence, blank anywhere they
#     are copied)
#   - a Tier A concept on a non-canonical icon (Dashboard / Store / Settings /
#     Documentation / Features & roadmap — the cross-app chrome)
#   - a legacy `icon-*` name with no CSS_ICON_TO_MDI bridge entry, which falls
#     through to the raw NC class and can render invisible on NC34+ light themes
#
# WARNS (non-blocking): any remaining bridged `icon-*` (deprecated by rule 1),
# and a Tier B concept on a non-canonical icon.
#
# Apps without a manifest are skipped. Diff-scoped per ADR-020.
#
# Spec: openspec/architecture/adr-077-semantic-icon-vocabulary.md
# ---------------------------------------------------------------------------
_iv_log=/tmp/hydra-gate-icon-vocabulary.log
: > "${_iv_log}"
if [ -f src/manifest.json ]; then
    _iv_args=""
    if [ "${SCOPE_TO_DIFF}" = "1" ]; then
        # Only manifests this PR touched. No touched manifest → nothing to gate.
        _iv_changed=$(printf '%s\n' "${CHANGED_FILES}" | grep -E '^src/(manifest\.json|manifest\.d/.*\.json)$' || true)
        if [ -z "${_iv_changed}" ]; then
            _iv_changed="__none__"
        fi
        if [ "${_iv_changed}" = "__none__" ]; then
            _pass 60 "icon-vocabulary"
            _iv_args="__skip__"
        else
            for _f in ${_iv_changed}; do
                _iv_args="${_iv_args} --changed-file ${_f}"
            done
        fi
    fi
    if [ "${_iv_args}" != "__skip__" ]; then
        set +e
        python3 "${SCRIPT_DIR}/lib/check_icon_vocabulary.py" . ${_iv_args} > "${_iv_log}" 2>&1
        _iv_rc=$?
        set -e
        # Surface warnings even on a pass — they are the deprecation pressure.
        grep -E '^(WARN|NOTE)' "${_iv_log}" || true
        if [ "${_iv_rc}" -eq 0 ]; then
            _pass 60 "icon-vocabulary"
        else
            _iv_n=$(grep -cE '^FAIL' "${_iv_log}" 2>/dev/null || echo 1)
            [ "${_iv_n}" -eq 0 ] && _iv_n=1
            _fail 60 "icon-vocabulary" "${_iv_n} icon(s) outside the canonical vocabulary (ADR-077); see ${_iv_log}"
        fi
    fi
else
    _pass 60 "icon-vocabulary"
fi

# ---------------------------------------------------------------------------
# Gate 61: listener-work-placement — a listener registered on a POST object
# event (ObjectCreatedEvent / ObjectUpdatedEvent / ObjectDeletedEvent) runs
# INSIDE the user's write. It cannot influence that write, so every millisecond
# it spends is pure latency charged to the request.
#
# The `*ing` / `*ed` suffix already encodes the sync/async line — `*ing`
# listeners may veto or mutate and MUST stay synchronous; `*ed` listeners must
# not do real work on the request path. Nothing enforced that: 134 of the
# fleet's 149 object-lifecycle registrations are on post events, and three
# route through the actor-forwarded deferral contract.
#
# FAILS when a post-event handler does outbound I/O (IClient / IMailer /
# curl_*), a write (saveObject / ->insert( / ->update(), or an UNBOUNDED
# findAll(), and neither routes through ListenerDeferralService nor carries
# a reason-bearing `@listener-placement inline <category> — <reason>` on the
# handler. A BARE annotation with no category, or a category with no reason,
# fails — same shape as gate 16's `@spec exclude` and gate 19's `@e2e exclude`.
#
# Categories are CLOSED (ADR-078 D2): realtime, sapi-memory, cheap-bounded,
# correctness. A fifth needs an ADR amendment, not a new string in a docblock.
#
# ALWAYS diff-scoped per ADR-020, in both full and scoped runs: this gate is
# about NEW debt. The 149-registration backlog is a fleet work-list, not a
# reason to block an unrelated PR. The helper fails closed when the base ref
# does not resolve, so an unscopable run is never reported as a clean one.
#
# NOTE ON PLACEMENT: this block is at TOP LEVEL, deliberately outside any
# `if [ "${_FAILED}" -eq 0 ]` guard. A gate that only runs once everything else
# passed is green-but-dead — its own failures are swallowed exactly when a PR
# is already in trouble.
#
# Spec: openspec/architecture/adr-078-object-event-work-placement.md
# Skill: .claude/skills/hydra-gate-listener-work-placement/SKILL.md
# ---------------------------------------------------------------------------
_lwp_log=/tmp/hydra-gate-listener-work-placement.log
: > "${_lwp_log}"
if [ -d lib/AppInfo ]; then
    set +e
    python3 "${SCRIPT_DIR}/lib/check_listener_placement.py" . --base "${BASE_REF}" > "${_lwp_log}" 2>&1
    _lwp_rc=$?
    set -e
    if [ "${_lwp_rc}" -eq 0 ]; then
        _pass 61 "listener-work-placement"
    else
        _lwp_n=$(grep -cE '^FAIL' "${_lwp_log}" 2>/dev/null || echo 1)
        [ "${_lwp_n}" -eq 0 ] && _lwp_n=1
        _fail 61 "listener-work-placement" "${_lwp_n} post-event listener(s) doing synchronous work with no deferral and no justification (ADR-078); see ${_lwp_log}"
    fi
else
    _pass 61 "listener-work-placement"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
_SUMMARY_REACHED=1
echo ""
if [ "${_FAILED}" -eq 0 ]; then
    echo "[hydra-gates] ALL 61 GATES GREEN"
else
    echo "[hydra-gates] ${_FAILED} gate(s) failed"
fi
exit "${_FAILED}"
