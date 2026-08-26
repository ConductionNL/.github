#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# test_gate_empty_scope_never_passes.sh — a gate must never report PASS over a
# scope it did not open.
#
# WHAT THIS GUARDS (.github#242, #240)
# ------------------------------------
# Gates 19 (e2e-coverage), 25 (contract-coverage), 62 (store-plane) and
# 63 (settings-surface) diff-scoped themselves INSIDE their own helpers, below
# the runner's base resolution, and did it UNCONDITIONALLY — the base ref was
# defaulted even when the caller had asked for no scoping at all.
#
# Two consequences, and the second is why it stayed hidden:
#
#   1. A full-tree run was silently narrowed to a diff against
#      origin/development, which on a mainline checkout is empty.
#   2. The verdict for "I inspected nothing" was PASS, not a skip. So
#      --require-full-coverage — the one assertion built to catch gates that did
#      not run — had nothing to catch. gate-63 was the clearest case: its log
#      said "gate skipped" on the line above a verdict that said PASS.
#
# Measured on openconnector 2026-08-08:
#   gate-19   5 findings as the runner invoked it   ->  412 over the full tree
#   gate-25   PASS as the runner invoked it         ->   32 over the full tree
#
# AND WHAT #268 CORRECTED
# -----------------------
# #258 filed the empty-scope case as `structural`, which COUNTS AGAINST
# --require-full-coverage. So any PR that happened to touch no spec and no
# manifest exited 98 for a gate that had nothing to judge — measured as 4 runs
# across 3 repos (doriath x2, larpingapp, softwarecatalog) blocked on nothing.
#
# The category was the bug, not the skip. The runner's own definitions:
#
#   na          subject matter absent from this repo OR THIS DIFF. Nothing in
#               the repository is missing and no change the author could make
#               would put a spec file into a diff that does not touch one.
#   structural  the subject matter EXISTS and nothing produced the gate's
#               input — a gap the repo CAN close (the axe-report case).
#
# An empty ADR-020 diff scope is the first. Gates 4/6/7/28 already called the
# identical situation `na`. What #258 bought survives the reclassification
# because it lives in the RENDERING, not the accounting: the verdict is
# `NOT APPLICABLE`, which is not `PASS`.
#
# FOUR ARMS, and all four are needed:
#
#   ARM 1  a planted TRUE POSITIVE is still caught in full-tree mode.
#          Widening a checker until it catches nothing is not a fix, so this
#          arm runs FIRST and everything else is meaningless without it.
#   ARM 2  an empty scope is VISIBLE and is never PASS (#242/#240), and it does
#          NOT fail --require-full-coverage (#268).
#   ARM 3  a genuinely non-empty scope with nothing wrong still PASSes, so the
#          fix has not simply turned every gate into a permanent skip.
#   ARM 4  ANTI-WIDENING. A genuinely `structural` gap — the same tree, the
#          same flags, plus --axe-enabled and no axe report — must STILL exit
#          98. Without this arm, ARM 2 could be satisfied by neutering
#          --require-full-coverage altogether, and `na` would become the hole
#          that the whole coverage accounting exists to prevent.

set -u

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_scripts="$(cd "${_here}/.." && pwd)"
_runner="${HYDRA_GATES_RUNNER_UNDER_TEST:-${_scripts}/run-hydra-gates.sh}"

_failures=0
_ok()  { echo "  ok   — $1"; }
_bad() { echo "  FAIL — $1"; _failures=$((_failures + 1)); }

echo "test_gate_empty_scope_never_passes.sh"

_tmp="$(mktemp -d "${TMPDIR:-/tmp}/hydra-emptyscope.XXXXXX")"
trap 'rm -rf "${_tmp}"' EXIT

# ---------------------------------------------------------------------------
# A fixture that carries ONE genuine finding for gate-19 and ONE for gate-25:
# a declared scenario with no @e2e tag, and a routed #[PublicPage] method with
# no Newman/PHPUnit contract test and no @contract exclude.
# ---------------------------------------------------------------------------
_app="${_tmp}/app"
mkdir -p "${_app}/src" "${_app}/openspec/specs/thing" "${_app}/appinfo" \
         "${_app}/lib/Controller"
printf '{"name":"fx","menu":[]}\n' > "${_app}/src/manifest.json"
printf '## Purpose\n\n#### Scenario: a thing happens\n- WHEN x\n- THEN y\n' \
    > "${_app}/openspec/specs/thing/spec.md"
printf "<?php\nreturn ['routes'=>[['name'=>'thing#index','url'=>'/api/thing','verb'=>'GET']]];\n" \
    > "${_app}/appinfo/routes.php"
