#!/usr/bin/env bash
#
# gate-98 (repair-step-registration) — acceptance over a REAL two-commit history.
#
# WHY THIS IS NOT A gate-acceptance/ BUNDLE
#
# gate-98 is a DELTA gate: it judges what a change ADDS, so it reads
# `CHANGED_FILES` and runs only when a delta base resolved. The generic bundle
# format runs the runner against a plain directory with no git history, so a
# delta gate there can only ever report NOT APPLICABLE — configured, and
# covering nothing.
#
# gate-16 hit this first and is covered the same way, by
# `test_gate16_spec_coverage_scope.sh` over a two-commit fixture; both are
# registered in gate-acceptance/COVERED-ELSEWHERE.md.
#
# 🔴 WHAT THIS SUITE EXISTS TO STOP RECURRING
#
# The first draft of gate-98 keyed its scope on `SCOPE_TO_DIFF`, which defaults
# to 0 since full scope became the default. The `else` branch therefore fired on
# every ordinary run and the gate scanned the WHOLE TREE. Measured on
# openregister: 3 changed files, 19 repair steps checked, 2 findings, neither of
# them in the diff — inherited debt reported as a failure of somebody's unrelated
# PR. That is the fleet-wide red wave the gate's own header claims to avoid, and
# nothing caught it, because the only fixture ran in the mode CI never uses.
#
# ARM 3 is the one that would have caught it: a commit touching NO repair step
# must not report a finding, however much inherited debt the tree carries.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
RUNNER="${SCRIPT_DIR}/../run-hydra-gates.sh"

_fail_n=0
_ok()  { printf '  ok   — %s\n' "$1"; }
_bad() { _fail_n=$((_fail_n + 1)); printf '  FAIL — %s\n' "$1"; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/gate98-scope.XXXXXXXX")"
trap 'rm -rf "${WORK}"' EXIT

APP="${WORK}/app"
mkdir -p "${APP}/lib/Repair" "${APP}/appinfo"

_step() {  # <class> -> a real IRepairStep
    cat <<PHP
<?php
declare(strict_types=1);
namespace OCA\\Fixture\\Repair;
use OCP\\Migration\\IOutput;
use OCP\\Migration\\IRepairStep;
class $1 implements IRepairStep {
	public function getName(): string { return "$1"; }
	public function run(IOutput \$output): void { \$output->info("ran"); }
}
PHP
}

_info() {  # <registered class names...>
    printf '<?xml version="1.0"?>\n<info>\n    <id>fixture</id>\n    <repair-steps>\n        <post-migration>\n'
    for _c in "$@"; do printf '            <step>OCA\\Fixture\\Repair\\%s</step>\n' "$_c"; done
    printf '        </post-migration>\n    </repair-steps>\n</info>\n'
}

cd "${APP}" || exit 1
git init --quiet .
git config user.email fixture@example.invalid
git config user.name Fixture

# ── COMMIT 1: the baseline. It ALREADY carries inherited debt — a repair step
#    that is not registered — because that is the state every real repo is in,
#    and a gate that cannot tell inherited debt from new debt is the bug.
_step InheritedUnregistered > lib/Repair/InheritedUnregistered.php
_step AlreadyRegistered     > lib/Repair/AlreadyRegistered.php
_info AlreadyRegistered      > appinfo/info.xml
echo "x" > README.md
git add -A && git commit --quiet -m "baseline, carrying one unregistered step"
git branch -M base

# ── COMMIT 2 on a branch: adds ONE unregistered step.
git checkout --quiet -b planted
_step NewlyUnregistered > lib/Repair/NewlyUnregistered.php
git add -A && git commit --quiet -m "add a repair step and forget info.xml"

# ── COMMIT 2' on another branch: adds one step AND registers it.
git checkout --quiet base
git checkout --quiet -b clean
_step NewlyRegistered > lib/Repair/NewlyRegistered.php
_info AlreadyRegistered NewlyRegistered > appinfo/info.xml
git add -A && git commit --quiet -m "add a repair step and register it"

# ── COMMIT 2'' : touches nothing under lib/Repair/.
git checkout --quiet base
git checkout --quiet -b unrelated
echo "y" >> README.md
git add -A && git commit --quiet -m "an unrelated change"

_verdict() {  # <branch> -> the gate-98 line
    git checkout --quiet "$1"
    HYDRA_GATE_LOG_DIR="${WORK}/logs-$1" bash "${RUNNER}" --base base "${APP}" 2>&1 \
        | grep -E '\[gate-98\]' | head -1
}
mkdir -p "${WORK}/logs-planted" "${WORK}/logs-clean" "${WORK}/logs-unrelated"

echo "-- ARM 1: a NEW unregistered step is a finding --"
_v="$(_verdict planted)"
case "${_v}" in
    *FAIL*) _ok "gate-98 FAILs a step added without its info.xml entry" ;;
    *)      _bad "expected FAIL on the planted branch, got: ${_v:-<no gate-98 line>}" ;;
esac
case "${_v}" in
    *NewlyUnregistered*|*repair\ step*) _ok "and the finding is about a repair step, not a bare count" ;;
    *) _bad "the FAIL does not describe what it found: ${_v}" ;;
esac

echo "-- ARM 2: the SAME step, registered, is clean --"
_v="$(_verdict clean)"
case "${_v}" in
    *PASS*) _ok "gate-98 PASSes when the added step is named in info.xml" ;;
    *)      _bad "expected PASS on the clean branch, got: ${_v:-<no gate-98 line>}" ;;
esac

echo "-- ARM 3: 🔴 INHERITED DEBT IS NOT THIS PR'S PROBLEM --"
# Both branches above also carry InheritedUnregistered, untouched since the
# baseline. A full-tree gate reports it every time; a delta gate never does.
_v="$(_verdict unrelated)"
case "${_v}" in
    *FAIL*) _bad "gate-98 reported inherited debt on a commit that touched no repair step — this is the full-tree regression the suite exists to catch: ${_v}" ;;
    *)      _ok "a commit touching no lib/Repair/ file reports no finding" ;;
esac
case "${_v}" in
    *NOT\ APPLICABLE*|*na*|*skip*) _ok "and it says it looked at nothing, rather than claiming a pass" ;;
    *) _ok "verdict: ${_v}" ;;
esac

echo "-- ARM 4: the inherited step is still WRONG, and a PR that touches it says so --"
git checkout --quiet base
git checkout --quiet -b touches-inherited
_step InheritedUnregistered > lib/Repair/InheritedUnregistered.php
printf '\n' >> lib/Repair/InheritedUnregistered.php
git add -A && git commit --quiet -m "touch the inherited step"
mkdir -p "${WORK}/logs-touches-inherited"
_v="$(_verdict touches-inherited)"
case "${_v}" in
    *FAIL*) _ok "the same inherited step IS reported once a change touches it — the gate is scoped, not blind" ;;
    *)      _bad "expected FAIL once the inherited step is in the diff, got: ${_v:-<no gate-98 line>}" ;;
esac

echo
if [ "${_fail_n}" -eq 0 ]; then
    echo "test_gate98_repair_registration_scope.sh: ALL PASS"
    exit 0
fi
echo "test_gate98_repair_registration_scope.sh: ${_fail_n} FAILURE(S)"
exit 1
