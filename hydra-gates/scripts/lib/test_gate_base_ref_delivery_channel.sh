#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# test_gate_base_ref_delivery_channel.sh — one tree, one base, two channels.
#
# THE PROPERTY
# ------------
#   FOR ONE TREE AND ONE BASE, THE PER-GATE VERDICTS MUST NOT DEPEND ON WHICH
#   CHANNEL DELIVERED THE BASE.
#
# `--base X` and `HYDRA_GATE_BASE_REF=X` are two spellings of ONE input. A gate
# that can tell them apart is reading a second, unprinted source of scope — and
# a scope nobody can name is the defect this whole package is organised around.
#
# WHY IT EXISTS (.github#416)
# ---------------------------
# `#378` made whole-tree the default file scope. It did not reach the event that
# gates a merge. Seven state gates — 19, 25, 26, 51, 52, 54, 55 — were invoked
# through this shape:
#
#     if [ "${SCOPE_TO_DIFF}" = "1" ]; then
#         HYDRA_GATE_BASE_REF="${BASE_REF}" python3 …/check_x.py .
#     else
#         python3 …/check_x.py .          # <-- inherits the AMBIENT variable
#     fi
#
# The `if` guards the EXPLICIT pass — it was written for `#242`, and gate-19's
# copy of the comment explains that defect at length. It cannot guard the
# ENVIRONMENT. The shared quality workflow exports the variable on
# `pull_request` and leaves it empty on `push`, so those seven silently
# diff-scoped themselves on pull requests and swept the tree on pushes, while
# both runs printed `SCOPE-MODE: full` and the same preamble sentence:
#
#     "The DELTA gates (16, 29, 47, 48, 61) judge that change set.
#      Every other gate reads the whole tree."
#
# Measured on a clean docudesk clone, `ConductionNL/.github@5e73e640`, one tree,
# one base (`origin/development`), full scope in both arms:
#
#     channel                     gate-19          gate-25   gate-26   COVERAGE
#     $HYDRA_GATE_BASE_REF        NOT APPLICABLE   NOT APPL. NOT APPL. 56 of 65
#     --base                      FAIL — 396       PASS      FAIL — 6  59 of 65
#
# 402 findings, invisible on every pull request in that repository, surfacing
# only on the push that happens AFTER the merge.
#
# WHY THIS SUITE AND NOT A PER-GATE ASSERTION
# -------------------------------------------
# Because the bug is not in any of the seven gates. Each one is individually
# reasonable; the leak is a property of the process boundary they share. An
# assertion about gate-19 would have to be written seven times and remembered an
# eighth, which is exactly the failure that produced four more instances of the
# defect AFTER gate-19's author documented it. So this suite compares the WHOLE
# verdict set and names whatever differs, including gates that do not exist yet.
#
# WHAT KEEPS IT FROM BEING VACUOUS
# --------------------------------
# Two arms agreeing that nothing is applicable is not parity, it is silence —
# and it is the precise shape the defect wore. So the suite refuses to grade
# until a positive control proves the subject is present and findable, and it
# separately asserts that gate-19 FAILS IN BOTH ARMS naming the fixture's own
# scenario. Agreement alone can never satisfy this file.
#
# Run: bash scripts/lib/test_gate_base_ref_delivery_channel.sh
set -uo pipefail

GF_PKG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../.." && pwd)"
export GF_PKG_ROOT
# shellcheck source=./gate_fixture_support.sh
. "${GF_PKG_ROOT}/scripts/lib/gate_fixture_support.sh"

SRC="${GF_PKG_ROOT}/scripts/test-fixtures/base-ref-channel/app"
RUNNER="${GF_PKG_ROOT}/scripts/run-hydra-gates.sh"
CHECKER="${GF_PKG_ROOT}/scripts/lib/check_e2e_coverage.py"
# The fixture's one uncovered scenario. Deliberately a token that appears
# nowhere else in this package, so a finding about any OTHER subject cannot
# satisfy an assertion below.
#
# Matched case-INSENSITIVELY on purpose: the checker reports the scenario by its
# SLUG (`channel-parity::channelparityuntracedscenario-…`), not by the title in
# the spec. An exact-case match here silently fails and reads as "the positive
# control did not fire" — i.e. as a dead checker — which is the same
# absence-from-a-bad-lookup shape the control exists to rule out.
SUBJECT="ChannelParityUntracedScenario"

_fail_n=0; _pass_n=0
_ok()  { _pass_n=$((_pass_n + 1)); printf 'PASS — %s\n' "$1"; }
_bad() { _fail_n=$((_fail_n + 1)); printf 'FAIL — %s\n' "$1"; }