cat > "${_app}/lib/Controller/ThingController.php" <<'PHP'
<?php
namespace OCA\Fx\Controller;
class ThingController {
    // The AnonRateLimit is here so this fixture carries ONLY the two findings
    // it was built to carry (gate-19 and gate-25). Without it, gate-82 fires a
    // genuine ADR-082 finding on the #[PublicPage] below and the run exits 1,
    // which is a real defect in the fixture rather than in the gate — the
    // method IS a public endpoint with no volume ceiling. gate-25 still fires,
    // because it judges the absence of a contract test, not the throttle.
    #[PublicPage]
    #[AnonRateLimit(limit: 120, period: 60)]
    public function index() { return 1; }
}
PHP
(
    cd "${_app}" || exit 1
    git init -q .
    git add -A
    git -c user.email=t@t -c user.name=t commit -qm init
    # A docs-only second commit. This is the ordinary shape of a PR that
    # touches no spec, no manifest and no controller — the EMPTY SCOPE case.
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

# NOTE the `( [A-Z]+)*`: the verdict word is not always one token. "NOT
# APPLICABLE" parsed as "NOT" under the original single-token pattern, so every
# arm comparing against a two-word verdict failed on the string rather than on
# the behaviour it meant to test.
_verdict() { grep -oE "^\[gate-$2\] [^:]+: [A-Z]+( [A-Z]+)*( \([a-z]+\))?" "$1" | head -1 | sed 's/^[^:]*: //'; }

# ---------------------------------------------------------------------------
# ARM 1 — the planted true positives are still caught, full-tree.
#
# ⚠️ WHAT THIS ARM ASSERTS, AND WHAT IT DELIBERATELY DOES NOT (.github#477)
# ------------------------------------------------------------------------
# This arm is the POSITIVE CONTROL for the fixture, not a statement about
# blocking policy. Everything below it — "an empty scope is NOT APPLICABLE" —
# proves nothing unless the gate demonstrably SEES the planted defect when the
# scope is open. So what has to hold is: the gate opened the scope, computed a
# real finding, and named a count.
#
# `.github#477` demoted gate-19 (e2e-coverage) from `_fail` to `_warn`: it
# still runs, still counts and still names every unannotated scenario, but the
# finding no longer stops a merge. That moved gate-19's verdict word from FAIL
# to WARNING and this arm — which matched the word rather than the property —
# went red on `.github@main` from 13:15 on 2026-08-16, alongside ARM P3 of
# test_gate_discarded_counts_and_empty_deltas.sh. Three sibling suites were
# taught the new word in the same commit (exit-code-semantics,
# base-ref-delivery-channel, the acceptance matrix + its expect.conf); these
# two were not, because they were not run. That is the hand-maintained-list
# decay this package's own runner exists to prevent — see
# tests/run-helper-suites.sh.
#
# So gate-19 is accepted at FAIL *or* WARNING, and NOT on the word alone: the
# verdict line must also carry a non-zero finding count, because a demotion's
# real failure mode is the finding quietly ceasing to be read. gate-25 is NOT
# demoted and keeps the strict FAIL — accepting WARNING for a gate nobody
# demoted would be exactly the invisible pass this file guards.
#
# Note what this arm still catches for gate-19 without the word FAIL: a gate
# that went blind prints PASS, and a gate that self-scoped to nothing prints
# NOT APPLICABLE. Neither is accepted here, and ARM 2 separately requires
# NOT APPLICABLE over the empty scope, so the two arms remain distinguishable.
#
# Which gates may be advisory at all is bounded by name — see ARM P4 of
# test_gate_discarded_counts_and_empty_deltas.sh, so a second demotion cannot
# land without reddening this package.
# ---------------------------------------------------------------------------
_full="${_tmp}/full.txt"
_run "${_full}"

# gate-25 — NOT demoted. Strict FAIL.
if grep -qE "^\[gate-25\][^:]*: FAIL" "${_full}"; then
    _ok "gate-25 still catches its planted true positive over the full tree"
else
    _bad "gate-25 did NOT catch its planted true positive — got: $(_verdict "${_full}" 25)"
fi

# gate-19 — advisory since .github#477. FAIL or WARNING, and it must NAME a count.
_g19_line="$(grep -E "^\[gate-19\][^:]*: (FAIL|WARNING)\b" "${_full}" | head -1)"
if [ -n "${_g19_line}" ]; then
    if printf '%s' "${_g19_line}" | grep -qE '[1-9][0-9]* scenario'; then
        _ok "gate-19 still catches its planted true positive over the full tree, and names the count — ${_g19_line#*: }"
    else
        _bad "gate-19 reached a FAIL/WARNING verdict but named no non-zero scenario count — a demotion whose finding stops being legible is the invisible pass. Got: ${_g19_line}"
    fi
else
    _bad "gate-19 did NOT catch its planted true positive — got: $(_verdict "${_full}" 19)"
fi

# …and the SUMMARY must say so. A demotion is only safe while the reader is
# told that a green verdict means "nothing BLOCKING failed", not "nothing was
# found". Without this, `_warn` degrades into a silent soft-fail.
if grep -qF 'reported ADVISORY findings' "${_full}" \
    && grep -qF "means 'nothing BLOCKING failed'" "${_full}"; then
    _ok "the run's summary announces the advisory findings and says green != 'nothing was found'"
else
    _bad "a gate reported an advisory finding and the summary did not say so — a demoted gate whose finding is not announced is a soft-fail nobody reads"
fi

# Full-tree must actually OPEN the manifests rather than diff-scope itself to
# nothing: 62/63 are clean in this fixture, so they must PASS, not SKIP.
for _g in 62 63; do
    _v="$(_verdict "${_full}" "${_g}")"
    if [ "${_v}" = "PASS" ]; then
        _ok "gate-${_g} audited the manifest over the full tree (PASS, not a self-inflicted skip)"
    else
        _bad "gate-${_g} full-tree verdict is '${_v}' — expected PASS over a clean manifest"
    fi
done

# ---------------------------------------------------------------------------
# ARM 2 — an empty scope is VISIBLE and never PASS (#242/#240), and it does not
#         fail --require-full-coverage (#268).
# ---------------------------------------------------------------------------
_scoped="${_tmp}/scoped.txt"
_run "${_scoped}" --scope-to-diff --base HEAD~1 --require-full-coverage
_scoped_rc=$?

for _g in 19 25 62 63; do
    _v="$(_verdict "${_scoped}" "${_g}")"
    case "${_v}" in
        "NOT APPLICABLE")
            _ok "gate-${_g} reports NOT APPLICABLE over an empty diff scope"
            ;;
        PASS)
            _bad "gate-${_g} reported PASS over a scope it never opened — this is the #242 defect"
            ;;
        "SKIPPED (structural)"|"SKIPPED (wiring)")
            _bad "gate-${_g} reported '${_v}' over an empty diff scope — this is the #268 regression: an empty ADR-020 scope counts against coverage and exits 98"
            ;;
        *)
            _bad "gate-${_g} empty-scope verdict is '${_v}' — expected NOT APPLICABLE"
            ;;
    esac
