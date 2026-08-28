#!/usr/bin/env bash
#
# gate-101 (demo-data-coverage) — acceptance over a REAL two-commit history.
#
# 🔴 RENUMBERED 99 -> 101. `manifest-l10n-coverage` also claimed 99, and both
# blocks called `_pass 99` / `_fail 99` with different names — so one gate's
# verdict overwrote the other's and this suite read the l10n gate's NOT
# APPLICABLE line while asserting on demo-data coverage. The number is part of
# the gate's identity; two gates cannot share one.
#
# A DELTA gate cannot be covered by a gate-acceptance/ bundle: that format runs
# the runner against a plain directory with no git history, so the gate can only
# ever report NOT APPLICABLE there — configured, and covering nothing. Same
# reason gate-16 and gate-98 are covered by dedicated suites and listed in
# COVERED-ELSEWHERE.md.
#
# 🔴 ARM 3 IS THE LOAD-BEARING ONE. The baseline deliberately ships a schema
# with NO demo data, because that is the state twenty of twenty-one fleet apps
# are in. A commit touching no descriptor must report nothing, however much
# inherited debt the tree carries — otherwise this gate reddens the whole fleet
# on the day it ships, which is precisely what gate-98 did.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
RUNNER="${SCRIPT_DIR}/../run-hydra-gates.sh"

_fail_n=0
_ok()  { printf '  ok   — %s\n' "$1"; }
_bad() { _fail_n=$((_fail_n + 1)); printf '  FAIL — %s\n' "$1"; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/gate99-scope.XXXXXXXX")"
trap 'rm -rf "${WORK}"' EXIT
APP="${WORK}/app"
mkdir -p "${APP}/lib/Settings"

_descriptor() {  # <register> <schema> -> a real (non-mock) descriptor
    cat <<JSON
{
  "openapi": "3.0.0",
  "info": {"title": "Fixture", "version": "1.0.0"},
  "x-openregister": {"type": "core", "app": "app"},
  "components": {
    "registers": {"$1": {"slug": "$1", "title": "$1", "version": "1.0.0"}},
    "schemas": {"$2": {"type": "object", "required": ["name"],
      "properties": {"name": {"type": "string"},
                     "status": {"type": "string", "enum": ["open", "closed"]}}}}
  }
}
JSON
}

_mock() {  # <register> <schema> <count> -> a mock descriptor with N valid objects
    python3 - "$1" "$2" "$3" <<'PY'
import json, sys
reg, sch, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
objs = [{"@self": {"register": reg, "schema": sch, "slug": f"{sch}-{i}"},
         "name": f"Voorbeeld {i}", "status": ["open", "closed"][i % 2]} for i in range(n)]
print(json.dumps({
    "openapi": "3.0.0", "info": {"title": "demo", "version": "1.0.0"},
    "x-openregister": {"type": "mock", "app": "app"},
    "components": {"registers": {reg: {"slug": reg}},
                   "schemas": {sch: {"type": "object"}}, "objects": objs}}, indent=2))
PY
}

cd "${APP}" || exit 1
git init --quiet .
git config user.email fixture@example.invalid
git config user.name Fixture

# COMMIT 1 — baseline carrying INHERITED debt: a schema with no demo data.
_descriptor inherited widget > lib/Settings/inherited_register.json
echo "x" > README.md
git add -A && git commit --quiet -m "baseline, one schema with no demo data"
git branch -M base

# planted: adds a schema, ships no demo data for it
git checkout --quiet -b planted
_descriptor added gadget > lib/Settings/added_register.json
git add -A && git commit --quiet -m "add a schema, forget its demo data"

# clean: adds the same schema WITH three valid demo objects
git checkout --quiet base && git checkout --quiet -b clean
_descriptor added gadget > lib/Settings/added_register.json
_mock added gadget 3 > lib/Settings/app_mock_register.json
git add -A && git commit --quiet -m "add a schema and its demo data"

# short: three objects present but one is INVALID (status outside its enum)
git checkout --quiet base && git checkout --quiet -b invalid
_descriptor added gadget > lib/Settings/added_register.json
_mock added gadget 3 > lib/Settings/app_mock_register.json
python3 - <<'PY'
import json
p = "lib/Settings/app_mock_register.json"
d = json.load(open(p))
d["components"]["objects"][0]["status"] = "not-in-the-enum"
json.dump(d, open(p, "w"), indent=2)
PY
git add -A && git commit --quiet -m "add a schema with demo data that fails its own schema"

# unrelated: touches no descriptor at all
git checkout --quiet base && git checkout --quiet -b unrelated
echo "y" >> README.md
git add -A && git commit --quiet -m "an unrelated change"

_verdict() {
    git checkout --quiet "$1"
    mkdir -p "${WORK}/logs-$1"
    HYDRA_GATE_LOG_DIR="${WORK}/logs-$1" bash "${RUNNER}" --base base "${APP}" 2>&1 \
        | grep -E '\[gate-101\]' | head -1
}

echo "-- ARM 1: a NEW schema without demo data is a finding --"
_v="$(_verdict planted)"
case "${_v}" in
    *FAIL*) _ok "gate-101 FAILs a schema added without demo data" ;;
    *)      _bad "expected FAIL on planted, got: ${_v:-<no gate-101 line>}" ;;
esac

echo "-- ARM 2: the same schema WITH three valid objects is clean --"
_v="$(_verdict clean)"
case "${_v}" in
    *PASS*) _ok "gate-101 PASSes when the added schema has its demo data" ;;
    *)      _bad "expected PASS on clean, got: ${_v:-<no gate-101 line>}" ;;
esac

echo "-- ARM 3: 🔴 INHERITED DEBT IS NOT THIS PR'S PROBLEM --"
_v="$(_verdict unrelated)"
case "${_v}" in
    *FAIL*) _bad "gate-101 reported the baseline's uncovered schema on a commit touching no descriptor — this is the fleet-wide red wave the suite exists to catch: ${_v}" ;;
    *)      _ok "a commit touching no descriptor reports no finding" ;;
esac

echo "-- ARM 4: COUNTING IS NOT CHECKING — three objects, one invalid, still fails --"
_v="$(_verdict invalid)"
case "${_v}" in
    *FAIL*) _ok "gate-101 FAILs when the count is met but an object breaks its own schema" ;;
    *)      _bad "expected FAIL on invalid: demo data that fails its schema fails at import, and a gate that only counts would have passed this. Got: ${_v:-<no gate-101 line>}" ;;
esac

echo
if [ "${_fail_n}" -eq 0 ]; then
    echo "test_gate101_demo_data_scope.sh: ALL PASS"
    exit 0
fi
echo "test_gate101_demo_data_scope.sh: ${_fail_n} FAILURE(S)"
exit 1
