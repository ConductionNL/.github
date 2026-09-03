#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# gate-108 (shipped-object-properties) — acceptance over a REAL two-commit history.
#
# A DELTA gate cannot be covered by a `gate-acceptance/` bundle: that format runs
# the runner against a plain directory with no git history, so the gate can only
# ever report NOT APPLICABLE there — configured, and covering nothing. Same
# reason gates 16, 98, 100 and 101 are covered by dedicated suites and listed in
# COVERED-ELSEWHERE.md.
#
# 🔴 THE PLANTED ARM CARRIES TWO INDEPENDENTLY FATAL DEFECTS, IN TWO DIFFERENT
# CONTAINER SHAPES, so a weakened gate cannot pass it by accident:
#
#   1. a `register.d` FRAGMENT ships an object with `bronEntiteit` where the
#      schema declares `sourceEntity` — the dossiq#1779 vocabulary drift, in a
#      file gate-101 cannot open at all (it reads only `type: mock`);
#   2. the MOCK descriptor ships an object with `catalog` — the dossiq#1782
#      shape, in the one file gate-101 does read and passed anyway, because
#      JSON Schema is open-world.
#
# ARM 5 removes each defect on its own and asserts the arm STILL fails. Without
# that, "the planted arm fails" is satisfied by a gate that only ever noticed
# one of them.
#
# 🔴 THE CLEAN ARM IS NOT MERELY DEFECT-FREE. It keeps seven near-misses a
# widened gate turns red, and every one is a shape the fleet actually ships:
#
#   * an object carrying top-level `id` and `uuid` — envelope. OpenRegister's
#     own `ImportService` exempts exactly `''`, `id`, `uuid`, `@*` and `_*`
#     when it reports what an import threw away.
#   * an object carrying an undeclared `name` and `description` —
#     `MetadataHydrationHandler` copies these into metadata columns whether the
#     schema declares them or not, so the value is not lost. 1,431 and 1,333
#     fleet occurrences; reporting them would drown every real finding.
#   * an object carrying `_note` — an authoring comment, `_`-prefixed.
#   * an object referencing its schema by a SLUG that differs from the
#     definition key. hermiq differs on 30 of 30 keys, buildiq on 15 of 16; a
#     checker keyed on one alone reports every property of every object.
#   * a property declared ONLY by a later `register.d` fragment that extends the
#     schema. shillinq defines `ARInvoice` across seventeen fragments.
#   * an object in the TOP-LEVEL `objects` list (shillinq's shape, 56 files)
#     and one under `x-openregister.seedData.objects` (decidiq's profiles).
#   * an object naming a schema this app does not define — NOTE, never a
#     finding, because every property would read as undeclared.
#
# ARM 3 is the fleet-trap arm: a commit touching no register JSON must report
# nothing, however much inherited debt the tree carries. ARM 4 is the one the
# incident demands: #1779 REMOVED a schema property and #1780 added the only
# object carrying it, a minute apart and in different PRs — so a commit that
# touches only the SCHEMA must still be judged against the objects relying on it.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
RUNNER="${SCRIPT_DIR}/../run-hydra-gates.sh"

