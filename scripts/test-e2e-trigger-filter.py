"""Execute the E2E trigger filter and the report's census, as shipped.

Two scripts decide whether a skipped Playwright job is a COST CONTROL or a
MISSING VERDICT, and they have to agree:

  * `changes` / `e2e-trigger` decides whether the suite runs on this event and
    states the reason.
  * `report` / the test-tier census turns "enabled but skipped" into either a
    declared skip (green, with the reason printed) or "NO VERDICT EXISTS" (red).

If the first one answers wrong, the fleet loses its browser verdict silently.
If the second one does not honour the reason, every development pull request
goes red on the aggregator instead — the red moves, it does not go away. So
both are EXTRACTED FROM THE WORKFLOW and executed here, never copied.

Usage:
  python3 scripts/test-e2e-trigger-filter.py [.github/workflows/quality.yml]
  python3 scripts/test-e2e-trigger-filter.py --positive-control [workflow]

`--positive-control` sabotages the fail-safe on purpose and requires this suite
to go red. A suite that cannot fail is not evidence.
"""
import os
import shutil
import subprocess
import sys
import tempfile

import yaml

BREAK = "--positive-control" in sys.argv
_args = [a for a in sys.argv[1:] if not a.startswith("--")]
WF = _args[0] if _args else ".github/workflows/quality.yml"

_doc = yaml.safe_load(open(WF))


def step_script(job, step_id=None, step_name=None):
    for s in _doc["jobs"][job]["steps"]:
        if (step_id and s.get("id") == step_id) or \
           (step_name and s.get("name") == step_name):
            return s["run"]
    raise SystemExit(f"step not found in job {job}: {step_id or step_name}")


def trigger_script():
    src = step_script("changes", step_id="e2e-trigger")
    if BREAK:
        # Sabotage the fail-safe: make the catch-all for unknown events answer
        # `false` instead of `true`. workflow_dispatch and schedule must then
        # fail below. If they do not, this suite is not reading the shipped
        # script.
        broken = src.replace(
            'emit_e2e true "event \'${EVENT}\' is neither a push',
            'emit_e2e false "SABOTAGED — event \'${EVENT}\' is neither a push')
        assert broken != src, "positive control could not find its anchor"
        return broken
    return src


def census_script():
    return step_script(
        "report",
        step_name="Gate — a test job that was ENABLED but never ran has no verdict")


def run_trigger(name, event, base_ref="", head_ref="", ref="",
                promotion_only="true", expect=None):
    d = tempfile.mkdtemp()
    try:
        out_f = os.path.join(d, "o")
        sum_f = os.path.join(d, "s")
        open(out_f, "w").close()
        open(sum_f, "w").close()
        env = dict(os.environ)
        env.update({
            "GITHUB_OUTPUT": out_f, "GITHUB_STEP_SUMMARY": sum_f,
            "PROMOTION_ONLY": promotion_only, "EVENT": event,
            "BASE_REF": base_ref, "HEAD_REF": head_ref, "REF": ref,
        })
        r = subprocess.run(["bash", "-c", trigger_script()], cwd=d, env=env,
                           capture_output=True, text=True)
        outs = dict(l.split("=", 1) for l in open(out_f).read().splitlines()
                    if "=" in l)
        got = outs.get("e2e")
        reason = outs.get("e2e_reason", "")
        ok = (got == expect)
        # A `false` with no reason is the defect this whole design exists to
        # avoid: the census would then call it a missing verdict.
        if ok and got == "false" and not reason.strip():
            ok = False
            reason = "<EMPTY — an undeclared skip>"
        print(f"  {'PASS' if ok else 'FAIL'}  {name:54} e2e={got!r} (want {expect!r}) rc={r.returncode}")
        if not ok:
            print("        reason:", reason[:200])
            print("        stderr:", r.stderr[-300:])
        return ok
    finally:
        shutil.rmtree(d, ignore_errors=True)


def run_census(name, e2e_trigger, e2e_reason, playwright_result="skipped",
               path_filter_code="true", expect_rc=None):
    d = tempfile.mkdtemp()
    try:
        sum_f = os.path.join(d, "s")
        open(sum_f, "w").close()
        env = dict(os.environ)
        env.update({
            "GITHUB_STEP_SUMMARY": sum_f,
            "GITHUB_OUTPUT": os.path.join(d, "o"),
            "SECURITY_RESULT": "success",
            "PHPUNIT_ENABLED": "true", "PHPUNIT_RESULT": "success",
            "NEWMAN_ENABLED": "false", "NEWMAN_RESULT": "skipped",
            "PLAYWRIGHT_ENABLED": "true", "PLAYWRIGHT_RESULT": playwright_result,
            "PATH_FILTER_CODE": path_filter_code,
            "PATH_FILTER_REASON": "a reason",
            "E2E_TRIGGER": e2e_trigger, "E2E_TRIGGER_REASON": e2e_reason,
            "JOURNEYDOC_ENABLED": "false", "JOURNEYDOC_RESULT": "skipped",
            # The supersession probe shells out to `gh`; without a token it
            # fails and `|| true` leaves TIP empty, which is the "this run is
            # still the tip" branch — the strict one.
            "GH_TOKEN": "",
        })
        r = subprocess.run(["bash", "-c", census_script()], cwd=d, env=env,
                           capture_output=True, text=True)
        ok = (r.returncode == expect_rc)
        print(f"  {'PASS' if ok else 'FAIL'}  {name:54} rc={r.returncode} (want {expect_rc})")
        if not ok:
            print("        stdout:", r.stdout[-600:])
        return ok
    finally:
        shutil.rmtree(d, ignore_errors=True)


