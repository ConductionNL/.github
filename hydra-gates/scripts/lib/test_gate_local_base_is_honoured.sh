#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# test_gate_local_base_is_honoured.sh — one --base, every gate, and a base that
# IS HEAD is refused by name rather than rewritten into a whole-tree audit.
#
# WHY THIS EXISTS (2026-09-12)
# ----------------------------
# A diff-scoped run on a fresh dossiq clone, `--scope-to-diff --base fake-base`,
# reported gate-16 FAIL "161 changed method(s) missing @spec" in files the
# change never touched, gate-52 "base=0 head=9", gate-69 FAIL, gate-19 WARNING
# on 1,668 scenarios, and took 22m48s. The two-line change under test was
# UNCOMMITTED and `fake-base` had been created AT HEAD. The runner saw a base
# equal to HEAD, found no push payload, and fell back — as #183 designed for a
# push whose previous tip is unreachable — to the EMPTY TREE: 4,753 files in
# scope. Every gate honoured the base it was handed; the base had been rewritten
# three screens up, in prose, and the run read as "the gates ignore --base".
#
# Three properties, each measured on a real repository with a real local branch:
#
#   1. A LOCAL BRANCH NAME IS A BASE. `--base local-base` (no `origin/`) scopes
#      every diff-scoped file list AND every delta gate to the one committed
#      change: SCOPE-FILE-COUNT is 1, gate-16 names ONLY the changed file, the
#      delta gates that have no subject in that diff decline by name, and the
#      whole diff-scoped run finishes in well under a minute.
#   2. A BASE THAT IS HEAD, WITH NO PUSH CONTEXT, IS REFUSED. Exit 99, the
#      uncommitted files named, `--full` named as the way to ask for the audit,
#      and ZERO `[gate-` lines: nothing is audited by accident.
#   3. THE #183 PUSH FALLBACK SURVIVES. With a push context the previous tip is
#      used when it resolves, and the whole-tree audit still happens when it is
#      the null sha — that path is CI's and this change must not touch it.
#
# Run: bash scripts/lib/test_gate_local_base_is_honoured.sh
set -uo pipefail

GF_PKG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../.." && pwd)"
export GF_PKG_ROOT
# shellcheck source=./gate_fixture_support.sh
. "${GF_PKG_ROOT}/scripts/lib/gate_fixture_support.sh"

SRC="${GF_PKG_ROOT}/scripts/test-fixtures/base-ref-channel/app"
RUNNER="${GF_PKG_ROOT}/scripts/run-hydra-gates.sh"
PROBE="lib/Service/LocalBaseProbe.php"
BUDGET_S=60

_fail_n=0; _pass_n=0
_ok()  { _pass_n=$((_pass_n + 1)); printf 'PASS — %s\n' "$1"; }
_bad() { _fail_n=$((_fail_n + 1)); printf 'FAIL — %s\n' "$1"; }

