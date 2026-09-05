#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# gate-109 (migration-version-bump) — acceptance over a REAL two-commit history.
#
# WHY THIS IS NOT A gate-acceptance/ BUNDLE
#
# gate-109 is a DELTA gate twice over: it needs a base to know what the change
# ADDED, and it needs that same base to read `<version>` as it stood before the
# change. The generic bundle format runs the runner against a plain directory
# with no git history, so a delta gate there can only ever report NOT
# APPLICABLE — configured, and covering nothing. gates 16, 98, 100, 101 and 108
# are covered this way for the same reason; all are registered in
# gate-acceptance/COVERED-ELSEWHERE.md.
#
# THE PLANTED ARM CARRIES TWO INDEPENDENTLY FATAL DEFECTS
#
# Both shapes Nextcloud gates on `<version>`, in one commit:
#
#   1. a core-discovered migration  (Version<n>Date<n> under lib/Migration/)
#   2. a registered repair step     (named in <post-migration>)
#
# ARM 5 then removes each one ON ITS OWN and asserts the arm STILL fails. Without
# that, a checker that had learned to see only migrations — the shape
# openregister's original script covered, and the shape that is NOT what bit
# dossiq — would pass ARM 1 for free and ship blind to the incident that
# prompted it.
#
# 🔴 WHAT ARM 3 EXISTS TO STOP RECURRING
#
# gate-98's first draft keyed its scope on `SCOPE_TO_DIFF`, which defaults to 0
# since full scope became the default, so its `else` fired on every ordinary run
# and it scanned the whole tree — reporting inherited debt as a failure of
# somebody's unrelated PR. Eight fleet apps carry stranded steps today; a
# full-tree gate-109 would redden every one of their branches on the day it
# landed. ARM 3 is the assertion that it does not.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
RUNNER="${SCRIPT_DIR}/../run-hydra-gates.sh"