done

# The exit code is the whole point of #268: this run has no findings and no
# real coverage gap, so --require-full-coverage must let it through.
if [ "${_scoped_rc}" -eq 98 ]; then
    _bad "--require-full-coverage exited 98 over an empty diff scope — the #268 regression: a PR that touches no spec and no manifest is blocked for a gate that had nothing to judge"
elif [ "${_scoped_rc}" -eq 0 ]; then
    _ok "--require-full-coverage let an empty diff scope through (exit 0)"
else
    _bad "empty-scope run exited ${_scoped_rc}, expected 0 — unexpected verdict"
fi

# ...and it must not be counted as a coverage gap in the summary either. The
# exit code alone would still pass if the four were listed as DID NOT RUN while
# some other gate happened to hold the run open.
if grep -q 'GATES THAT DID NOT RUN' "${_scoped}"; then
    _bad "the empty-scope run reported a coverage gap — expected none; DID-NOT-RUN list: $(sed -n '/GATES THAT DID NOT RUN/,$p' "${_scoped}" | grep -oE 'gate-[0-9]+' | tr '\n' ' ')"
else
    _ok "the empty-scope run reports NO coverage gap at all"
fi

# The declaration must carry a REASON naming the diff-scoping rule. A bare
# "NOT APPLICABLE" is how a gate disappears quietly, which is the failure this
# whole accounting exists to stop.
for _g in 19 25 62 63; do
    if grep -qE "^\[gate-${_g}\][^:]*: NOT APPLICABLE — .+ADR-020" "${_scoped}"; then
        _ok "gate-${_g} states WHY it was not applicable, and names ADR-020"
    else
        _bad "gate-${_g}'s NOT APPLICABLE line has no reason naming ADR-020 diff scoping"
    fi
done

# ---------------------------------------------------------------------------
# ARM 4 — ANTI-WIDENING. `na` must not have become a hole.
#
# ARM 2 asserts that --require-full-coverage does NOT fire over an empty diff
# scope. On its own that assertion is satisfiable by breaking
# --require-full-coverage outright, which would re-open .github#169 — the
# accounting hole this whole mechanism was built to close.
#
# So: THE SAME TREE AND THE SAME FLAGS AS ARM 2, plus --axe-enabled and no
# tests/axe/report.json. That is a GENUINELY structural gap — the input was
# expected, the repo could produce it, and it did not arrive — and it must
# still exit 98.
#
# It has to be this tree specifically. `_FAILED` is evaluated BEFORE the
# coverage branch, so any gate with a real finding pre-empts exit 98 and the
# arm would measure nothing. (Measured while writing this: run it after ARM 3's
# manifest commit and gates 22/53 fail on an unresolvable ajv, the run exits 2,
# and the assertion reads as a widening regression that is not there.)
# ---------------------------------------------------------------------------
_axe="${_tmp}/axe.txt"
_run "${_axe}" --scope-to-diff --base HEAD~1 --require-full-coverage --axe-enabled
_axe_rc=$?

