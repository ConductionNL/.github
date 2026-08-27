#!/usr/bin/env bash
#
# gate-100 (setup-demo-data-first) — acceptance over a REAL two-commit history.
#
# A delta gate cannot be covered by a gate-acceptance/ bundle: that format has no
# git, so the gate could only ever report NOT APPLICABLE there. Same reason
# gate-16, gate-98 and gate-99 are covered by dedicated suites and listed in
# COVERED-ELSEWHERE.md.
#
# 🔴 ARM 3 IS LOAD-BEARING. Twenty of thirty fleet manifests declare no `setup`
# block at all. If this gate failed them, it would block every unrelated
# manifest edit in the fleet on the day it shipped — the exact wave gate-98
# produced a day earlier. Adoption is a rollout; this gate holds the line on the
# apps that HAVE declared setup.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
RUNNER="${SCRIPT_DIR}/../run-hydra-gates.sh"

_fail_n=0
_ok()  { printf '  ok   — %s\n' "$1"; }
_bad() { _fail_n=$((_fail_n + 1)); printf '  FAIL — %s\n' "$1"; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/gate100-scope.XXXXXXXX")"
trap 'rm -rf "${WORK}"' EXIT
APP="${WORK}/app"
mkdir -p "${APP}/src"

_manifest() {  # <first-step-id | "none">
    if [ "$1" = "none" ]; then
        printf '{"id":"app","name":"App"}\n'
        return
    fi
    cat <<JSON
{
  "id": "app",
  "name": "App",
  "setup": {
    "steps": [
      {"id": "$1", "type": "info", "title": "First"},
      {"id": "storage", "type": "config-fields", "title": "Storage"}
    ]
  }
}
JSON
}

cd "${APP}" || exit 1
git init --quiet .
git config user.email fixture@example.invalid
git config user.name Fixture

# COMMIT 1 — baseline: a manifest with NO setup block, which is what twenty of
# thirty fleet manifests look like today.
_manifest none > src/manifest.json
echo "x" > README.md
git add -A && git commit --quiet -m "baseline, manifest with no setup"
git branch -M base

git checkout --quiet -b planted
_manifest welcome > src/manifest.json
git add -A && git commit --quiet -m "declare setup opening with welcome"

git checkout --quiet base && git checkout --quiet -b clean
_manifest demo-data > src/manifest.json
git add -A && git commit --quiet -m "declare setup opening with demo-data"

git checkout --quiet base && git checkout --quiet -b nosetup
printf '{"id":"app","name":"App","version":"1.0.1"}\n' > src/manifest.json
git add -A && git commit --quiet -m "edit the manifest, still no setup block"

git checkout --quiet base && git checkout --quiet -b unrelated
echo "y" >> README.md
git add -A && git commit --quiet -m "an unrelated change"

_verdict() {
    git checkout --quiet "$1"
    mkdir -p "${WORK}/logs-$1"
    HYDRA_GATE_LOG_DIR="${WORK}/logs-$1" bash "${RUNNER}" --base base "${APP}" 2>&1 \
        | grep -E '\[gate-100\]' | head -1
}

echo "-- ARM 1: setup that opens with welcome is a finding --"
_v="$(_verdict planted)"
case "${_v}" in
    *FAIL*) _ok "gate-100 FAILs a setup whose first step is not demo-data" ;;
    *)      _bad "expected FAIL on planted, got: ${_v:-<no gate-100 line>}" ;;
esac

echo "-- ARM 2: the same setup opening with demo-data is clean --"
_v="$(_verdict clean)"
case "${_v}" in
    *PASS*) _ok "gate-100 PASSes when the first step is demo-data" ;;
    *)      _bad "expected PASS on clean, got: ${_v:-<no gate-100 line>}" ;;
esac

echo "-- ARM 3: 🔴 AN APP WITH NO SETUP IS NOT THIS GATE'S BUSINESS --"
_v="$(_verdict nosetup)"
case "${_v}" in
    *FAIL*) _bad "gate-100 failed a manifest edit on an app that declares no setup — twenty of thirty fleet manifests are in that state, so this would block unrelated work fleet-wide: ${_v}" ;;
    *)      _ok "editing a manifest with no setup block reports no finding" ;;
esac

echo "-- ARM 4: a commit touching no manifest reports nothing --"
_v="$(_verdict unrelated)"
case "${_v}" in
    *FAIL*) _bad "gate-100 reported on a commit touching no manifest: ${_v}" ;;
    *)      _ok "a commit touching no manifest reports no finding" ;;
esac

echo
if [ "${_fail_n}" -eq 0 ]; then
    echo "test_gate100_setup_demo_first_scope.sh: ALL PASS"
    exit 0
fi
echo "test_gate100_setup_demo_first_scope.sh: ${_fail_n} FAILURE(S)"
exit 1
