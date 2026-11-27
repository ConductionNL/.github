#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Prove the PHPUnit shard plan runs every test file exactly once.

WHY
---
`phpunit-shards` splits each PHPUnit leg across runners, and each shard writes
its own configuration with the "Plan this shard" step. The one outcome that must
never happen is a test file that runs on NO shard: every shard goes green
without it, and the run reads exactly like a run in which it passed. The second
is a file that runs on two shards, which costs time and double-counts.

This suite runs the SHIPPED program, extracted from quality.yml by its step id,
against a small app tree:

  * lossless     every file the suites select is on exactly one shard, for 2 to
                 8 shards, with and without durations.
  * selection    a <directory> suffix, an <exclude>, a <file>, a phpVersion
                 condition and defaultTestSuite are read as PHPUnit reads them.
  * durations    the slowest file is dealt out first, the shards' loads end up
                 close, and every shard runs its fastest file first and its
                 slowest file last.
  * refusals     a shard count outside 1..8 and an empty shard fail the leg; an
                 empty shard of the merge base (ALLOW_EMPTY) exits 3.
  * config       the written configuration keeps every other setting, lists
                 the shard's files in run order and drops defaultTestSuite.
  * file input   the durations reach the plan as a file with the digest
                 `phpunit-plan` published: a file over the kernel's 128 KiB
                 limit for one environment string plans, a missing or other
                 file fails the leg, and no step passes them through `env:`.

--positive-control drops one file from the plan and requires the lossless case
to go red, so this suite is shown to read the program's partition.

Usage:  test-phpunit-shard-plan.py [--positive-control] [workflow.yml]
Exit:   0 all assertions hold, 1 at least one failed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

import yaml

ROOT = Path(__file__).resolve().parent.parent
STEP_ID = "phpunit-shard-plan"
HEREDOC_OPEN = "<<'PYEOF'"
HEREDOC_CLOSE = "PYEOF"
LOSS = ("parts[target].append(f)", "parts[target].append(f) if not f.endswith('AlphaTest.php') else None")

CONFIG = """<?xml version="1.0" encoding="UTF-8"?>
<phpunit xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" bootstrap="tests/bootstrap.php" colors="true" defaultTestSuite="{default}">
    <testsuites>
        <testsuite name="Unit">
            <directory>tests/Unit</directory>
            <exclude>tests/Unit/Skipped</exclude>
        </testsuite>
        <testsuite name="Integration">
            <directory suffix="Spec.php">tests/Integration</directory>
            <file>tests/Extra/LoneTest.php</file>
            <directory phpVersion="9.0" phpVersionOperator="&gt;=">tests/Future</directory>
        </testsuite>
    </testsuites>
    <source><include><directory>lib</directory></include></source>
</phpunit>
"""

FILES = [
    "tests/Unit/AlphaTest.php", "tests/Unit/BetaTest.php", "tests/Unit/Deep/GammaTest.php",
    "tests/Unit/Deep/DeltaTest.php", "tests/Unit/EpsilonTest.php", "tests/Unit/ZetaTest.php",
    "tests/Unit/EtaTest.php", "tests/Unit/ThetaTest.php",
    "tests/Integration/IotaSpec.php", "tests/Integration/KappaSpec.php",
    "tests/Extra/LoneTest.php",
]
NOT_SELECTED = [
    "tests/Unit/Skipped/IgnoredTest.php",    # under <exclude>
    "tests/Unit/Helper.php",                 # no Test.php suffix
    "tests/Integration/HelperTest.php",      # that directory's suffix is Spec.php
    "tests/Future/NextTest.php",             # phpVersion 9.0 on PHP 8.3
]


def extract(workflow: Path) -> str:
    doc = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    steps = [s for job in doc["jobs"].values() for s in (job.get("steps") or []) if s.get("id") == STEP_ID]
    if len(steps) != 1:
        raise SystemExit(f"FATAL: expected exactly one step with id {STEP_ID!r}, found {len(steps)}.")
    run = steps[0]["run"]
    if HEREDOC_OPEN not in run:
        raise SystemExit(f"FATAL: step {STEP_ID!r} no longer opens a {HEREDOC_OPEN} heredoc.")
    lines = run.split(HEREDOC_OPEN, 1)[1].split("\n", 1)[1].split("\n")
    if HEREDOC_CLOSE not in lines:
        raise SystemExit(f"FATAL: step {STEP_ID!r} has no {HEREDOC_CLOSE} terminator in column 0.")
    return "\n".join(lines[: lines.index(HEREDOC_CLOSE)]) + "\n"