[ -d "${SRC}" ] || { echo "FAIL — fixture missing at ${SRC}; every assertion below would be vacuous."; exit 1; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/hydra-localbase.XXXXXXXX")"
trap 'rm -rf "${WORK}"' EXIT
REPO="${WORK}/app"

# Base: the fixture as shipped. `local-base` is a plain local branch, no
# `origin/` prefix, no remote-tracking ref — the shape a human types.
gf_build_repo "${REPO}" "${SRC}"
gf_commit_all "${REPO}" "base"
( cd "${REPO}" && git branch local-base )
# The change: ONE new file with ONE public method and no @spec, so gate-16 has
# exactly one finding to make, and it is in the changed file.
mkdir -p "${REPO}/lib/Service"
cat > "${REPO}/${PROBE}" <<'PHP'
<?php
/**
 * @license EUPL-1.2
 * @copyright Conduction B.V.
 */

namespace OCA\ChannelFixture\Service;

class LocalBaseProbe {
	public function probe(): bool {
		return true;
	}
}
PHP
gf_commit_paths "${REPO}" "feat: one probe method" "${PROBE}"

# _run <outfile> <logdir> [runner args...]
# The RUNNER directly: bin/hydra-gates refuses a base that is HEAD before the
# runner sees it, and property 2 is about the runner's own rewrite.
_run() {
    local _out="$1" _logs="$2"; shift 2
    mkdir -p "${_logs}"
    ( cd "${REPO}" && env -u GITHUB_EVENT_NAME -u HYDRA_GATE_PUSH_BEFORE -u HYDRA_GATE_BASE_REF \
        HYDRA_GATE_LOG_DIR="${_logs}" HYDRA_OR_GATE_BLOCK_AFTER_EPOCH=0 \
        bash "${RUNNER}" "$@" . > "${_out}" 2>&1 )
}

# ===========================================================================
echo "== property 1: a local branch name scopes every gate to the one change =="
# ===========================================================================
_t0=$(date +%s)
_run "${WORK}/one.txt" "${WORK}/log-one" --scope-to-diff --base local-base
_rc=$?
_t1=$(date +%s)
_elapsed=$((_t1 - _t0))

if grep -qxF '[hydra-gates] SCOPE-FILE-COUNT: 1' "${WORK}/one.txt"; then
    _ok "SCOPE-FILE-COUNT is 1 against --base local-base"
else
    _bad "expected SCOPE-FILE-COUNT: 1, got: $(grep -F 'SCOPE-FILE-COUNT' "${WORK}/one.txt" | head -1)"
fi
if grep -qE '^\[hydra-gates\] Scope: diff vs local-base — 1 changed file\(s\)' "${WORK}/one.txt"; then
    _ok "the scope line names the local branch as given, not a rewritten ref"
else
    _bad "the scope line does not name local-base: $(grep -E '^\[hydra-gates\] Scope:' "${WORK}/one.txt" | head -1)"
fi
if [ "${_rc}" -ne 99 ] && [ "${_rc}" -ne 98 ]; then
    _ok "the run reached a verdict (exit ${_rc}, the failure count)"
else
    _bad "the run did not reach a verdict (exit ${_rc})"
fi

_v16="$(gf_verdict "$(cat "${WORK}/one.txt")" 16)"
case "${_v16}" in
    *"FAIL — 1 changed method"*) _ok "gate-16 reports exactly the one method the change added — ${_v16#*: }" ;;
    *) _bad "gate-16 wanted 'FAIL — 1 changed method(s)', got: ${_v16:0:160}" ;;
esac
_sc_log="${WORK}/log-one/hydra-gate-spec-coverage.log"
if [ -s "${_sc_log}" ]; then
    _outside="$(grep -v "^${PROBE}" "${_sc_log}" | grep -c . || true)"
    if [ "${_outside}" = "0" ]; then
        _ok "every gate-16 finding names ${PROBE}; none is outside the changed file"
    else
        _bad "gate-16 reported ${_outside} finding(s) OUTSIDE the changed file: $(grep -v "^${PROBE}" "${_sc_log}" | head -3 | tr '\n' ' ')"
    fi
else
    _bad "gate-16 wrote no findings log at ${_sc_log}"
fi

_v19="$(gf_verdict "$(cat "${WORK}/one.txt")" 19)"
case "${_v19}" in
    *"NOT APPLICABLE"*) _ok "gate-19 declines by name: the diff touches no spec — ${_v19:0:80}" ;;
    *) _bad "gate-19 did not decline on a diff that touches no spec (the whole-tree sweep): ${_v19:0:160}" ;;
esac
for _g in 52 69; do
    if grep -qE "^\[gate-${_g}\] [a-z0-9-]+: FAIL" "${WORK}/one.txt"; then
        _bad "gate-${_g} FAILED on a one-file PHP change (its base was rewritten): $(grep -E "^\[gate-${_g}\]" "${WORK}/one.txt" | head -1 | cut -c1-140)"
    else
        _ok "gate-${_g} does not fail on a change with no subject for it"
    fi
done
if [ "${_elapsed}" -lt "${BUDGET_S}" ]; then
    _ok "the whole diff-scoped run took ${_elapsed}s (budget ${BUDGET_S}s)"
else
    _bad "the diff-scoped run took ${_elapsed}s, over the ${BUDGET_S}s budget"
fi
if grep -q 'TIMING WARNING' "${WORK}/one.txt"; then
    _bad "a gate exceeded the per-gate budget on a one-file diff: $(grep 'TIMING WARNING' "${WORK}/one.txt" | head -1 | cut -c1-120)"
else
    _ok "no gate exceeded the per-gate timing budget"
fi