if grep -qE "^\[gate-33\][^:]*: SKIPPED \(structural\)" "${_axe}"; then
    _ok "a genuinely structural gap is still categorised structural (gate-33, axe report expected and absent)"
else
    _bad "gate-33 did not report a structural skip with --axe-enabled and no report — got: $(_verdict "${_axe}" 33)"
fi

if [ "${_axe_rc}" -eq 98 ]; then
    _ok "--require-full-coverage STILL fails a genuinely structural gap (exit 98) — \`na\` did not become a hole"
else
    _bad "--require-full-coverage exited ${_axe_rc} over a real structural gap, expected 98 — the #268 fix has widened into .github#169"
fi

# ---------------------------------------------------------------------------
# ARM 3 — a NON-empty scope with nothing wrong still passes.
#
# Without this arm, "make every empty scope a skip" could be satisfied by
# skipping unconditionally, and the suite would look fixed while checking
# nothing. The second commit here touches the manifest, so 62/63 have real work.
# ---------------------------------------------------------------------------
(
    cd "${_app}" || exit 1
    printf '{"name":"fx","menu":[],"version":"1.0.1"}\n' > src/manifest.json
    git add src/manifest.json
    git -c user.email=t@t -c user.name=t commit -qm "chore: bump manifest"
) >/dev/null 2>&1

_touched="${_tmp}/touched.txt"
_run "${_touched}" --scope-to-diff --base HEAD~1
for _g in 62 63; do
    _v="$(_verdict "${_touched}" "${_g}")"
    if [ "${_v}" = "PASS" ]; then
        _ok "gate-${_g} PASSes when the diff genuinely contains a clean manifest"
    else
        _bad "gate-${_g} returned '${_v}' for a real, clean, in-scope manifest — the gate has been skipped into uselessness"
    fi
done

# ---------------------------------------------------------------------------
# ARM 5 — THE INVERSE INVARIANT. A gate must not report "nothing to judge"
#         when its subject matter IS sitting in the diff.
#
# ARM 3 proves a clean in-scope manifest still PASSes. That is necessary but
# not sufficient: a gate that had been neutered to always-`na` would fail ARM 3
# loudly, but a gate that merely stopped ENFORCING would sail through it. So
# plant a REAL ADR-079 violation in the manifest the diff touches — a
# type:settings page claiming the reserved platform name — and require a FAIL.
#
# Together with ARM 2 this pins both directions:
#   subject absent from the diff  -> na, does not fail the run
#   subject present in the diff   -> a real verdict, and violations still FAIL
# ---------------------------------------------------------------------------
(
    cd "${_app}" || exit 1
    printf '{"name":"fx","menu":[],"pages":[{"id":"settings","type":"settings","title":"Settings"}]}\n' \
        > src/manifest.json
    git add src/manifest.json
    git -c user.email=t@t -c user.name=t commit -qm "feat: a settings page claiming the reserved name"
) >/dev/null 2>&1

_violation="${_tmp}/violation.txt"
_run "${_violation}" --scope-to-diff --base HEAD~1 --require-full-coverage
_violation_rc=$?

_v="$(_verdict "${_violation}" 63)"
case "${_v}" in
    FAIL)
        _ok "gate-63 FAILs a real ADR-079 violation sitting in the diff — the subject was judged, not declared away"
        ;;
    "NOT APPLICABLE")
        _bad "gate-63 declared NOT APPLICABLE over a manifest THE DIFF TOUCHED and which carries a real ADR-079 violation — \`na\` is swallowing a present subject"
        ;;
    *)
        _bad "gate-63 returned '${_v}' for a planted ADR-079 violation in an in-scope manifest — expected FAIL"
        ;;
esac

if [ "${_violation_rc}" -ne 0 ] && [ "${_violation_rc}" -ne 98 ]; then
    _ok "the run exits non-zero on the planted violation (exit ${_violation_rc} = finding count, not a coverage verdict)"
else
    _bad "the run exited ${_violation_rc} with a planted ADR-079 violation in scope — a finding must fail the run on its own merits"
fi

