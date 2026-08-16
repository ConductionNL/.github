#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# test_gate_discarded_counts_and_empty_deltas.sh — five repairs, one theme:
# A GATE MUST NOT PRINT A VERDICT ABOUT SOMETHING IT DID NOT MEASURE.
#
#   .github#396  gate-15 computed its finding and then THREW IT AWAY.
#   .github#394  gate-23 turned a CRASHED linter into a finding of size 1.
#   .github#401  gate-48's advisory DISPLACED its own verdict, and gates 47
#                and 48 passed over a delta containing zero inspectable files.
#   .github#403  gate-57 printed PASS over a scope its checker had EXPLICITLY
#                DECLINED to judge — a false green that arrived through a FIX.
#
# WHY A SEPARATE SUITE RATHER THAN AN expect.conf BUNDLE
# -----------------------------------------------------
# The acceptance matrix runs each bundle as a plain directory, with no git
# history and no flags. Four of the five defects here are invisible at that
# scope by construction:
#
#   * gate-15's defect only exists UNDER `--scope-to-diff`. At full scope the
#     gate is correct, which is why a static bundle would grade it green while
#     the defect stood.
#   * gates 47 and 48 are DELTA gates. Without a base they decline outright,
#     so a bundle can only ever observe the branch that was already honest.
#   * gate-23's defect needs the linter to CRASH, which needs the helper
#     replaced — the runner resolves it from its own SCRIPT_DIR.
#   * gate-57's turns on whether a SIBLING app exists beside the repo, which
#     is a property of the parent directory, not of the fixture.
#
# So this suite materialises real repositories with real base refs, and shadows
# the package directory when a crash is the subject. It is discovered and run
# by tests/run-helper-suites.sh like every other `scripts/lib/test_*`.
#
# HOW THE ARMS ARE BUILT TO SURVIVE A REVERT
# ------------------------------------------
# Every repair below was reverted, one at a time, while writing this file, and
# each revert had to turn a NAMED assertion red — not merely change a count.
# Two properties do that work:
#
#   1. ONE MECHANISM PER NAMED FILE. gate-15 has two rules
#      (`dashboard-component-used-as-widget`, `dashboard-in-dashboard-slot`)
#      and gets one file each, so a repair that loses one rule cannot hide
#      behind the other still producing a FAIL naming "some file".
#   2. THE SUBJECT IS ANCHORED. Assertions grep for a full token
#      (`rule=dashboard-in-dashboard-slot`, `csrf-cochange: PASS`) rather than
#      a prefix another line contains — a sibling that merely CONTAINS the
#      subject keeps an arm green over a reverted fix.
#
# ⚠️ AND THE FIXTURES ARE WRITTEN HERE, NOT COMMITTED TO THIS REPOSITORY.
# A fixture's own prose can satisfy the gate it is testing (`.github#358`).
# Everything below is generated into a temp directory, so nothing in this file
# ever enters a scanned corpus.
#
# Run: bash scripts/lib/test_gate_discarded_counts_and_empty_deltas.sh
set -uo pipefail

GF_PKG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../.." && pwd)"
export GF_PKG_ROOT
# shellcheck source=./gate_fixture_support.sh
. "${GF_PKG_ROOT}/scripts/lib/gate_fixture_support.sh"

RUNNER="${HYDRA_GATES_RUNNER_UNDER_TEST:-${GF_PKG_ROOT}/scripts/run-hydra-gates.sh}"
WRAPPER="${GF_PKG_ROOT}/bin/hydra-gates"

_failures=0
_asserts=0
_ok()  { _asserts=$((_asserts + 1)); echo "  ok   — $1"; }
_bad() { _asserts=$((_asserts + 1)); _failures=$((_failures + 1)); echo "  FAIL — $1"; }

echo "test_gate_discarded_counts_and_empty_deltas.sh"

_tmp="$(mktemp -d "${TMPDIR:-/tmp}/hydra-discarded.XXXXXX")" || {
    echo "FAIL — could not create a temp directory; refusing to run."
    exit 1
}
trap 'rm -rf "${_tmp}"' EXIT

# A run that aborted before its summary leaves per-gate lines on stdout and
# reads exactly like a completed one. Nothing below is graded until this says
# the run finished.
_finished() { printf '%s' "$1" | grep -q '^\[hydra-gates\] COVERAGE:'; }

# The RAW first line, with no filtering whatsoever. This is deliberately NOT
# gf_verdict: it is the parser shape `.github#401` broke, and asserting on it
# is what pins the ORDERING fix independently of the parser fix. If only the
# parsers were repaired and the advisory were still printed first, gf_verdict
# would be green here and this would be red.
_raw_first() { printf '%s' "$1" | grep -E "^\[gate-$2\] " | head -1; }

_init_repo() {  # <dir>
    (
        cd "$1" || exit 1
        git init -q .
        git symbolic-ref HEAD refs/heads/development
        git config user.email fixture@example.invalid
        git config user.name "Gate Fixture"
        git config commit.gpgsign false
        git add -f . >/dev/null 2>&1
        git commit -qm base >/dev/null
        git update-ref refs/remotes/origin/development "$(git rev-parse HEAD)"
    )
}

# ===========================================================================
# .github#396 — gate-15 COMPUTED THE FINDING, THEN DISCARDED IT
# ===========================================================================
#
# The checker runs whole-tree by necessity (a dashboard-in-dashboard is a
# relation between a manifest entry and a component file, so neither half
# alone is a finding). `--scope-to-diff` then filtered its FINDINGS and `wc -l`
# read 0 — 140 bytes of measured defect became `PASS`.
#
# THE FIX IS NOT "REFUSE TO PASS". That was measured and rejected: guarding on
# "pre-filter count non-zero" ALSO fires at PARTIAL scope, so a PR touching one
# clean .vue would drop this gate to NOT APPLICABLE on most PRs in an affected
# repo. The scoped verdict is right; what was missing is that it never said
# anything had been thrown away. So the repair states the DISCARDED COUNT, and
# ARM 15.5 below is the control that the verdict itself did not move.
echo
echo "== .github#396 — gate-15: a discarded finding must be STATED =="