def make_app(where: Path, default: str = "") -> Path:
    app = where / "app"
    for rel in FILES + NOT_SELECTED + ["tests/bootstrap.php"]:
        (app / rel).parent.mkdir(parents=True, exist_ok=True)
        (app / rel).write_text("<?php\n", encoding="utf-8")
    (app / "phpunit.xml").write_text(CONFIG.format(default=default), encoding="utf-8")
    # A `php` that reports 8.3.4, so the phpVersion condition is read the way
    # a PHP 8.3 leg reads it, without PHP on the machine running this suite.
    bin_dir = where / "bin"
    bin_dir.mkdir()
    (bin_dir / "php").write_text("#!/bin/sh\nprintf '8.3.4'\n", encoding="utf-8")
    (bin_dir / "php").chmod(0o755)
    return app


def plan(program: Path, app: Path, shard: int, shards, durations: dict | None = None, **env) -> tuple[int, list[str], str]:
    full = {"PATH": f"{app.parent / 'bin'}:/usr/bin:/bin", "SHARD": str(shard), "SHARDS": str(shards)}
    if durations is not None:
        # As `phpunit-plan` publishes them: a file, and its digest.
        data = json.dumps({"files": durations}, separators=(",", ":"), sort_keys=True).encode("utf-8")
        path = app.parent / "durations.json"
        path.write_bytes(data)
        full.update(DURATIONS_FILE=str(path), DURATIONS_SHA256=hashlib.sha256(data).hexdigest())
    full.update(env)
    out = app / "phpunit-shard.xml"
    out.unlink(missing_ok=True)
    proc = subprocess.run([sys.executable, str(program)], cwd=app, env=full, capture_output=True, text=True)
    files = []
    if out.is_file():
        suites = ET.parse(out).getroot().find("testsuites")
        files = [f.text for f in suites.iter("file")]
    return proc.returncode, files, proc.stdout + proc.stderr


def assertions(program: Path, tmp: Path) -> dict[str, str]:
    failures: dict[str, str] = {}

    def check(case: str, ok: bool, detail: str) -> None:
        if not ok:
            failures.setdefault(case, detail)

    app = make_app(tmp / "plain")
    durations = {f: float(i + 1) for i, f in enumerate(sorted(FILES))}
    durations["tests/Unit/ThetaTest.php"] = 40.0

    for weights, label in ((None, "count"), (durations, "durations")):
        for shards in range(2, 9):
            seen: list[str] = []
            for shard in range(1, shards + 1):
                code, files, log = plan(program, app, shard, shards, weights)
                check("lossless", code == 0, f"{label}, shard {shard} of {shards}: exit {code}\n{log}")
                seen += files
            check("lossless", sorted(seen) == sorted(FILES),
                  f"{label}, {shards} shards: want every selected file exactly once, got {sorted(seen)}")

    code, files, log = plan(program, app, 1, 2)
    check("selection", not set(files) & set(NOT_SELECTED), f"selected a file PHPUnit would not run: {files}\n{log}")

    default_app = make_app(tmp / "default", default="Integration")
    seen = []
    for shard in (1, 2):
        code, files, log = plan(program, default_app, shard, 2)
        seen += files
    want = sorted(f for f in FILES if not f.startswith("tests/Unit/"))
    check("selection-default-suite", sorted(seen) == want, f"defaultTestSuite: want {want}, got {sorted(seen)}")

    loads = []
    for shard in (1, 2, 3):
        code, files, log = plan(program, app, shard, 3, durations)
        weights = [durations[f] for f in files]
        loads.append(sum(weights))
        check("durations-order", weights == sorted(weights), f"shard {shard}: not fastest first: {list(zip(files, weights))}")
        if "tests/Unit/ThetaTest.php" in files:
            check("durations-slowest-alone", files == ["tests/Unit/ThetaTest.php"],
                  f"the 40 s file shares its shard with {files}, though the other files fit beside each other")
    check("durations-balance", max(loads) - min(loads) <= 40.0 and max(loads) == 40.0,
          f"want the 40 s file to set the longest shard, got loads {loads}")

    code, files, log = plan(program, app, 1, 2, {"tests/Unit/ThetaTest.php": 30.0})
    check("durations-partial", code == 0 and files, f"durations for one file only: exit {code}\n{log}")

    # Over 200 KB of durations, past what one environment string may hold.
    large = {f"tests/Unit/Generated/Module{i:05d}/SomeRatherLongGeneratedNameTest.php": 1.5 for i in range(4000)}
    large.update(durations)
    seen = []
    for shard in (1, 2, 3):
        code, files, log = plan(program, app, shard, 3, large)
        check("durations-large-file", code == 0, f"{len((app.parent / 'durations.json').read_bytes())} bytes of durations, shard {shard}: exit {code}\n{log}")
        seen += files
    check("durations-large-file", len((app.parent / "durations.json").read_bytes()) > 200_000 and sorted(seen) == sorted(FILES),
          f"want every file once from a >200 KB durations file, got {sorted(seen)}")

    code, files, log = plan(program, app, 1, 2, durations, DURATIONS_SHA256="0" * 64)
    check("durations-other-file", code == 1 and "not the file phpunit-plan published" in log,
          f"want exit 1 on a durations file with another digest, got {code}\n{log}")
    code, files, log = plan(program, app, 1, 2, durations, DURATIONS_FILE=str(app.parent / "absent.json"))
    check("durations-missing-file", code == 1 and "are missing" in log,
          f"want exit 1 when the published durations file is absent, got {code}\n{log}")
    code, files, log = plan(program, app, 1, 2, None, DURATIONS_FILE=str(app.parent / "absent.json"))
    check("durations-none-published", code == 0 and "file count" in log,
          f"want a plan by count when nothing was published, got {code}\n{log}")

    for bad in ("12", "0", "x", ""):
        code, files, log = plan(program, app, 1, bad)
        check("refuses-shard-count", code == 1 and "must be a whole number from 1 to 8" in log,
              f"phpunit-shards={bad!r}: want exit 1 naming the range, got {code}\n{log}")

    small = make_app(tmp / "small")
    for f in FILES[1:]:
        (small / f).unlink()
    code, files, log = plan(program, small, 2, 2)
    check("refuses-empty-shard", code == 1 and "Lower phpunit-shards" in log, f"want exit 1 on an empty shard, got {code}\n{log}")
    code, files, log = plan(program, small, 2, 2, ALLOW_EMPTY="1")
    check("allows-empty-base-shard", code == 3 and not files, f"want exit 3 and no config with ALLOW_EMPTY, got {code}\n{log}")

    code, files, log = plan(program, default_app, 1, 2)
    written = (default_app / "phpunit-shard.xml").read_text(encoding="utf-8")
    check("config-keeps-settings", 'bootstrap="tests/bootstrap.php"' in written and "<source>" in written
          and "defaultTestSuite" not in written and written.count("<testsuite ") == 1,
          f"the written configuration lost a setting or kept defaultTestSuite:\n{written}")
    return failures


