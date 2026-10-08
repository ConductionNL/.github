#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Run quality.yml's SHIPPED test-count steps against real tool output.

WHY
---
The Quality Report shows `passed/run` behind each test row. Four inline
programs in quality.yml produce it: one "Record test counts" step each in the
phpunit, newman and playwright jobs, which parse the tool's own output, and
"Compute test counts" in the report job, which turns the recorded files into
the cell. Each one reads a format another project owns, and a misreading is
silent: Newman's `stats.assertions.pending` looks like a skip count and is 0 at
the end of every run, so a skipped assertion read as a passed one.

This suite extracts each program from quality.yml by its step `id:` and runs
THAT, the way run-derive-step.py and test-e2e-shard-partition.py do. There is
no second copy of the logic to drift. Extraction is strict: a missing id, a
missing heredoc or an empty body is a failure, never a skipped case.

FIXTURES (scripts/fixtures/test-counts/), all real tool output:

  phpunit-10.5-junit.xml       PHPUnit 10.5.63 `--log-junit`: 2 passing, 1
                               `markTestSkipped`, 1 failing test. Only the
                               absolute paths in `file=` were shortened.
  newman-6.2.2-export.json     newman 6.2.2 `--reporters json` for
                               newman-skip.postman_collection.json: one passing
                               `pm.test`, one `pm.test.skip`, one failing.
  playwright-report/index.html Playwright 1.63.0 HTML report, cut down to its
                               embedded result blob. Six tests: 1 passed, 1
                               failed, 1 `test.skip(true, reason)`, 1
                               `test.fixme`, and in a serial suite with
                               `globalTimeout: 4000` one test interrupted by the
                               timeout and one never started.

--positive-control applies a battery of mutations to the extracted programs,
each one re-introducing a known defect, and requires the case named for it to
go red. A suite whose clean pass survives a mutation is not reading the
programs' output.

Usage:  test-quality-test-counts.py [--positive-control] [workflow.yml]
Needs:  python3 with PyYAML.
Exit:   0 all assertions hold, 1 at least one failed.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "scripts" / "fixtures" / "test-counts"
HEREDOC_OPEN = "<<'PYEOF'"
HEREDOC_CLOSE = "PYEOF"
STEPS = {
    "phpunit": "test-counts-phpunit",
    "newman": "test-counts-newman",
    "playwright": "test-counts-playwright",
    "compute": "test-counts",
}
BLOB = re.compile(r"(data:application/zip;base64,)([A-Za-z0-9+/=]+)")

# (program, anchor, replacement, case that must go red, what it re-introduces)
MUTATIONS = [
    ("newman", "skipped += skipped_here", 'skipped += int(assertions.get("pending") or 0)',
     "newman-real", "read Newman's in-flight `pending` counter as the skip count"),
    ("compute", "if len(legs) < expected:", "if False:",
     "cell-missing-leg", "no comparison against the recorded matrix size"),
    ("compute", " and len(legs) >= expected and ", " and ",
     "cell-missing-leg", "a leg with no file still reads as a complete matrix"),
    ("playwright", 'tally["skipped" if deliberate(test) else "not_run"] += 1', 'tally["skipped"] += 1',
     "playwright-real", "every `skipped` outcome counted as a deliberate skip"),
    ("playwright", 'if result.get("status") == "interrupted":', "if False:",
     "playwright-interrupted", "an interrupted result read as a deliberate skip"),
    ("playwright", "except (binascii.Error, zipfile.BadZipFile):", "except ImportError:",
     "playwright-truncated", "a truncated blob crashes the step"),
    ("compute", "if missing:", "if False:",
     "cell-null-leg", "a leg recorded without counts is dropped from the cell"),
]