_a15="${_tmp}/gate15"
mkdir -p "${_a15}/src/views"
cat > "${_a15}/src/manifest.json" <<'JSON'
{
  "name": "fx",
  "menu": [],
  "pages": [
    { "id": "Home", "type": "custom", "component": "DashboardView", "route": "/" },
    { "id": "Overview", "type": "dashboard",
      "config": { "widgets": [ { "id": "embed", "type": "custom", "component": "DashboardView" },
                               { "id": "my-work", "type": "custom" } ] } },
    { "id": "Slots", "type": "dashboard", "component": "SlotDash",
      "config": { "widgets": [ { "id": "my-work", "type": "custom" } ] } }
  ]
}
JSON
# MECHANISM 1, and only this one: a custom page component that is also
# referenced as a widget on a dashboard page.
cat > "${_a15}/src/views/DashboardView.vue" <<'VUE'
<template>
  <CnDashboardPage :widgets="widgets" />
</template>
VUE
# MECHANISM 2, and only this one: a dashboard rendered inside another
# dashboard's widget body slot.
cat > "${_a15}/src/views/SlotDash.vue" <<'VUE'
<template>
  <CnDashboardPage :widgets="widgets" :layout="layout">
    <template #widget-my-work="{ item }">
      <CnDashboardPage :widgets="subWidgets" :layout="subLayout" />
    </template>
  </CnDashboardPage>
</template>
VUE
echo "# fixture" > "${_a15}/README.md"
_init_repo "${_a15}"
_a15_base="$(cd "${_a15}" && git rev-parse HEAD)"
# The head commit touches ONLY documentation, so every finding above falls out
# of a narrowed scope. This is the shape of an ordinary docs PR.
echo "second line" >> "${_a15}/README.md"
( cd "${_a15}" && git add -f README.md >/dev/null && git commit -qm docs >/dev/null )

_l15f="${_tmp}/logs-15-full"; mkdir -p "${_l15f}"
_o15f="$(HYDRA_GATE_LOG_DIR="${_l15f}" HYDRA_OR_GATE_BLOCK_AFTER_EPOCH=0 \
    bash "${WRAPPER}" --base "${_a15_base}" --app-dir "${_a15}" 2>&1 || true)"

if ! _finished "${_o15f}"; then
    _bad "gate-15 full-scope run ABORTED before its summary — nothing below it is a result"
else
    # ARM 15.1 / 15.2 — the positive controls, and they run FIRST. A gate
    # widened until it catches nothing would satisfy every other arm here.
    if grep -qF 'rule=dashboard-component-used-as-widget' "${_l15f}/hydra-gate-dashboard-antipattern.log" 2>/dev/null \
        && grep -qF 'DashboardView.vue' "${_l15f}/hydra-gate-dashboard-antipattern.log" 2>/dev/null; then
        _ok "control: at full scope gate-15 NAMES DashboardView.vue for rule=dashboard-component-used-as-widget"
    else
        _bad "control FAILED: gate-15 did not report rule=dashboard-component-used-as-widget on DashboardView.vue at full scope — every arm below is measuring an inert fixture"
    fi
    if grep -qF 'rule=dashboard-in-dashboard-slot' "${_l15f}/hydra-gate-dashboard-antipattern.log" 2>/dev/null \
        && grep -qF 'SlotDash.vue' "${_l15f}/hydra-gate-dashboard-antipattern.log" 2>/dev/null; then
        _ok "control: at full scope gate-15 NAMES SlotDash.vue for rule=dashboard-in-dashboard-slot"
    else
        _bad "control FAILED: gate-15 did not report rule=dashboard-in-dashboard-slot on SlotDash.vue at full scope — the second mechanism is not in play, so a repair could lose it unnoticed"
    fi
    # ARM 15.5 — ANTI-WIDENING, stated before the interesting arm so it cannot
    # be read as an afterthought. The advisory must appear ONLY when something
    # was actually discarded; a NOTE printed unconditionally would satisfy
    # ARM 15.3 while meaning nothing.
    if printf '%s' "${_o15f}" | grep -qE '^\[gate-15\] NOTE:'; then
        _bad "gate-15 printed its discarded-findings NOTE at FULL scope, where nothing was discarded — the advisory is unconditional and therefore says nothing"
    else
        _ok "gate-15 prints no discarded-findings NOTE at full scope (nothing was discarded)"
    fi
fi

_l15d="${_tmp}/logs-15-diff"; mkdir -p "${_l15d}"
_o15d="$(HYDRA_GATE_LOG_DIR="${_l15d}" HYDRA_OR_GATE_BLOCK_AFTER_EPOCH=0 \
    bash "${WRAPPER}" --scope-to-diff --base "${_a15_base}" --app-dir "${_a15}" 2>&1 || true)"

if ! _finished "${_o15d}"; then
    _bad "gate-15 diff-scoped run ABORTED before its summary — nothing below it is a result"
