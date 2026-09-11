#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Prove the E2E shard-partition step CAN FAIL, and fails on a lost test.

WHY
---
`e2e-shards` splits the Playwright suite across runners. The one outcome that
must never happen is a test that runs on NO shard: every leg goes green without
it, and the run reads exactly like a run in which it passed. That is the defect
this workflow keeps fighting, so the playwright job lists every shard before any
test runs and refuses to continue when the shards do not cover the suite.

A guard nobody has watched refuse is not a guard. This suite runs the SHIPPED
program, extracted from quality.yml, against real Playwright projects:

  * lossless    Playwright's own --shard over two files. Must pass.
  * lossy       a config that drops one file on shard 2. Must FAIL, naming it.
  * dependency  the main project is a `dependencies` target, so Playwright runs
                it in full on every shard. Must pass, with a warning. This is
                dossiq's shape before its config was changed.
  * empty       a suite with zero tests. Must FAIL, either on the empty list
                or because Playwright refuses to list it.

--positive-control removes the program's refusal on a lost test and requires
the lossy case to stop failing, so this suite is shown to be reading the
program's verdict and not something else.

Usage:  test-e2e-shard-partition.py [--positive-control] [workflow.yml]
Needs:  node and npm. @playwright/test is installed into a temp dir unless
        PLAYWRIGHT_NODE_MODULES points at an existing node_modules.
Exit:   0 all assertions hold, 1 at least one failed.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

STEP_NAME = "Prove the shards cover the whole suite"
HEREDOC_OPEN = "<<'SHARD_PARTITION_PY'"
HEREDOC_CLOSE = "SHARD_PARTITION_PY"
PLAYWRIGHT_VERSION = "1.63.0"
REFUSAL = "this leg refuses to run at all.\")\n    sys.exit(1)"


def extract_program(workflow: Path) -> str:
    steps = yaml.safe_load(workflow.read_text())["jobs"]["playwright"]["steps"]
    run = next((s.get("run") for s in steps if s.get("name") == STEP_NAME), None)
    if run is None:
        raise SystemExit(f"FATAL: no step named {STEP_NAME!r} in the playwright job.")
    if HEREDOC_OPEN not in run:
        raise SystemExit(f"FATAL: {STEP_NAME!r} no longer opens a {HEREDOC_OPEN} heredoc.")
    body = run.split(HEREDOC_OPEN, 1)[1].split("\n", 1)[1]
    lines = body.split("\n")
    end = lines.index(HEREDOC_CLOSE)
    return "\n".join(lines[:end]) + "\n"


SPEC = """import {{ test }} from '@playwright/test'
test('{name} one', async () => {{}})
test('{name} two', async () => {{}})
"""

CONFIGS = {
    "lossless": """import { defineConfig } from '@playwright/test'
export default defineConfig({ testDir: './t', projects: [{ name: 'main' }] })
""",
    "lossy": """import { defineConfig } from '@playwright/test'
const sharded = Number(process.env.E2E_SHARD_TOTAL ?? 1) > 1
const dropOnTwo = sharded && process.env.E2E_SHARD_INDEX === '2'
export default defineConfig({
  testDir: './t',
  projects: [{ name: 'main', testIgnore: dropOnTwo ? ['**/c.spec.ts'] : [] }],
})
""",
    "dependency": """import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './t',
  projects: [
    { name: 'main', testIgnore: ['**/c.spec.ts', '**/d.spec.ts'] },
    { name: 'last', testMatch: ['**/c.spec.ts', '**/d.spec.ts'], dependencies: ['main'] },
  ],
})
""",
    "empty": """import { defineConfig } from '@playwright/test'
export default defineConfig({ testDir: './t', testMatch: ['**/none.spec.ts'] })
""",
}


def node_modules(tmp: Path) -> Path:
    given = os.environ.get("PLAYWRIGHT_NODE_MODULES")
    if given:
        return Path(given)
    pkg = tmp / "pw"
    pkg.mkdir()
    (pkg / "package.json").write_text('{"name":"shard-fixture","private":true}\n')
    subprocess.run(
        ["npm", "install", "--no-audit", "--no-fund", f"@playwright/test@{PLAYWRIGHT_VERSION}"],
        cwd=pkg, check=True, capture_output=True,
    )
    return pkg / "node_modules"


def run_case(program: str, tmp: Path, modules: Path, case: str, shards: int) -> tuple[int, str]:
    root = tmp / case
    (root / "t").mkdir(parents=True)
    for name in ("a", "b", "c", "d"):
        (root / "t" / f"{name}.spec.ts").write_text(SPEC.format(name=name))
    (root / "playwright.config.ts").write_text(CONFIGS[case])
    link = root / "node_modules"
    if not link.exists():
        link.symlink_to(modules)
    script = root / "partition.py"
    script.write_text(program)
    env = dict(
        os.environ,
        CONFIG="playwright.config.ts",
        E2E_SHARD_TOTAL=str(shards),
        E2E_SHARD_INDEX="1",
        GITHUB_STEP_SUMMARY=str(root / "summary.md"),
    )
    proc = subprocess.run([sys.executable, str(script)], cwd=root, env=env, capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def assertions(program: str, tmp: Path, modules: Path) -> list[str]:
    failures: list[str] = []

    code, out = run_case(program, tmp, modules, "lossless", 3)
    if code != 0 or "OK: all 8 tests" not in out:
        failures.append(f"lossless: expected exit 0 and 'OK: all 8 tests', got {code}:\n{out}")

    code, out = run_case(program, tmp, modules, "lossy", 3)
    if code == 0 or "On NO shard" not in out or "c.spec.ts" not in out:
        failures.append(f"lossy: expected a failure naming c.spec.ts, got {code}:\n{out}")

    # Two shards, two files in `last`: each shard gets one of them, so each
    # shard also runs all of `main`, which is the shape dossiq had.
    code, out = run_case(program, tmp, modules, "dependency", 2)
    if code != 0 or "more than one shard" not in out:
        failures.append(f"dependency: expected exit 0 with a repeated-test warning, got {code}:\n{out}")

    code, out = run_case(program, tmp, modules, "empty", 2)
    # Playwright itself exits non-zero on "No tests found", so the program
    # refuses at the listing. Either refusal is the right direction.
    if code == 0 or not ("ZERO tests" in out or "Could not list" in out):
        failures.append(f"empty: expected a failure on zero tests, got {code}:\n{out}")

    return failures


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("workflow", nargs="?", default=".github/workflows/quality.yml")
    ap.add_argument("--positive-control", action="store_true")
    args = ap.parse_args()

    program = extract_program(Path(args.workflow))
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        modules = node_modules(tmp)

        if args.positive_control:
            if REFUSAL not in program:
                print(f"::error::the refusal this control removes is no longer in the program: {REFUSAL!r}")
                return 1
            neutered = program.replace(REFUSAL, "this leg refuses to run at all.\")")
            failures = assertions(neutered, tmp / "control", modules)
            if not any(f.startswith("lossy:") for f in failures):
                print("::error::with the refusal removed, the lossy case still passed this suite. It is not reading the program's verdict.")
                return 1
            print("OK: removing the refusal on a lost test makes this suite fail. Its clean pass is a verdict.")
            return 0

        failures = assertions(program, tmp, modules)

    for failure in failures:
        print(f"::error::{failure}")
    if failures:
        return 1
    print("OK: the shard partition step passes a lossless split, warns on a dependency, and fails on a lost test and on an empty suite.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