if [ ! -d "${SRC}" ]; then
    echo "FAIL — base-ref-channel fixture missing at ${SRC}; every assertion below would be vacuous."
    exit 1
fi

WORK="$(mktemp -d "${TMPDIR:-/tmp}/hydra-channel.XXXXXXXX")"
trap 'rm -rf "${WORK}"' EXIT

# Extract every gate's verdict as `<n>|<VERDICT-WORD><count>` — enough to detect
# a scope change (NOT APPLICABLE vs FAIL vs PASS) and a count change, without
# dragging in log paths, which contain a per-run mktemp directory and would make
# every comparison differ for free.
#
# EXTRACT ON THE VERDICT SHAPE, NEVER BY EXCLUDING WHAT LOOKS LIKE A PASS: a
# FAIL line whose remedial prose contains the word "pass" was silently dropped
# by a `grep -v PASS` elsewhere in this programme on 2026-08-12.
#
# ⚠️ WARNING BELONGS IN THIS SET (.github#477, added late).
# When gate-19 was demoted to advisory, WARNING was added to the package's two
# OTHER verdict parsers and not to this one. Nothing went red: a verdict word
# this pattern does not know is simply DROPPED, so gate-19 vanished from both
# channels' sets and the comparison went on matching — over a set that no
# longer contained the gate this whole suite was built to watch. A parser that
# narrows silently is the same defect as two parsers that disagree loudly, and
# only the loud one has ever been caught. This set is asserted identical to the
# other two by ARM P3 of test_gate_discarded_counts_and_empty_deltas.sh.
_verdict_set() {
    printf '%s\n' "$1" \
        | grep -E '^\[gate-[0-9]+\] [a-z0-9-]+: (PASS|FAIL|WARNING|NOT APPLICABLE|SKIPPED)' \
        | sed -E 's/^\[gate-([0-9]+)\] [a-z0-9-]+: (PASS|FAIL — [0-9]+|FAIL|WARNING — [0-9]+|WARNING|NOT APPLICABLE|SKIPPED).*/\1|\2/' \
        | sort -t'|' -k1,1n -u
}

# ---------------------------------------------------------------------------
# Build ONE repository. Both arms read this same tree at this same commit, so
# nothing but the channel can differ.
#
# The diff deliberately touches only docs/CHANGELOG.md: no spec, no controller,
# no page component. That is what makes a diff-scoped gate-19/25/26 decline —
# and therefore what makes the leak visible. A diff that touched the spec would
# put it in scope through either channel and the arms would agree while the bug
# was live.
# ---------------------------------------------------------------------------
gf_build_repo "${WORK}/app" "${SRC}"
gf_commit_all "${WORK}/app" "base: fixture app carrying one uncovered scenario"
gf_mark_base  "${WORK}/app"
printf '\n- unrelated doc tweak\n' >> "${WORK}/app/docs/CHANGELOG.md"
gf_commit_paths "${WORK}/app" "docs: unrelated change" docs/CHANGELOG.md
BASE="$(cd "${WORK}/app" && git rev-parse refs/remotes/origin/development)"

# ===========================================================================
echo "== positive control: the subject IS present and findable in this tree =="
# ===========================================================================
# Without this, agreement between the arms is ambiguous between "the leak is
# fixed" and "this fixture never contained anything to find". Run FIRST, always.
_pc="$(cd "${WORK}/app" && env -u HYDRA_GATE_BASE_REF python3 "${CHECKER}" . 2>&1)"
if printf '%s' "${_pc}" | grep -qiF "${SUBJECT}"; then
    _ok "positive control: check_e2e_coverage.py NAMES ${SUBJECT} on an unscoped read"
else
    echo "FAIL — the positive control did not fire. check_e2e_coverage.py, run with no base"
    echo "       at all, did not name ${SUBJECT} in a tree that contains it. EITHER the"
    echo "       fixture stopped carrying the uncovered scenario (someone added an anchor"
    echo "       or an exclusion to openspec/specs/channel-parity/spec.md) OR the checker"
    echo "       went blind. Both are fatal here: every arm below reads agreement as"
    echo "       meaningful ONLY if this control proves there was something to disagree"
    echo "       about. Refusing to grade."
    printf '%s\n' "${_pc}" | sed 's/^/       /' | head -20
    exit 1
fi

# ===========================================================================
echo
echo "== arm 1 — the base arrives as --base (the push channel) =="
# ===========================================================================
_out_arg="$(env -u HYDRA_GATE_BASE_REF bash "${GF_PKG_ROOT}/bin/hydra-gates" \
    --base "${BASE}" --app-dir "${WORK}/app" 2>&1)"