_fail_n=0
_ok()  { printf '  ok   — %s\n' "$1"; }
_bad() { _fail_n=$((_fail_n + 1)); printf '  FAIL — %s\n' "$1"; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/gate109-scope.XXXXXXXX")"
trap 'rm -rf "${WORK}"' EXIT

APP="${WORK}/app"
mkdir -p "${APP}/lib/Migration" "${APP}/lib/Repair" "${APP}/appinfo"

BASE_VERSION="0.3.15-unstable.20260904192451"

_migration() {  # <class> -> a core-discovered migration
    cat <<PHP
<?php
declare(strict_types=1);
namespace OCA\\Fixture\\Migration;
use Closure;
use OCP\\DB\\ISchemaWrapper;
use OCP\\Migration\\IOutput;
use OCP\\Migration\\SimpleMigrationStep;
class $1 extends SimpleMigrationStep {
	public function changeSchema(IOutput \$output, Closure \$schemaClosure, array \$options): ?ISchemaWrapper {
		return null;
	}
}
PHP
}

_step() {  # <class> -> a real IRepairStep under lib/Repair/
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

# info.xml with a chosen <version>. Every fixture registers the same two repair
# steps under <post-migration>, plus one under <install> ONLY — the near-miss
# ARM 4 relies on.
_info() {  # <version>
    cat <<XML
<?xml version="1.0"?>
<info>
    <id>fixture</id>
    <version>$1</version>
    <repair-steps>
        <post-migration>
            <step>OCA\\Fixture\\Repair\\AlreadyShipped</step>
            <step>OCA\\Fixture\\Repair\\RealignVocabulary</step>
        </post-migration>
        <install>
            <step>OCA\\Fixture\\Repair\\InstallOnly</step>
        </install>
    </repair-steps>
</info>
XML
}

cd "${APP}" || exit 1
git init --quiet .
git config user.email fixture@example.invalid
git config user.name Fixture

# ── COMMIT 1: the baseline. It ALREADY ships a migration and a repair step, so
#    every branch below carries inherited history the gate must not re-report.
_migration Version1Date20260101000000 > lib/Migration/Version1Date20260101000000.php
_step AlreadyShipped                  > lib/Repair/AlreadyShipped.php
_info "${BASE_VERSION}"               > appinfo/info.xml
echo "x" > README.md
git add -A && git commit --quiet -m "baseline"
git branch -M base

# ── planted: BOTH defects, no version bump.
git checkout --quiet -b planted
_migration Version9Date20260906090000 > lib/Migration/Version9Date20260906090000.php
_step RealignVocabulary               > lib/Repair/RealignVocabulary.php
git add -A && git commit --quiet -m "add a migration and a repair step, forget the version"

# ── clean: the SAME two additions, WITH the bump.
git checkout --quiet base
git checkout --quiet -b clean
_migration Version9Date20260906090000 > lib/Migration/Version9Date20260906090000.php
_step RealignVocabulary               > lib/Repair/RealignVocabulary.php
_info "0.3.16-unstable.20260906090000" > appinfo/info.xml
git add -A && git commit --quiet -m "add both, and move the version"

# ── unrelated: touches nothing under lib/Migration or lib/Repair.
git checkout --quiet base
git checkout --quiet -b unrelated
echo "y" >> README.md
git add -A && git commit --quiet -m "an unrelated change"

# ── near-miss: three additions Nextcloud will NOT run on upgrade, no bump.
git checkout --quiet base
git checkout --quiet -b near-miss
cat > lib/Migration/ReadsLegacyRows.php <<'PHP'
<?php
declare(strict_types=1);
namespace OCA\Fixture\Migration;
trait ReadsLegacyRows { public function legacy(): array { return []; } }
PHP
cat > lib/Repair/VocabularyTable.php <<'PHP'
<?php
declare(strict_types=1);
namespace OCA\Fixture\Repair;
final class VocabularyTable { public const ROWS = []; }
PHP
_step InstallOnly > lib/Repair/InstallOnly.php
git add -A && git commit --quiet -m "a trait, a helper, and an install-only step"

# ── timestamp-only: the release bot's own shape of a bump.
git checkout --quiet base
git checkout --quiet -b timestamp-only
_step RealignVocabulary > lib/Repair/RealignVocabulary.php
_info "0.3.15-unstable.20260905000000" > appinfo/info.xml
git add -A && git commit --quiet -m "add a step, bump only the timestamp"

# ── only-migration / only-step: ARM 5's single-defect probes.
git checkout --quiet base
git checkout --quiet -b only-migration
_migration Version9Date20260906090000 > lib/Migration/Version9Date20260906090000.php
git add -A && git commit --quiet -m "just the migration, no bump"

git checkout --quiet base
git checkout --quiet -b only-step
_step RealignVocabulary > lib/Repair/RealignVocabulary.php
git add -A && git commit --quiet -m "just the repair step, no bump"

# The log directory is DERIVED from the branch name, not assigned inside the
# helper. `_v="$(_verdict planted --full)"` runs the helper in a SUBSHELL, so a
# variable it sets is gone by the time the assertion below reads it — the first
# draft did exactly that and three assertions reported "the gate never named its
# subject" about a gate that had named it correctly all along.
_logdir() { printf '%s/logs-%s' "${WORK}" "$1"; }
_findings_of() { printf '%s/hydra-gate-migration-version-bump.log' "$(_logdir "$1")"; }

_verdict() {  # <branch> [runner args...] -> the gate-109 line
    local _branch="$1"; shift
    git checkout --quiet "${_branch}"
    mkdir -p "$(_logdir "${_branch}")"
    HYDRA_GATE_LOG_DIR="$(_logdir "${_branch}")" bash "${RUNNER}" "$@" "${APP}" 2>&1 \
        | grep -E '\[gate-109\]' | head -1
}

echo "-- ARM 1: TWO independently fatal defects, neither delivered --"
_v="$(_verdict planted --base base)"
case "${_v}" in
    *FAIL*) _ok "gate-109 FAILs a migration and a repair step added with no version bump" ;;
    *)      _bad "expected FAIL on the planted branch, got: ${_v:-<no gate-109 line>}" ;;
esac
_findings="$(_findings_of planted)"
if grep -qF 'lib/Migration/Version9Date20260906090000.php' "${_findings}" 2>/dev/null; then
    _ok "and it NAMES the migration, not a bare count"
else
    _bad "the finding never names lib/Migration/Version9Date20260906090000.php — a bare count is not a finding"
fi
if grep -qF 'lib/Repair/RealignVocabulary.php' "${_findings}" 2>/dev/null; then
    _ok "and it NAMES the repair step — the dossiq shape, which a migration-only checker misses"
else
    _bad "the finding never names lib/Repair/RealignVocabulary.php — this is the dossiq shape and it must not be invisible"
