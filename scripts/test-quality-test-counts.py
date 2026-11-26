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

A fifth program decides how many PHPUnit legs owe a count: the nextcloud-matrix
job's "Resolve the install-only database legs" (`database-legs`). Its list of
install-only legs is subtracted from the matrix size, so a caller that sets
only database-test-matrix, or nothing, must get no legs and the full total.

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

The Playwright step carries a copy of hydra-gates' check_e2e_skips.py report
parser. The case `playwright-agrees-with-gate` runs the gate's own collect()
on the same report and requires the two to agree.

Usage:  test-quality-test-counts.py [--positive-control] [workflow.yml]
Needs:  python3 with PyYAML.
Exit:   0 all assertions hold, 1 at least one failed.
"""

from __future__ import annotations

import argparse
import base64
import importlib.util
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
GATE = ROOT / "hydra-gates" / "scripts" / "lib" / "check_e2e_skips.py"
HEREDOC_OPEN = "<<'PYEOF'"
HEREDOC_CLOSE = "PYEOF"
STEPS = {
    "phpunit": "test-counts-phpunit",
    "newman": "test-counts-newman",
    "playwright": "test-counts-playwright",
    "compute": "test-counts",
    # The nextcloud-matrix job's resolver for database-install-matrix. Its
    # output is the phpunit job's `include:` list and the EXTRA_LEGS the
    # phpunit program subtracts, so it decides every leg's `total`.
    "legs": "database-legs",
}
BLOB = re.compile(r"(data:application/zip;base64,)([A-Za-z0-9+/=]+)")

# (program, anchor, replacement, case that must go red, what it re-introduces)
MUTATIONS = [
    ("newman", "skipped += skipped_here", 'skipped += int(assertions.get("pending") or 0)',
     "newman-real", "read Newman's in-flight `pending` counter as the skip count"),
    ("compute", "if rows < expected:", "if False:",
     "cell-missing-leg", "no comparison against the recorded matrix size"),
    ("compute", "if n not in numbers:", "if False:",
     "cell-sharded-missing-shard", "a shard that left no file missing from the lines"),
    ("compute", "for g in set(groups) - set(seen)]", "for g in ()]",
     "cell-sharded-missing-leg", "a leg whose every shard left no file not named"),
    ("phpunit", 'shard["groups"] = ', "_ = ",
     "phpunit-sharded-groups", "a shard recorded without the matrix's legs"),
    ("compute", "crashed.append(dict(", "missing.append(str(",
     "playwright-crashed-shard", "a crashed shard left out of the lines"),
    ("compute", "bullets = shard_lines(legs, crashed, 1)", "pass",
     "playwright-sharded-failing", "Playwright's failing shards not named"),
    ("compute", 'failed = [r for r in rows if r.get("shard") and r["failed"]]', "failed = []",
     "cell-sharded-failing-shard", "a failing shard not named in the cell"),
    ("compute", 'elif e.get("failures") is not None and e.get("errored") is not None:', "elif False:",
     "list-one-leg", "a shard's failures and errors read as one number"),
    ("compute", "raw, legs = legs, by_leg(legs)", "raw = legs",
     "cell-sharded-green", "a sharded leg's shards read as separate legs"),
    ("phpunit", 'if os.environ.get("SHARDS"):', "if False:",
     "phpunit-sharded", "a shard's count recorded without its shard"),
    ("compute", " and len(legs) >= expected and ", " and ",
     "cell-missing-leg", "a leg with no file still reads as a complete matrix"),
    ("playwright", 'tally["skipped" if deliberate(test) else "not_run"] += 1', 'tally["skipped"] += 1',
     "playwright-real", "every `skipped` outcome counted as a deliberate skip"),
    ("playwright", 'if result.get("status") == "interrupted":', "if False:",
     "playwright-interrupted", "an interrupted result read as a deliberate skip"),
    ("playwright", "except (binascii.Error, zipfile.BadZipFile):", "except ImportError:",
     "playwright-truncated", "a truncated blob crashes the step"),
    ("playwright", 'elif outcome == "skipped":', 'elif outcome in ("skipped", "unexpected"):',
     "playwright-agrees-with-gate", "the copied parser drifts from check_e2e_skips.py on what executed"),
    ("compute", "if missing:", "if False:",
     "cell-null-leg", "a leg recorded without counts is dropped from the cell"),
    ("phpunit", 'total -= len(json.loads(os.environ.get("EXTRA_LEGS") or "[]"))', "pass",
     "phpunit-extra-database-legs", "install-only database legs counted as legs that owe a count"),
    ("legs", 'os.environ.get("INSTALL_MATRIX", "")', 'os.environ.get("TEST_MATRIX", "")',
     "legs-test-matrix-only", "database-test-matrix entries turned into install-only legs"),
    ("legs", "if both:", "if False:",
     "legs-overlap", "an install-only leg accepted on a database that already runs the full suite"),
    ("legs", 'else [os.environ.get("DATABASE", "").strip()]', "else []",
     "legs-overlap-single-database", "the single `database` input left out of the full-suite databases"),
    ("legs", "if bad:", "if False:",
     "legs-unsupported", "an install-only leg accepted on a database outside the allow-list"),
    ("legs", "if dupes:", "if False:",
     "legs-duplicate", "the same install-only database accepted twice"),
    ("legs", "if dbs is not None and not isinstance(dbs, list):", "if False:",
     "legs-install-string", "a non-array database-install-matrix read as a list"),
    ("legs", "if not isinstance(tests, list):", "if False:",
     "legs-test-matrix-not-array", "a non-array database-test-matrix read as a list"),
    ("legs", "if not single:", "if False:",
     "legs-no-single-server", "install-only legs emitted with no Nextcloud branch to run on"),
    ("legs", "except json.JSONDecodeError as exc:", "except ImportError as exc:",
     "legs-install-invalid-json", "an invalid database-install-matrix crashes the step before extra-legs is written"),
    ("legs", "if dbs is not None and not isinstance(dbs, list):", "if isinstance(dbs, str):",
     "legs-install-object", "a JSON object database-install-matrix read as an empty list"),
    ("legs", "except json.JSONDecodeError:", "except ImportError:",
     "legs-test-matrix-invalid-json", "an invalid database-test-matrix crashes the step before extra-legs is written"),
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

    # Install-only extra database legs record nothing, so a counted leg must
    # not expect them: 6 legs in the job, 2 of them extra, 4 to count.
    extra = json.dumps([{"php-version": "8.3", "nextcloud-ref": "stable34", "database": db, "extra-database": True}
                        for db in ("mysql", "mariadb")])
    d = r.case_dir("phpunit-extra-database-legs")
    out = d / "test-counts" / "phpunit-leg.json"
    proc = r.run("phpunit", d, [str(FIXTURES / "phpunit-10.5-junit.xml")],
                 {"LEG": "PHP 8.3", "TOTAL": "6", "EXTRA_LEGS": extra, "OUT": str(out)})
    got = read_counts(d) if proc.returncode == 0 else {}
    check("phpunit-extra-database-legs", got.get("total") == 4,
          f"want total 4 (6 legs minus 2 install-only), got exit {proc.returncode} {got}\n{proc.stderr}")

    # ── database-install-matrix legs, and the `total` they leave ───────────
    def legs(case: str, env: dict[str, str]) -> tuple[int, object, str]:
        d = r.case_dir(case)
        out = d / "github-output"
        proc = r.run("legs", d, env={"GITHUB_OUTPUT": str(out), "PHP_VERSION": "8.3", "SINGLE": "stable34",
                                     "DATABASE": "pgsql", **env})
        value = None
        if out.is_file():
            for line in out.read_text(encoding="utf-8").splitlines():
                if line.startswith("extra-legs="):
                    value = json.loads(line.partition("=")[2])
        return proc.returncode, value, proc.stdout + proc.stderr

    def total_after(case: str, extra: object, job_total: int) -> object:
        d = r.case_dir(case + "-total")
        out = d / "test-counts" / "phpunit-leg.json"
        proc = r.run("phpunit", d, [str(FIXTURES / "phpunit-10.5-junit.xml")],
                     {"LEG": "PHP 8.3", "TOTAL": str(job_total), "EXTRA_LEGS": json.dumps(extra), "OUT": str(out)})
        return read_counts(d).get("total") if proc.returncode == 0 else f"exit {proc.returncode}"

    # A caller that sets nothing: no legs, and every leg owes a count, as on
    # main (2 PHP x 3 Nextcloud on pgsql).
    code, got, log = legs("legs-nothing-set", {})
    total = total_after("legs-nothing-set", got, 6)
    check("legs-nothing-set", code == 0 and got == [] and total == 6,
          f"want exit 0, [] and total 6, got exit {code}, {got}, total {total}\n{log}")

    # A caller that sets only database-test-matrix, as openregister, launchpad
    # and keepiq do: every listed database runs the full suite, so there are
    # no install legs and `total` is the whole matrix (2 x 3 x 3 = 18).
    code, got, log = legs("legs-test-matrix-only", {"TEST_MATRIX": '["pgsql", "mysql", "sqlite"]'})
    total = total_after("legs-test-matrix-only", got, 18)
    check("legs-test-matrix-only", code == 0 and got == [] and total == 18,
          f"want exit 0, [] and total 18, got exit {code}, {got}, total {total}\n{log}")

    # One install-only leg on the primary PHP and newest Nextcloud; the 6
    # pgsql legs owe a count, the mariadb leg does not (7 - 1).
    code, got, log = legs("legs-install-one", {"INSTALL_MATRIX": '["mariadb"]'})
    want = [{"php-version": "8.3", "nextcloud-ref": "stable34", "database": "mariadb", "extra-database": True}]
    total = total_after("legs-install-one", got, 7)
    check("legs-install-one", code == 0 and got == want and total == 6,
          f"want exit 0, {want} and total 6, got exit {code}, {got}, total {total}\n{log}")

    # A database in both lists would merge into its full-suite leg through
    # `include:`. Refused, and no legs are written.
    code, got, log = legs("legs-overlap", {"INSTALL_MATRIX": '["mysql"]', "TEST_MATRIX": '["pgsql", "mysql"]'})
    check("legs-overlap", code == 1 and got == []
          and "already run the full test suite through database-test-matrix" in log,
          f"want exit 1, [] and the overlap error naming database-test-matrix, got exit {code}, {got}\n{log}")

    # Every other refusal: exit 1, still `extra-legs=[]` (written before the
    # exit, so the phpunit matrix expands without install legs), and the
    # error that names the problem. DATABASE is pgsql unless a case says so.
    refusals = [
        # No database-test-matrix, so the single `database` input runs the
        # full suite; an install-only leg on it is the same overlap.
        ("legs-overlap-single-database", {"INSTALL_MATRIX": '["pgsql"]'},
         "already run the full test suite through the `database` input"),
        ("legs-unsupported", {"INSTALL_MATRIX": '["oci"]'}, "unsupported entries ['oci']"),
        ("legs-duplicate", {"INSTALL_MATRIX": '["mariadb", "mariadb"]'}, "lists ['mariadb'] more than once"),
        ("legs-install-invalid-json", {"INSTALL_MATRIX": '["mariadb"'}, "database-install-matrix is not valid JSON"),
        ("legs-install-string", {"INSTALL_MATRIX": '"mariadb"'}, "database-install-matrix is not a JSON array"),
        ("legs-install-object", {"INSTALL_MATRIX": '{}'}, "database-install-matrix is not a JSON array"),
        ("legs-test-matrix-not-array", {"INSTALL_MATRIX": '["mariadb"]', "TEST_MATRIX": '"pgsql"'},
         "database-test-matrix is not a JSON array"),
        ("legs-test-matrix-invalid-json", {"INSTALL_MATRIX": '["mariadb"]', "TEST_MATRIX": '["pgsql"'},
         "database-test-matrix is not a JSON array"),
        ("legs-no-single-server", {"INSTALL_MATRIX": '["mariadb"]', "SINGLE": ""}, "no newest Nextcloud branch was resolved"),
    ]
    for case, env, error in refusals:
        code, got, log = legs(case, env)
        check(case, code == 1 and got == [] and error in log,
              f"want exit 1, [] and {error!r}, got exit {code}, {got}\n{log}")

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

    # The shard step carries a copy of check_e2e_skips.py's report parser.
    # Run the gate's own collect() on the same report: the two must agree on
    # what executed and on what did not (the copy splits the gate's skipped
    # into deliberate skips and tests that did not run).
    if not GATE.is_file():
        failures["playwright-agrees-with-gate"] = f"{GATE} is missing, so the copy cannot be compared."
    else:
        spec = importlib.util.spec_from_file_location("check_e2e_skips", GATE)
        gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gate)
        files = gate.collect(gate._load_report(FIXTURES / "playwright-report"))
        executed = sum(f["executed"] for f in files.values())
        skipped = sum(f["skipped"] for f in files.values())
        ours = (playwright_real.get("run"), (playwright_real.get("skipped") or 0) + (playwright_real.get("not_run") or 0))
        check("playwright-agrees-with-gate", files and ours == (executed, skipped),
              f"gate executed {executed}, skipped {skipped}; shard step run, skipped + not_run = {ours}")

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
    check("cell-missing-shard", cells.get("PLAYWRIGHT_COUNTS")
          == "10/10 (counts from 1 of 3 shards)<br>3 shards in total:<br>• Shard 2: no test report<br>• Shard 3: no test report",
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

    # ── phpunit-shards: one row per shard, the leg is their sum ───────────
    d = r.case_dir("phpunit-sharded")
    out = d / "test-counts" / "phpunit-leg.json"
    proc = r.run("phpunit", d, [str(FIXTURES / "phpunit-10.5-junit.xml")],
                 {"LEG": "PHP 8.3, NC stable35, pgsql, shard 2 of 3", "GROUP": "PHP 8.3, NC stable35, pgsql",
                  "SHARD": "2", "SHARDS": "3", "TOTAL": "3", "OUT": str(out)})
    got = read_counts(d)
    check("phpunit-sharded", got.get("group") == "PHP 8.3, NC stable35, pgsql" and got.get("shard") == 2
          and got.get("shards") == 3 and got.get("run") == phpunit_real.get("run")
          and got.get("failures") == 1 and got.get("errored") == 0,
          f"want the counts with group, shard 2 and shards 3, got exit {proc.returncode} {got}\n{proc.stderr}")

    d = r.case_dir("phpunit-sharded-no-junit")
    out = d / "test-counts" / "phpunit-leg.json"
    proc = r.run("phpunit", d, [str(d / "absent.xml")],
                 {"LEG": "PHP 8.3, NC stable35, pgsql, shard 3 of 3", "GROUP": "PHP 8.3, NC stable35, pgsql",
                  "SHARD": "3", "SHARDS": "3", "TOTAL": "3", "OUT": str(out)})
    got = read_counts(d)
    check("phpunit-sharded-no-junit", got.get("run", "x") is None and got.get("shard") == 3,
          f"want run null on shard 3, got exit {proc.returncode} {got}\n{proc.stderr}")

    # Every shard lists all legs of the matrix, built from its three vectors.
    d = r.case_dir("phpunit-sharded-groups")
    out = d / "test-counts" / "phpunit-leg.json"
    proc = r.run("phpunit", d, [str(d / "absent.xml")],
                 {"LEG": "PHP 8.3, NC stable35, pgsql, shard 1 of 2", "GROUP": "PHP 8.3, NC stable35, pgsql",
                  "SHARD": "1", "SHARDS": "2", "TOTAL": "8", "OUT": str(out),
                  "GROUP_PHP": '["8.3","8.4"]', "GROUP_NEXTCLOUD": '["stable34","stable35"]', "GROUP_DATABASE": '["pgsql"]'})
    got = read_counts(d)
    want = ["PHP 8.3, NC stable34, pgsql", "PHP 8.3, NC stable35, pgsql", "PHP 8.4, NC stable34, pgsql", "PHP 8.4, NC stable35, pgsql"]
    check("phpunit-sharded-groups", got.get("groups") == want,
          f"want every leg of the matrix {want}, got exit {proc.returncode} {got}\n{proc.stderr}")

    shard = lambda n, run, passed, failed=0, of=3, group="PHP 8.3, NC stable35, pgsql": leg(  # noqa: E731
        f"{group}, shard {n} of {of}", run, passed, failed, total=of, group=group, shard=n, shards=of)

    code, cells, log = compute(r, "cell-sharded-green",
                               {"phpunit-1.json": shard(1, 100, 100), "phpunit-2.json": shard(2, 150, 150),
                                "phpunit-3.json": shard(3, 162, 162)},
                               {"phpunit": "success"})
    check("cell-sharded-green", cells.get("PHPUNIT_COUNTS") == "412/412",
          f"want the three shards added up to one leg, got {cells.get('PHPUNIT_COUNTS')!r}\n{log}")

    code, cells, log = compute(r, "cell-sharded-failing-shard",
                               {"phpunit-1.json": shard(1, 100, 100), "phpunit-2.json": shard(2, 150, 147, failed=3),
                                "phpunit-3.json": shard(3, 162, 162)},
                               {"phpunit": "failure"})
    check("cell-sharded-failing-shard", cells.get("PHPUNIT_COUNTS") == "409/412<br>3 shards in total:<br>• Shard 2: 3 failed tests",
          f"got {cells.get('PHPUNIT_COUNTS')!r}\n{log}")

    other = "PHP 8.4, NC stable35, pgsql"
    code, cells, log = compute(r, "cell-sharded-two-legs",
                               {"phpunit-a1.json": shard(1, 200, 200, of=2), "phpunit-a2.json": shard(2, 212, 212, of=2),
                                "phpunit-b1.json": shard(1, 200, 200, of=2, group=other),
                                "phpunit-b2.json": shard(2, 212, 211, failed=1, of=2, group=other)},
                               {"phpunit": "failure"})
    want = f"411/412 (worst of 2 legs: {other})<br>2 shards per leg:<br>• {other}, shard 2: 1 failed test"
    check("cell-sharded-two-legs", cells.get("PHPUNIT_COUNTS") == want,
          f"want {want!r}, got {cells.get('PHPUNIT_COUNTS')!r}\n{log}")

    code, cells, log = compute(r, "cell-sharded-several-shards",
                               {"phpunit-1.json": shard(1, 100, 99, failed=1), "phpunit-2.json": shard(2, 150, 150),
                                "phpunit-3.json": shard(3, 162, 160, failed=2)},
                               {"phpunit": "failure"})
    check("cell-sharded-several-shards", cells.get("PHPUNIT_COUNTS") == "409/412<br>3 shards in total:<br>• Shard 1: 1 failed test<br>• Shard 3: 2 failed tests",
          f"got {cells.get('PHPUNIT_COUNTS')!r}\n{log}")

    many = {}
    for v, version in enumerate(("stable31", "stable32", "stable33", "stable34", "stable35")):
        for n in (1, 2):
            many[f"phpunit-{v}-{n}.json"] = shard(n, 206, 205, failed=1, of=2, group=f"PHP 8.3, NC {version}, pgsql")
            many[f"phpunit-{v}-{n}.json"]["total"] = 10
    code, cells, log = compute(r, "cell-sharded-many-legs", many, {"phpunit": "failure"})
    cell = cells.get("PHPUNIT_COUNTS", "")
    check("cell-sharded-many-legs", cell.count("<br>• ") == 9 and "<br>2 shards per leg:<br>" in cell and cell.endswith("<br>• … and 2 more shards"),
          f"want eight shards named and the other two counted, got {cell!r}\n{log}")

    # One line per failed shard in the cell, failures and errors apart, the
    # leg named only when there is more than one.
    errored = shard(2, 150, 143, failed=7)
    errored.update(failures=0, errored=7)
    failing = shard(3, 162, 161, failed=1)
    failing.update(failures=1, errored=0)
    code, cells, log = compute(r, "list-one-leg", {"phpunit-1.json": shard(1, 100, 100), "phpunit-2.json": errored,
                                                   "phpunit-3.json": failing}, {"phpunit": "failure"})
    want = "404/412<br>3 shards in total:<br>• Shard 2: 7 errors<br>• Shard 3: 1 failure"
    check("list-one-leg", cells.get("PHPUNIT_COUNTS") == want, f"want {want!r}, got {cells.get('PHPUNIT_COUNTS')!r}\n{log}")

    mixed = shard(1, 206, 203, failed=3, of=2, group=other)
    mixed.update(failures=2, errored=1)
    code, cells, log = compute(r, "list-two-legs",
                               {"phpunit-a1.json": shard(1, 206, 206, of=2), "phpunit-a2.json": shard(2, 206, 206, of=2),
                                "phpunit-b1.json": mixed, "phpunit-b2.json": shard(2, 206, 206, of=2, group=other)},
                               {"phpunit": "failure"})
    want = f"409/412 (worst of 2 legs: {other})<br>2 shards per leg:<br>• {other}, shard 1: 2 failures, 1 error"
    check("list-two-legs", cells.get("PHPUNIT_COUNTS") == want, f"want {want!r}, got {cells.get('PHPUNIT_COUNTS')!r}\n{log}")

    code, cells, log = compute(r, "cell-sharded-missing-shard",
                               {"phpunit-1.json": shard(1, 100, 100), "phpunit-2.json": shard(2, 150, 150)},
                               {"phpunit": "failure"})
    cell = cells.get("PHPUNIT_COUNTS", "")
    want = "250/250 (counts from 2 of 3 shards)<br>3 shards in total:<br>• Shard 3: no test report"
    check("cell-sharded-missing-shard", cell == want, f"want {want!r}, got {cell!r}\n{log}")

    code, cells, log = compute(r, "cell-sharded-null-shard",
                               {"phpunit-1.json": shard(1, 100, 100), "phpunit-2.json": shard(2, 150, 150),
                                "phpunit-3.json": {"leg": "PHP 8.3, NC stable35, pgsql, shard 3 of 3", "run": None, "total": 3,
                                                   "group": "PHP 8.3, NC stable35, pgsql", "shard": 3, "shards": 3}},
                               {"phpunit": "failure"})
    cell = cells.get("PHPUNIT_COUNTS", "")
    want = "250/250 (counts from 2 of 3 shards)<br>3 shards in total:<br>• Shard 3: no test report"
    check("cell-sharded-null-shard", cell == want, f"want the shard without counts as a line, {want!r}, got {cell!r}\n{log}")

    # A whole leg whose every shard died before uploading: only the matrix's
    # list of legs, recorded by the other leg's shards, can name it.
    both = ["PHP 8.3, NC stable35, pgsql", other]
    alone = {f"phpunit-a{n}.json": dict(shard(n, 206, 206, of=2), total=4, groups=both) for n in (1, 2)}
    code, cells, log = compute(r, "cell-sharded-missing-leg", alone, {"phpunit": "failure"})
    want = f"412/412 (counts from 2 of 4 shards)<br>2 shards per leg:<br>• {other}: no test report from any shard"
    check("cell-sharded-missing-leg", cells.get("PHPUNIT_COUNTS") == want,
          f"want the leg that left no file named, {want!r}, got {cells.get('PHPUNIT_COUNTS')!r}\n{log}")

    # Playwright gets the same lines; it records no failure/error split.
    pw = lambda n, run, passed: leg(f"shard {n}", run, passed, run - passed, total=6)  # noqa: E731
    code, cells, log = compute(r, "playwright-sharded-failing",
                               {f"playwright-shard-{n}.json": pw(n, 70, 70 - {2: 2, 5: 1}.get(n, 0)) for n in range(1, 7)},
                               {"playwright": "failure"})
    want = "417/420<br>6 shards in total:<br>• Shard 2: 2 failed tests<br>• Shard 5: 1 failed test"
    check("playwright-sharded-failing", cells.get("PLAYWRIGHT_COUNTS") == want,
          f"want {want!r}, got {cells.get('PLAYWRIGHT_COUNTS')!r}\n{log}")

    code, cells, log = compute(r, "playwright-crashed-shard",
                               {"playwright-shard-1.json": leg("shard 1", 70, 70, total=2),
                                "playwright-shard-2.json": {"leg": "shard 2", "run": None, "total": 2}},
                               {"playwright": "failure"})
    want = "70/70 (counts from 1 of 2 shards)<br>2 shards in total:<br>• Shard 2: no test report"
    check("playwright-crashed-shard", cells.get("PLAYWRIGHT_COUNTS") == want,
          f"want {want!r}, got {cells.get('PLAYWRIGHT_COUNTS')!r}\n{log}")

    return failures


def groups_match_matrix(workflow: Path) -> dict[str, str]:
    """The phpunit counts step lists every leg from copies of the matrix's three vectors; they must not drift."""
    job = yaml.safe_load(workflow.read_text(encoding="utf-8"))["jobs"]["phpunit"]
    matrix = job["strategy"]["matrix"]
    env = next(s for s in job["steps"] if s.get("id") == STEPS["phpunit"])["env"]
    failures = {}
    for key, vector in (("GROUP_PHP", "php-version"), ("GROUP_NEXTCLOUD", "nextcloud-ref"), ("GROUP_DATABASE", "database")):
        want = "${{ toJSON(" + str(matrix[vector]).removeprefix("${{ ").removesuffix(" }}") + ") }}"
        if str(env.get(key)) != want:
            failures[f"groups-match-matrix ({key})"] = f"want the matrix's {vector} expression {want!r}, got {env.get(key)!r}"
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
    failures.update(groups_match_matrix(Path(args.workflow)))

    for case, failure in failures.items():
        print(f"::error::{case}: {failure}")
    if failures:
        return 1
    print("OK: the four test-count steps read real PHPUnit, Newman and Playwright output and render every cell as asserted, and the install-only leg resolver leaves every total as asserted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