else
    # ARM 15.3 — THE ASSERTION THE REPAIR EXISTS FOR. Two findings were
    # computed over the whole tree and then filtered out. The count must be
    # stated, and it must be the RIGHT count: `2`, not "some".
    _n15="$(printf '%s' "${_o15d}" | grep -E '^\[gate-15\] NOTE:' | grep -oE 'DISCARDED [0-9]+' | grep -oE '[0-9]+' | head -1)"
    if [ "${_n15:-0}" = "2" ]; then
        _ok "gate-15 states that the scope filter DISCARDED 2 findings it had already computed"
    else
        _bad "gate-15 discarded 2 computed findings and reported '${_n15:-<no NOTE line at all>}' — this is .github#396: it measured the defect, threw it away, and printed the same word as a clean tree"
    fi
    # ARM 15.4 — a count with no file behind it has to be believed; a file can
    # be read. Both mechanisms must be recoverable, one row each.
    _d15="${_l15d}/hydra-gate-dashboard-antipattern.log.discarded"
    if [ -f "${_d15}" ] \
        && grep -qF 'rule=dashboard-component-used-as-widget' "${_d15}" \
        && grep -qF 'rule=dashboard-in-dashboard-slot' "${_d15}"; then
        _ok "the discarded findings are written out and both rules are recoverable from ${_d15##*/}"
    else
        _bad "gate-15 stated a discarded count with no readable evidence behind it — ${_d15##*/} is missing or does not carry both rules"
    fi
    # ARM 15.6 — the verdict must still BE the verdict. This repair adds a
    # `[gate-15] ` line, which is exactly how `.github#401` happened one gate
    # over. Graded on the RAW first line, so ordering is pinned regardless of
    # what the shared parsers do.
    _r15="$(_raw_first "${_o15d}" 15)"
    case "${_r15}" in
        *"dashboard-antipattern: "*)
            _ok "gate-15's FIRST [gate-15] line is still its verdict, not the new advisory" ;;
        *)
            _bad "gate-15's new advisory DISPLACED its verdict — the .github#401 shape, reintroduced by its own fix. First line: ${_r15}" ;;
    esac
    # ARM 15.7 — and the verdict itself must not have moved. The rejected fix
    # would show up here as NOT APPLICABLE.
    case "$(gf_verdict "${_o15d}" 15)" in
        *"NOT APPLICABLE"*)
            _bad "gate-15 went NOT APPLICABLE on a narrowed scope — this is the fix that was measured and rejected: it retires the gate on any PR that touches a clean .vue" ;;
        *": PASS"*)
            _ok "gate-15's scoped verdict is unchanged (PASS over the files this diff touched)" ;;
        *)
            _bad "gate-15's scoped verdict is neither PASS nor NOT APPLICABLE: $(gf_verdict "${_o15d}" 15)" ;;
    esac
fi

# ARM 15.8 — PARTIAL scope, the case that killed the obvious fix. A PR that
# touches ONE CLEAN .vue must still get a real verdict.
_a15p="${_tmp}/gate15-partial"
cp -r "${_a15}" "${_a15p}"
printf '<template>\n  <div class="clean">ok</div>\n</template>\n' > "${_a15p}/src/views/CleanView.vue"
( cd "${_a15p}" && git add -f src/views/CleanView.vue >/dev/null && git commit -qm "one clean vue" >/dev/null )
_l15p="${_tmp}/logs-15-partial"; mkdir -p "${_l15p}"
_o15p="$(HYDRA_GATE_LOG_DIR="${_l15p}" HYDRA_OR_GATE_BLOCK_AFTER_EPOCH=0 \
    bash "${WRAPPER}" --scope-to-diff --base "${_a15_base}" --app-dir "${_a15p}" 2>&1 || true)"
if ! _finished "${_o15p}"; then
    _bad "gate-15 partial-scope run ABORTED before its summary"
elif printf '%s' "$(gf_verdict "${_o15p}" 15)" | grep -qF ': PASS'; then
    _ok "a PR touching one CLEAN .vue still gets a real gate-15 verdict, not a self-inflicted skip"
else
    _bad "a PR touching one clean .vue no longer gets a gate-15 verdict: $(gf_verdict "${_o15p}" 15)"
fi

# ===========================================================================
# .github#394 — gate-23 TURNED A CRASHED LINTER INTO A FINDING
# ===========================================================================
#
# `[ "${_or_abs_hits}" -eq 0 ] && _or_abs_hits=1` clamped an UNREAD count to
# one, so a linter that died before opening a file reported `FAIL — 1
# OR-abstraction match(es)` over a clean repository: a number nobody measured,
# naming an anti-pattern nobody found.
#
# ONLY THE BLOCK BRANCH REACHES IT. In WARN mode the linter exits 0 whatever it
# found, so a crash is read one branch higher. BLOCK is what the acceptance
# driver forces (HYDRA_OR_GATE_BLOCK_AFTER_EPOCH=0) and what the fleet gets
# after the bake-in epoch, so every arm here sets it.
echo
echo "== .github#394 — gate-23: a crashed linter is not a finding =="

_a23c="${_tmp}/gate23-clean"
mkdir -p "${_a23c}/lib/Service"
cat > "${_a23c}/lib/Service/ThingService.php" <<'PHP'
<?php
namespace OCA\Fx\Service;

class ThingService {
	public function ping(): int {
		return 1;
	}
}
PHP

_a23p="${_tmp}/gate23-planted"
mkdir -p "${_a23p}/lib/Service"
cat > "${_a23p}/lib/Service/TenantIsolationService.php" <<'PHP'
<?php
namespace OCA\Fx\Service;

class TenantIsolationService {
	public function isolate(): void {
	}
}
PHP

# ARM 23.1 — POSITIVE CONTROL FIRST. A real BLOCK-mode finding must still be a
# FAIL carrying its real size. Without this arm the repair could have been
# "never fail", which satisfies every other assertion here.
_l231="${_tmp}/logs-23-planted"; mkdir -p "${_l231}"
_o231="$(HYDRA_GATE_LOG_DIR="${_l231}" HYDRA_OR_GATE_BLOCK_AFTER_EPOCH=0 \
    bash "${RUNNER}" --full "${_a23p}" 2>&1 || true)"
_v231="$(gf_verdict "${_o231}" 23)"
if printf '%s' "${_v231}" | grep -qF 'FAIL — 1 OR-abstraction match(es)'; then
    _ok "control: gate-23 still FAILs a real BLOCK-mode match with its measured count (TenantIsolationService)"
else
    _bad "control FAILED: gate-23 did not report a real planted anti-pattern — got: ${_v231}"
fi

# ARM 23.2 — and it must still PASS a clean tree, so the repair did not turn
# the gate into a permanent skip.
_l232="${_tmp}/logs-23-clean"; mkdir -p "${_l232}"
_o232="$(HYDRA_GATE_LOG_DIR="${_l232}" HYDRA_OR_GATE_BLOCK_AFTER_EPOCH=0 \
    bash "${RUNNER}" --full "${_a23c}" 2>&1 || true)"