def extract(workflow: Path, step_id: str) -> str:
    """Return the Python inside the `<<'PYEOF'` heredoc of the step with this id."""
    data = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    matches = [
        step
        for job in (data.get("jobs") or {}).values()
        for step in (job.get("steps") or [])
        if step.get("id") == step_id
    ]
    if len(matches) != 1:
        raise SystemExit(f"FATAL: expected exactly one step with id {step_id!r} in {workflow}, found {len(matches)}.")
    run = matches[0].get("run") or ""
    if HEREDOC_OPEN not in run:
        raise SystemExit(f"FATAL: step {step_id!r} no longer opens a {HEREDOC_OPEN} heredoc.")
    lines = run.split(HEREDOC_OPEN, 1)[1].split("\n", 1)[1].split("\n")
    if HEREDOC_CLOSE not in lines:
        raise SystemExit(f"FATAL: step {step_id!r} has no {HEREDOC_CLOSE} terminator in column 0.")
    body = "\n".join(lines[: lines.index(HEREDOC_CLOSE)]).strip()
    if not body:
        raise SystemExit(f"FATAL: step {step_id!r} has an empty program.")
    return body + "\n"


class Runner:
    def __init__(self, programs: dict[str, str], tmp: Path) -> None:
        self.programs = programs
        self.tmp = tmp
        self.n = 0

    def case_dir(self, name: str) -> Path:
        self.n += 1
        d = self.tmp / f"{self.n:02d}-{name}"
        (d / "test-counts").mkdir(parents=True)
        return d

    def run(self, program: str, cwd: Path, args: list[str] | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
        script = cwd / f"{program}.py"
        script.write_text(self.programs[program], encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(script), *(args or [])],
            cwd=cwd, env={"PATH": "/usr/bin:/bin", **(env or {})}, capture_output=True, text=True,
        )


def read_counts(d: Path) -> dict:
    files = sorted((d / "test-counts").glob("*.json"))
    if len(files) != 1:
        return {"_error": f"expected one count file, found {[f.name for f in files]}"}
    return json.loads(files[0].read_text(encoding="utf-8"))


def compute(r: Runner, name: str, files: dict[str, dict], results: dict[str, str]) -> tuple[int, dict[str, str], str]:
    d = r.case_dir(name)
    for fname, payload in files.items():
        (d / "test-counts" / fname).write_text(json.dumps(payload), encoding="utf-8")
    env = {"GITHUB_ENV": str(d / "github-env")}
    env.update({f"{k.upper()}_RESULT": v for k, v in results.items()})
    proc = r.run("compute", d, env=env)
    cells: dict[str, str] = {}
    if (d / "github-env").is_file():
        for line in (d / "github-env").read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            cells[key] = value
    return proc.returncode, cells, proc.stdout + proc.stderr


def report_html(mutate=None, blob_text: str | None = None) -> str:
    """The fixture report, optionally with its zip's per-file JSON rewritten."""
    html = (FIXTURES / "playwright-report" / "index.html").read_text(encoding="utf-8")
    if blob_text is not None:
        return BLOB.sub(lambda m: m.group(1) + blob_text, html)
    if mutate is None:
        return html
    src = zipfile.ZipFile(io.BytesIO(base64.b64decode(BLOB.search(html).group(2))))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as out:
        for name in src.namelist():
            data = src.read(name)
            if name.endswith(".json") and name != "report.json":
                payload = json.loads(data)
                for test in payload.get("tests") or []:
                    mutate(test)
                data = json.dumps(payload).encode()
            out.writestr(name, data)
    return BLOB.sub(lambda m: m.group(1) + base64.b64encode(buf.getvalue()).decode(), html)


def playwright(r: Runner, name: str, html: str | None, shard: str = "1", total: str = "1") -> tuple[int, dict, str]:
    d = r.case_dir(name)
    app = d / "app"
    if html is not None:
        (app / "playwright-report").mkdir(parents=True)
        (app / "playwright-report" / "index.html").write_text(html, encoding="utf-8")
    else:
        app.mkdir()
    proc = r.run("playwright", d, env={"SHARD": shard, "TOTAL": total, "APP_DIR": str(app)})
    return proc.returncode, read_counts(d) if proc.returncode == 0 else {}, proc.stdout + proc.stderr


