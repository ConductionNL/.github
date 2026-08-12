#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""test_exclusion_reason_adjacent — .github#412, gates 17, 52 and 57.

WHAT IS UNDER TEST
==================
`#411` put one shared predicate behind the four `#400` coverage gates. Three
more checkers grade an exclusion marker, and none of them was on that list:

    gate-17  detect-redundant-controllers.py     `@spec exclude`
    gate-52  check_custom_widget_ratchet.py      `@custom-widget-ratchet exclude`
    gate-57  check_orphaned_write_capability.py  `@orphaned-write-capability exclude`

Each was wrong in its own way, and gate-17 is the one that matters most: it
reads the SAME `@spec` tag as gate-16, and it required NO REASON AT ALL. So
after `#411` a bare `@spec exclude` was refused by gate-16 and still honoured by
gate-17 — one annotation, two gates, opposite verdicts, and nothing in either
gate's output that would let a reader notice. gate-52 asked only for `\\S+`,
which a full stop satisfies (`#400` under another tag). gate-57 asked for ten
characters and never for a letter, so `..........` was a justification.

WHY THE FLOORS STILL DIFFER, AND WHY THAT IS ASSERTED HERE
-----------------------------------------------------------
gate-57 keeps its own floor of ten. That is not an oversight and it is not a
detail — it is the package's open threshold disagreement, left open on purpose
(`#412`). `assertion 'gate-57 keeps its OWN floor of 10'` below exists so that a
future "harmonisation" of these numbers cannot happen SILENTLY: collapsing
gate-57 to the shared 3 turns that assertion red and forces the decision to be
made out loud, by whoever makes it.

WHY EACH DEFECT LIVES IN ITS OWN NAMED FILE
-------------------------------------------
`#404` and `#409`: a subject that a SIBLING finding can also satisfy makes an
assertion vacuous, and one named file emitting two findings from two different
code paths survives a partial revert. So every probe here is a file with exactly
ONE method, hence at most one finding, and the file names are pairwise
non-containing — no name is a substring of another, including across the
extension.

ANTI-WIDENING NEEDS A WITNESS
-----------------------------
"`X` is not reported" is equally true of a run that inspected nothing. Every
"must NOT be reported" arm therefore runs in a fixture that also contains a
witness which MUST be reported, so the negative claim is only reachable through
a run that provably opened the directory.

Run: python3 hydra-gates/scripts/lib/test_exclusion_reason_adjacent.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB))

from exclusion_reason import (  # noqa: E402
    REASON_MIN_CHARS,
    exclude_pattern,
    is_reason_bearing,
    why_rejected,
)
import check_orphaned_write_capability as owc  # noqa: E402

# An empty run is not a green run — the same trap run-helper-suites.sh guards.
MIN_ASSERTIONS = 31

_passed: list[str] = []
_failed: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        _passed.append(name)
        print(f"  ok   — {name}")
    else:
        _failed.append(name)
        print(f"  FAIL — {name}")
        if detail:
            for line in str(detail).splitlines():
                print(f"           {line}")


def run(script: str, argv: list[str], cwd: str | None = None,
        base: str | None = None) -> str:
    env = dict(os.environ)
    if base:
        env["HYDRA_GATE_BASE_REF"] = base
    else:
        env.pop("HYDRA_GATE_BASE_REF", None)
    r = subprocess.run(["python3", str(LIB / script), *argv],
                       capture_output=True, text=True, env=env, cwd=cwd,
                       check=False)
    return r.stdout + r.stderr


def _git(repo: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-c", "user.email=t@example.invalid", "-c", "user.name=t",
         "-c", "commit.gpgsign=false", "-C", repo, *args],
        capture_output=True, text=True, check=False)