# ---------------------------------------------------------------------------
# GATES 12 AND 13: `src/` EXISTS, AND HOLDS NOT ONE .vue (.github#274, #271)
#
# The same defect one layer down from #272. Those four a11y gates declared
# themselves NOT APPLICABLE on a templates-only repo; gates 12 and 13 did the
# opposite on an nldesign-shaped one — `[ -d src ]` passed, `find src -name
# '*.vue'` matched nothing, the findings log was empty, and both printed PASS.
#
# MEASURED at package sha fef032b (origin/main, post-#272) against a repo whose
# `src/` holds a single `manifest.json` and whose `templates/` holds real
# markup:
#
#     [gate-12] nc-input-labels: PASS
#     [gate-13] modal-isolation: PASS
#
# That is nldesign's exact shape — the shape that let twelve gates certify it in
# #225 — and it is not one `rm` away, it is current. `na` is the honest verdict:
# NcSelect / NcModal / NcDialog are Vue SFC components, a PHP template cannot
# instantiate one, so nothing in such a repo is unverified. But PASS says the
# gate looked and found nothing, and it did not look.
# ---------------------------------------------------------------------------
_novue="${_tmp}/novue"
mkdir -p "${_novue}/src" "${_novue}/templates"
printf '{"name":"nl","pages":[]}\n' > "${_novue}/src/manifest.json"
printf '<div><select name="x"></select></div>\n' > "${_novue}/templates/admin.php"
(
    cd "${_novue}" || exit 1
    git init -q .
    git add -A
    git -c user.email=t@t -c user.name=t commit -qm init
) >/dev/null 2>&1

_novue_out="${_tmp}/novue.txt"
_novue_logs="${_tmp}/novue-logs"
mkdir -p "${_novue_logs}"
(
    cd "${_novue}" || exit 1
    HYDRA_GATE_LOG_DIR="${_novue_logs}" bash "${_runner}" . > "${_novue_out}" 2>&1
)
for _g in 12 13; do
    _v="$(_verdict "${_novue_out}" "${_g}")"
    case "${_v}" in
        "NOT APPLICABLE")
            _ok "gate-${_g}: NOT APPLICABLE when src/ holds no .vue — it says it looked at nothing"
            ;;
        PASS)
            _bad "gate-${_g}: PASS over a src/ containing zero .vue files — the nldesign shape, green over nothing (#225/#274)"
            ;;
        *)
            _bad "gate-${_g}: returned '${_v:-none emitted}' on a src/ with no .vue — expected NOT APPLICABLE"
            ;;
    esac
done
# The reason must say WHY it cannot apply, not merely that it does not. The old
# shared reason claimed these gates inspect ".vue/.js/.ts source", which is
# false — they are .vue-only, and that is the judgement #274 asked to be made
# explicit.
if grep -qE '^\[gate-12\][^:]*: NOT APPLICABLE — .*(Vue SFC|no \.vue)' "${_novue_out}"; then
    _ok "gate-12's na reason states the .vue-only judgement rather than a generic 'no frontend'"
else
    _bad "gate-12's na reason does not state why a template repo cannot contain its subject"
fi

# THE ANTI-WIDENING CONTROL. Add ONE .vue carrying the defect and both gates
# must go back to judging — this is not "skip whenever src/ looks thin".
mkdir -p "${_novue}/src/views"
cat > "${_novue}/src/views/Probe.vue" <<'VUE'
<template>
  <div>
    <NcSelect v-model="v" :options="o" :reduce="(option) => option.value" />
    <NcModal v-if="open" @close="open = false"><p>inline</p></NcModal>
  </div>
</template>
VUE
(
    cd "${_novue}" || exit 1
    git add -A
    git -c user.email=t@t -c user.name=t commit -qm probe
) >/dev/null 2>&1
_novue_out2="${_tmp}/novue2.txt"
_novue_logs2="${_tmp}/novue-logs2"
mkdir -p "${_novue_logs2}"
(
    cd "${_novue}" || exit 1
    HYDRA_GATE_LOG_DIR="${_novue_logs2}" bash "${_runner}" . > "${_novue_out2}" 2>&1
)
for _g in 12 13; do
    _v="$(_verdict "${_novue_out2}" "${_g}")"
    if [ "${_v}" = "FAIL" ]; then
        _ok "control: gate-${_g} FAILS on the planted defect once ONE .vue exists — the na is about absence, not about skipping"
    else
        _bad "control FAILED: gate-${_g} returned '${_v:-none}' with a planted unnamed NcSelect / inline NcModal in src/views/Probe.vue"
    fi
done

echo
# ===========================================================================
# ARM 6 — THE PROPERTY, ACROSS THE WHOLE PACKAGE, NOT SEVEN GATES BY NAME
# ===========================================================================
#
# Everything above names its gates. That is how this suite covered 12, 13, 19,
# 25, 33, 62 and 63 — SEVEN of 64 — while gates 14, 17, 18, 20, 21, 22, 34-44
# and 52 carried the identical defect for months (.github#374). A property
# enforced gate-by-gate is enforced by whoever remembered to add a line.
#
# So this arm asserts the property ITSELF, gate-agnostically:
#
#   OVER A TREE THAT CARRIES REAL, PLANTED DEFECTS, NO GATE MAY REPORT `PASS`
#   ON A RUN WHOSE SCOPE EXCLUDES EVERY ONE OF THEM.
#
# The fixture is the shape #374 was measured on: a tree with a planted defect
# for a broad slice of the package, and a docs-only second commit. Any gate
# that says PASS there said it having opened nothing.
#
# ⚠️ THE ALLOWLIST IS THE LOAD-BEARING PART, AND IT MAY ONLY SHRINK.
# A gate on it is one whose PASS over this diff is HONEST — it computed a real
# answer about a real change set. Adding a gate to it to make this arm green is
# how the defect comes back, so each entry states what it computed.
echo
echo "-- ARM 6: the property, across the package --"