def assertions(programs: dict[str, str], tmp: Path) -> dict[str, str]:
    """Return {case: failure} for every case that does not hold."""
    r = Runner(programs, tmp)
    failures: dict[str, str] = {}

    def check(case: str, ok: bool, detail: str) -> None:
        if not ok:
            failures[case] = detail

    # ── PHPUnit ────────────────────────────────────────────────────────────
    d = r.case_dir("phpunit-real")
    out = d / "test-counts" / "phpunit-leg.json"
    proc = r.run("phpunit", d, [str(FIXTURES / "phpunit-10.5-junit.xml")], {"LEG": "PHP 8.3", "TOTAL": "4", "OUT": str(out)})
    got = read_counts(d) if proc.returncode == 0 else {}
    want = {"leg": "PHP 8.3", "run": 3, "passed": 2, "failed": 1, "skipped": 1, "total": 4}
    check("phpunit-real", got == want, f"want {want}, got exit {proc.returncode} {got}\n{proc.stderr}")
    phpunit_real = got

    d = r.case_dir("phpunit-no-junit")
    out = d / "test-counts" / "phpunit-leg.json"
    proc = r.run("phpunit", d, [str(d / "absent.xml")], {"LEG": "PHP 8.4", "TOTAL": "2", "OUT": str(out)})
    got = read_counts(d) if proc.returncode == 0 else {}
    check("phpunit-no-junit", got == {"leg": "PHP 8.4", "run": None, "total": 2},
          f"want run null with total 2, got exit {proc.returncode} {got}\n{proc.stderr}")

    # ── Newman ─────────────────────────────────────────────────────────────
    def newman(case: str, exports: int, ran: str) -> tuple[int, dict, str]:
        d = r.case_dir(case)
        (d / "json").mkdir()
        for i in range(1, exports + 1):
            shutil.copy(FIXTURES / "newman-6.2.2-export.json", d / "json" / f"{i}.json")
        (d / "ran").write_text(ran, encoding="utf-8")
        proc = r.run("newman", d, [str(d / "json"), str(d / "ran")])
        return proc.returncode, read_counts(d) if proc.returncode == 0 else {}, proc.stdout + proc.stderr

    code, got, log = newman("newman-real", 1, "1\n")
    want = {"leg": "newman", "run": 2, "passed": 1, "failed": 1, "skipped": 1, "errors": 0, "reported": 1, "expected": 1}
    check("newman-real", got == want, f"want {want}, got exit {code} {got}\n{log}")
    newman_real = got

    code, got, log = newman("newman-missing-export", 1, "2\n")
    check("newman-missing-export", got.get("reported") == 1 and got.get("expected") == 2,
          f"want reported 1 of expected 2, got exit {code} {got}\n{log}")

    code, got, log = newman("newman-none", 0, "1\n")
    check("newman-none", got == {"leg": "newman", "run": None}, f"want run null, got exit {code} {got}\n{log}")

    # ── Playwright ─────────────────────────────────────────────────────────
    code, got, log = playwright(r, "playwright-real", report_html())
    want = {"leg": "shard 1", "run": 2, "passed": 1, "failed": 1, "skipped": 2, "not_run": 2, "total": 1}
    check("playwright-real", got == want, f"want {want}, got exit {code} {got}\n{log}")
    playwright_real = got

    # Playwright 1.63 reports the globalTimeout victim as a `skipped` result;
    # older runs and a Ctrl-C write `interrupted`. Give the annotated skip an
    # `interrupted` result so only the status check can tell it apart.
    def interrupt_the_skip(test: dict) -> None:
        if test.get("title") == "skipped with a reason":
            for result in test.get("results") or []:
                result["status"] = "interrupted"
    code, got, log = playwright(r, "playwright-interrupted", report_html(mutate=interrupt_the_skip))
    check("playwright-interrupted", got.get("skipped") == 1 and got.get("not_run") == 3,
          f"want skipped 1, not_run 3, got exit {code} {got}\n{log}")

    blob = BLOB.search(report_html()).group(2)
    cut = blob[: len(blob) // 2]
    while len(cut) % 4 == 0:
        cut = cut[:-1]
    for case, text in (("playwright-truncated", cut), ("playwright-not-a-zip", base64.b64encode(b"not a zip").decode())):
        code, got, log = playwright(r, case, report_html(blob_text=text), shard="2", total="2")
        check(case, code == 0 and got == {"leg": "shard 2", "run": None, "total": 2},
              f"want exit 0 and run null, got exit {code} {got}\n{log}")

    code, got, log = playwright(r, "playwright-no-report", None)
    check("playwright-no-report", code == 0 and got.get("run", "x") is None, f"want run null, got exit {code} {got}\n{log}")

    # ── Compute test counts: cell() ────────────────────────────────────────
    leg = lambda name, run, passed, failed=0, skipped=0, total=2, **kw: {  # noqa: E731
        "leg": name, "run": run, "passed": passed, "failed": failed, "skipped": skipped, "total": total, **kw}

    code, cells, log = compute(r, "cell-end-to-end",
                               {"phpunit-a.json": phpunit_real, "newman.json": newman_real,
                                "playwright-shard-1.json": playwright_real},
                               {"phpunit": "failure", "newman": "failure", "playwright": "failure"})
    want = {"PHPUNIT_COUNTS": "2/3 · 1 skipped (counts from 1 of 4 legs)",
            "NEWMAN_COUNTS": "1/2 · 1 skipped",
            "PLAYWRIGHT_COUNTS": "1/2 · 2 skipped · 2 did not run"}
    check("cell-end-to-end", code == 0 and cells == want, f"want {want}, got exit {code} {cells}\n{log}")

    code, cells, log = compute(r, "cell-missing-leg", {"phpunit-a.json": leg("PHP 8.3", 412, 412)}, {"phpunit": "failure"})
    cell = cells.get("PHPUNIT_COUNTS", "")
    check("cell-missing-leg", "1 of 2 legs" in cell and "no test failed" not in cell,
          f"want '1 of 2 legs' and no 'no test failed' note, got {cell!r}\n{log}")

    code, cells, log = compute(r, "cell-null-leg",
                               {"phpunit-a.json": leg("PHP 8.3", 412, 412),
                                "phpunit-b.json": {"leg": "PHP 8.4", "run": None, "total": 2}},
                               {"phpunit": "failure"})
    cell = cells.get("PHPUNIT_COUNTS", "")
    check("cell-null-leg", "no counts from `PHP 8.4`" in cell and "no test failed" not in cell,
          f"want 'no counts from `PHP 8.4`' and no 'no test failed' note, got {cell!r}\n{log}")

    code, cells, log = compute(r, "cell-differing-legs",
                               {"phpunit-a.json": leg("PHP 8.3", 400, 400), "phpunit-b.json": leg("PHP 8.4", 412, 412)},
                               {"phpunit": "success"})
    check("cell-differing-legs", cells.get("PHPUNIT_COUNTS") == "412/412 (2 legs, 400–412 tests per leg)",
          f"got {cells.get('PHPUNIT_COUNTS')!r}\n{log}")

    code, cells, log = compute(r, "cell-worst-leg",
                               {"phpunit-a.json": leg("PHP 8.3", 412, 412), "phpunit-b.json": leg("PHP 8.4", 412, 409, failed=3)},
                               {"phpunit": "failure"})
    check("cell-worst-leg", cells.get("PHPUNIT_COUNTS") == "409/412 (worst of 2 legs: PHP 8.4)",
          f"got {cells.get('PHPUNIT_COUNTS')!r}\n{log}")

    code, cells, log = compute(r, "cell-failed-job-green-tests",
                               {"phpunit-a.json": leg("PHP 8.3", 412, 412, total=1)}, {"phpunit": "failure"})
    check("cell-failed-job-green-tests",
          cells.get("PHPUNIT_COUNTS") == "412/412 (no test failed, the job failed for another reason — see its log)",
          f"got {cells.get('PHPUNIT_COUNTS')!r}\n{log}")

    code, cells, log = compute(r, "cell-cancelled", {"phpunit-a.json": leg("PHP 8.3", 412, 412, total=1)}, {"phpunit": "cancelled"})
    check("cell-cancelled", code == 0 and cells.get("PHPUNIT_COUNTS", "x") == "", f"want an empty cell, got {cells}\n{log}")

    code, cells, log = compute(r, "cell-no-files", {}, {"phpunit": "failure", "newman": "success", "playwright": "failure"})
    check("cell-no-files", code == 0 and set(cells.values()) == {""} and len(cells) == 3, f"want three empty cells, got {cells}\n{log}")

    code, cells, log = compute(r, "cell-missing-shard",
                               {"playwright-shard-1.json": leg("shard 1", 10, 10, total=3)}, {"playwright": "success"})
    check("cell-missing-shard", cells.get("PLAYWRIGHT_COUNTS") == "10/10 (counts from 1 of 3 shards)",
          f"got {cells.get('PLAYWRIGHT_COUNTS')!r}\n{log}")

    code, cells, log = compute(r, "cell-not-run",
                               {"playwright-shard-1.json": leg("shard 1", 10, 10, total=1, not_run=4)}, {"playwright": "failure"})
    check("cell-not-run", cells.get("PLAYWRIGHT_COUNTS") == "10/10 · 4 did not run",
          f"got {cells.get('PLAYWRIGHT_COUNTS')!r}\n{log}")

    code, cells, log = compute(r, "cell-newman-missing-export",
                               {"newman.json": {"leg": "newman", "run": 5, "passed": 5, "failed": 0, "skipped": 0,
                                                "errors": 0, "reported": 1, "expected": 2}},
                               {"newman": "failure"})
    check("cell-newman-missing-export", cells.get("NEWMAN_COUNTS") == "5/5 (counts from 1 of 2 collections)",
          f"got {cells.get('NEWMAN_COUNTS')!r}\n{log}")

    return failures


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("workflow", nargs="?", default=str(ROOT / ".github" / "workflows" / "quality.yml"))
    ap.add_argument("--positive-control", action="store_true")
    args = ap.parse_args()

    programs = {name: extract(Path(args.workflow), step_id) for name, step_id in STEPS.items()}

    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        if args.positive_control:
            baseline = assertions(programs, tmp / "baseline")
            if baseline:
                for case, failure in baseline.items():
                    print(f"::error::{case} fails before any mutation, so no control can be read: {failure}")
                return 1
            bad = 0
            for i, (program, anchor, replacement, case, what) in enumerate(MUTATIONS):
                if programs[program].count(anchor) != 1:
                    print(f"::error::mutation {what!r}: anchor {anchor!r} is not in the {program} program exactly once.")
                    bad += 1
                    continue
                mutated = dict(programs, **{program: programs[program].replace(anchor, replacement)})
                failures = assertions(mutated, tmp / f"mutation-{i}")
                if case not in failures:
                    print(f"::error::mutation {what!r} left case {case!r} green. This suite is not reading that branch.")
                    bad += 1
                else:
                    print(f"OK: {what} -> {case} goes red.")
            if bad:
                return 1
            print(f"OK: all {len(MUTATIONS)} mutations turn their named case red. The clean pass is a verdict.")
            return 0

        failures = assertions(programs, tmp)

    for case, failure in failures.items():
        print(f"::error::{case}: {failure}")
    if failures:
        return 1
    print("OK: the four test-count steps read real PHPUnit, Newman and Playwright output and render every cell as asserted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
