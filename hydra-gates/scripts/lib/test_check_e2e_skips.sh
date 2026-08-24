#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# Self-test for check_e2e_skips.py — the e2e skip-discipline gate.
#
# Discovered and run by tests/run-helper-suites.sh — no workflow edit needed.
#
# Every assertion is paired: a NEGATIVE control (a report where every test ran,
# or skipped for a reason naming a real absence, must produce zero findings) and
# a POSITIVE control (a report carrying exactly one defect must produce exactly
# that finding, and must EXIT NON-ZERO under --mode enforce).
#
# The pairing matters more here than usual. This gate exists because a skipped
# test and a passing test are indistinguishable from the outside, and a checker
# that stays silent on a broken report is the same program as one that stays
# silent on a clean report. So the enforce-mode exit code is asserted in BOTH
# directions on every case, never only on the failing one.
#
# One case is easy to get backwards and is asserted explicitly: a MISSING or
# unparseable report must exit non-zero, not 0. A gate that reads an artifact
# has to treat an absent artifact as an absent measurement. Reporting success
# because there was nothing to read is precisely the class of lie this gate was
# written to catch.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECKER="${HERE}/check_e2e_skips.py"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

pass=0
fail=0

ok() { echo "  PASS  $1"; pass=$((pass + 1)); }
no() { echo "  FAIL  $1"; [ -n "${2:-}" ] && printf '        %s\n' "$2"; fail=$((fail + 1)); }

# synth <dir> <json-spec>
#
# Build a Playwright HTML report whose embedded result blob contains exactly the
# tests described by <json-spec>, which is a JSON list of
#   {"file": "a.spec.ts", "title": "...", "outcome": "expected"|"skipped",
#    "reason": "..."}
# The real reporter embeds a zip as a data: URI inside a <script> tag; this
# reproduces that shape rather than a hand-rolled one, so the parser under test
# is exercised through the same path it takes in CI.
synth() {
    local dir="$1"
    local spec="$2"
    mkdir -p "$dir"
    SYNTH_DIR="$dir" SYNTH_SPEC="$spec" python3 - <<'PY'
import base64, collections, io, json, os, zipfile

out = os.environ["SYNTH_DIR"]
tests = json.loads(os.environ["SYNTH_SPEC"])

by_file = collections.OrderedDict()
for t in tests:
    by_file.setdefault(t["file"], []).append(t)

buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as z:
    files_rollup = []
    for i, (name, entries) in enumerate(by_file.items()):
        payload = {"fileId": f"f{i}", "fileName": name, "tests": []}
        for j, t in enumerate(entries):
            test = {
                "testId": f"f{i}-t{j}",
                "title": t["title"],
                "outcome": t["outcome"],
                "path": ["suite"],
                "location": {"file": name, "line": 10 + j, "column": 3},
                "annotations": [],
                "results": [{"duration": 1, "retry": 0}],
            }
            if t["outcome"] == "skipped" and t.get("reason") is not None:
                test["annotations"].append({
                    "type": "skip",
                    "description": t["reason"],
                    "location": {"file": f"/repo/tests/e2e/{name}", "line": 99, "column": 4},
                })
            payload["tests"].append(test)
        z.writestr(f"{i:04d}deadbeef.json", json.dumps(payload))
        files_rollup.append(payload)
    # The roll-up repeats every per-file entry. The checker must ignore it, or
    # every count doubles — the exact mistake this fixture pins.
    z.writestr("report.json", json.dumps({
        "files": files_rollup,
        "stats": {},
        "projectNames": ["chromium"],
    }))

blob = base64.b64encode(buf.getvalue()).decode("ascii")
html = (
    "<!doctype html><html><body>"
    f'<script id="playwrightReportBase64">data:application/zip;base64,{blob}</script>'
    "</body></html>"
)
io.open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(html)
PY
}

# expect <label> <dir> <expected-report-exit> <expected-enforce-exit> [grep-for]
expect() {
    local label="$1" dir="$2" want_report="$3" want_enforce="$4" needle="${5:-}"
    local out rc

    out="$(python3 "$CHECKER" --report "$dir" --mode report 2>&1)"; rc=$?
    if [ "$rc" -ne "$want_report" ]; then
        no "$label (report mode exit)" "expected ${want_report}, got ${rc}"
        return
    fi

    out="$(python3 "$CHECKER" --report "$dir" --mode enforce 2>&1)"; rc=$?
    if [ "$rc" -ne "$want_enforce" ]; then
        no "$label (enforce mode exit)" "expected ${want_enforce}, got ${rc}"
        return
    fi

    if [ -n "$needle" ] && ! printf '%s' "$out" | grep -qF "$needle"; then
        no "$label (message)" "expected to find: ${needle}"
        return
    fi
    ok "$label"
}