_set_arg="$(_verdict_set "${_out_arg}")"

# ===========================================================================
echo "== arm 2 — the same base arrives as \$HYDRA_GATE_BASE_REF (the PR channel) =="
# ===========================================================================
_out_env="$(HYDRA_GATE_BASE_REF="${BASE}" bash "${GF_PKG_ROOT}/bin/hydra-gates" \
    --app-dir "${WORK}/app" 2>&1)"
_set_env="$(_verdict_set "${_out_env}")"

# --- both arms must actually be the run we think they are -------------------
# A comparison between two runs that were not the same shape proves nothing, and
# "the rig was misconfigured" and "the gates agree" are indistinguishable
# downstream. So pin the inputs before grading the outputs.
for _arm in arg env; do
    # Indirect expansion rather than `eval`: it assigns `_o` where ShellCheck
    # can see it (an `eval` form trips SC2154, and this repo's wrapper fails on
    # any finding, note severity included).
    _ovar="_out_${_arm}"
    _o="${!_ovar}"
    if printf '%s' "${_o}" | grep -qF 'SCOPE-MODE: full'; then
        _ok "arm ${_arm}: ran at FULL file scope"
    else
        _bad "arm ${_arm}: did NOT report 'SCOPE-MODE: full', so this is not the scope the property is about; the comparison below is uninterpretable"
    fi
    if printf '%s' "${_o}" | grep -qE "^\[hydra-gates\] Delta base: .*$(printf '%s' "${BASE}" | cut -c1-8)"; then
        _ok "arm ${_arm}: resolved the delta base to the commit both arms were given"
    else
        _bad "arm ${_arm}: did not resolve the delta base to ${BASE:0:8}; the two arms are not comparing one base"
    fi
done

# The two arms must have been delivered DIFFERENTLY, or this file is comparing a
# run with itself. Check the printed source LABEL rather than reasoning about
# the value — the label is the only thing that distinguishes the channels, and
# on 2026-08-12 checking the label instead of reasoning about the value is what
# exposed this defect in the first place.
if printf '%s' "${_out_arg}" | grep -qF 'Delta base:' \
    && printf '%s' "${_out_arg}" | grep -F 'Delta base:' | grep -qF -- '(--base)'; then
    _ok "arm arg: the run labels its base source as (--base)"
else
    _bad "arm arg: the run does not label its base source as (--base), so the two arms may have used the SAME channel and the parity assertion below would be vacuous"
fi
if printf '%s' "${_out_env}" | grep -F 'Delta base:' | grep -qF 'HYDRA_GATE_BASE_REF'; then
    _ok "arm env: the run labels its base source as \$HYDRA_GATE_BASE_REF"
else
    _bad "arm env: the run does not label its base source as \$HYDRA_GATE_BASE_REF, so the two arms may have used the SAME channel and the parity assertion below would be vacuous"
fi

# ===========================================================================
echo
echo "== the subject must be REPORTED, in BOTH arms =="
# ===========================================================================
# This is what makes agreement non-vacuous. Two arms that both say NOT
# APPLICABLE agree perfectly and prove nothing — that is the exact state
# `#416` produced. Assert the finding, by name, on each side independently.
for _arm in arg env; do
    # Indirect expansion rather than `eval`: it assigns `_o` where ShellCheck
    # can see it (an `eval` form trips SC2154, and this repo's wrapper fails on
    # any finding, note severity included).
    _ovar="_out_${_arm}"
    _o="${!_ovar}"
    _v="$(gf_verdict "${_o}" 19)"
    # FAIL or WARNING both satisfy this suite: it asserts the gate SAW the
    # uncovered scenario at full file scope, not that the finding blocks.
    # gate-19 became advisory in .github#477 (see _warn in run-hydra-gates.sh).
    case "${_v}" in
        *FAIL*|*WARNING*) _ok "arm ${_arm}: gate-19 reports the finding — ${_v#*: }" ;;
        *"NOT APPLICABLE"*)
            _bad "arm ${_arm}: gate-19 reported NOT APPLICABLE at FULL file scope over a tree whose uncovered scenario the positive control just named. This is .github#416: the base leaked past the scope decision and diff-scoped a state gate. Verdict: ${_v:0:200}"
            ;;
        "") _bad "arm ${_arm}: gate-19 emitted no verdict line at all" ;;
        *)  _bad "arm ${_arm}: gate-19 gave an unrecognised verdict: ${_v:0:200}" ;;
    esac
done