def make_repo(root: str, base_files: dict[str, str], head_files: dict[str, str]) -> str:
    """Two commits; returns the BASE sha. HARD-FAILS on every git step.

    `#411` learned this the expensive way: `git init -b main` does not exist on
    git 2.25, every fixture silently failed to be a repo, the files were on disk
    either way, and the gates ran at a DIFFERENT SCOPE while still printing a
    plausible verdict. A fixture that failed to build must not look like one.
    """
    def must(*args: str) -> subprocess.CompletedProcess:
        r = _git(root, *args)
        if r.returncode != 0:
            raise RuntimeError(f"fixture build failed: git {' '.join(args)} -> "
                               f"{r.returncode}\n{r.stdout}{r.stderr}")
        return r

    def write(files: dict[str, str]) -> None:
        for rel, body in files.items():
            p = Path(root) / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body, encoding="utf-8")

    must("init", "-q")
    write(base_files)
    must("add", "-A")
    must("commit", "-q", "-m", "base")
    base = must("rev-parse", "HEAD").stdout.strip()
    if len(base) != 40:
        raise RuntimeError(f"fixture build failed: no base sha (got {base!r})")
    write(head_files)
    must("add", "-A")
    must("commit", "-q", "-m", "head")
    if _git(root, "diff", "--quiet", f"{base}...HEAD").returncode == 0:
        raise RuntimeError("fixture build failed: base...HEAD is an EMPTY diff")
    return base


# ---------------------------------------------------------------------------
# 1. The predicate's per-tag floor
# ---------------------------------------------------------------------------


def suite_predicate() -> None:
    print("\n== the shared predicate, with a per-tag floor ==")
    check("the default floor is unchanged by #412",
          REASON_MIN_CHARS == 3, f"REASON_MIN_CHARS={REASON_MIN_CHARS}")
    check("min_chars raises the bar: 'abcde' passes at the default and is "
          "refused at 10",
          is_reason_bearing("abcde") is True
          and is_reason_bearing("abcde", min_chars=10) is False)
    check("min_chars does NOT replace the alphabet rule: ten full stops are "
          "refused at a floor of 10 — the exact gate-57 hole",
          is_reason_bearing("." * 10, min_chars=10) is False)
    check("ANTI-WIDENING: a real reason still passes at a floor of 10",
          is_reason_bearing("Wired in the next PR (issue 999)", min_chars=10) is True)
    check("why_rejected quotes the CALLER's floor, not the default — a message "
          "naming 3 would send a gate-57 author to pad to the wrong number",
          "10 characters" in why_rejected("abcde", min_chars=10)
          and "3 characters" in why_rejected("ab"))
    check("why_rejected blames the ALPHABET, not the length, when the reason is "
          "long enough and still degenerate",
          "no letter or digit" in why_rejected("." * 10, min_chars=10))
    check("gate-57 keeps its OWN floor of 10 — #412 aligned its ALPHABET rule "
          "and deliberately left the threshold question open (harmonising this "
          "silently is what this assertion exists to prevent)",
          owc.REASON_MIN_CHARS == 10, f"got {owc.REASON_MIN_CHARS}")
    check("all three tags now generate their marker pattern from the ONE "
          "template, so the regexes cannot drift apart again",
          exclude_pattern("spec")
          == r"@spec\s+exclude\b[ \t]*(?P<reason>.*?)\s*$"
          and exclude_pattern("custom-widget-ratchet").startswith(
              r"@custom-widget-ratchet\s+exclude\b")
          and exclude_pattern("orphaned-write-capability").startswith(
              r"@orphaned-write-capability\s+exclude\b"))


# ---------------------------------------------------------------------------
# 2. gate-17 redundant-controller — the bare-marker hole
# ---------------------------------------------------------------------------

_CTRL = """<?php
namespace OCA\\Fixture\\Controller;
{classdoc}class {cls} {{
    /**{marker}
     */
    public function index() {{
        return new JSONResponse($this->objectService->findAll([]));
    }}
}}
"""

_G17_FILES = {
    # one method per file => at most one finding per named subject (#409)
    "SpecExcludeBareProbeController":
        ("\n     * @spec exclude", "", True),
    "SpecExcludeDotProbeController":
        ("\n     * @spec exclude .", "", True),
    "SpecExcludeUnderscoreProbeController":
        ("\n     * @spec exclude ___", "", True),
    "SpecExcludeHonouredProbeController":
        ("\n     * @spec exclude deliberate ObjectService facade, ADR-022", "", False),
    "SpecExcludeClassLevelProbeController":
        ("", "/**\n * @spec exclude a class-level marker is not a method marker\n */\n", True),
    "RedundantWitnessProbeController":
        ("", "", True),
}