results = []

print("── THE PROMOTION PATH RUNS E2E (a missed one is a lost verdict) ───")
results.append(run_trigger("PR development -> beta", "pull_request",
                           base_ref="beta", head_ref="development", expect="true"))
results.append(run_trigger("PR beta -> main", "pull_request",
                           base_ref="main", head_ref="beta", expect="true"))
results.append(run_trigger("PR development -> main (the narrow hop skipped)",
                           "pull_request", base_ref="main",
                           head_ref="development", expect="true"))
results.append(run_trigger("push to beta", "push", ref="refs/heads/beta",
                           expect="true"))
results.append(run_trigger("push to main", "push", ref="refs/heads/main",
                           expect="true"))

print("── ORDINARY DEVELOPMENT TRAFFIC DOES NOT (the point) ─────────────")
results.append(run_trigger("PR feature -> development", "pull_request",
                           base_ref="development", head_ref="feat/x",
                           expect="false"))
results.append(run_trigger("push to development", "push",
                           ref="refs/heads/development", expect="false"))
results.append(run_trigger("push to a feature branch", "push",
                           ref="refs/heads/feat/x", expect="false"))
results.append(run_trigger("PR release/ -> development (rule 1, predates this)",
                           "pull_request", base_ref="development",
                           head_ref="release/1.2.3", expect="false"))

print("── FAIL-SAFE: anything not proven ordinary must RUN ───────────────")
results.append(run_trigger("workflow_dispatch on development", "workflow_dispatch",
                           ref="refs/heads/development", expect="true"))
results.append(run_trigger("workflow_dispatch on a feature branch",
                           "workflow_dispatch", ref="refs/heads/feat/x",
                           expect="true"))
results.append(run_trigger("schedule", "schedule",
                           ref="refs/heads/development", expect="true"))
results.append(run_trigger("merge_group (event this workflow has not met)",
                           "merge_group", ref="refs/heads/development",
                           expect="true"))
results.append(run_trigger("e2e-promotion-only: false -> PR into development",
                           "pull_request", base_ref="development",
                           head_ref="feat/x", promotion_only="false",
                           expect="true"))
results.append(run_trigger("e2e-promotion-only: false -> push to development",
                           "push", ref="refs/heads/development",
                           promotion_only="false", expect="true"))
results.append(run_trigger("e2e-promotion-only unresolvable (empty) -> RUN",
                           "push", ref="refs/heads/development",
                           promotion_only="", expect="true"))

print("── THE CENSUS MUST HONOUR THE REASON, AND ONLY THE REASON ────────")
results.append(run_census("declared skip -> green",
                          "false", "E2E runs on the promotion path.",
                          expect_rc=0))
results.append(run_census("CONTROL: skip with NO reason -> NO VERDICT, red",
                          "false", "", expect_rc=1))
results.append(run_census("CONTROL: skipped, trigger says it RAN -> red",
                          "true", "", expect_rc=1))
results.append(run_census("E2E ran and passed -> green",
                          "true", "", playwright_result="success", expect_rc=0))
results.append(run_census("path-filter skip, unchanged -> green",
                          "true", "", path_filter_code="false", expect_rc=0))

print()
passed, total = sum(results), len(results)
if BREAK:
    if passed == total:
        print("::error::POSITIVE CONTROL DID NOT FIRE — the E2E trigger filter's "
              "fail-safe was sabotaged and every case still passed. This suite "
              "is not exercising the shipped script.")
        sys.exit(1)
    print(f"OK — the control fires: {total - passed} case(s) failed with a "
          f"sabotaged fail-safe, so a clean pass of this suite is a verdict.")
    sys.exit(0)

print(f"{passed}/{total} passed")
if passed != total:
    print("::error::The E2E trigger filter or the report census is not behaving "
          "as specified. A wrong answer here either deletes the browser verdict "
          "silently, or moves every development PR's red onto the aggregator.")
sys.exit(0 if passed == total else 1)