# ===========================================================================
echo
echo "== property 2: a base that IS HEAD, with an uncommitted edit, is refused by name =="
# ===========================================================================
( cd "${REPO}" && git branch at-head )
printf '\n// an edit that is not committed\n' >> "${REPO}/${PROBE}"
_run "${WORK}/head.txt" "${WORK}/log-head" --scope-to-diff --base at-head
_rc=$?
( cd "${REPO}" && git checkout -q -- "${PROBE}" )

if [ "${_rc}" -eq 99 ]; then
    _ok "exit 99: the run refused rather than auditing the tree"
else
    _bad "expected exit 99, got ${_rc}"
fi
if grep -q "resolves to HEAD" "${WORK}/head.txt"; then
    _ok "the refusal says the base resolves to HEAD"
else
    _bad "the refusal does not say the base is HEAD"
fi
if grep -q "uncommitted change(s)" "${WORK}/head.txt" && grep -qF "${PROBE}" "${WORK}/head.txt"; then
    _ok "the refusal names the uncommitted file (${PROBE})"
else
    _bad "the refusal does not name the uncommitted file"
fi
if grep -q -- '--full' "${WORK}/head.txt"; then
    _ok "the refusal names --full as the way to ask for the audit"
else
    _bad "the refusal does not mention --full"
fi
if grep -qE '^\[gate-' "${WORK}/head.txt"; then
    _bad "gates ran over a rewritten scope: $(grep -cE '^\[gate-' "${WORK}/head.txt") verdict line(s)"
else
    _ok "no gate ran: nothing was audited by accident"
fi
if grep -q 'FALLING BACK TO A FULL-TREE AUDIT' "${WORK}/head.txt"; then
    _bad "the empty-tree fallback fired outside a push context"
else
    _ok "the empty-tree fallback did not fire outside a push context"
fi

# ===========================================================================
echo
echo "== property 3: the push fallback (#183) is untouched =="
# ===========================================================================
_base_sha="$(cd "${REPO}" && git rev-parse local-base)"
# The runner refuses (exit 97) a HYDRA_GATE_LOG_DIR that does not exist; it
# only mktemps one when the variable is unset.
mkdir -p "${WORK}/log-push" "${WORK}/log-null"
( cd "${REPO}" && GITHUB_EVENT_NAME=push HYDRA_GATE_PUSH_BEFORE="${_base_sha}" \
    HYDRA_GATE_LOG_DIR="${WORK}/log-push" HYDRA_OR_GATE_BLOCK_AFTER_EPOCH=0 \
    bash "${RUNNER}" --scope-to-diff --base at-head . > "${WORK}/push.txt" 2>&1 )
if grep -qxF '[hydra-gates] SCOPE-FILE-COUNT: 1' "${WORK}/push.txt" \
    && grep -q 'github.event.before, push' "${WORK}/push.txt"; then
    _ok "with a push context, a base that is HEAD is re-scoped to the previous tip"
else
    _bad "the push re-scope did not happen: $(grep -E 'SCOPE-FILE-COUNT|Base ref' "${WORK}/push.txt" | head -2 | tr '\n' ' ')"
fi
( cd "${REPO}" && GITHUB_EVENT_NAME=push HYDRA_GATE_PUSH_BEFORE=0000000000000000000000000000000000000000 \
    HYDRA_GATE_LOG_DIR="${WORK}/log-null" HYDRA_OR_GATE_BLOCK_AFTER_EPOCH=0 \
    bash "${RUNNER}" --scope-to-diff --base at-head . > "${WORK}/null.txt" 2>&1 )
_null_count="$(sed -n 's/^\[hydra-gates\] SCOPE-FILE-COUNT: //p' "${WORK}/null.txt" | head -1)"
if grep -q 'FALLING BACK TO A FULL-TREE AUDIT' "${WORK}/null.txt" && [ "${_null_count:-0}" -gt 1 ]; then
    _ok "with a push context whose previous tip is the null sha, the whole tree is audited (${_null_count} files), as #183 designed"
else
    _bad "the #183 fallback no longer fires on a push with an unusable previous tip: count='${_null_count:-}'"
fi

echo
echo "== summary =="
echo "   passed: ${_pass_n}"
echo "   failed: ${_fail_n}"
[ "${_fail_n}" -eq 0 ] || exit 1
[ "${_pass_n}" -gt 0 ] || { echo "FAIL — zero assertions ran; an empty suite is not a green one."; exit 1; }
echo
echo "ALL local-base controls PASSED"
exit 0
