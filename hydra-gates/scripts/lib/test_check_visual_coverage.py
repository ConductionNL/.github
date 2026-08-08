#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""test_check_visual_coverage.py — gate-26 helper self-tests.

WHY THIS EXISTS
===============
``check_visual_coverage.py`` shipped with no test suite at all, and it
returned its FINDING COUNT as its exit status:

    return count          # -> sys.exit(count)

An exit status is one byte. Measured on openregister 2026-08-08 by planting
uncovered page components under ``src/views/``:

    260 findings  ->  exit 4  ->  runner printed "FAIL — 4 new page component(s)"
    256 findings  ->  exit 0  ->  runner printed "[gate-26] visual-coverage: PASS"

while this helper's own stdout read ``FAIL — 256 new page component(s)`` on
the very same run. Two numbers for one measurement means one of them came
through a lossy channel. It is the identical defect ConductionNL/.github#209
fixed in gate-19's helper.

``test_the_256_case`` below is the one that matters: it constructs exactly the
count whose low byte is zero, so the pre-fix helper reports success. The other
tests keep the repair honest in the opposite direction — an empty scope is not
a pass, and a covered page is not a finding.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

# The expected statuses are written as LITERALS, deliberately. Importing the
# module's own EXIT_* names would make the test agree with whatever the module
# currently believes, and a suite that cannot disagree with its subject is not
# a test. These are the values the runner's gate-26 branch reads.
EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_EMPTY_SCOPE = 3

_passed = 0
_failed: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    global _passed
    if cond:
        _passed += 1
        print(f"  PASS  {name}")
    else:
        _failed.append(name)
        print(f"  FAIL  {name}{(' — ' + detail) if detail else ''}")


PAGE = """<template>
\t<div class="p">x</div>
</template>

<script>
export default {{ name: 'P{n}' }}
</script>
"""


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
    )


def _repo(n_pages: int, *, covered: bool = False) -> tempfile.TemporaryDirectory:
    """A git repo whose HEAD commit ADDS ``n_pages`` page components."""
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    (root / "src" / "views").mkdir(parents=True)
    (root / "README.md").write_text("base\n")
    # `git init -b` is not available on older gits in the fleet images.
    _git(["init", "-q"], root)
    _git(["add", "-A"], root)
    _git(["commit", "-qm", "base"], root)
    for i in range(1, n_pages + 1):
        (root / "src" / "views" / f"P{i}.vue").write_text(PAGE.format(n=i))
    if covered:
        vis = root / "tests" / "e2e" / "visual"
        vis.mkdir(parents=True)
        for i in range(1, n_pages + 1):
            (vis / f"p{i}.spec.js").write_text(
                f"test('P{i}', async () => {{ await expect(page)"
                f".toHaveScreenshot('P{i}.png') }})\n"
            )
    _git(["add", "-A"], root)
    _git(["commit", "-qm", "add pages", "--allow-empty"], root)
    return tmp


def _run(root: Path, base_ref: str | None) -> tuple[int, str]:
    env = dict(os.environ)
    env.pop("HYDRA_GATE_BASE_REF", None)
    if base_ref:
        env["HYDRA_GATE_BASE_REF"] = base_ref
    out = subprocess.run(
        [sys.executable, str(HERE / "check_visual_coverage.py"), str(root)],
        capture_output=True,
        text=True,
        env=env,
    )
    return out.returncode, out.stdout


def _reported_count(stdout: str) -> int | None:
    for line in stdout.splitlines():
        if "FAIL — " in line and "new page component" in line:
            return int(line.split("FAIL — ")[1].split()[0])
    return None


# ---------------------------------------------------------------------------
print("== gate-26 helper: an exit status is a STATUS, never a count ==")

with _repo(3) as t:
    rc, out = _run(Path(t), "HEAD~1")
    check(
        "3 uncovered pages -> exit status 1 (FAIL), not 3",
        rc == EXIT_FAIL,
        f"rc={rc}",
    )
    check("the count travels on stdout", _reported_count(out) == 3, out.strip()[-120:])

with _repo(256) as t:
    rc, out = _run(Path(t), "HEAD~1")
    # THE MUTANT-KILLING CASE. Pre-fix this returned 256, whose low byte is 0,
    # so the process exited SUCCESS and the runner printed PASS.
    check(
        "256 uncovered pages -> exit status 1, NOT 0 (the byte-wrap false green)",
        rc == EXIT_FAIL,
        f"rc={rc} — pre-fix this was 0 and gate-26 reported PASS",
    )
    check(
        "the helper still reports all 256 on stdout",
        _reported_count(out) == 256,
        out.strip()[-120:],
    )

with _repo(260) as t:
    rc, _ = _run(Path(t), "HEAD~1")
    check(
        "260 uncovered pages -> exit status 1, not 4 (260 mod 256)",
        rc == EXIT_FAIL,
        f"rc={rc}",
    )

# ---------------------------------------------------------------------------
print("== gate-26 helper: an empty scope is not a pass (#268) ==")

with _repo(0) as t:
    rc, out = _run(Path(t), "HEAD~1")
    check(
        "a diff that ADDS no page component -> EXIT_EMPTY_SCOPE, not PASS",
        rc == EXIT_EMPTY_SCOPE,
        f"rc={rc}",
    )
    check("...and says so", "EMPTY SCOPE" in out or "NOT APPLICABLE" in out, out.strip())

# ---------------------------------------------------------------------------
print("== gate-26 helper: covered pages pass (no widening) ==")

with _repo(3, covered=True) as t:
    rc, out = _run(Path(t), "HEAD~1")
    check("3 pages each with a visual baseline -> PASS", rc == EXIT_PASS, out.strip())

# ---------------------------------------------------------------------------
print("== gate-26 helper: no base ref means FULL TREE, not a silent diff (#242) ==")

with _repo(3) as t:
    # The pages are in the FIRST-PARENT history, so a diff against HEAD finds
    # nothing added. An unscoped caller must still see all three.
    rc, out = _run(Path(t), None)
    check(
        "no HYDRA_GATE_BASE_REF -> every page in the tree is audited",
        rc == EXIT_FAIL and _reported_count(out) == 3,
        f"rc={rc} out={out.strip()[-140:]}",
    )

with _repo(3, covered=True) as t:
    rc, out = _run(Path(t), None)
    check(
        "full-tree mode still passes when every page is baselined",
        rc == EXIT_PASS,
        out.strip()[-140:],
    )

print()
print(f"{_passed}/{_passed + len(_failed)} passed")
if _failed:
    print("FAILED: " + ", ".join(_failed))
    sys.exit(1)
sys.exit(0)