_wide="${_tmp}/wide"
mkdir -p "${_wide}/lib/Controller" "${_wide}/lib/Settings" "${_wide}/appinfo" \
         "${_wide}/src/views" "${_wide}/templates"
cat > "${_wide}/lib/Controller/ThingController.php" <<'PHP'
<?php
namespace OCA\Fx\Controller;
class ThingController {
    public function index(): JSONResponse
    {
        return new JSONResponse($this->objectService->findAll([]));
    }
    public function orphan(): JSONResponse
    {
        return new JSONResponse($this->objectService->findObjects([]));
    }
}
PHP
printf '<?php\nreturn [];\n' > "${_wide}/appinfo/routes.php"
printf '{"schemas":[{"slug":"thing","notifications":{"onCreate":{"subject":"x"}}}]}\n' \
    > "${_wide}/lib/Settings/register.json"
printf '<<<<<<< HEAD\nconst a = 1;\n=======\nconst a = 2;\n>>>>>>> other\n' \
    > "${_wide}/src/conflicted.js"
cat > "${_wide}/src/views/Probe.vue" <<'VUE'
<template>
  <div>
    <p @click="go">clicky</p>
    <img src="/avatar.png" alt="" />
    <span tabindex="3">tabbed</span>
    <div aria-hidden="true"><button>hidden but focusable</button></div>
    <input type="text" name="email" />
    <a href="/x">click here</a>
    <table><tr><th>Name</th></tr></table>
  </div>
</template>
<script>
export default { methods: { go() { if (window.confirm('sure?')) { return true } } } }
</script>
VUE
printf '<html>\n<body><p>hi</p></body>\n</html>\n' > "${_wide}/templates/admin.php"
printf '{"name":"fx","menu":[],"pages":[]}\n' > "${_wide}/src/manifest.json"
(
    cd "${_wide}" || exit 1
    git init -q .
    git add -A
    git -c user.email=t@t -c user.name=t commit -qm "the planted tree"
    printf 'docs only\n' > README.md
    git add README.md
    git -c user.email=t@t -c user.name=t commit -qm docs
) >/dev/null 2>&1

_wide_full="${_tmp}/wide-full.txt"
_wide_logs="${_tmp}/wide-logs"; mkdir -p "${_wide_logs}"
(
    cd "${_wide}" || exit 1
    HYDRA_GATE_LOG_DIR="${_wide_logs}" bash "${_runner}" . > "${_wide_full}" 2>&1
)
_wide_diff="${_tmp}/wide-diff.txt"
_wide_logs2="${_tmp}/wide-logs2"; mkdir -p "${_wide_logs2}"
(
    cd "${_wide}" || exit 1
    HYDRA_GATE_LOG_DIR="${_wide_logs2}" bash "${_runner}" --scope-to-diff --base HEAD~1 . \
        > "${_wide_diff}" 2>&1
)

# THE POSITIVE CONTROL RUNS FIRST AND EVERYTHING ELSE IS MEANINGLESS WITHOUT
# IT. If the full run finds nothing, the fixture is broken and "no gate passed
# over the empty scope" would be satisfied by a runner that gates nothing.
_wide_fails=$(grep -cE '^\[gate-[0-9]+\][^:]*: FAIL' "${_wide_full}" || true)
_wide_fails="${_wide_fails:-0}"
if [ "${_wide_fails}" -ge 8 ]; then
    _ok "positive control: the planted tree FAILS ${_wide_fails} gate(s) at full scope"
else
    _bad "positive control BROKEN: the planted tree fails only ${_wide_fails} gate(s) at full scope — the fixture no longer plants what this arm assumes, so every assertion below proves nothing"
fi