def wiring(workflow: Path) -> dict[str, str]:
    """No step hands the durations over through `env:`; every planner reads the file."""
    doc = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    failures = {}
    planners = 0
    for name, job in doc["jobs"].items():
        for step in job.get("steps") or []:
            env = step.get("env") or {}
            for key, value in env.items():
                if "durations" in str(value) and "durations-sha256" not in str(value) and "phpunit-shard-plan/durations.json" not in str(value):
                    failures["durations-through-env"] = f"{name} / {step.get('name')}: {key} = {value!r} passes the durations through the environment"
            if "phpunit-shard-plan.py" in str(step.get("run") or ""):
                planners += 1
                if "DURATIONS_FILE" not in env or "DURATIONS_SHA256" not in env:
                    failures["durations-file-wiring"] = f"{name} / {step.get('name')} runs the planner without DURATIONS_FILE and DURATIONS_SHA256"
    if not planners:
        failures["durations-file-wiring"] = "found no step that runs the planner"
    return failures


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("workflow", nargs="?", default=str(ROOT / ".github" / "workflows" / "quality.yml"))
    ap.add_argument("--positive-control", action="store_true")
    args = ap.parse_args()
    source = extract(Path(args.workflow))

    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        program = tmp / "plan.py"
        if args.positive_control:
            if source.count(LOSS[0]) != 1:
                print(f"::error::the anchor {LOSS[0]!r} is not in the plan program exactly once.")
                return 1
            program.write_text(source.replace(*LOSS), encoding="utf-8")
            failures = assertions(program, tmp / "mutant")
            if "lossless" not in failures:
                print("::error::a plan that drops a test file left the lossless case green. This suite is not reading the partition.")
                return 1
            print("OK: a plan that drops a test file -> lossless goes red.")
            return 0
        program.write_text(source, encoding="utf-8")
        failures = assertions(program, tmp / "run")
    failures.update(wiring(Path(args.workflow)))
    for case, detail in failures.items():
        print(f"::error::{case}: {detail}")
    if failures:
        return 1
    print("OK: every selected test file is on exactly one shard for 2 to 8 shards, the plan reads the suites as PHPUnit "
          "does, deals the slowest files out first and runs them last, and refuses a bad shard count and an empty shard.")
    return 0


if __name__ == "__main__":
    os.umask(0o022)
    sys.exit(main())
