#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Prove the sharded coverage merge reports what an unsharded run reports.

WHY
---
With `phpunit-shards` above 1 no shard holds the whole suite, so the coverage
gate reads a clover report that the `phpunit-shards` job merges from each
shard's `--coverage-php` part. If that merge counted statements differently
from one unsharded run (a part dropped, a file no test loads left out), the
ratchet would trip on a floor measured unsharded, or pass with nothing behind
it.

This suite runs the SHIPPED programs, extracted from quality.yml, on a real
app (scripts/fixtures/coverage-merge) with a real coverage driver:

  * equal        the "Plan this shard" program splits the suite over two
                 shards, each shard writes its part as the shard step does,
                 and the "Merge the shards' coverage" program merges them with
                 the coverage driver switched off, as in that job. The merged
                 clover covers exactly the lines, and counts exactly the
                 statements and methods, of one unsharded run. The fixture's
                 Beta class has one branch per test file, so only both parts
                 together cover it, and Gamma is loaded by no test.
  * one-part     a merge of one shard's part only covers less, so `equal`
                 can tell a merge from a copy.
  * refusals     a missing part, a file that holds no coverage and no part at
                 all each exit 1 and write no report.

--positive-control makes the merge keep the first part only and requires
`equal` to go red, so the comparison is shown to read the merge.

Needs php with pcov or xdebug, and composer. Without them this suite FAILS:
a coverage test that could not run is not a pass.

Usage:  test-phpunit-coverage-merge.py [--positive-control] [workflow.yml]
Exit:   0 all assertions hold, 1 at least one failed or could not run.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

import yaml

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "scripts" / "fixtures" / "coverage-merge"
PLAN_STEP_ID = "phpunit-shard-plan"
MERGE_STEP_NAME = "Merge the shards' coverage"
SHARDS = 2
# Keep the first part only: the merge a dropped part would produce.
DROP = ("$merged->merge($part);", "// dropped")


def heredoc(workflow: Path, opener: str, closer: str, step_id: str | None = None, name: str | None = None) -> str:
    """Return the program inside the heredoc of the one step with this id or name."""
    data = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    steps = [
        step
        for job in (data.get("jobs") or {}).values()
        for step in (job.get("steps") or [])
        if (step_id is not None and step.get("id") == step_id) or (name is not None and step.get("name") == name)
    ]
    if len(steps) != 1:
        raise SystemExit(f"FATAL: expected exactly one step {step_id or name!r} in {workflow}, found {len(steps)}.")
    run = steps[0].get("run") or ""
    if opener not in run:
        raise SystemExit(f"FATAL: step {step_id or name!r} no longer opens a {opener} heredoc.")
    lines = run.split(opener, 1)[1].split("\n", 1)[1].split("\n")
    if closer not in lines:
        raise SystemExit(f"FATAL: step {step_id or name!r} has no {closer} terminator in column 0.")
    return "\n".join(lines[: lines.index(closer)]).strip() + "\n"


def run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, env={**os.environ, **(env or {})}, capture_output=True, text=True)


def driver_flags() -> list[str]:
    """The ini flags that switch on the coverage driver this php has, or exit when it has none."""
    modules = run(["php", "-m"], Path.cwd()).stdout.lower().split()
    if "pcov" in modules:
        return ["-d", "pcov.enabled=1"]
    if "xdebug" in modules:
        return ["-d", "xdebug.mode=coverage"]
    raise SystemExit("FATAL: php has neither pcov nor xdebug, so no coverage can be measured. This suite cannot run.")


# The merge job installs no coverage driver; switch off whatever this php has.
NO_DRIVER = ["-d", "pcov.enabled=0", "-d", "xdebug.mode=off"]


def clover(path: Path) -> dict:
    """Per file: the statement lines, the covered ones and the method counts; plus the project metrics."""
    root = ET.parse(path).getroot()
    files = {}
    for f in root.iter("file"):
        stmts = {int(l.get("num")) for l in f.iter("line") if l.get("type") == "stmt"}
        covered = {int(l.get("num")) for l in f.iter("line") if l.get("type") == "stmt" and int(l.get("count") or 0) > 0}
        m = f.find("metrics")
        files[Path(f.get("name")).name] = {
            "statements": stmts, "covered": covered,
            "methods": int(m.get("methods")), "coveredmethods": int(m.get("coveredmethods")),
        }
    project = root.find("project/metrics")
    totals = {k: int(project.get(k)) for k in ("statements", "coveredstatements", "methods", "coveredmethods")}
    return {"files": files, "totals": totals}