fi
if grep -qF "${BASE_VERSION}" "${_findings}" 2>/dev/null; then
    _ok "and it quotes the version it compared against"
else
    _bad "the finding does not say which version it compared against"
fi

echo "-- ARM 2: the SAME two additions, with the bump, are clean --"
_v="$(_verdict clean --base base)"
case "${_v}" in
    *PASS*) _ok "gate-109 PASSes once <version> moves" ;;
    *)      _bad "expected PASS on the clean branch, got: ${_v:-<no gate-109 line>}" ;;
esac

echo "-- ARM 3: 🔴 INHERITED DEBT IS NOT THIS PR'S PROBLEM --"
# Eight fleet apps carry stranded steps today. A full-tree gate reddens every
# branch they cut; a delta gate reddens none of them.
_v="$(_verdict unrelated --base base)"
case "${_v}" in
    *FAIL*) _bad "gate-109 reported a finding on a commit touching no migration or repair step — this is the full-tree regression the suite exists to catch: ${_v}" ;;
    *)      _ok "a commit touching neither directory reports no finding" ;;
esac
case "${_v}" in
    *NOT\ APPLICABLE*) _ok "and it says it judged nothing, rather than claiming a pass" ;;
    *)                 _bad "expected NOT APPLICABLE on a commit with nothing in scope, got: ${_v}" ;;
esac

echo "-- ARM 4: near misses — a trait, an unregistered helper, an <install>-only step --"
# All three are added under the watched directories with NO version bump. None
# of them runs on upgrade, so demanding a bump for any of them is a finding its
# author cannot act on. This is the anti-widening arm.
_v="$(_verdict near-miss --base base)"
case "${_v}" in
    *FAIL*) _bad "gate-109 demanded a version bump for a trait, a helper or an <install>-only step — none of which Nextcloud runs on upgrade: ${_v}" ;;
    *)      _ok "a trait, an unregistered helper and an <install>-only step are not subjects" ;;
esac

echo "-- ARM 5: each planted defect is fatal ON ITS OWN --"
# Without this, a checker that sees only one of the two shapes passes ARM 1 for
# free. openregister's original script saw only migrations; dossiq's incident
# was a repair step.
_v="$(_verdict only-migration --base base)"
case "${_v}" in
    *FAIL*) _ok "the migration alone still FAILs" ;;
    *)      _bad "a lone unbumped migration did not fail: ${_v:-<no gate-109 line>}" ;;
esac
_v="$(_verdict only-step --base base)"
case "${_v}" in
    *FAIL*) _ok "the repair step alone still FAILs" ;;
    *)      _bad "a lone unbumped repair step did not fail — this is exactly the dossiq incident: ${_v:-<no gate-109 line>}" ;;
esac

echo "-- ARM 6: a timestamp-only move IS a bump, because Nextcloud thinks so --"
# 0.3.15-unstable.20260905000000 > 0.3.15-unstable.20260904192451 under PHP's
# version_compare, which is the comparison the server itself makes. The release
# bot produces exactly this shape, so a gate that refused it would fail every
# bot release.
_v="$(_verdict timestamp-only --base base)"
case "${_v}" in
    *PASS*) _ok "a timestamp-only move is accepted" ;;
    *)      _bad "a move Nextcloud would act on was rejected: ${_v:-<no gate-109 line>}" ;;
esac

echo "-- ARM 7: with NO base, the gate says nothing — it never says PASS --"
# The whole point of the gate is that a silent pass is the failure being
# removed. A run that cannot see a base has no verdict to give.
_v="$(_verdict planted --full)"
case "${_v}" in
    *PASS*) _bad "gate-109 PASSED with no delta base — it compared nothing and called it green: ${_v}" ;;
    *NOT\ APPLICABLE*|*SKIPPED*) _ok "no base resolves to a skip that says so, not to a pass" ;;
    *FAIL*) _ok "verdict without a base: ${_v}" ;;
    *)      _bad "no gate-109 line at all on a run with no base" ;;
esac

echo
if [ "${_fail_n}" -eq 0 ]; then
    echo "test_gate109_migration_version_bump_scope.sh: ALL PASS"
    exit 0
fi
echo "test_gate109_migration_version_bump_scope.sh: ${_fail_n} FAILURE(S)"
exit 1