_fail_n=0
_ok()  { printf '  ok   — %s\n' "$1"; }
_bad() { _fail_n=$((_fail_n + 1)); printf '  FAIL — %s\n' "$1"; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/gate108-scope.XXXXXXXX")"
trap 'rm -rf "${WORK}"' EXIT
APP="${WORK}/app"
mkdir -p "${APP}/lib/Settings/register.d" "${APP}/appinfo"

cat > "${APP}/appinfo/info.xml" <<'XML'
<?xml version="1.0"?>
<info xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <id>fixture</id>
    <name>Fixture</name>
    <version>1.0.0</version>
</info>
XML

# --- the base register: two schemas, one keyed differently from its slug -----
_base_register() {  # <sourceEntityDeclared: yes|no>
    python3 - "$1" <<'PY'
import json, sys
declare_source = sys.argv[1] == "yes"
message_props = {
    "messageKind": {"type": "string"},
    "referenceNumber": {"type": "string"},
}
if declare_source:
    message_props["sourceEntity"] = {"type": "string"}
print(json.dumps({
    "openapi": "3.0.0",
    "info": {"title": "Fixture", "version": "1.0.0"},
    "x-openregister": {"type": "application", "app": "fixture"},
    "components": {
        "registers": {"fixture": {"slug": "fixture", "title": "Fixture", "version": "1.0.0",
                                  "schemas": ["StufMessage", "documentType"]}},
        "schemas": {
            # NEAR MISS: the definition KEY is PascalCase, the SLUG is not.
            # The objects below reference the slug, which is what the importer
            # resolves. A checker keyed on the key alone reports every one.
            "StufMessage": {"type": "object", "slug": "stuf_message",
                            "properties": message_props},
            "documentType": {"type": "object", "slug": "documentType",
                             "properties": {"mimeType": {"type": "string"}}},
        },
    },
}, indent=2))
PY
}

# --- a register.d fragment that EXTENDS StufMessage --------------------------
_fragment_extends() {
    cat <<'JSON'
{
  "$comment": "NEAR MISS: `durationMs` is declared ONLY here. shillinq defines ARInvoice across seventeen fragments; a checker reading one file reports the other sixteen's properties.",
  "components": { "schemas": { "StufMessage": { "properties": { "durationMs": { "type": "integer" } } } } }
}
JSON
}

# --- a register.d fragment shipping OBJECTS (gate-101 cannot see this file) --
_fragment_objects() {  # <key-for-the-source-entity>
    python3 - "$1" <<'PY'
import json, sys
key = sys.argv[1]
print(json.dumps({
    "components": {"objects": [
        {"@self": {"register": "fixture", "schema": "stuf_message", "slug": "msg-1"},
         "messageKind": "Lk01", "referenceNumber": "REF-1", "durationMs": 12, key: "zaak"},
        # NEAR MISS: envelope keys and metadata-bearing keys, none declared.
        {"@self": {"register": "fixture", "schema": "stuf_message", "slug": "msg-2"},
         "id": "b3c1a000-0000-4000-a000-00000000f001",
         "uuid": "b3c1a000-0000-4000-a000-00000000f001",
         "name": "Bericht twee", "description": "Een bericht", "slug": "msg-2",
         "_note": "an authoring comment, never data",
         "messageKind": "Lk02"},
    ]}
}, indent=2))
PY
}

# --- shillinq's two other container shapes, plus an unresolvable reference ---
_odd_containers() {
    cat <<'JSON'
{
  "$comment": "NEAR MISS: the top-level `objects` list (56 shillinq files) and an object naming a schema this app does not define.",
  "objects": [
    { "@self": { "register": "fixture", "schema": "documentType", "slug": "doc-1" }, "mimeType": "application/pdf" },
    { "@self": { "register": "elsewhere", "schema": "notMine", "slug": "foreign-1" }, "whatever": "unjudgeable" }
  ]
}
JSON
}

_seed_data() {
    cat <<'JSON'
{
  "$comment": "NEAR MISS: x-openregister.seedData.objects, a schema-slug -> list map (decidiq's four profiles ship this).",
  "x-openregister": { "seedData": { "objects": { "documentType": [
    { "@self": { "register": "fixture", "schema": "documentType", "slug": "doc-seed-1" }, "mimeType": "text/plain" }
  ] } } }
}
JSON
}

_mock() {  # <extra-key-or-empty>
    python3 - "$1" <<'PY'
import json, sys
extra = sys.argv[1]
obj = {"@self": {"register": "fixture", "schema": "documentType", "slug": "doctype-1"},
       "mimeType": "application/pdf"}
if extra:
    obj[extra] = "00000000-0000-4000-8000-000000000000"
print(json.dumps({
    "openapi": "3.0.0", "info": {"title": "demo", "version": "1.0.0"},
    "x-openregister": {"type": "mock", "app": "fixture"},
    "components": {"registers": {"fixture": {"slug": "fixture"}},
                   "schemas": {"documentType": {"type": "object", "slug": "documentType"}},
                   "objects": [obj]}}, indent=2))
PY
}

_write_tree() {  # <source-key> <mock-extra> <declare-sourceEntity>
    _base_register "$3"        > lib/Settings/fixture_register.json
    _fragment_extends          > lib/Settings/register.d/10-extends.json
    _fragment_objects "$1"     > lib/Settings/register.d/20-objects.json
    _odd_containers            > lib/Settings/register.d/30-odd-containers.json
    _seed_data                 > lib/Settings/register.d/40-seed.json
    _mock "$2"                 > lib/Settings/fixture_mock_register.json
}

cd "${APP}" || exit 1
git init --quiet .
git config user.email fixture@example.invalid
git config user.name Fixture

# COMMIT 1 — the baseline, clean, and carrying every near-miss.
_write_tree sourceEntity "" yes
echo "x" > README.md
git add -A && git commit --quiet -m "baseline: every container shape, every near miss, no defect"
git branch -M base

# planted — TWO independently fatal defects.
git checkout --quiet -b planted
_write_tree bronEntiteit catalog yes
git add -A && git commit --quiet -m "drift a fragment object's key AND add an undeclared key to the mock"

# planted-fragment-only — defect 1 alone.
git checkout --quiet base && git checkout --quiet -b planted-fragment
_write_tree bronEntiteit "" yes
git add -A && git commit --quiet -m "only the fragment defect"

# planted-mock-only — defect 2 alone.
git checkout --quiet base && git checkout --quiet -b planted-mock
_write_tree sourceEntity catalog yes
git add -A && git commit --quiet -m "only the mock defect"

# clean — a real edit to the register JSON that introduces nothing.
git checkout --quiet base && git checkout --quiet -b clean
python3 - <<'PY'
import json
p = "lib/Settings/fixture_register.json"
d = json.load(open(p))
d["components"]["schemas"]["documentType"]["properties"]["fileSize"] = {"type": "integer"}
json.dump(d, open(p, "w"), indent=2)
PY
git add -A && git commit --quiet -m "declare a new property; no object relies on anything undeclared"

# schema-side — the #1779 half: REMOVE a property, touch no object file.
git checkout --quiet base && git checkout --quiet -b schema-side
_base_register no > lib/Settings/fixture_register.json
git add -A && git commit --quiet -m "remove sourceEntity from the schema; touch no object"

# unrelated — touches no register JSON at all.
git checkout --quiet base && git checkout --quiet -b unrelated
echo "y" >> README.md
git add -A && git commit --quiet -m "an unrelated change"

_verdict() {
    git checkout --quiet "$1"
    mkdir -p "${WORK}/logs-$1"
    HYDRA_GATE_LOG_DIR="${WORK}/logs-$1" bash "${RUNNER}" --base base "${APP}" 2>&1 \
        | grep -E '^\[gate-108\]' | head -1
}

_names() {  # <branch> <substring>
    grep -qF -- "$2" "${WORK}/logs-$1/hydra-gate-shipped-object-properties.log" 2>/dev/null
}

echo "-- ARM 1: TWO independently fatal defects are a finding, and are NAMED --"
_v="$(_verdict planted)"
case "${_v}" in
    *FAIL*) _ok "gate-108 FAILs the planted arm" ;;
    *)      _bad "expected FAIL on planted, got: ${_v:-<no gate-108 line>}" ;;