def suite_gate17() -> None:
    print("\n== gate-17 redundant-controller (@spec exclude) ==")
    with tempfile.TemporaryDirectory() as d:
        ctrl = Path(d) / "lib" / "Controller"
        ctrl.mkdir(parents=True)
        for cls, (marker, classdoc, _exp) in _G17_FILES.items():
            (ctrl / f"{cls}.php").write_text(
                _CTRL.format(cls=cls, marker=marker, classdoc=classdoc),
                encoding="utf-8")
        out = run("detect-redundant-controllers.py", [d])

    if "# count=" not in out:
        check("gate-17 finished (it printed its terminal `# count=` marker)",
              False, out[-1500:])
        return
    check("gate-17 finished (it printed its terminal `# count=` marker)", True)

    def reported(cls: str) -> bool:
        return any(f"{cls}.php" in ln and "rule=pass-through-to-ObjectService" in ln
                   for ln in out.splitlines())

    check("WITNESS: an unannotated pass-through IS reported, so every "
          "'is not reported' claim below came from a run that opened this "
          "directory (RedundantWitnessProbeController)",
          reported("RedundantWitnessProbeController"), out)
    check("gate-17 refuses a BARE `@spec exclude` and names "
          "SpecExcludeBareProbeController — the marker gate-16 already refuses",
          reported("SpecExcludeBareProbeController"), out)
    check("gate-17 refuses `@spec exclude .` and names "
          "SpecExcludeDotProbeController",
          reported("SpecExcludeDotProbeController"), out)
    check("gate-17 refuses `@spec exclude ___` and names "
          "SpecExcludeUnderscoreProbeController — \\w would have accepted it",
          reported("SpecExcludeUnderscoreProbeController"), out)
    check("SCOPE CONTROL: a `@spec exclude` in the CLASS docblock does not "
          "silence the method below it (SpecExcludeClassLevelProbeController)",
          reported("SpecExcludeClassLevelProbeController"), out)
    check("ANTI-WIDENING: a real reason is still honoured and "
          "SpecExcludeHonouredProbeController is NOT reported",
          not reported("SpecExcludeHonouredProbeController"), out)
    expected = sum(1 for _c, (_m, _cd, exp) in _G17_FILES.items() if exp)
    got = int(out.rsplit("# count=", 1)[1].split()[0])
    check(f"gate-17's own terminal count is exactly {expected} — a COUNT arm, so "
          "one probe silently ceasing to fire cannot hide behind the others "
          "keeping the log non-empty (#409)",
          got == expected, f"# count={got}, expected {expected}\n{out}")


# ---------------------------------------------------------------------------
# 3. gate-52 custom-widget-ratchet
# ---------------------------------------------------------------------------

_REG_BASE = """export const registry = {
\t'keptCanvas': {
\t\tkind: 'widget',
\t\t_note: "bespoke analytics canvas",
\t},
};
"""

_REG_HEAD = """export const registry = {{
{marker}\t'grownCanvas': {{
\t\tkind: 'widget',
\t\t_note: "bespoke analytics canvas",
\t}},
\t'keptCanvas': {{
\t\tkind: 'widget',
\t\t_note: "bespoke analytics canvas",
\t}},
}};
"""


def _g52(marker: str) -> str:
    with tempfile.TemporaryDirectory() as d:
        base = make_repo(
            d,
            {"src/registry.js": _REG_BASE},
            {"src/registry.js": _REG_HEAD.format(marker=marker)})
        # RELATIVE path, with cwd at the repo root: the helper resolves the base
        # side with `git show <base>:<path>`, which only works for a
        # repo-relative path. Handed an absolute one it silently reads base=0 —
        # a ratchet whose base is empty reports growth for everything, which
        # looks exactly like the marker being refused.
        return run("check_custom_widget_ratchet.py",
                   [os.path.join("src", "registry.js")], cwd=d, base=base)