echo "check_e2e_skips.py"

# --- NEGATIVE control: everything ran ---------------------------------------
synth "$WORK/clean" '[
  {"file":"a.spec.ts","title":"one","outcome":"expected"},
  {"file":"a.spec.ts","title":"two","outcome":"expected"},
  {"file":"b.spec.ts","title":"three","outcome":"expected"}
]'
expect "a report where every test ran is clean" "$WORK/clean" 0 0 "every spec file ran something"

# The roll-up must not be double-counted. Three tests in, three tests reported.
count="$(python3 "$CHECKER" --report "$WORK/clean" --mode report 2>/dev/null | head -1)"
case "$count" in
    "0/3 tests skipped"*) ok "report.json roll-up is not double-counted" ;;
    *) no "report.json roll-up is not double-counted" "header was: ${count}" ;;
esac

# --- NEGATIVE control: a skip naming a real absence -------------------------
synth "$WORK/absence" '[
  {"file":"a.spec.ts","title":"one","outcome":"expected"},
  {"file":"a.spec.ts","title":"two","outcome":"skipped",
   "reason":"No chat backend reachable on this instance"}
]'
expect "a skip naming an absent external service is allowed" "$WORK/absence" 0 0 "allowed (named a real absence) : 1"

# --- POSITIVE control V1: a spec file that ran nothing ----------------------
synth "$WORK/v1" '[
  {"file":"a.spec.ts","title":"one","outcome":"expected"},
  {"file":"dead.spec.ts","title":"never","outcome":"skipped",
   "reason":"no seeded fixture, tracked in openspec"}
]'
expect "a spec file executing zero tests is a finding" "$WORK/v1" 0 1 "dead.spec.ts"

# --- POSITIVE control V2: deferring to a deploy state CI decides ------------
synth "$WORK/v2" '[
  {"file":"a.spec.ts","title":"one","outcome":"expected"},
  {"file":"a.spec.ts","title":"two","outcome":"skipped",
   "reason":"Members tab not deployed on this instance"}
]'
expect "a deploy-state skip is a finding" "$WORK/v2" 0 1 "deploy state CI decides : 1"

synth "$WORK/v2b" '[
  {"file":"a.spec.ts","title":"one","outcome":"expected"},
  {"file":"a.spec.ts","title":"two","outcome":"skipped",
   "reason":"Deploy drift: the deployed app predates minutes-ui-v1"}
]'
expect "deploy drift is a finding" "$WORK/v2b" 0 1 "deploy state CI decides : 1"

# --- POSITIVE control V3: no reason at all ----------------------------------
synth "$WORK/v3" '[
  {"file":"a.spec.ts","title":"one","outcome":"expected"},
  {"file":"a.spec.ts","title":"two","outcome":"skipped","reason":null}
]'
expect "a skip with no reason is a finding" "$WORK/v3" 0 1 "no reason recorded : 1"

synth "$WORK/v3b" '[
  {"file":"a.spec.ts","title":"one","outcome":"expected"},
  {"file":"a.spec.ts","title":"two","outcome":"skipped","reason":"   "}
]'
expect "a whitespace-only reason is no reason" "$WORK/v3b" 0 1 "no reason recorded : 1"

# --- precedence: a real absence wins over a deploy-state phrase -------------
# "not installed" names something the app does not control, even though the same
# sentence also says "on this instance". Classifying this as a deploy claim would
# make the gate cry wolf on exactly the skips that are legitimate.
synth "$WORK/prec" '[
  {"file":"a.spec.ts","title":"one","outcome":"expected"},
  {"file":"a.spec.ts","title":"two","outcome":"skipped",
   "reason":"the Talk app is not installed on this instance"}
]'
expect "a real absence outranks a deploy-state phrase" "$WORK/prec" 0 0 "allowed (named a real absence) : 1"

# --- a missing measurement is NOT a pass -----------------------------------
mkdir -p "$WORK/empty"
python3 "$CHECKER" --report "$WORK/empty" --mode report >/dev/null 2>&1
rc=$?
if [ "$rc" -ne 0 ]; then
    ok "a missing report fails even in report mode"
else
    no "a missing report fails even in report mode" "exit was 0 — an absent artifact read as a pass"
fi

printf '\n  %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ] || exit 1