esac
if _names planted bronEntiteit; then
    _ok "the log NAMES 'bronEntiteit' — the fragment-object defect"
else
    _bad "gate-108 failed but never named 'bronEntiteit'. A bare count is not a finding, and a gate that fails for some OTHER reason proves nothing."
fi
if _names planted catalog; then
    _ok "the log NAMES 'catalog' — the mock-object defect"
else
    _bad "gate-108 failed but never named 'catalog' — the dossiq#1782 shape, in the file gate-101 already reads and passes."
fi

echo "-- ARM 2: the clean baseline, with every near miss, is PASS --"
_v="$(_verdict clean)"
case "${_v}" in
    *PASS*) _ok "gate-108 PASSes a real register edit that introduces nothing" ;;
    *) _bad "expected PASS on clean, got: ${_v:-<no gate-108 line>}. Envelope keys, metadata-bearing keys, a slug that differs from its definition key, a property declared only by an extending fragment, the top-level and seedData containers, and an unresolvable cross-app reference are ALL legitimate — widening the checker until everything trips it is not a repair." ;;
esac

echo "-- ARM 3: 🔴 INHERITED DEBT IS NOT THIS PR'S PROBLEM --"
_v="$(_verdict unrelated)"
case "${_v}" in
    *FAIL*) _bad "gate-108 reported something on a commit touching no register JSON — this is the fleet-wide red wave a new full-tree gate causes: ${_v}" ;;
    *)      _ok "a commit touching no register JSON reports no finding" ;;
esac

echo "-- ARM 4: 🔴 REMOVING A SCHEMA PROPERTY IS JUDGED AGAINST THE OBJECTS USING IT --"
_v="$(_verdict schema-side)"
case "${_v}" in
    *FAIL*) _ok "gate-108 FAILs a commit that removes a property objects rely on, without touching an object file" ;;
    *) _bad "expected FAIL on schema-side: dossiq#1782 was built by two PRs a minute apart — #1779 removed the property, #1780 added the object. A gate scoped to the object's own file passes BOTH. Got: ${_v:-<no gate-108 line>}" ;;
esac
if _names schema-side sourceEntity; then
    _ok "the log NAMES 'sourceEntity' — the property the schema stopped declaring"
else
    _bad "the schema-side arm failed without naming 'sourceEntity', so it proves nothing"
fi

echo "-- ARM 5: NEGATIVE CONTROLS — each defect alone must still fail --"
_v="$(_verdict planted-fragment)"
case "${_v}" in
    *FAIL*) _ok "the fragment defect alone fails (gate-101 cannot open this file at all)" ;;
    *) _bad "expected FAIL with only the fragment defect: a gate that reads only 'type: mock' descriptors misses dossiq's 91 base-register objects and the 100 across its ten fragments. Got: ${_v:-<no gate-108 line>}" ;;
esac
_v="$(_verdict planted-mock)"
case "${_v}" in
    *FAIL*) _ok "the mock defect alone fails" ;;
    *) _bad "expected FAIL with only the mock defect. Got: ${_v:-<no gate-108 line>}" ;;
esac

echo
if [ "${_fail_n}" -eq 0 ]; then
    echo "test_gate108_shipped_object_properties_scope.sh: ALL PASS"
    exit 0
fi
echo "test_gate108_shipped_object_properties_scope.sh: ${_fail_n} FAILURE(S)"
exit 1