# Gates whose PASS over THIS diff is a real answer to a real question.
# Each computed something; none of them is passing over an unopened scope.
#   4  composer-audit  — no composer file in this tree at all; it declines by
#                        subject matter, not by scope (it reports na, listed
#                        here only so a future change of that verdict is not
#                        silently swallowed)
#   15 dashboard-antipattern — its helper reads the WHOLE tree and the diff
#                        filter is applied to its FINDINGS, so it did open the
#                        manifest and the .vue tree. See the note below.
#   16 spec-coverage   — a DELTA gate with a real base: it diffed HEAD~1..HEAD
#                        and found no changed method. That is a computed zero.
#   23 or-abstraction-anti-patterns — never diff-scoped; it lints all of lib/.
#   47 security-change-has-tests — DELTA, real base: it classified the docs-only
#                        hunks and found no security change. Computed.
#   48 csrf-cochange   — DELTA, real base: it looked for a removed attribute in
#                        the diff and found none. Computed.
#   68 duplicate-index-pages — never diff-scoped, same posture as gate-23: it
#                        always assembles the WHOLE effective manifest (base +
#                        manifest.d/* fragments) and groups every type:"index"
#                        page by (register, schema), regardless of which files
#                        the diff touched — that is this gate's OWN spec
#                        requirement ("Gate scope — computed app-wide, not
#                        file-diff-scoped"). This fixture's manifest is
#                        {"pages":[]} — zero pages of any type — so there is
#                        no type:"index" page anywhere in the tree for it to
#                        group, at either scope. MEASURED, not assumed:
#                        `hydra-gate-duplicate-index-pages.log` reads
#                        `findings=0` byte-for-byte identically at full scope
#                        and at --scope-to-diff --base HEAD~1; the ONLY line
#                        that differs between the two runs is the
#                        informational "ratchet computed against BASE_REF"
#                        note, not the verdict. A computed, honest,
#                        whole-tree zero, not a scope artifact.
#                        SEPARATELY: gate-68 is a RATCHET (design.md Decision
#                        3) — with no resolvable base (the plain `_wide_full`
#                        run above passes none) it can only ever report WARN
#                        or PASS, by design, never FAIL; a planted duplicate
#                        here would show WARNING (which this arm does not
#                        flag — only literal PASS), never FAIL, so "FAIL the
#                        planted tree at full scope" is not a reachable
#                        verdict for this gate absent a base showing growth,
#                        which this fixture's docs-only second commit does
#                        not supply for ANY gate.
#   96 system-elevation-reachability — never diff-scoped, same posture as
#                        gate-23 and gate-68, and for a reason its own spec
#                        states: it establishes that a BOUNDARY holds, and a
#                        boundary cannot be established from a diff. A
#                        diff-scoped version reports nothing on the ~99% of PRs
#                        that never open a node or a controller.
#                        MEASURED, not assumed: `check_system_elevation.py`
#                        reads NO scope input at all — no BASE_REF, no diff, no
#                        file list — it walks lib/ itself. On this fixture it
#                        prints `checked 1 PHP file(s) under lib/ [full tree]:
#                        0 elevate, 0 failure(s)` byte-for-byte identically at
#                        full scope and at --scope-to-diff --base HEAD~1,
#                        because there is no code path by which the scope could
#                        reach it. The fixture's ThingController calls
#                        `findAll()`, which is what gates 14/17/21 plant it for;
#                        it does not elevate, so a whole-tree read of it is an
#                        honest zero rather than a scope artifact.
#                        SEPARATELY: "FAIL the planted tree at full scope" is
#                        not a reachable verdict for this gate on THIS fixture —
#                        nothing in it elevates at all — so it is deliberately
#                        absent from the anti-widening list below. Its
#                        equivalent lives in gate-acceptance/system-elevation,
#                        whose planted arm FAILS and whose clean arm PASSES on
#                        a tree built for it.
_ARM6_ALLOWED=" 4 15 16 23 47 48 68 96 "

_wide_bad=""
while IFS= read -r _g; do
    [ -z "${_g}" ] && continue
    case "${_ARM6_ALLOWED}" in
        *" ${_g} "*) continue ;;
    esac
    _wide_bad="${_wide_bad}${_g} "
done < <(grep -E '^\[gate-[0-9]+\][^:]*: PASS' "${_wide_diff}" \
    | grep -oE '^\[gate-[0-9]+\]' | grep -oE '[0-9]+' | sort -un)

if [ -z "${_wide_bad}" ]; then
    _ok "no gate reports PASS over a diff that excludes every planted defect (the .github#374 property, package-wide)"
else
    _bad "gate(s) ${_wide_bad}reported PASS over a scope that excludes every planted defect — this is the .github#374 defect. Each of them printed the same word as a gate that read the whole tree and found it clean. Fix the gate's fall-through (see _skip_empty_scope in run-hydra-gates.sh); do NOT add it to _ARM6_ALLOWED unless you can state what it computed."
fi

# ANTI-WIDENING. ARM 6 is satisfiable by making every gate skip always, so the
# same tree at FULL scope must still produce those findings — asserted by name,
# so "the gate went quiet" cannot pass as "the gate went green".
_wide_missing=""
for _g in 14 17 21 22 34 35 36 38 40 41 42 43 44; do
    grep -qE "^\[gate-${_g}\][^:]*: FAIL" "${_wide_full}" || _wide_missing="${_wide_missing}${_g} "
done
if [ -z "${_wide_missing}" ]; then
    _ok "anti-widening: every one of those gates still FAILS the planted tree at full scope"
else
    _bad "gate(s) ${_wide_missing}no longer FAIL the planted tree at FULL scope — the empty-scope fix has widened into a permanent skip, which is the strictly worse defect"
