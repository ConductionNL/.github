#!/usr/bin/env python3
"""Golden test: coverage-guard.php must keep its exact output and exit codes.

Every case below runs the guard as CI runs it, from `<case>/scripts/` with the
committed floor at `<case>/.coverage-baseline`, and records stdout, stderr, the
exit code and the floor file after the run. fixtures/coverage-guard-golden.json
holds the expected results, so a refactor that changes one byte of any message,
any exit code or the floor it writes fails here.

RUN
    python3 quality-config/tests/test-coverage-guard-golden.py [guard.php]
    python3 quality-config/tests/test-coverage-guard-golden.py --record [guard.php]

Plain mode exits 0 when every case matches the recording, 1 otherwise.
`--record` rewrites the recording and compares nothing, so always run plain
mode after recording.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
GOLDEN = HERE / "fixtures" / "coverage-guard-golden.json"

# (name, statements, covered). A name of None emits a method line without a
# name attribute; "" emits name="".
Method = Tuple[Optional[str], int, int]


def file_xml(path: str, methods: List[Method], *, lines: bool = True, nested: bool = False,
             declared: Optional[int] = None, covered_attr: Optional[str] = None,
             lead: int = 0, metrics: bool = True) -> Tuple[str, int, int]:
    """One clover <file> entry. Returns (xml, statements, covered)."""
    num = 10
    body: List[str] = []
    st = 0
    cov = 0
    for _ in range(lead):
        body.append(f'<line num="{num}" type="stmt" count="1"/>')
        num += 1
        st += 1
        cov += 1
    for name, statements, covered in methods:
        attr = "" if name is None else f' name="{name}"'
        body.append(f'<line num="{num}" type="method"{attr} visibility="public" complexity="1" '
                    f'crap="1" count="{1 if covered else 0}"/>')
        num += 1
        for i in range(statements):
            body.append(f'<line num="{num}" type="stmt" count="{3 if i < covered else 0}"/>')
            num += 1
        st += statements
        cov += covered
        body.append(f'<line num="{num}" type="cond" count="0"/>')
        num += 3
    if not lines:
        body = []
    d = st if declared is None else declared
    c = str(cov) if covered_attr is None else covered_attr
    out = [f'    <file name="{path}">']
    class_open = f'      <class name="{Path(path).stem}" namespace="global"><metrics statements="{d}" coveredstatements="{c}"/>'
    if nested:
        out.append(class_open)
        out.extend("        " + b for b in body)
        out.append("      </class>")
    else:
        out.append(class_open + "</class>")
        out.extend("      " + b for b in body)
    if metrics:
        out.append(f'      <metrics loc="{num}" statements="{d}" coveredstatements="{c}" elements="{d}"/>')
    out.append("    </file>")
    return "\n".join(out), st, cov


def clover(entries: List[Tuple[str, int, int]], *, project: Optional[Tuple[int, int]] = None,
           package: bool = False) -> str:
    st = sum(e[1] for e in entries)
    cov = sum(e[2] for e in entries)
    if project is not None:
        st, cov = project
    inner = "\n".join(e[0] for e in entries)
    if package:
        inner = '    <package name="App">\n' + inner + "\n    </package>"
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<coverage generated="0">\n  <project timestamp="0">\n'
            + inner + "\n"
            + f'    <metrics files="{len(entries)}" statements="{st}" coveredstatements="{cov}"/>\n'
            + "  </project>\n</coverage>\n")


def one(root: str, path: str, methods: List[Method], **kw) -> str:
    return clover([file_xml(f"{root}/{path}", methods, **kw)])


# ── shared method lists (the shapes test-coverage-guard.py measures) ────────
SURVIVORS: List[Method] = [
    ("registerWidget", 20, 20), ("resolveLayout", 18, 18), ("buildTiles", 16, 16),
    ("applyTheme", 22, 22), ("readPreferences", 14, 14), ("writePreferences", 19, 19),
    ("serialiseBoard", 17, 17), ("restoreBoard", 21, 12), ("mergeDefaults", 15, 8),
    ("pruneStale", 13, 6), ("auditPlacement", 18, 10), ("exportBoard", 20, 9),
    ("importBoard", 16, 5), ("validateSlot", 12, 4), ("describeSlot", 13, 3),
]
DELETED: Method = ("legacyWidgetPayload", 50, 37)
LP = "lib/Service/WidgetService.php"
LP_BASE = SURVIVORS[:7] + [DELETED] + SURVIVORS[7:]
REGRESSED = [("registerWidget", 20, 17)] + SURVIVORS[1:]
WITH_NEW = SURVIVORS + [("renderWidgetV2", 40, 0)]
OTHER = "lib/Controller/BoardController.php"
OTHER_M: List[Method] = [("index", 10, 7), ("show", 8, 8)]
H = "/runner/head/app"
B = "/runner/base/app"


def whole(statements: int, covered: int) -> str:
    return clover([file_xml(f"{H}/{LP}", [("m", statements, covered)])])


# Each case: name -> {files: {relpath: text}, args: [...], baseline: str|None}
def cases() -> Dict[str, dict]:
    c: Dict[str, dict] = {}

    def add(name: str, args: List[str], files: Optional[Dict[str, str]] = None,
            baseline: Optional[str] = None) -> None:
        c[name] = {"args": args, "files": files or {}, "baseline": baseline}

    def scoped(name: str, head: str, base: str, changed: str, dn: bool = True) -> None:
        args = ["head.xml", "--against=base.xml", "--changed-files=changed.txt"]
        if dn:
            args.append("--deletion-neutral")
        add(name, args, {"head.xml": head, "base.xml": base, "changed.txt": changed})

    # ── argument handling ────────────────────────────────────────────────
    add("capabilities", ["--capabilities"])
    add("capabilities-with-other-flags", ["head.xml", "--against=x", "--capabilities"])
    add("default-clover-path-missing", [], baseline="50.00\n")
    add("default-clover-path-present", [], {"coverage/clover.xml": whole(10, 5)}, baseline="50.00\n")
    add("positional-after-options", ["--against=", "head.xml"], {"head.xml": whole(10, 5)}, baseline="50\n")
    add("bare-double-dash", ["--", "head.xml"], {"head.xml": whole(10, 5)}, baseline="50\n")
    add("against-flag-without-value", ["head.xml", "--against"], {"head.xml": whole(10, 5)}, baseline="40\n")
    add("deletion-neutral-alone", ["head.xml", "--deletion-neutral"], {"head.xml": whole(10, 5)})
    add("deletion-neutral-empty-changed", ["head.xml", "--changed-files=", "--deletion-neutral"],
        {"head.xml": whole(10, 5)})
    add("deletion-neutral-changed-flag-no-value", ["head.xml", "--changed-files", "--deletion-neutral"],
        {"head.xml": whole(10, 5)})
    add("changed-without-against", ["head.xml", "--changed-files=changed.txt"],
        {"head.xml": whole(10, 5), "changed.txt": LP + "\n"})
    add("changed-with-empty-against", ["head.xml", "--against=", "--changed-files=changed.txt"],
        {"head.xml": whole(10, 5), "changed.txt": LP + "\n"})
    add("changed-list-missing", ["head.xml", "--against=base.xml", "--changed-files=nope.txt"],
        {"head.xml": whole(10, 5), "base.xml": whole(10, 5)})
    add("changed-list-no-php", ["head.xml", "--against=base.xml", "--changed-files=changed.txt"],
        {"changed.txt": "webpack.config.js\nsrc/main.js\n\n"})
    add("changed-list-no-php-dn", ["head.xml", "--against=base.xml", "--changed-files=changed.txt",
                                   "--deletion-neutral"], {"changed.txt": "README.md\n"})
    add("changed-list-empty-file", ["head.xml", "--against=base.xml", "--changed-files=changed.txt"],
        {"changed.txt": ""})

    # ── whole project against the committed floor ────────────────────────
    add("floor-missing", ["head.xml"], {"head.xml": whole(10, 5)})
    add("floor-unparseable", ["head.xml"], {"head.xml": whole(10, 5)}, baseline="about 50%\n")
    add("floor-negative", ["head.xml"], {"head.xml": whole(10, 5)}, baseline="-5\n")
    add("floor-equal", ["head.xml"], {"head.xml": whole(10, 5)}, baseline="50.00\n")
    add("floor-equal-rounding", ["head.xml"], {"head.xml": whole(3, 1)}, baseline="33.33\n")
    add("floor-below", ["head.xml"], {"head.xml": whole(10, 4)}, baseline="50.00\n")
    add("floor-below-tiny", ["head.xml"], {"head.xml": whole(10000, 4999)}, baseline="50.00\n")
    add("floor-above", ["head.xml"], {"head.xml": whole(10, 6)}, baseline="50.00\n")
    add("floor-above-update", ["head.xml", "--update-baseline"], {"head.xml": whole(3, 2)}, baseline="50.00\n")
    add("floor-equal-update", ["head.xml", "--update-baseline"], {"head.xml": whole(10, 5)}, baseline="50\n")
    add("floor-below-update", ["head.xml", "--update-baseline"], {"head.xml": whole(10, 1)}, baseline="50\n")
    add("floor-integer-value", ["head.xml"], {"head.xml": whole(7, 7)}, baseline="99\n")
    add("floor-whitespace", ["head.xml"], {"head.xml": whole(7, 7)}, baseline="  12.5  \n\n")

    # ── whole project: degenerate inputs ─────────────────────────────────
    add("head-missing", ["absent.xml"], baseline="50\n")
    add("head-empty-file", ["head.xml"], {"head.xml": ""}, baseline="50\n")
    add("head-not-xml", ["head.xml"], {"head.xml": "this is not xml <"}, baseline="50\n")
    add("head-no-project-metrics", ["head.xml"],
        {"head.xml": '<?xml version="1.0"?>\n<coverage><project/></coverage>\n'}, baseline="50\n")
    add("head-zero-statements", ["head.xml"], {"head.xml": clover([], project=(0, 0))}, baseline="50\n")
    add("head-negative-statements", ["head.xml"], {"head.xml": clover([], project=(-3, 0))}, baseline="50\n")
    add("base-missing", ["head.xml", "--against=base.xml"], {"head.xml": whole(10, 5)})
    add("base-zero-statements", ["head.xml", "--against=base.xml"],
        {"head.xml": whole(10, 5), "base.xml": clover([], project=(0, 0))})
    add("base-not-xml", ["head.xml", "--against=base.xml"], {"head.xml": whole(10, 5), "base.xml": "<x"})

    # ── whole project against the merge base ─────────────────────────────
    for suffix, baseline in (("", None), ("-with-floor", "61.10\n")):
        add("against-unchanged" + suffix, ["head.xml", "--against=base.xml"],
            {"head.xml": whole(100, 61), "base.xml": whole(100, 61)}, baseline=baseline)
        add("against-dropped" + suffix, ["head.xml", "--against=base.xml"],
            {"head.xml": whole(100, 55), "base.xml": whole(100, 61)}, baseline=baseline)
        add("against-dropped-added" + suffix, ["head.xml", "--against=base.xml"],
            {"head.xml": whole(140, 61), "base.xml": whole(100, 61)}, baseline=baseline)
        add("against-dropped-tiny" + suffix, ["head.xml", "--against=base.xml"],
            {"head.xml": whole(13987, 8228), "base.xml": whole(13987, 8229)}, baseline=baseline)
        add("against-improved" + suffix, ["head.xml", "--against=base.xml"],
            {"head.xml": whole(100, 70), "base.xml": whole(100, 61)}, baseline=baseline)
        add("against-improved-tiny" + suffix, ["head.xml", "--against=base.xml"],
            {"head.xml": whole(13987, 8230), "base.xml": whole(13987, 8229)}, baseline=baseline)
        add("against-same-ratio-other-size" + suffix, ["head.xml", "--against=base.xml"],
            {"head.xml": whole(200, 122), "base.xml": whole(100, 61)}, baseline=baseline)
    add("against-update-flag-ignored", ["head.xml", "--against=base.xml", "--update-baseline"],
        {"head.xml": whole(100, 70), "base.xml": whole(100, 61)}, baseline="10\n")

    # ── file-scoped (no --deletion-neutral) ──────────────────────────────
    lp_head = one(H, LP, SURVIVORS)
    lp_base = one(B, LP, LP_BASE)
    scoped("fs-pure-deletion", lp_head, lp_base, LP + "\n", dn=False)
    scoped("fs-unchanged", lp_head, one(B, LP, SURVIVORS), LP + "\n", dn=False)
    scoped("fs-improved", one(H, LP, SURVIVORS[:-1] + [("describeSlot", 13, 13)]), one(B, LP, SURVIVORS),
           LP + "\n", dn=False)
    scoped("fs-added-untested", one(H, LP, WITH_NEW), one(B, LP, SURVIVORS), LP + "\n", dn=False)
    scoped("fs-new-file", lp_head, one(B, OTHER, OTHER_M), LP + "\n", dn=False)
    scoped("fs-absent-both", lp_head, lp_base, "lib/Service/Absent.php\n", dn=False)
    scoped("fs-head-zero-statements", one(H, LP, [("a", 0, 0)]), one(B, LP, [("a", 4, 2)]), LP + "\n", dn=False)
    scoped("fs-two-files", clover([file_xml(f"{H}/{LP}", SURVIVORS), file_xml(f"{H}/{OTHER}", OTHER_M)]),
           clover([file_xml(f"{B}/{LP}", SURVIVORS), file_xml(f"{B}/{OTHER}", [("index", 10, 9), ("show", 8, 8)])]),
           f"{LP}\n{OTHER}\n", dn=False)
    scoped("fs-suffix-matches-many", clover([file_xml(f"{H}/lib/A/Foo.php", OTHER_M),
                                             file_xml(f"{H}/lib/B/Foo.php", [("x", 5, 1)])]),
           clover([file_xml(f"{B}/lib/A/Foo.php", OTHER_M)]), "Foo.php\n", dn=False)
    scoped("fs-list-noise", lp_head, lp_base, f"  {LP}  \n\n{LP}\nREADME.md\n{LP}\n", dn=False)
    scoped("fs-tiny-drop", one(H, LP, [("a", 13987, 8228)]), one(B, LP, [("a", 13987, 8229)]), LP + "\n", dn=False)
    add("fs-head-missing", ["head.xml", "--against=base.xml", "--changed-files=changed.txt"],
        {"base.xml": lp_base, "changed.txt": LP + "\n"})
    add("fs-base-not-xml", ["head.xml", "--against=base.xml", "--changed-files=changed.txt"],
        {"head.xml": lp_head, "base.xml": "nope", "changed.txt": LP + "\n"})
    scoped("fs-unnamed-file-entry", clover([file_xml("", OTHER_M), file_xml(f"{H}/{LP}", SURVIVORS)]),
           lp_base, LP + "\n", dn=False)
    scoped("fs-package-wrapped", clover([file_xml(f"{H}/{LP}", SURVIVORS)], package=True),
           clover([file_xml(f"{B}/{LP}", LP_BASE)], package=True), LP + "\n", dn=False)

    # ── --deletion-neutral ───────────────────────────────────────────────
    scoped("dn-pure-deletion", lp_head, lp_base, LP + "\n")
    scoped("dn-regression", one(H, LP, REGRESSED), lp_base, LP + "\n")
    scoped("dn-added-untested", one(H, LP, WITH_NEW), one(B, LP, SURVIVORS), LP + "\n")
    scoped("dn-delete-and-add", one(H, LP, WITH_NEW), lp_base, LP + "\n")
    scoped("dn-improved", one(H, LP, SURVIVORS[:-1] + [("describeSlot", 13, 13)]), lp_base, LP + "\n")
    scoped("dn-tiny-drop", one(H, LP, [("a", 13987, 8228)]), one(B, LP, [("a", 13987, 8229)]), LP + "\n")
    scoped("dn-absent-both", lp_head, lp_base, "lib/Service/Absent.php\n")
    scoped("dn-new-file", lp_head, one(B, OTHER, OTHER_M), LP + "\n")
    scoped("dn-deleted-file", one(H, OTHER, OTHER_M), clover([file_xml(f"{B}/{LP}", SURVIVORS),
                                                             file_xml(f"{B}/{OTHER}", OTHER_M)]),
           f"{LP}\n{OTHER}\n")
    scoped("dn-base-no-lines", lp_head, one(B, LP, LP_BASE, lines=False), LP + "\n")
    scoped("dn-head-no-lines", one(H, LP, SURVIVORS, lines=False), lp_base, LP + "\n")
    scoped("dn-both-no-lines", one(H, LP, SURVIVORS, lines=False), one(B, LP, LP_BASE, lines=False), LP + "\n")
    scoped("dn-no-lines-raw-covered-attr", one(H, LP, SURVIVORS, lines=False, covered_attr="0183"),
           lp_base, LP + "\n")
    scoped("dn-no-lines-other-file-kept",
           clover([file_xml(f"{H}/{LP}", SURVIVORS, lines=False), file_xml(f"{H}/{OTHER}", OTHER_M)]),
           clover([file_xml(f"{B}/{LP}", LP_BASE), file_xml(f"{B}/{OTHER}", [("index", 10, 9), ("show", 8, 8)])]),
           f"{LP}\n{OTHER}\n")
    scoped("dn-declared-mismatch", one(H, LP, SURVIVORS, declared=260), one(B, LP, LP_BASE, declared=300),
           LP + "\n")
    scoped("dn-zero-declared-zero-lines", one(H, LP, SURVIVORS, lines=False, declared=0), lp_base, LP + "\n")
    scoped("dn-lines-nested-in-class", one(H, LP, SURVIVORS, nested=True), lp_base, LP + "\n")
    scoped("dn-no-file-metrics", one(H, LP, SURVIVORS, metrics=False), lp_base, LP + "\n")
    scoped("dn-unnamed-methods", one(H, LP, [(None, 5, 5), ("", 4, 1), ("run", 3, 3)]),
           one(B, LP, [(None, 5, 5), ("", 4, 2), ("run", 3, 3)]), LP + "\n")
    scoped("dn-statements-before-first-method", one(H, LP, [("run", 3, 3)], lead=4),
           one(B, LP, [("run", 3, 3)], lead=2), LP + "\n")
    scoped("dn-unnamed-method-meets-leading-statements", one(H, LP, [("run", 3, 3)], lead=4),
           one(B, LP, [("", 4, 4), ("run", 3, 3)]), LP + "\n")
    scoped("dn-same-name-twice", one(H, LP, [("__construct", 5, 5), ("__construct", 3, 0)]),
           one(B, LP, [("__construct", 5, 5), ("__construct", 3, 1)]), LP + "\n")
    scoped("dn-rename", one(H, LP, [("newName", 10, 10), ("other", 10, 5)]),
           one(B, LP, [("oldName", 10, 10), ("other", 10, 5)]), LP + "\n")
    scoped("dn-suffix-matches-many", clover([file_xml(f"{H}/lib/A/Foo.php", OTHER_M),
                                             file_xml(f"{H}/lib/B/Foo.php", [("x", 5, 1)])]),
           clover([file_xml(f"{B}/lib/A/Foo.php", OTHER_M)]), "Foo.php\n")
    scoped("dn-two-wanted-one-entry", one(H, LP, SURVIVORS), lp_base, f"WidgetService.php\n{LP}\n")
    scoped("dn-package-wrapped", clover([file_xml(f"{H}/{LP}", SURVIVORS)], package=True),
           clover([file_xml(f"{B}/{LP}", LP_BASE)], package=True), LP + "\n")
    scoped("dn-unnamed-file-entry", clover([file_xml("", OTHER_M), file_xml(f"{H}/{LP}", SURVIVORS)]),
           lp_base, LP + "\n")
    scoped("dn-empty-clover", clover([], project=(0, 0)), clover([], project=(0, 0)), LP + "\n")
    scoped("dn-head-empty-clover", clover([], project=(0, 0)), lp_base, LP + "\n")
    add("dn-head-missing", ["head.xml", "--against=base.xml", "--changed-files=changed.txt", "--deletion-neutral"],
        {"base.xml": lp_base, "changed.txt": LP + "\n"})
    add("dn-base-missing", ["head.xml", "--against=base.xml", "--changed-files=changed.txt", "--deletion-neutral"],
        {"head.xml": one(H, LP, SURVIVORS, declared=1), "changed.txt": LP + "\n"})
    add("dn-base-not-xml", ["head.xml", "--against=base.xml", "--changed-files=changed.txt", "--deletion-neutral"],
        {"head.xml": lp_head, "base.xml": "", "changed.txt": LP + "\n"})
    return c


def run_case(guard: Path, case: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "scripts").mkdir()
        shutil.copyfile(guard, root / "scripts" / "coverage-guard.php")
        for rel, text in case["files"].items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        floor = root / ".coverage-baseline"
        if case["baseline"] is not None:
            floor.write_text(case["baseline"])
        p = subprocess.run(["php", "scripts/coverage-guard.php", *case["args"]], cwd=root,
                           capture_output=True, text=True, timeout=60)
        # The guard prints the floor's path, which contains the temp dir.
        def scrub(s: str) -> str:
            return s.replace(tmp, "<case>")
        return {
            "exit": p.returncode,
            "stdout": scrub(p.stdout),
            "stderr": scrub(p.stderr),
            "floor_after": floor.read_text() if floor.exists() else None,
        }


def main(argv: List[str]) -> int:
    record = "--record" in argv
    rest = [a for a in argv[1:] if a != "--record"]
    guard = Path(rest[0]).resolve() if rest else (HERE.parent / "coverage-guard.php")
    if shutil.which("php") is None:
        print("::error::php is not on PATH")
        return 1
    if not guard.exists():
        print(f"::error::coverage guard not found at {guard}")
        return 1

    results = {name: run_case(guard, case) for name, case in cases().items()}

    if record:
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps(results, indent=1, sort_keys=True) + "\n")
        print(f"recorded {len(results)} cases into {GOLDEN} (compared nothing)")
        return 0

    golden = json.loads(GOLDEN.read_text())
    failed = 0
    if set(golden) != set(results):
        print(f"FAIL — case set differs: missing {sorted(set(golden) - set(results))}, "
              f"extra {sorted(set(results) - set(golden))}")
        failed += 1
    for name in sorted(set(golden) & set(results)):
        want, got = golden[name], results[name]
        diffs = [k for k in ("exit", "stdout", "stderr", "floor_after") if want[k] != got[k]]
        if diffs:
            failed += 1
            print(f"  FAIL — {name}: {', '.join(diffs)} differ")
            for k in diffs:
                print(f"         want {k}: {want[k]!r}"[:600])
                print(f"         got  {k}: {got[k]!r}"[:600])
        else:
            print(f"  ok   — {name} (exit {got['exit']})")
    print(f"\n{len(results)} cases, {failed} differing")
    print("PASS" if failed == 0 else "FAIL")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