if printf '%s' "$(gf_verdict "${_o232}" 23)" | grep -qF ': PASS'; then
    _ok "control: gate-23 PASSes the same clean tree with the real linter"
else
    _bad "control FAILED: gate-23 did not pass a clean tree — got: $(gf_verdict "${_o232}" 23)"
fi

# ARM 23.3 — THE DEFECT. The linter is replaced by a stub that writes a
# traceback and exits 1, which is byte-for-byte what a BLOCK-mode failure looks
# like to a caller reading only the status. The package directory is shadowed
# with symlinks so the runner resolves the stub from its own SCRIPT_DIR, which
# is where it looks first.
_shadow="${_tmp}/shadow-scripts"
mkdir -p "${_shadow}"
for _f in "${GF_PKG_ROOT}"/scripts/*; do
    ln -s "${_f}" "${_shadow}/$(basename "${_f}")"
done
rm -f "${_shadow}/lint-or-abstraction-anti-patterns.sh"
cat > "${_shadow}/lint-or-abstraction-anti-patterns.sh" <<'STUB'
#!/usr/bin/env bash
echo "hydra-gate-fixture-stub: the OR-abstraction linter died before scanning anything" >&2
exit 1
STUB
_l233="${_tmp}/logs-23-stub"; mkdir -p "${_l233}"
_o233="$(HYDRA_GATE_LOG_DIR="${_l233}" HYDRA_OR_GATE_BLOCK_AFTER_EPOCH=0 \
    bash "${_shadow}/run-hydra-gates.sh" --full "${_a23c}" 2>&1 || true)"

# ARM 23.4 — the control that the stub was actually in play. Without it, a
# green ARM 23.3 could mean the shadow directory was never used.
if grep -qF 'hydra-gate-fixture-stub' "${_l233}/hydra-gate-or-abstraction-anti-patterns.log" 2>/dev/null; then
    _ok "control: the stubbed linter really ran (its output reached gate-23's log)"
else
    _bad "control FAILED: no evidence the stubbed linter was used — the assertion below proves nothing"
fi

_v233="$(gf_verdict "${_o233}" 23)"
if printf '%s' "${_v233}" | grep -qF 'OR-abstraction match(es)'; then
    _bad "gate-23 reported a MATCH COUNT from a linter that crashed before opening a file — this is .github#394, a finding nobody measured. Line: ${_v233}"
elif printf '%s' "${_v233}" | grep -qF 'SKIPPED (wiring)'; then
    _ok "gate-23 reports SKIPPED (wiring) when its linter dies without printing its terminal summary"
else
    _bad "gate-23's verdict over a crashed linter is neither a fabricated count nor a wiring skip: ${_v233}"
fi
# The reason must say what went unchecked. A skip with no subject is how a gate
# disappears quietly, which is the failure this whole family is about.
if printf '%s' "${_v233}" | grep -qF 'UNVERIFIED by this run'; then
    _ok "gate-23's wiring skip states that ADR-022 duplication is UNVERIFIED, rather than declining silently"
else
    _bad "gate-23's wiring skip does not say what went unchecked: ${_v233}"
fi

# ===========================================================================
# .github#401 — gate-48's ADVISORY DISPLACED ITS VERDICT
# ===========================================================================
#
# `[gate-48] no CSRF signal was ADDED ...` was printed BEFORE `[gate-48]
# csrf-cochange: PASS`. Both parsers in this package take the first match, and
# neither skipped that shape — so the first author of a gate-48 fixture is told
# "gate-48 emitted NO verdict line at all": a gate defect that does not exist.
echo
echo "== .github#401(a) — gate-48: the verdict must not be displaced by its own advisory =="

_a48="${_tmp}/gate48"
mkdir -p "${_a48}/lib/Controller" "${_a48}/src"
cat > "${_a48}/lib/Controller/ThingController.php" <<'PHP'
<?php
namespace OCA\Fx\Controller;

use OCP\AppFramework\Controller;
use OCP\AppFramework\Http\Attribute\NoAdminRequired;
use OCP\AppFramework\Http\Attribute\NoCSRFRequired;

class ThingController extends Controller {
	#[NoAdminRequired]
	#[NoCSRFRequired]
	public function destroy(int $id): void {
	}
}
PHP
echo "export function ping() { return 1 }" > "${_a48}/src/main.js"
echo "# fixture" > "${_a48}/README.md"
_init_repo "${_a48}"
_a48_base="$(cd "${_a48}" && git rev-parse HEAD)"
# The head commit DROPS the attribute. Every caller under src/ is already
# protected (there is no mutating call site at all), so the gate reaches its
# "none was needed" branch — the branch that prints the advisory.
python3 - "${_a48}/lib/Controller/ThingController.php" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1])
p.write_text(p.read_text().replace("\t#[NoCSRFRequired]\n", ""))
PY
( cd "${_a48}" && git add -f lib/Controller/ThingController.php >/dev/null && git commit -qm "drop the attribute" >/dev/null )

_l48="${_tmp}/logs-48"; mkdir -p "${_l48}"
_o48="$(HYDRA_GATE_LOG_DIR="${_l48}" HYDRA_OR_GATE_BLOCK_AFTER_EPOCH=0 \
    bash "${WRAPPER}" --base "${_a48_base}" --app-dir "${_a48}" 2>&1 || true)"

if ! _finished "${_o48}"; then
    _bad "the gate-48 advisory run ABORTED before its summary"
else
    # ARM 48.0 — control: the advisory branch was actually reached. Without
    # this the ordering assertions are vacuously green.
    if printf '%s' "${_o48}" | grep -qF 'no CSRF signal was ADDED by this diff'; then
        _ok "control: the advisory branch was reached (the removal is real and every caller is already protected)"
    else
        _bad "control FAILED: gate-48 never printed its callers advisory, so the ordering assertions below prove nothing"
    fi
    # ARM 48.1 — THE ORDERING, graded on the RAW first line. This is the arm
    # that stays red if only the parsers are hardened.
    _r48="$(_raw_first "${_o48}" 48)"
    case "${_r48}" in
        *"csrf-cochange: "*)
            _ok "gate-48's FIRST [gate-48] line is its verdict, so a first-match-wins parser reads a verdict" ;;
        *)
            _bad "gate-48's advisory is printed BEFORE its verdict — this is .github#401(a), and a reader is told the gate emitted no verdict at all. First line: ${_r48}" ;;
    esac
    # ARM 48.2 — THE TAG, so the shared parsers skip it even if someone
    # reorders this again. This is the arm that stays red if only the ordering
    # is fixed.
    if printf '%s' "${_o48}" | grep -qE '^\[gate-48\] NOTE: no CSRF signal was ADDED'; then
        _ok "gate-48's advisory carries the NOTE: tag the shared parsers already skip"
    else
        _bad "gate-48's callers advisory is untagged — reorder it once and it silently becomes the verdict again"
    fi
    # ARM 48.3 — and the information must survive the repair. Deleting the
    # advisory would satisfy both arms above and lose a stated claim about the
    # callers, which is why it is asserted separately.
    if printf '%s' "${_o48}" | grep -qF 'check_csrf_callers.py over the working tree'; then
        _ok "the advisory still states WHICH claim the green rests on (checked by check_csrf_callers.py)"
    else
        _bad "the advisory's content was lost in the reorder — a green here is a claim about the callers and must say so"
    fi
    # ARM 48.4 — the shared parser agrees with the raw one.
    if printf '%s' "$(gf_verdict "${_o48}" 48)" | grep -qF 'csrf-cochange: PASS'; then
        _ok "gf_verdict returns gate-48's verdict, not its advisory"
    else
        _bad "gf_verdict still returns gate-48's advisory: $(gf_verdict "${_o48}" 48)"
    fi
fi

# ===========================================================================
# .github#401(b) — GATES 47 AND 48 PASSED OVER A ZERO-FILE DELTA
# ===========================================================================
#
# ⚠️ THE SHAPE, precisely: a TRULY empty delta is unreachable through the
# wrapper (`--base <sha-of-HEAD>` yields NOT APPLICABLE upstream). What IS
# reachable, and is the common docs PR, is a delta with a real diff in it that
# contains ZERO INSPECTABLE FILES. Measured before the repair: gates 19, 29 and
# 61 declined and named what they had excluded, while 16, 47 and 48 said PASS.
#
# Gates 46, 50, 55, 56, 58, 59, 60 and 62 were fixed for exactly this by
# `#242`/`#268`; 47 and 48 were the last two without the remedy.
echo
echo "== .github#401(b) — gates 47/48: a delta with no candidate file is not a PASS =="

_l47na="${_tmp}/logs-47-na"; mkdir -p "${_l47na}"
_o47na="$(HYDRA_GATE_LOG_DIR="${_l47na}" HYDRA_OR_GATE_BLOCK_AFTER_EPOCH=0 \
    bash "${WRAPPER}" --base "${_a15_base}" --app-dir "${_a15}" 2>&1 || true)"

if ! _finished "${_o47na}"; then
    _bad "the zero-candidate delta run ABORTED before its summary"
else
    for _g in 47 48; do
        _v="$(gf_verdict "${_o47na}" "${_g}")"
        case "${_v}" in
            *": PASS"*)
                _bad "gate-${_g} printed PASS over a delta containing no file it can read — this is .github#401(b), and that PASS counts toward 'N of N applicable gates ran'" ;;
            *"NOT APPLICABLE"*)
                _ok "gate-${_g} reports NOT APPLICABLE over a delta with no candidate file" ;;
            *)
                _bad "gate-${_g}'s verdict over a zero-candidate delta is neither PASS nor NOT APPLICABLE: ${_v}" ;;
        esac
    done
    # The reason has to NAME what was absent, or the decline is unfalsifiable —
    # the `.github#347` failure, where a true verdict carried a reason nobody
    # could check.
    if printf '%s' "$(gf_verdict "${_o47na}" 47)" | grep -qF 'lib/ or src/'; then
        _ok "gate-47 names the file classes its delta did not contain (lib/ or src/)"
    else
        _bad "gate-47 declined without naming what was absent — an uncheckable reason is how .github#347 stood for weeks"
    fi
    if printf '%s' "$(gf_verdict "${_o47na}" 48)" | grep -qF 'lib/Controller'; then
        _ok "gate-48 names the file class its delta did not contain (lib/Controller)"
    else
        _bad "gate-48 declined without naming what was absent"
    fi
fi

# ARM 47/48 ANTI-WIDENING — the same two gates over a delta that DOES contain
# their subject must still reach a verdict, and a real violation must still
# FAIL. Without these arms the repair could be "always decline", which is a
# strictly worse hole than the PASS it replaces.
_a48f="${_tmp}/gate48-fail"
cp -r "${_a48}" "${_a48f}"
cat > "${_a48f}/src/deleteModal.js" <<'JS'
export async function removeThing(id) {
	return fetch(`/apps/fx/api/things/${id}`, { method: 'DELETE' })
}
JS
( cd "${_a48f}" && git add -f src/deleteModal.js >/dev/null && git commit -qm "an unprotected delete caller" >/dev/null )

_l48f="${_tmp}/logs-48-fail"; mkdir -p "${_l48f}"
_o48f="$(HYDRA_GATE_LOG_DIR="${_l48f}" HYDRA_OR_GATE_BLOCK_AFTER_EPOCH=0 \
    bash "${WRAPPER}" --base "${_a48_base}" --app-dir "${_a48f}" 2>&1 || true)"

if ! _finished "${_o48f}"; then
    _bad "the gate-47/48 anti-widening run ABORTED before its summary"
else
    if printf '%s' "$(gf_verdict "${_o48f}" 48)" | grep -qF ': FAIL'; then
        _ok "anti-widening: gate-48 still FAILs a real @NoCSRFRequired removal with an unprotected caller"
    else
        _bad "gate-48 no longer catches a real removal — the empty-delta guard has widened into a green hole: $(gf_verdict "${_o48f}" 48)"
    fi
    if grep -qF 'src/deleteModal.js' "${_l48f}/hydra-gate-csrf-cochange.log" 2>/dev/null; then
        _ok "anti-widening: gate-48 NAMES the unprotected call site (src/deleteModal.js)"
    else
        _bad "gate-48 failed without naming the unprotected call site — a bare count is not a finding"
    fi
    if printf '%s' "$(gf_verdict "${_o48f}" 47)" | grep -qF ': FAIL'; then
        _ok "anti-widening: gate-47 still FAILs a security-annotation change shipped with no test co-change"
    else
        _bad "gate-47 no longer catches an annotation change without a test — the empty-delta guard has widened: $(gf_verdict "${_o48f}" 47)"
    fi
fi

# ===========================================================================
# gate-57 — A CHECKER THAT DECLINED TO JUDGE IS NOT A PASS (.github#403 follow-up)
# ===========================================================================
#
# `#403` repaired the hydra#106 fail-safe so it keys on the intrinsic
# `appinfo/info.xml` id instead of the checkout directory name. It had never
# engaged in CI, for any repository, because `quality.yml` checks out to
# `path: app`. Now that it engages, a foundation repo with no siblings beside
# it makes the checker REFUSE — correctly, since a cross-app caller cannot be
# told from no caller at all.
#
# 🔑 But the refusal is on STDERR and this gate counted STDOUT lines, so a
# checker that judged nothing produced zero lines and zero lines printed PASS.
# **Repairing a guard that had never engaged replaced a false RED with a false
# GREEN** — the `#374` family arriving through a fix rather than a bug.
#
# The three arms below differ by exactly ONE thing at a time, which is what
# makes them a control rather than three observations.
echo
echo "== gate-57: a declined judgement is not a clean bill =="

_owc_p1="${_tmp}/owc-with-sibling"
_owc_p2="${_tmp}/owc-alone"
_owc_p3="${_tmp}/owc-leaf"
for _p in "${_owc_p1}" "${_owc_p2}" "${_owc_p3}"; do mkdir -p "${_p}"; done

_owc_make_foundation() {  # <parent>
    local _a="$1/openregister"
    mkdir -p "${_a}/appinfo" "${_a}/lib/Service"
    printf '<?xml version="1.0"?>\n<info><id>openregister</id><name>Open Register</name></info>\n' \
        > "${_a}/appinfo/info.xml"
    cat > "${_a}/lib/Service/JournalEmitter.php" <<'PHP'
<?php
namespace OCA\OpenRegister\Service;

class JournalEmitter {
	public function postJournalEntry(string $subject): void {
	}
}
PHP
}
_owc_make_foundation "${_owc_p1}"
_owc_make_foundation "${_owc_p2}"
# The ONLY difference between p1 and p2: a sibling Nextcloud app beside it.
mkdir -p "${_owc_p1}/docudesk/appinfo" "${_owc_p1}/docudesk/lib"
printf '<?xml version="1.0"?>\n<info><id>docudesk</id></info>\n' > "${_owc_p1}/docudesk/appinfo/info.xml"
printf '<?php\nnamespace OCA\\Docudesk;\nclass Noop {}\n' > "${_owc_p1}/docudesk/lib/Noop.php"

# ARM 57.1 — POSITIVE CONTROL FIRST. With a sibling on disk the checker CAN
# resolve callers, and the planted orphan must be reported by name. Without
# this arm, arm 57.2 could be satisfied by a fixture carrying no subject at all.
_l571="${_tmp}/logs-57-sibling"; mkdir -p "${_l571}"
_o571="$(HYDRA_GATE_LOG_DIR="${_l571}" HYDRA_OR_GATE_BLOCK_AFTER_EPOCH=0 \
    bash "${RUNNER}" --full "${_owc_p1}/openregister" 2>&1 || true)"
if printf '%s' "$(gf_verdict "${_o571}" 57)" | grep -qF ': FAIL'; then
    _ok "control: with a sibling app beside it, gate-57 judges the tree and FAILs the planted orphan"
else
    _bad "control FAILED: gate-57 did not report the planted orphan even with a sibling present — the fixture carries no subject, so arm 57.2 would prove nothing. Got: $(gf_verdict "${_o571}" 57)"
fi
if grep -qF 'method=postJournalEntry' "${_l571}/hydra-gate-orphaned-write-capability.log" 2>/dev/null; then
    _ok "control: the finding NAMES the planted method (method=postJournalEntry)"
else
    _bad "control FAILED: gate-57 failed without naming the planted method — it failed for some other reason"
fi

# ARM 57.2 — THE DEFECT. The same tree, the same planted orphan, ONE thing
# changed: no sibling. The checker declines on stderr and the gate saw zero
# lines on stdout.
_l572="${_tmp}/logs-57-alone"; mkdir -p "${_l572}"
_o572="$(HYDRA_GATE_LOG_DIR="${_l572}" HYDRA_OR_GATE_BLOCK_AFTER_EPOCH=0 \
    bash "${RUNNER}" --full "${_owc_p2}/openregister" 2>&1 || true)"
if ! grep -qF '[orphaned-write-capability] SKIP:' "${_l572}/hydra-gate-orphaned-write-capability.err" 2>/dev/null; then
    _bad "control FAILED: the checker did not emit its SKIP marker on the no-sibling arm, so the assertion below is measuring something else"
else
    _ok "control: the checker emitted its SKIP marker (it declined to judge this tree)"
fi
_v572="$(gf_verdict "${_o572}" 57)"
case "${_v572}" in
    *": PASS"*)
        _bad "gate-57 printed PASS over a scope the checker EXPLICITLY DECLINED to judge — repairing the hydra#106 guard turned a false red into a false green, and that PASS counts toward the applicable-gate arithmetic. Line: ${_v572}" ;;
    *"NOT APPLICABLE"*)
        _ok "gate-57 reports NOT APPLICABLE when the checker declines, rather than a green" ;;
    *)
        _bad "gate-57's verdict over a declined judgement is neither PASS nor NOT APPLICABLE: ${_v572}" ;;
esac
# ⚠️ The wording is load-bearing. A `na` whose reason reads as "nothing to
# find here" is the same false green with a different word on it — these two
# repos' orphaned capabilities are unverified in CI and always were.
if printf '%s' "${_v572}" | grep -qF 'NOT A CLEAN BILL OF HEALTH'; then
    _ok "gate-57's decline says it is NOT a clean bill of health, so a reader cannot take it for one"
else
    _bad "gate-57 declined without saying that the capabilities are UNVERIFIED — a decline that reads like a clean tree is the same false green wearing a different word"
fi

# ARM 57.3 — ANTI-WIDENING. A LEAF app, alone, with a clean service must still
# reach a real verdict. Without this arm the repair could be "decline whenever
# the checker writes anything to stderr", which retires the gate fleet-wide.
mkdir -p "${_owc_p3}/docudesk/appinfo" "${_owc_p3}/docudesk/lib/Service"
printf '<?xml version="1.0"?>\n<info><id>docudesk</id></info>\n' > "${_owc_p3}/docudesk/appinfo/info.xml"
cat > "${_owc_p3}/docudesk/lib/Service/ThingService.php" <<'PHP'
<?php
namespace OCA\Docudesk\Service;

class ThingService {
	public function ping(): int {
		return 1;
	}
}
PHP
_l573="${_tmp}/logs-57-leaf"; mkdir -p "${_l573}"
_o573="$(HYDRA_GATE_LOG_DIR="${_l573}" HYDRA_OR_GATE_BLOCK_AFTER_EPOCH=0 \
    bash "${RUNNER}" --full "${_owc_p3}/docudesk" 2>&1 || true)"
if printf '%s' "$(gf_verdict "${_o573}" 57)" | grep -qF ': PASS'; then
    _ok "anti-widening: a LEAF app checked out alone still gets a real gate-57 verdict"
else
    _bad "gate-57 no longer reaches a verdict for a leaf app — the decline has widened into a permanent skip: $(gf_verdict "${_o573}" 57)"
fi

# ===========================================================================
# .github#401 — THE PARSERS THEMSELVES
# ===========================================================================
#
# Tagging gate-48's advisory closes the ONE case that was measured. It does not
# close the CLASS: any "first line wins" parser is one advisory away from
# reporting silence, and a denylist of `NOTE|WARN|INFO:` can only ever be
# repaired one entry at a time, after the fact. So both parsers now match a
# verdict by its SHAPE — the four forms `_pass` / `_fail` / `_skip` can emit.
#
# These two arms are the only ones here that can distinguish the parser repair
# from the ordering repair, because the fixture gates above are (correctly) no
# longer emitting an untagged advisory for them to trip over.
echo
echo "== .github#401 — a verdict is matched by its SHAPE, not by a denylist =="

# ARM P1 — an advisory carrying NONE of the three known tags, printed first.
# This is byte-for-byte the shape gate-48 had, and the shape any future gate
# can grow by accident.
_synth="$(printf '%s\n%s\n' \
    '[gate-99] some advisory this parser has never been taught to skip' \
    '[gate-99] example-gate: PASS')"
_pv="$(gf_verdict "${_synth}" 99)"
if [ "${_pv}" = '[gate-99] example-gate: PASS' ]; then
    _ok "gf_verdict returns the VERDICT past an untagged advisory"
else
    _bad "gf_verdict returned an untagged advisory instead of the verdict — the denylist is exact and therefore always one entry short. Got: ${_pv}"
fi

# ARM P2 — and the same past a SKIPPED form, which carries a parenthesis the
# naive shape matcher would have to survive.
_synth2="$(printf '%s\n%s\n' \
    '[gate-99] 3 PRE-EXISTING finding(s) on entries this PR did not touch' \
    '[gate-99] example-gate: SKIPPED (wiring) — the helper never started')"
_pv2="$(gf_verdict "${_synth2}" 99)"
case "${_pv2}" in
    *'example-gate: SKIPPED (wiring)'*)
        _ok "gf_verdict returns a SKIPPED verdict past an untagged PRE-EXISTING advisory (gate-53's live shape)" ;;
    *)
        _bad "gf_verdict returned gate-53's PRE-EXISTING advisory instead of the verdict. Got: ${_pv2}" ;;
esac

# ARM P3 — THE TWO PARSERS MUST STAY IN STEP. `gf_verdict` is used by the
# repo-shaped suites; the acceptance matrix has its own copy, and that copy is
# the one that filtered NOTHING. A comment saying "keep these in step" is not a
# mechanism; this is.
#
# ⚠️ THE FIRST MECHANISM WAS THE WRONG SHAPE, AND IT SAID SO OUT LOUD.
# It asserted that the literal string `(PASS|FAIL|NOT APPLICABLE|SKIPPED)`
# appeared in BOTH files. That is not "the parsers agree" — it is "the verdict
# vocabulary is frozen at these four words". `.github#477` added WARNING to
# both files, IN STEP, exactly as their comments require, and this assertion
# went red anyway; it was one of the two that reddened `.github@main` from
# 13:15 on 2026-08-16. Worse, its own repair path was to retype the literal in
# the test, which nobody can check against the files it is supposed to police.
#
# So the property is asserted directly instead: EXTRACT the alternation each
# parser actually uses and require the two to be byte-identical. Vocabulary may
# grow — it just cannot grow in one file only. The shape half of the property
# is kept as a floor: whatever the alternation contains, it must still contain
# the four core verdict forms, so nobody can satisfy "identical" by gutting
# both parsers back to a denylist.
_matrix="${GF_PKG_ROOT}/scripts/lib/test_gate_acceptance_matrix.sh"
_support="${GF_PKG_ROOT}/scripts/lib/gate_fixture_support.sh"

# `\((PASS|FAIL)…\)` — the parenthesised alternation a verdict matcher uses.
# Anchored on PASS|FAIL so it cannot latch onto some unrelated group.
_verdict_alternation() {  # <file> -> the alternation, or empty
    grep -oE '\(PASS\|FAIL[A-Z| ]*\)' "$1" | head -1
}
_alt_support="$(_verdict_alternation "${_support}")"
_alt_matrix="$(_verdict_alternation "${_matrix}")"

if [ -z "${_alt_support}" ] || [ -z "${_alt_matrix}" ]; then
    _bad "a verdict parser no longer carries a recognisable \`(PASS|FAIL|…)\` alternation — support='${_alt_support:-none}' matrix='${_alt_matrix:-none}'. A parser this suite cannot read is a parser it cannot police."
elif [ "${_alt_support}" != "${_alt_matrix}" ]; then
    _bad "the two verdict parsers have drifted apart: gate_fixture_support.sh matches ${_alt_support} and the acceptance matrix matches ${_alt_matrix}, so the same output would be graded differently by two suites"
else
    _missing_form=""
    for _form in 'PASS' 'FAIL' 'NOT APPLICABLE' 'SKIPPED'; do
        printf '%s' "${_alt_support}" | grep -qF -- "${_form}" \
            || _missing_form="${_missing_form}${_form}, "
    done
    if [ -n "${_missing_form}" ]; then
        _bad "both verdict parsers agree, but the shared alternation ${_alt_support} no longer covers ${_missing_form%, } — agreement satisfied by narrowing both is the .github#401 defect in a new coat"
    else
        _ok "both verdict parsers match by the SAME shape — gate_fixture_support.sh and the acceptance matrix agree on ${_alt_support}"
    fi
fi

# POSITIVE CONTROL for the assertion above. Without it, "extract and compare"
# is satisfiable by an extractor that returns empty for everything and calls
# that agreement. Drift a COPY of one parser by one word and require the same
# check to say NO.
_pdrift="${_tmp}/parser-drift"; mkdir -p "${_pdrift}"
sed 's/(PASS|FAIL/(PASS|FAIL|BOGUS/' "${_matrix}" > "${_pdrift}/matrix.sh"
_alt_drifted="$(_verdict_alternation "${_pdrift}/matrix.sh")"
if [ -n "${_alt_drifted}" ] && [ "${_alt_drifted}" != "${_alt_support}" ]; then
    _ok "control: the drift check FAILS a parser changed on one side only (${_alt_drifted} vs ${_alt_support})"
else
    _bad "control BROKEN: a one-sided parser change was not detected (drifted='${_alt_drifted:-none}', support='${_alt_support}') — the arm above proves nothing"
fi

# ---------------------------------------------------------------------------
# ARM P4 — WHICH GATES MAY BE ADVISORY IS BOUNDED BY NAME.
#
# `_warn` (added by .github#477) is one line away from being a soft-fail switch
# for any gate in the suite: a gate that reports a real finding and does not
# reach `_FAILED`. That is the invisible pass, in the package whose entire job
# is preventing them — and nothing else in this package would notice a second
# one landing.
#
# So the allowlist lives here, and demoting another gate means editing this
# test and stating why. This does not stop a demotion; it stops a SILENT one.
#
# ⚠️ Note this counts `_warn` CALL SITES, not the word WARNING. gate-18 prints
# a long-standing advisory line that is not a demotion of its verdict.
# ---------------------------------------------------------------------------
# gate -> the reason it is permitted to be non-blocking.
_ADVISORY_ALLOWED_GATES="19"   # e2e-coverage — .github#477, temporary, owned.

_runner_src="${GF_PKG_ROOT}/scripts/run-hydra-gates.sh"
_warn_gates="$(grep -oE '^[[:space:]]*_warn[[:space:]]+[0-9]+' "${_runner_src}" \
    | grep -oE '[0-9]+$' | sort -un | tr '\n' ' ')"
_warn_gates="${_warn_gates% }"
if [ "${_warn_gates}" = "${_ADVISORY_ALLOWED_GATES}" ]; then
    _ok "the advisory (_warn) gates are exactly the allowlisted ones: ${_ADVISORY_ALLOWED_GATES:-none}"
else
    _bad "the set of gates demoted to advisory has changed without this test being told: found '${_warn_gates:-none}', allowed '${_ADVISORY_ALLOWED_GATES:-none}'. A gate that reports a real finding and does not block is a soft-fail; if the demotion is intended, add it here WITH its tracking issue."
fi

# POSITIVE CONTROL — the allowlist check must be able to say NO. Plant a second
# `_warn` call site in a COPY of the runner and require the same extraction to
# come back with a set the allowlist rejects.
_wdrift="${_tmp}/warn-drift"; mkdir -p "${_wdrift}"
{ cat "${_runner_src}"; printf '    _warn 7 "no-admin-idor" "pretend"\n'; } > "${_wdrift}/runner.sh"
_warn_drifted="$(grep -oE '^[[:space:]]*_warn[[:space:]]+[0-9]+' "${_wdrift}/runner.sh" \
    | grep -oE '[0-9]+$' | sort -un | tr '\n' ' ')"
_warn_drifted="${_warn_drifted% }"
if [ "${_warn_drifted}" != "${_ADVISORY_ALLOWED_GATES}" ] && [ -n "${_warn_drifted}" ]; then
    _ok "control: a second _warn call site is detected (${_warn_drifted}) — the allowlist can refuse"
else
    _bad "control BROKEN: planting a _warn on gate-7 produced '${_warn_drifted:-none}', which the allowlist would accept — ARM P4 proves nothing"
fi

echo
echo "== summary =="
echo "   assertions: ${_asserts}"
echo "   failures:   ${_failures}"
# 34 -> 37: ARM P3 gained its positive control, and ARM P4 (the advisory-gate
# allowlist) plus its control are new. The floor tracks the suite, otherwise a
# whole arm can be deleted and the run still reads green.
if [ "${_asserts}" -lt 37 ]; then
    echo "FAIL — only ${_asserts} assertions ran; this suite declares 37+. A short run is not a green run."
    exit 1
fi
[ "${_failures}" -eq 0 ] || exit 1
echo "ALL discarded-count and empty-delta controls PASSED"
exit 0