fi

# ===========================================================================
# ARM 7 — A RELATIVE APP-DIR PATH MUST PRODUCE THE SAME VERDICTS (.github#374)
# ===========================================================================
#
# `run-hydra-gates.sh:238` never absolutised APP_DIR before its `cd`, and
# gate-17 is the only gate that hands `${APP_DIR}` to its checker afterwards —
# so the scan root resolved a SECOND time, against the app dir itself, and the
# checker read `relapp/relapp`. It found nothing, printed its terminal
# `# count=0`, and gate-17 reported PASS. Same tree, absolute path: FAIL — 1.
#
# ⚠️ THIS IS THE ARM THE REST OF THE PACKAGE STRUCTURALLY CANNOT HAVE.
# `test_gate_acceptance_matrix.sh` builds every fixture path from `${PKG_ROOT}`,
# so its driver can only ever reproduce the SAFE invocation. A suite that can
# only express the safe call cannot test the unsafe one, and that is worth more
# than the bug: the invocation this runner's own header documents for humans
# (`./scripts/run-hydra-gates.sh [options] [app-dir]`) was untestable here.
#
# So this arm deliberately `cd`s to the PARENT and passes a BARE RELATIVE NAME.
echo
echo "-- ARM 7: a relative app-dir path --"

_rel_parent="${_tmp}/relparent"
mkdir -p "${_rel_parent}/relapp/lib/Controller" "${_rel_parent}/relapp/appinfo"
cat > "${_rel_parent}/relapp/lib/Controller/ThingController.php" <<'PHP'
<?php
namespace OCA\Fx\Controller;
class ThingController {
    public function index(): JSONResponse
    {
        return new JSONResponse($this->objectService->findAll([]));
    }
}
PHP
printf '<?php\nreturn [];\n' > "${_rel_parent}/relapp/appinfo/routes.php"
(
    cd "${_rel_parent}/relapp" || exit 1
    git init -q .
    git add -A
    git -c user.email=t@t -c user.name=t commit -qm init
) >/dev/null 2>&1

_rel_abs_out="${_tmp}/rel-abs.txt"
_rel_rel_out="${_tmp}/rel-rel.txt"
_rel_logs="${_tmp}/rel-logs"; mkdir -p "${_rel_logs}"
_rel_logs2="${_tmp}/rel-logs2"; mkdir -p "${_rel_logs2}"
(
    cd "${_rel_parent}" || exit 1
    HYDRA_GATE_LOG_DIR="${_rel_logs}" bash "${_runner}" "${_rel_parent}/relapp" \
        > "${_rel_abs_out}" 2>&1
)
(
    # THE WHOLE POINT: parent directory, bare relative name, no leading `./`.
    cd "${_rel_parent}" || exit 1
    HYDRA_GATE_LOG_DIR="${_rel_logs2}" bash "${_runner}" relapp > "${_rel_rel_out}" 2>&1
)

# Positive control FIRST: the absolute invocation must catch the plant, or the
# comparison below is between two meaningless numbers.
if grep -qE '^\[gate-17\][^:]*: FAIL' "${_rel_abs_out}"; then
    _ok "positive control: gate-17 FAILS the planted pass-through wrapper via an ABSOLUTE path"
else
    _bad "positive control BROKEN: gate-17 did not catch the planted ADR-022 wrapper even via an absolute path — got: $(_verdict "${_rel_abs_out}" 17)"
fi

_rel_abs_v="$(_verdict "${_rel_abs_out}" 17)"
_rel_rel_v="$(_verdict "${_rel_rel_out}" 17)"
if [ "${_rel_abs_v}" = "${_rel_rel_v}" ]; then
    _ok "gate-17 returns the same verdict ('${_rel_rel_v}') for a relative and an absolute app-dir"
else
    _bad "gate-17 verdict DEPENDS ON HOW THE CALLER SPELLED THE PATH: absolute '${_rel_abs_v}' vs relative '${_rel_rel_v}'. This is .github#374 — APP_DIR is not absolutised before the cd, so the checker resolves it a second time against the app dir."
fi

# And the invariant that makes it impossible rather than merely fixed: the run
# must STATE the absolute path it resolved. A silent fix is one refactor from
# regressing with nothing to notice it.
if grep -qE '^\[hydra-gates\] App dir: /.* \(absolute\)$' "${_rel_rel_out}"; then
    _ok "the run states the ABSOLUTE app dir it resolved, so a future relative path cannot reach a checker unannounced"
else
    _bad "the run does not print an absolute 'App dir:' line — nothing in the output distinguishes a relative invocation from an absolute one"
fi

echo
if [ "${_failures}" -eq 0 ]; then
    echo "test_gate_empty_scope_never_passes.sh: ALL PASS"
    exit 0
fi
echo "test_gate_empty_scope_never_passes.sh: ${_failures} FAILURE(S)"
exit 1