def assertions(plan: str, merge: str, tmp: Path) -> dict[str, str]:
    """Return {case: failure} for every case that does not hold."""
    failures: dict[str, str] = {}

    def check(case: str, ok: bool, detail: str) -> None:
        if not ok:
            failures[case] = detail

    app = tmp / "app"
    shutil.copytree(FIXTURE, app, ignore=shutil.ignore_patterns("vendor"))
    installed = run(["composer", "install", "--no-progress", "--no-interaction", "--prefer-dist"], app)
    if installed.returncode != 0:
        raise SystemExit(f"FATAL: composer install failed in the fixture app:\n{installed.stderr}")
    on = driver_flags()
    (tmp / "plan.py").write_text(plan, encoding="utf-8")
    (tmp / "merge.php").write_text(merge, encoding="utf-8")

    full = run(["php", *on, "vendor/bin/phpunit", "-c", "phpunit.xml", "--coverage-clover", str(tmp / "full.xml")], app)
    if full.returncode != 0:
        raise SystemExit(f"FATAL: the unsharded fixture run failed:\n{full.stdout}{full.stderr}")

    parts = []
    for shard in range(1, SHARDS + 1):
        planned = run([sys.executable, str(tmp / "plan.py")], app, {"SHARD": str(shard), "SHARDS": str(SHARDS), "DURATIONS": ""})
        if planned.returncode != 0:
            raise SystemExit(f"FATAL: the plan failed for shard {shard}:\n{planned.stdout}{planned.stderr}")
        part = tmp / "coverage" / f"head-{shard}.cov"
        part.parent.mkdir(exist_ok=True)
        ran = run(["php", *on, "vendor/bin/phpunit", "-c", "phpunit-shard.xml", "--coverage-php", str(part)], app)
        if ran.returncode != 0 or not part.is_file():
            raise SystemExit(f"FATAL: shard {shard} did not write its part:\n{ran.stdout}{ran.stderr}")
        parts.append(str(part))

    want = clover(tmp / "full.xml")

    merged = tmp / "merged.xml"
    proc = run(["php", *NO_DRIVER, str(tmp / "merge.php"), str(merged), *parts], app)
    got = clover(merged) if proc.returncode == 0 and merged.is_file() else None
    check("equal", got == want,
          f"the merge of {SHARDS} parts differs from the unsharded run\nwant {want}\ngot  {got}\n{proc.stdout}{proc.stderr}")

    one = tmp / "one-part.xml"
    proc = run(["php", *NO_DRIVER, str(tmp / "merge.php"), str(one), parts[0]], app)
    got = clover(one) if proc.returncode == 0 and one.is_file() else None
    check("one-part", got is not None and got["totals"]["coveredstatements"] < want["totals"]["coveredstatements"],
          f"one shard's part should cover less than the whole suite: want fewer than "
          f"{want['totals']['coveredstatements']} covered statements, got {got and got['totals']}\n{proc.stderr}")

    not_coverage = tmp / "not-coverage.php"
    not_coverage.write_text("<?php\nreturn 1;\n", encoding="utf-8")
    for case, args in (("refuses-missing-part", [parts[0], str(tmp / "absent.cov")]),
                       ("refuses-non-coverage", [parts[0], str(not_coverage)]),
                       ("refuses-no-parts", [])):
        out = tmp / f"{case}.xml"
        proc = run(["php", *NO_DRIVER, str(tmp / "merge.php"), str(out), *args], app)
        check(case, proc.returncode == 1 and not out.exists(),
              f"want exit 1 and no report, got exit {proc.returncode}, report written: {out.exists()}\n{proc.stderr}")

    return failures


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("workflow", nargs="?", default=str(ROOT / ".github" / "workflows" / "quality.yml"))
    ap.add_argument("--positive-control", action="store_true")
    args = ap.parse_args()

    workflow = Path(args.workflow)
    plan = heredoc(workflow, "<<'PYEOF'", "PYEOF", step_id=PLAN_STEP_ID)
    merge = heredoc(workflow, "<<'PHPEOF'", "PHPEOF", name=MERGE_STEP_NAME)

    with tempfile.TemporaryDirectory() as raw:
        if args.positive_control:
            if merge.count(DROP[0]) != 1:
                print(f"::error::the anchor {DROP[0]!r} is not in the merge program exactly once.")
                return 1
            failures = assertions(plan, merge.replace(*DROP), Path(raw))
            if "equal" not in failures:
                print("::error::a merge that keeps only the first part left case 'equal' green. This suite is not reading the merge.")
                return 1
            print("OK: a merge that drops a part turns 'equal' red.")
            return 0
        failures = assertions(plan, merge, Path(raw))

    for case, failure in failures.items():
        print(f"::error::{case}: {failure}")
    if failures:
        return 1
    print(f"OK: {SHARDS} shards' coverage parts, merged by the shipped program without a coverage driver, report the same "
          "covered lines, statements and methods as one unsharded run; one part alone covers less, and a missing part, "
          "a file without coverage and no part at all are refused.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