def suite_gate52() -> None:
    print("\n== gate-52 custom-widget-ratchet (@custom-widget-ratchet exclude) ==")
    arms = {
        "dot": "\t// @custom-widget-ratchet exclude .\n",
        "real": "\t// @custom-widget-ratchet exclude no built-in widget renders "
                "a computed scorecard\n",
        "nextline": "\t// @custom-widget-ratchet exclude\n"
                    "\t// no built-in widget renders a computed scorecard\n",
        "bare": "\t// @custom-widget-ratchet exclude\n",
    }
    out = {k: _g52(v) for k, v in arms.items()}

    for k, o in out.items():
        if "[custom-widget-ratchet] findings=" in o:
            continue
        check(f"gate-52 finished on the {k!r} arm (it printed `findings=`)",
              False, o[-1500:])
        return
    check("gate-52 finished on all four arms (each printed its `findings=` "
          "count, so none of the verdicts below came from a crash)", True)

    check("gate-52 refuses `@custom-widget-ratchet exclude .` — the entry is "
          "NOT ratchet-excluded and the growth is reported",
          "ratchet-excluded" not in out["dot"]
          and "the ratchet forbids growth" in out["dot"], out["dot"])
    check("UNCHANGED BEHAVIOUR: a bare marker with no reason still does not "
          "count (this was already true under `\\S+` and must stay true)",
          "ratchet-excluded" not in out["bare"]
          and "the ratchet forbids growth" in out["bare"], out["bare"])
    check("SAME-LINE RULE PRESERVED: a reason on the line BELOW the marker does "
          "not count, exactly as the old `\\S+` form required",
          "ratchet-excluded" not in out["nextline"]
          and "the ratchet forbids growth" in out["nextline"], out["nextline"])
    check("ANTI-WIDENING: a real reason still lifts the entry out of the head "
          "count, and the growth is NOT reported",
          "(1 ratchet-excluded)" in out["real"]
          and "the ratchet forbids growth" not in out["real"], out["real"])
    check("WITNESS on the anti-widening arm: the ratchet still RAN and still "
          "counted both entries (base=1 head=2), so 'not reported' is not a "
          "claim about a run that computed nothing",
          "base=1 head=2 delta=+1" in out["real"], out["real"])


# ---------------------------------------------------------------------------
# 4. gate-57 orphaned-write-capability
# ---------------------------------------------------------------------------

_SVC = """<?php
namespace OCA\\Fixture\\Service;
class {cls} {{
    /**{marker}
     */
    public function publishReport(): void {{}}
}}
"""

_G57_FILES = {
    "OrphanDotsProbeService":
        ("\n     * @orphaned-write-capability exclude ..........", True),
    "OrphanContinuationProbeService":
        ("\n     * @orphaned-write-capability exclude"
         "\n     * wired up in a later PR, see issue 999", True),
    "OrphanFloorProbeService":
        ("\n     * @orphaned-write-capability exclude abcde", True),
    "OrphanHonouredProbeService":
        ("\n     * @orphaned-write-capability exclude Wired in the next PR (issue 999)", False),
    "OrphanWitnessProbeService":
        ("", True),
}


def suite_gate57() -> None:
    print("\n== gate-57 orphaned-write-capability ==")
    with tempfile.TemporaryDirectory() as d:
        svc = Path(d) / "lib" / "Service"
        svc.mkdir(parents=True)
        paths = []
        for cls, (marker, _exp) in _G57_FILES.items():
            p = svc / f"{cls}.php"
            p.write_text(_SVC.format(cls=cls, marker=marker), encoding="utf-8")
            paths.append(str(p))
        out = run("check_orphaned_write_capability.py", sorted(paths), cwd=d)

    if "SKIP:" in out:
        check("gate-57 judged the fixture rather than declining it", False, out)
        return

    def reported(cls: str) -> bool:
        return any(f"{cls}.php" in ln and "rule=orphaned-write-capability" in ln
                   for ln in out.splitlines())

    check("WITNESS: an unannotated orphaned write IS reported, so every "
          "'is not reported' claim below came from a run that opened this "
          "directory (OrphanWitnessProbeService)",
          reported("OrphanWitnessProbeService"), out)
    check("gate-57 refuses ten full stops and names OrphanDotsProbeService — "
          "the exact input `.{10,}` accepted",
          reported("OrphanDotsProbeService"), out)
    check("gate-57 refuses a bare marker that borrows the docblock "
          "CONTINUATION LINE below it (OrphanContinuationProbeService) — the "
          "`\\s+` separator used to let a newline in",
          reported("OrphanContinuationProbeService"), out)
    check("gate-57's floor of 10 SURVIVES: a 5-character alphanumeric reason is "
          "still refused (OrphanFloorProbeService). If #412 had collapsed this "
          "tag to the shared floor of 3, this arm would go green and a live bar "
          "would have been relaxed inside a tightening.",
          reported("OrphanFloorProbeService"), out)
    check("ANTI-WIDENING: a real >=10-character reason is still honoured and "
          "OrphanHonouredProbeService is NOT reported",
          not reported("OrphanHonouredProbeService"), out)
    expected = sum(1 for _c, (_m, exp) in _G57_FILES.items() if exp)
    got = sum(1 for ln in out.splitlines()
              if "rule=orphaned-write-capability" in ln)
    check(f"gate-57 reports exactly {expected} of the {len(_G57_FILES)} probes — "
          "a COUNT arm beside the by-name arms, so a probe that stops firing "
          "cannot hide behind its siblings (#409)",
          got == expected, f"got {got}, expected {expected}\n{out}")


