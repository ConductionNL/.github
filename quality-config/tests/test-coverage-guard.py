#!/usr/bin/env python3
"""Exercise quality-config/coverage-guard.php against synthetic clover reports.

WHAT IS BEING TESTED, AND WHY IT NEEDED A TEST AT ALL
-----------------------------------------------------
`cgRatioDropped()` is one integer cross-product with no tolerance. Read plainly
it says: *the code you touched must be at least as well covered as the code you
did not*. That is right for additions and inverted for deletions — removing `d`
statements of which `c` were covered lowers the ratio whenever `c/d` exceeds the
ratio of what remains, and dead code is dead because nothing CALLS it, not
because nothing TESTED it.

`--deletion-neutral` fixes that by comparing METHOD BUCKETS asymmetrically:
base-only methods (deletions) leave the base side, head-only methods (additions)
stay on the head side.

The asymmetry is the part that needs guarding. The obvious symmetric rule —
"compare over statements present in both reports" — also drops head-only
statements, so a change adding forty new statements with none of them covered
compares an empty set to an empty set and passes. CASE_NEW below is that shape,
and the mutation battery at the bottom reintroduces the symmetric rule and
requires this suite to go red for it.

RUN
    python3 quality-config/tests/test-coverage-guard.py [path/to/coverage-guard.php]

Exit code is 0 when every assertion holds, 1 otherwise.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Tuple

HERE = Path(__file__).resolve().parent
GUARD = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else (HERE.parent / "coverage-guard.php")

failures: list[str] = []
checks = 0


def flat(text: str) -> str:
    """Collapse runs of spaces so assertions do not depend on printf padding."""
    return re.sub(r"[ \t]+", " ", text)


def says(stdout: str, *needles: str) -> bool:
    haystack = flat(stdout)
    return all(flat(n) in haystack for n in needles)


def check(ok: bool, what: str, detail: str = "") -> None:
    global checks
    checks += 1
    if ok:
        print(f"  ok   — {what}")
        return
    failures.append(what)
    print(f"  FAIL — {what}")
    if detail:
        for line in detail.rstrip("\n").split("\n"):
            print(f"         {line}")


# ── clover generation ───────────────────────────────────────────────────────
#
# The shape below is the one PHPUnit actually emits, verified against 2 608 file
# entries in four real artifacts from this fleet: `<class>` first with metrics
# only, then FLAT `<line>` children in document order, a `type="method"` line
# opening each method and `type="stmt"` lines belonging to whichever method
# preceded them. `metrics/@statements` counts the stmt lines; methods are counted
# separately and `elements` is their sum.
#
# Line numbers are assigned by walking the method list, so a fixture built from a
# shorter method list AUTOMATICALLY shifts every line after the cut — which is
# the whole reason a line-number intersection cannot work and is asserted below.

# `typing.Tuple`, not `tuple[...]`: this is a real assignment rather than an
# annotation, so PEP 563 does not defer it and the subscript is evaluated on
# import. Runners have 3.12; a developer machine here has 3.8.
Method = Tuple[str, int, int]  # (name, statements, covered)


def clover(root_dir: str, files: dict[str, list[Method]]) -> str:
    project_st = 0
    project_cov = 0
    parts = ['<?xml version="1.0" encoding="UTF-8"?>', "<coverage generated=\"0\">", "  <project timestamp=\"0\">"]

    for path, methods in files.items():
        num = 10
        lines = []
        st = 0
        cov = 0
        for name, statements, covered in methods:
            lines.append(f'      <line num="{num}" type="method" name="{name}" '
                         f'visibility="public" complexity="1" crap="1" count="{1 if covered else 0}"/>')
            num += 1
            for i in range(statements):
                hit = 1 if i < covered else 0
                lines.append(f'      <line num="{num}" type="stmt" count="{hit}"/>')
                num += 1
            st += statements
            cov += covered
            num += 3  # a gap, as real source has between methods

        project_st += st
        project_cov += cov
        nmethods = len(methods)
        covered_methods = sum(1 for _, _, c in methods if c)

        parts.append(f'    <file name="{root_dir}/{path}">')
        parts.append(f'      <class name="{Path(path).stem}" namespace="global">')
        parts.append(f'        <metrics complexity="1" methods="{nmethods}" coveredmethods="{covered_methods}" '
                     f'conditionals="0" coveredconditionals="0" statements="{st}" coveredstatements="{cov}" '
                     f'elements="{st + nmethods}" coveredelements="{cov + covered_methods}"/>')
        parts.append("      </class>")
        parts.extend(lines)
        parts.append(f'      <metrics loc="{num}" ncloc="{num}" classes="1" methods="{nmethods}" '
                     f'coveredmethods="{covered_methods}" conditionals="0" coveredconditionals="0" '
                     f'statements="{st}" coveredstatements="{cov}" elements="{st + nmethods}" '
                     f'coveredelements="{cov + covered_methods}"/>')
        parts.append("    </file>")

    parts.append(f'    <metrics files="{len(files)}" loc="0" ncloc="0" classes="{len(files)}" methods="0" '
                 f'coveredmethods="0" conditionals="0" coveredconditionals="0" statements="{project_st}" '
                 f'coveredstatements="{project_cov}" elements="{project_st}" coveredelements="{project_cov}"/>')
    parts.append("  </project>")
    parts.append("</coverage>")
    return "\n".join(parts) + "\n"


# ── the fixtures ────────────────────────────────────────────────────────────
#
# LAUNCHPAD#128 SHAPE — a pure deletion of a well-covered method.
# Surviving code: 15 methods, 254 statements, 183 covered  -> 72.05%
# Deleted method: 50 statements, 37 covered
# Base file total: 304 statements, 220 covered              -> 72.37%
# so the file-scoped rule sees a 0.32% drop, which is what CI reported.
SURVIVORS: list[Method] = [
    ("registerWidget", 20, 20),
    ("resolveLayout", 18, 18),
    ("buildTiles", 16, 16),
    ("applyTheme", 22, 22),
    ("readPreferences", 14, 14),
    ("writePreferences", 19, 19),
    ("serialiseBoard", 17, 17),
    # the deletion site sits here — everything below shifts
    ("restoreBoard", 21, 12),
    ("mergeDefaults", 15, 8),
    ("pruneStale", 13, 6),
    ("auditPlacement", 18, 10),
    ("exportBoard", 20, 9),
    ("importBoard", 16, 5),
    ("validateSlot", 12, 4),
    ("describeSlot", 13, 3),
]
DELETED: Method = ("legacyWidgetPayload", 50, 37)
LP_FILE = "lib/Service/WidgetService.php"
LP_BASE = SURVIVORS[:7] + [DELETED] + SURVIVORS[7:]

# OPENCATALOGI#895 SHAPE — the deleted block was 100% covered.
# head 112/115 (97.39%), base 148/151 (98.01%), file-scoped drop 0.62%.
OC_SURVIVORS: list[Method] = [
    ("loadSettings", 20, 20),
    ("saveSettings", 18, 18),
    ("normaliseKey", 15, 14),
    ("readDefaults", 12, 12),
    ("mergeOverrides", 14, 13),
    ("validateShape", 16, 16),
    ("describeKey", 10, 10),
    ("flushCache", 10, 9),
]
OC_DELETED: Method = ("renderLegacyBanner", 36, 36)
OC_FILE = "lib/Service/SettingsService.php"
OC_BASE = OC_SURVIVORS[:4] + [OC_DELETED] + OC_SURVIVORS[4:]

# CASE 3 — a real regression in surviving code: registerWidget loses 3 covered.
REGRESSED = [("registerWidget", 20, 17)] + SURVIVORS[1:]

# CASE 4 — the openconnector#1265 shape: 40 new statements, 0 covered.
ADDED_UNTESTED: Method = ("renderWidgetV2", 40, 0)
WITH_NEW = SURVIVORS + [ADDED_UNTESTED]


def totals(methods: list[Method]) -> tuple[int, int]:
    return sum(m[1] for m in methods), sum(m[2] for m in methods)


def run_guard(guard: Path, work: Path, head: str, base: str, changed: list[str],
              deletion_neutral: bool) -> subprocess.CompletedProcess:
    (work / "head.xml").write_text(head)
    (work / "base.xml").write_text(base)
    (work / "changed.txt").write_text("\n".join(changed) + "\n")
    cmd = [
        "php", str(guard), str(work / "head.xml"),
        f"--against={work / 'base.xml'}",
        f"--changed-files={work / 'changed.txt'}",
    ]
    if deletion_neutral:
        cmd.append("--deletion-neutral")
    return subprocess.run(cmd, capture_output=True, text=True)


def case(work: Path, path: str, head_methods: list[Method], base_methods: list[Method]) -> tuple[str, str]:
    return (
        clover("/runner/head/app", {path: head_methods}),
        clover("/runner/base/app", {path: base_methods}),
    )


def suite(guard: Path, label: str) -> int:
    """Run every assertion against `guard`. Returns the number of failures."""
    global failures, checks
    failures = []
    checks = 0
    print(f"\n== {label} ==")

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)

        # ── FAIL FIRST: the file-scoped rule blocks both pure deletions ──────
        print("\n-- the shipped file-scoped rule, on the two PRs it blocked --")

        head, base = case(work, LP_FILE, SURVIVORS, LP_BASE)
        r = run_guard(guard, work, head, base, [LP_FILE], deletion_neutral=False)
        check(r.returncode == 1, "launchpad#128 shape FAILS under --changed-files alone",
              r.stdout + r.stderr)
        check(says(r.stdout, "Changed files, head: 72.05% (183/254 statements)",
                   "Changed files, base: 72.37% (220/304 statements)",
                   "dropped by 0.32%"),
              "  ...and reports exactly 72.05% (183/254) vs 72.37% (220/304), -0.32%", r.stdout)

        head_oc, base_oc = case(work, OC_FILE, OC_SURVIVORS, OC_BASE)
        r = run_guard(guard, work, head_oc, base_oc, [OC_FILE], deletion_neutral=False)
        check(r.returncode == 1, "opencatalogi#895 shape FAILS under --changed-files alone",
              r.stdout + r.stderr)
        check(says(r.stdout, "Changed files, head: 97.39% (112/115 statements)",
                   "Changed files, base: 98.01% (148/151 statements)",
                   "dropped by 0.62%"),
              "  ...and reports exactly 97.39% (112/115) vs 98.01% (148/151), -0.62% — "
              "the numbers CI printed on job 95170517430", r.stdout)

        # ── CASE 1 + 2: pure deletions become exactly neutral ────────────────
        print("\n-- --deletion-neutral: the four measured cases --")

        head, base = case(work, LP_FILE, SURVIVORS, LP_BASE)
        r = run_guard(guard, work, head, base, [LP_FILE], deletion_neutral=True)
        check(r.returncode == 0, "CASE 1 launchpad#128 (pure deletion) PASSES", r.stdout + r.stderr)
        check(says(r.stdout, "Surviving code, head: 72.05% (183/254 statements)",
                   "Surviving code, base: 72.05% (183/254 statements)"),
              "  ...at exactly 183/254 vs 183/254 — neutral, not marginally passing", r.stdout)
        check("1 method(s) absent from head, 37/50 statements" in r.stdout,
              "  ...and it names what it removed from the base side (37/50)", r.stdout)

        r = run_guard(guard, work, head_oc, base_oc, [OC_FILE], deletion_neutral=True)
        check(r.returncode == 0, "CASE 2 opencatalogi#895 (pure deletion) PASSES", r.stdout + r.stderr)
        check(says(r.stdout, "Surviving code, head: 97.39% (112/115 statements)",
                   "Surviving code, base: 97.39% (112/115 statements)"),
              "  ...at exactly 112/115 vs 112/115", r.stdout)

        # ── CASE 3: a regression in surviving code still fails ───────────────
        head, base = case(work, LP_FILE, REGRESSED, LP_BASE)
        r = run_guard(guard, work, head, base, [LP_FILE], deletion_neutral=True)
        check(r.returncode == 1, "CASE 3 regression in SURVIVING code still FAILS", r.stdout + r.stderr)
        check(says(r.stdout, "Surviving code, head: 70.87% (180/254 statements)",
                   "Surviving code, base: 72.05% (183/254 statements)"),
              "  ...at 180/254 vs 183/254", r.stdout)

        # ── CASE 4: new untested code still fails ────────────────────────────
        head, base = case(work, LP_FILE, WITH_NEW, LP_BASE)
        r = run_guard(guard, work, head, base, [LP_FILE], deletion_neutral=True)
        check(r.returncode == 1, "CASE 4 new untested code (40 statements, 0 covered) still FAILS",
              r.stdout + r.stderr)
        check(says(r.stdout, "Surviving code, head: 62.24% (183/294 statements)",
                   "Surviving code, base: 72.05% (183/254 statements)"),
              "  ...at 62.24% (183/294) vs 72.05% (183/254)", r.stdout)
        check("adds 40 statements" in r.stdout,
              "  ...and says the change added 40 statements", r.stdout)
        check("RENAMED" in r.stdout,
              "  ...and states the rename residual in the failure message rather than "
              "leaving it to be discovered", r.stdout)

        # ── the combination: delete one method AND add an untested one ───────
        head, base = case(work, LP_FILE, WITH_NEW, LP_BASE)
        r = run_guard(guard, work, head, base, [LP_FILE], deletion_neutral=True)
        check("1 method(s) absent from head" in r.stdout and r.returncode == 1,
              "a change that deletes AND adds-untested is charged for the addition only, and fails",
              r.stdout)

        # ── degenerate inputs must not read as a pass ────────────────────────
        print("\n-- degenerate inputs --")

        r = subprocess.run(["php", str(guard), str(work / "head.xml"), "--deletion-neutral"],
                           capture_output=True, text=True)
        check(r.returncode == 2 and "requires --changed-files" in r.stderr,
              "--deletion-neutral without --changed-files is an ERROR, not a silent whole-project run",
              r.stdout + r.stderr)

        # A file present in neither report claims nothing.
        head, base = case(work, LP_FILE, SURVIVORS, LP_BASE)
        r = run_guard(guard, work, head, base, ["lib/Service/Absent.php"], deletion_neutral=True)
        check(r.returncode == 0 and "Nothing was measured" in r.stdout,
              "a changed file absent from both reports claims nothing and does not fail",
              r.stdout + r.stderr)

        # A file with metrics but no line data must NOT measure 0/0 and pass.
        # This is the hole the guard's cgCollapseFiles() exists to close: the
        # fallback bucket lives on one side only, so without the collapse the
        # asymmetric rule calls the whole base file "deleted" and reports
        # "none of the changed PHP existed at the merge base" — a file the guard
        # could not read passing every possible drop.
        stripped = re.sub(r'\n\s*<line [^>]*/>', "", base)
        r = run_guard(guard, work, head, stripped, [LP_FILE], deletion_neutral=True)
        check("no line data" in r.stdout,
              "a base file with metrics but no line data falls back to its file metric, out loud",
              r.stdout + r.stderr)
        check(r.returncode == 1,
              "  ...and that fallback is conservative — the file-level comparison still fails",
              r.stdout + r.stderr)

    return len(failures)


# ── the two controls that are NOT about the guard's own output ──────────────

def control_symmetric_would_pass() -> None:
    """A symmetric intersection passes CASE 4. This is why the rule is asymmetric.

    Computed here rather than in the guard, because the symmetric rule is the one
    thing the guard must never implement. If this control ever stops passing, the
    fixture no longer exercises the hole and CASE 4 stops proving anything.
    """
    print("\n-- control: the symmetric rule the guard deliberately does NOT implement --")
    head = {name: (s, c) for name, s, c in WITH_NEW}
    base = {name: (s, c) for name, s, c in LP_BASE}
    both = set(head) & set(base)
    hs = sum(head[k][0] for k in both)
    hc = sum(head[k][1] for k in both)
    bs = sum(base[k][0] for k in both)
    bc = sum(base[k][1] for k in both)
    dropped = (hc * bs) < (bc * hs)
    check(not dropped and (hc, hs) == (183, 254) and (bc, bs) == (183, 254),
          "symmetric 'statements present in BOTH reports' PASSES the 40-new-0-covered case "
          f"({hc}/{hs} vs {bc}/{bs}) — which is why head-only methods are kept",
          "")


def control_line_numbers_are_meaningless() -> None:
    """Intersecting by clover `num` compares unrelated statements after a deletion."""
    print("\n-- control: why the intersection is by method NAME, never line number --")
    head_xml = clover("/runner/head/app", {LP_FILE: SURVIVORS})
    base_xml = clover("/runner/base/app", {LP_FILE: LP_BASE})

    def stmt_lines(xml: str) -> dict[int, int]:
        root = ET.fromstring(xml)
        out = {}
        for f in root.iter("file"):
            for line in f.findall("line"):
                if line.get("type") == "stmt":
                    out[int(line.get("num"))] = int(line.get("count"))
        return out

    h = stmt_lines(head_xml)
    b = stmt_lines(base_xml)
    shared = set(h) & set(b)
    hs, hc = len(shared), sum(1 for n in shared if h[n] > 0)
    bs, bc = len(shared), sum(1 for n in shared if b[n] > 0)

    # How much of the surviving file sits at or after the cut, i.e. is shifted.
    before_cut = sum(m[1] for m in SURVIVORS[:7])
    after_cut = sum(m[1] for m in SURVIVORS) - before_cut
    print(f"         {after_cut} of {sum(m[1] for m in SURVIVORS)} surviving statements "
          f"({after_cut * 100 // sum(m[1] for m in SURVIVORS)}%) sit at or after the deletion site "
          f"— launchpad's real file was 117 of 254 (46%).")

    check((hc, hs) != (183, 254) or (bc, bs) != (183, 254),
          f"a line-number intersection does NOT reconcile ({hc}/{hs} head vs {bc}/{bs} base) — "
          "it compares unrelated statements across the shifted half of the file",
          "")


def mutation_battery() -> int:
    """Reintroduce known defects; the suite above must go red for each.

    A green suite proves nothing on its own — the question is whether it would
    have NOTICED. The last mutant is an ANTI-WIDENING control: it edits a log
    string nothing asserts on and the suite must STAY GREEN, so a suite that
    failed on any edit at all cannot score a perfect kill rate while being
    worthless.
    """
    print("\n== mutation battery ==")
    source = GUARD.read_text()
    survivors = 0

    mutants: list[tuple[str, str, str, bool]] = [
        (
            "the SYMMETRIC rule — head-only methods dropped too (the openconnector#1265 hole)",
            "        [$statements, $covered]         = cgSumBuckets($headBuckets);",
            "        $mutantKeep = [];\n"
            "        foreach ($baseBuckets as $mutantKey => $mutantPair) { $mutantKeep[$mutantKey] = true; }\n"
            "        [$statements, $covered]         = cgSumBuckets($headBuckets, $mutantKeep);",
            True,
        ),
        (
            "base-only methods KEPT — i.e. the deletion penalty put back",
            "        [$baseStatements, $baseCovered] = cgSumBuckets($baseBuckets, $keep);",
            "        [$baseStatements, $baseCovered] = cgSumBuckets($baseBuckets);",
            True,
        ),
        (
            "attribution by ordinal instead of name — every bucket key made unique",
            "                $method = ($named === '' ? CG_WHOLE_FILE : $named);",
            "                $method = ($named === '' ? CG_WHOLE_FILE : ($named . '@' . (string) $line['num']));",
            True,
        ),
        (
            "the no-line-data fallback removed — an unmeasurable file reads as 0/0",
            "        if ($statements === 0 && $declared > 0) {",
            "        if (false) {",
            True,
        ),
        (
            "ANTI-WIDENING: a log string nothing asserts on is reworded",
            "            echo \"    A method that no longer exists is not a coverage regression; it is deleted code.\\n\";",
            "            echo \"    Deleted methods are not regressions.\\n\";",
            False,
        ),
    ]

    for name, needle, replacement, must_die in mutants:
        if needle not in source:
            print(f"  FAIL — mutant anchor not found, the battery is not reaching the code: {name}")
            survivors += 1
            continue

        with tempfile.TemporaryDirectory() as tmp:
            mutant = Path(tmp) / "coverage-guard.php"
            mutant.write_text(source.replace(needle, replacement, 1))
            lint = subprocess.run(["php", "-l", str(mutant)], capture_output=True, text=True)
            if lint.returncode != 0:
                print(f"  FAIL — mutant does not parse: {name}\n         {lint.stdout}")
                survivors += 1
                continue

            broke = suite(mutant, f"mutant: {name}")

        if must_die and broke == 0:
            print(f"  SURVIVED — {name}: the suite stayed green. The fixture cannot reach that branch.")
            survivors += 1
        elif must_die:
            print(f"  killed   — {name} ({broke} assertion(s) went red)")
        elif broke != 0:
            print(f"  OVER-FIRED — {name}: the suite went red on a change that alters no behaviour.")
            survivors += 1
        else:
            print(f"  ok       — {name}: suite stayed green, as it must.")

    return survivors


def main() -> int:
    if shutil.which("php") is None:
        print("::error::php is not on PATH; this suite exercises the shipped PHP program and "
              "cannot be satisfied by reading it.")
        return 1
    if GUARD.exists() is False:
        print(f"::error::coverage guard not found at {GUARD}")
        return 1

    broke = suite(GUARD, f"coverage-guard.php ({GUARD})")

    failures.clear()
    control_symmetric_would_pass()
    control_line_numbers_are_meaningless()
    control_failures = len(failures)

    # The battery runs last on purpose: it re-enters suite() against mutated
    # copies and resets the module-level counters as it goes.
    survivors = mutation_battery()

    print("\n== summary ==")
    print(f"   subject assertions failed:     {broke}")
    print(f"   control assertions failed:     {control_failures}")
    print(f"   surviving/over-firing mutants: {survivors}")
    if broke == 0 and control_failures == 0 and survivors == 0:
        print("PASS")
        return 0
    print("FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