# ===========================================================================
echo
echo "== THE PROPERTY: the verdict sets must be identical =="
# ===========================================================================
# Gate-agnostic and future-proof: a gate added tomorrow that reads the ambient
# variable is caught here without anyone editing this file.
if [ "${_set_arg}" = "${_set_env}" ]; then
    _ok "every gate returned the same verdict through both channels ($(printf '%s\n' "${_set_arg}" | grep -c . ) gate(s) compared)"
else
    _bad "THE DELIVERY CHANNEL CHANGED THE VERDICT. One tree, one base, full scope in both arms — the gates below answered differently depending on whether the base arrived as --base or in the environment. That is a second, unprinted source of scope (.github#416)."
    # The column header names the variable WITHOUT a leading `$`. With one, every
    # spelling ShellCheck accepts is either SC2016 or an actual expansion, and
    # this repo's wrapper fails the build on findings of any severity — so the
    # sigil would cost a suppression directive to buy nothing a reader needs.
    printf '   gate | --base            | env HYDRA_GATE_BASE_REF\n'
    printf '   -----+-------------------+---------------------\n'
    # Join on the gate number so the reader gets the PAIR, not two lists.
    #
    # ⚠️ `join` and `comm` both require their inputs in the collating order they
    # compare with, and `_verdict_set` sorts NUMERICALLY so the table reads 1, 2,
    # …, 10 rather than 1, 10, 2. Feeding that straight in makes `join` skip
    # pairs SILENTLY — it would drop differing gates out of the very message that
    # is supposed to name them, which is worse than no diagnostic at all. So both
    # are re-sorted lexically here, and only here; the equality test above is
    # order-insensitive as long as both sides use one order, which they do.
    join -t'|' -j1 \
        <(printf '%s\n' "${_set_arg}" | LC_ALL=C sort -t'|' -k1,1) \
        <(printf '%s\n' "${_set_env}" | LC_ALL=C sort -t'|' -k1,1) 2>/dev/null \
        | LC_ALL=C sort -t'|' -k1,1n \
        | awk -F'|' '$2 != $3 { printf "   %4s | %-17s | %s\n", $1, $2, $3 }'
    # A gate present in one arm and absent from the other never reaches `join`,
    # and vanishing entirely is a WORSE symptom than answering differently.
    comm -3 \
        <(printf '%s\n' "${_set_arg}" | cut -d'|' -f1 | LC_ALL=C sort) \
        <(printf '%s\n' "${_set_env}" | cut -d'|' -f1 | LC_ALL=C sort) \
        | tr -d '\t' | sed 's/^/   only one arm emitted a verdict for gate-/'
fi

# ===========================================================================
echo
echo "== the environment variable is still an ACCEPTED INPUT to the runner =="
# ===========================================================================
# The fix must not be "stop reading it". Direct callers — the builder skill, a
# human at a shell, scripts/lib/test_check_schema_property_meta.py — set the
# variable and invoke the RUNNER, with no `bin/hydra-gates` in between. If that
# path stopped honouring it, the delta gates would go NOT APPLICABLE fleet-wide
# and this suite's parity assertion above would still pass, because both arms
# would be equally deaf.
_out_direct="$(HYDRA_GATE_BASE_REF="${BASE}" bash "${RUNNER}" --full "${WORK}/app" 2>&1)"
if printf '%s' "${_out_direct}" | grep -qE '^\[hydra-gates\] Delta base: .* — [0-9]+ changed file\(s\)'; then
    _ok "the runner, invoked directly, still resolves a delta base from \$HYDRA_GATE_BASE_REF"
else
    _bad "the runner invoked directly with \$HYDRA_GATE_BASE_REF set did NOT resolve a delta base. The variable was removed as an INPUT rather than as an ambient inheritance, which silently retires gates 16/29/47/48/61 for every direct caller. Preamble: $(printf '%s' "${_out_direct}" | grep -F 'Delta base:' | head -1)"
fi
# And the delta gates must actually have used it.
_v16="$(gf_verdict "${_out_direct}" 16)"
case "${_v16}" in
    *"NOT APPLICABLE"*|"")
        _bad "gate-16 reported '${_v16:0:120}' on a direct runner call that was given a base in the environment — the delta gates are not receiving it"
        ;;
    *) _ok "gate-16 has a real verdict on the direct-runner call — the env channel still feeds the delta gates" ;;
esac

echo
echo "== summary =="
echo "   passed: ${_pass_n}"
echo "   failed: ${_fail_n}"
[ "${_fail_n}" -eq 0 ] || exit 1
[ "${_pass_n}" -gt 0 ] || { echo "FAIL — zero assertions ran; an empty suite is not a green one."; exit 1; }
echo
echo "ALL base-ref delivery-channel controls PASSED"
exit 0