# ---------------------------------------------------------------------------
# 5. The three gates agree with gate-16 about one tag
# ---------------------------------------------------------------------------


def suite_cross_gate() -> None:
    print("\n== gate-16 and gate-17 now agree about `@spec exclude` ==")
    # NOT str.format — the PHP body is full of braces, and `.format` on it
    # raises `unexpected '{' in field name`. A template that cannot render is a
    # suite that cannot run.
    spec = """<?php
namespace OCA\\Fixture\\Controller;
class SpecAgreementProbeController {
    /**
     * @spec exclude __REASON__
     */
    public function index() {
        return new JSONResponse($this->objectService->findAll([]));
    }
}
"""
    import importlib.util
    s = importlib.util.spec_from_file_location(
        "csc", str(LIB / "check_spec_coverage.py"))
    csc = importlib.util.module_from_spec(s)
    sys.modules["csc"] = csc
    s.loader.exec_module(csc)
    s2 = importlib.util.spec_from_file_location(
        "drc", str(LIB / "detect-redundant-controllers.py"))
    drc = importlib.util.module_from_spec(s2)
    sys.modules["drc"] = drc
    s2.loader.exec_module(drc)

    for label, reason, expect_honoured in (
        ("a full stop", ".", False),
        ("nothing at all", "", False),
        ("a real reason", "deliberate ObjectService facade, ADR-022", True),
    ):
        lines = spec.replace("__REASON__", reason).splitlines()
        idx = next(i for i, ln in enumerate(lines) if "public function index" in ln)
        opening = next(i for i in range(idx - 1, -1, -1) if "/**" in lines[i])
        docblock = "\n".join(lines[opening:idx])
        # The two gates are handed the same docblock in the same shape their own
        # callers hand it to them, and must agree.
        if "@spec exclude" not in docblock:
            check("cross-gate fixture actually carries the marker", False, docblock)
            return
        g16 = csc._docblock_spec_status(lines, idx)[0] == "excluded"
        g17 = drc._has_reason_bearing_spec_exclude(docblock)
        check(f"gate-16 and gate-17 give the SAME verdict for `@spec exclude` "
              f"with {label} (both {'honour' if expect_honoured else 'refuse'} it)",
              g16 is expect_honoured and g17 is expect_honoured,
              f"gate-16 honoured={g16} gate-17 honoured={g17}")


def main() -> int:
    suite_predicate()
    suite_gate17()
    suite_gate52()
    suite_gate57()
    suite_cross_gate()
    total = len(_passed) + len(_failed)
    print(f"\n== {len(_passed)} passed / {len(_failed)} failed / {total} run ==")
    if total < MIN_ASSERTIONS:
        print(f"SUITE TOO SHORT: {total} assertions ran, expected at least "
              f"{MIN_ASSERTIONS}. A run that stopped early prints a green "
              f"summary exactly like a complete one.")
        return 1
    if _failed:
        print("FAILURES:")
        for n in _failed:
            print(f"  - {n}")
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
