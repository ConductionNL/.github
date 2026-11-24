#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
#
# gate-124 (perf-budget) through the real runner.
#
#   ARM 1  an app with no tests/performance/budget.json: FAIL, naming the file
#   ARM 2  an app with a budget file, the spec and Newman on the shared
#          workflow: PASS with the census line
#   ARM 3  an app whose workflow runs `newman run` itself: FAIL
#   ARM 4  a repository without appinfo/info.xml: NOT APPLICABLE
#
# The rule-by-rule arms (exceptions, the app id, the injected Newman test and
# the time table) are in test_check_perf_budget.py.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
RUNNER="${SCRIPT_DIR}/../run-hydra-gates.sh"

_fail_n=0
_ok()  { printf '  ok:   %s\n' "$1"; }
_bad() { _fail_n=$((_fail_n + 1)); printf '  FAIL: %s\n' "$1"; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/gate124.XXXXXXXX")"
trap 'rm -rf "${WORK}"' EXIT

_app() {  # <dir>: a wired fixture app
    mkdir -p "$1/appinfo" "$1/tests/performance" "$1/tests/e2e" "$1/tests/integration" "$1/.github/workflows"
    printf '<?xml version="1.0"?>\n<info>\n    <id>fixture</id>\n</info>\n' > "$1/appinfo/info.xml"
    printf '{"app": "fixture", "pages": [{"name": "Home", "path": "/index.php/apps/fixture/"}]}\n' \
        > "$1/tests/performance/budget.json"
    printf "import { test } from '@playwright/test'\nimport { definePerformanceSpec } from '@conduction/nextcloud-vue/testing/performance'\ndefinePerformanceSpec(test)\n" \
        > "$1/tests/e2e/performance.spec.ts"
    printf '{"info": {"name": "f"}, "item": []}\n' > "$1/tests/integration/f.postman_collection.json"
    printf 'jobs:\n  quality:\n    uses: ConductionNL/.github/.github/workflows/quality.yml@main\n    with:\n      enable-newman: true\n' \
        > "$1/.github/workflows/code-quality.yml"
}

_run() {  # <dir>
    mkdir -p "${WORK}/logs-$(basename "$1")"
    (cd "$1" && HYDRA_GATE_LOG_DIR="${WORK}/logs-$(basename "$1")" bash "${RUNNER}" . 2>&1)
}

_verdict() {
    printf '%s\n' "$1" | grep -E '^\[gate-124\] perf-budget: (PASS|FAIL|WARNING|SKIPPED|NOT APPLICABLE)' | head -1
}

echo "-- ARM 1: no budget file: FAIL --"
_app "${WORK}/nobudget"
rm "${WORK}/nobudget/tests/performance/budget.json"
_out="$(_run "${WORK}/nobudget")"
case "$(_verdict "${_out}")" in
    *FAIL*) _ok "an app without a budget file fails" ;;
    *)      _bad "expected FAIL, got: $(_verdict "${_out}")" ;;
esac
if printf '%s\n' "${_out}" | grep -q '^  tests/performance/budget.json is missing'; then
    _ok "the failure names the missing file"
else
    _bad "the failure does not name tests/performance/budget.json"
fi

echo "-- ARM 2: a wired app: PASS --"
_app "${WORK}/wired"
_out="$(_run "${WORK}/wired")"
case "$(_verdict "${_out}")" in
    *PASS*) _ok "a wired app passes" ;;
    *)      _bad "expected PASS, got: $(_verdict "${_out}")" ;;
esac
if printf '%s\n' "${_out}" | grep -q '^\[gate-124\] perf-budget: checked 1 page(s)'; then
    _ok "the census line reaches the run's output"
else
    _bad "no census line in the PASS output"
fi

echo "-- ARM 3: a workflow that runs newman itself: FAIL --"
_app "${WORK}/direct"
printf 'jobs:\n  api:\n    runs-on: ubuntu-latest\n    steps:\n      - run: npx newman run tests/integration/f.postman_collection.json\n' \
    > "${WORK}/direct/.github/workflows/api.yml"
_out="$(_run "${WORK}/direct")"
case "$(_verdict "${_out}")" in
    *FAIL*) _ok "a direct newman run fails" ;;
    *)      _bad "expected FAIL, got: $(_verdict "${_out}")" ;;
esac

echo "-- ARM 4: not an app: NOT APPLICABLE --"
mkdir -p "${WORK}/notapp"
case "$(_verdict "$(_run "${WORK}/notapp")")" in
    *"NOT APPLICABLE"*) _ok "a repository without appinfo/info.xml is not applicable" ;;
    *)                  _bad "expected NOT APPLICABLE, got: $(_verdict "$(_run "${WORK}/notapp")")" ;;
esac

if [ "${_fail_n}" -gt 0 ]; then
    echo "gate-124 perf-budget: ${_fail_n} assertion(s) failed"
    exit 1
fi
echo "gate-124 perf-budget: all assertions passed"
