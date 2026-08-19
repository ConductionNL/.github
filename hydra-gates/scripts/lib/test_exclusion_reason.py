#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""test_exclusion_reason — .github#400, across all FOUR exclusion gates.

WHAT IS UNDER TEST
==================
Four gates let a change opt out of coverage by writing a justification beside a
marker. All four captured that justification with the same regex and then graded
it with plain Python truthiness, so a single full stop was accepted as a reason:

    gate-16 spec-coverage      check_spec_coverage.py
    gate-19 e2e-coverage       check_e2e_coverage.py   (scenario AND whole-spec)
    gate-25 contract-coverage  check_contract_coverage.py
    gate-26 visual-coverage    check_visual_coverage.py

Reproduced through the real wrapper on two repositories byte-identical apart
from one character: `@spec exclude` FAILED, `@spec exclude.` PASSED.

The repair is a single shared predicate, exclusion_reason.is_reason_bearing().
This suite exists because the defect's real cause was STRUCTURAL — the rule was
copied four times — so the assertions below deliberately exercise all four call
sites separately. Reverting any ONE of them to `if reason:` must turn a NAMED
assertion red; that is the revert-proof, and it is why there are four fixtures
and not one.

WHY EACH FIXTURE HAS ITS OWN SUBJECT TOKEN
------------------------------------------
Every assertion greps for a token unique to its own fixture
(`specReasonPunctuationProbe`, `contractReasonPunctuationProbe`,
`VisualReasonPunctuationProbe`, `e2e-scenario-punctuation-probe`,
`wholespecpunctuationprobe`). None is a prefix of another. A subject that a
SIBLING finding could also satisfy makes a bundle vacuous for its own defect —
an assertion that passes because some other gate produced some other finding has
measured nothing.

WHY THERE IS A PURE-PROSE CONTROL
---------------------------------
A test fixture that EXPLAINS an exclusion marker contains the marker, and a
scanner cannot tell the explanation from the thing. So one fixture mentions the
markers only in prose and must produce NO exclusion at all. If that control ever
goes red, this suite has started measuring its own commentary.

ANTI-WIDENING
-------------
Every gate also gets an arm in which a REAL reason is written, and it must still
be credited. A predicate that rejected everything would satisfy every defect
assertion here while retiring the exclusion mechanism fleet-wide — strictly
worse than the bug it replaces.

Run: python3 hydra-gates/scripts/lib/test_exclusion_reason.py
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

# An empty run is not a green run — see run-helper-suites.sh on the same trap.
MIN_ASSERTIONS = 38

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


# ---------------------------------------------------------------------------
# git fixture support
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-c", "user.email=t@example.invalid", "-c", "user.name=t",
         "-c", "commit.gpgsign=false", "-C", str(repo), *args],
        capture_output=True, text=True, check=False,
    )


def make_repo(root: Path, base_files: dict[str, str], head_files: dict[str, str]) -> str:
    """Two commits. Returns the BASE sha, for HYDRA_GATE_BASE_REF.

    A FIXTURE THAT FAILED TO BUILD MUST NOT LOOK LIKE A FIXTURE.
    ------------------------------------------------------------
    The first version of this helper called ``git init -b main``, which git
    2.25 does not support. Every repo silently failed to exist, so the gates ran
    with no base ref at all — i.e. at FULL SCOPE — and two arms went green while
    testing something other than what they claimed. The files are on disk either
    way, which is exactly what makes the failure invisible. So every git step is
    now checked, and a broken fixture raises instead of degrading into a
    differently-scoped run that still prints a plausible verdict.
    """
    root.mkdir(parents=True, exist_ok=True)

    def must(*args: str) -> subprocess.CompletedProcess:
        r = _git(root, *args)
        if r.returncode != 0:
            raise RuntimeError(
                f"fixture build failed: git {' '.join(args)} -> rc={r.returncode}\n"
                f"{r.stdout}{r.stderr}"
            )
        return r

    def write(files: dict[str, str]) -> None:
        for rel, body in files.items():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body, encoding="utf-8")

    must("init", "-q")
    write(base_files)
    must("add", "-A")
    must("commit", "-q", "-m", "base")
    base = must("rev-parse", "HEAD").stdout.strip()
    if len(base) < 7:
        raise RuntimeError(f"fixture build failed: no base sha (got {base!r})")
    write(head_files)
    must("add", "-A")
    must("commit", "-q", "-m", "head")
    # The base must actually be an ancestor, or `BASE...HEAD` is not the diff
    # the gate thinks it is.
    if not _git(root, "diff", "--quiet", f"{base}...HEAD").returncode:
        raise RuntimeError("fixture build failed: base...HEAD is an EMPTY diff")
    return base


def run_checker(script: str, app: Path, base: str | None = None,
                mode: str | None = None) -> tuple[int, str]:
    env = dict(os.environ)
    if base:
        env["HYDRA_GATE_BASE_REF"] = base
    else:
        env.pop("HYDRA_GATE_BASE_REF", None)
    argv = ["python3", str(LIB / script), str(app)]
    if mode:
        argv += ["--mode", mode]
    r = subprocess.run(argv, capture_output=True, text=True, env=env, check=False)
    return r.returncode, r.stdout + r.stderr


# ---------------------------------------------------------------------------
# 1. The predicate itself
# ---------------------------------------------------------------------------


def suite_predicate() -> None:
    print("\n== the shared predicate ==")
    check("a full stop is NOT a reason — the exact input from .github#400",
          is_reason_bearing(".") is False)
    check("an empty reason is NOT a reason (unchanged behaviour)",
          is_reason_bearing("") is False)
    check("None is NOT a reason (unchanged behaviour)",
          is_reason_bearing(None) is False)
    # Every one of these is a real shape the fleet-wide scan turned up as a
    # candidate "reason" (mostly prose whose trailing backtick or bracket became
    # the capture). Graded as ONE assertion, but the detail names the offender —
    # and deliberately without an early return, so a failure here does not
    # silently shorten the rest of this suite.
    junk_accepted = [j for j in ("..", "...", "-", "--", "?", "!", "*", "/",
                                 ")", "`)", "`.")
                     if is_reason_bearing(j) is not False]
    check("every punctuation-only shape observed in the fleet scan is refused "
          "('..', '...', '-', '--', '?', '!', '*', '/', ')', '`)', '`.')",
          not junk_accepted,
          f"accepted as reasons: {junk_accepted}")
    check("an underscore run is refused — \\w would have accepted it, "
          "so the rule is letter-or-digit, not word-character",
          is_reason_bearing("___") is False)
    check(f"a reason shorter than REASON_MIN_CHARS={REASON_MIN_CHARS} is refused "
          "('x', 'ok')",
          is_reason_bearing("x") is False and is_reason_bearing("ok") is False)
    check("ANTI-WIDENING: a real prose reason is still a reason",
          is_reason_bearing("pure plumbing, verified by PHPUnit") is True)
    check("ANTI-WIDENING: a terse but alphanumeric reason is still a reason "
          "— the floor is degenerate-token detection, NOT quality grading",
          is_reason_bearing("below") is True
          and is_reason_bearing("covered by") is True)
    # 10 is the shortest reason any of the four checkers actually credits today,
    # measured over all 18 core apps. The floor must stay clear of it, or the
    # first legitimately terse reason someone writes goes red — and raising it
    # to 10 would be a fleet POLICY change, not a repair of #400.
    check("the floor keeps margin below the shortest reason a checker credits "
          f"today (10 chars): REASON_MIN_CHARS={REASON_MIN_CHARS} <= 3",
          REASON_MIN_CHARS <= 3)
    check("a non-ASCII reason is accepted — the rule is Unicode letter-or-digit, "
          "not [a-z], so a Dutch-language reason is not silently refused",
          is_reason_bearing("één reden, gedekt door PHPUnit") is True)
    check("why_rejected() names PUNCTUATION for '...', which is long enough to "
          "reach that branch — the message is kept beside the rule so the two "
          "cannot drift apart",
          "punctuation" in why_rejected("...").lower()
          and "letter or digit" in why_rejected("..."),
          why_rejected("..."))
    check("why_rejected() reports LENGTH for '.', not punctuation — a "
          "one-character reason fails the floor first, and the message must "
          "say which rule actually rejected it",
          "shorter than" in why_rejected("."), why_rejected("."))
    check("why_rejected() still says 'no reason given' for the bare marker",
          why_rejected("") == "no reason given", why_rejected(""))
    check("why_rejected() is EMPTY for an accepted reason — a gate must not be "
          "handed a rejection message for something it accepted",
          why_rejected("covered by SpecProbeServiceTest") == "")


# ---------------------------------------------------------------------------
# 2. The marker patterns did not move
# ---------------------------------------------------------------------------


def suite_patterns() -> None:
    print("\n== the marker patterns are byte-identical to the four originals ==")
    historical = {
        "gate-16 @spec": (
            ("spec", False),
            r"@spec\s+exclude\b[ \t]*(?P<reason>.*?)\s*$"),
        "gate-19 @e2e scenario/requirement": (
            ("e2e", False),
            r"@e2e\s+exclude\b[ \t]*(?P<reason>.*?)\s*$"),
        "gate-19 @e2e WHOLE-SPEC (anchored, .github#358)": (
            ("e2e", True),
            r"^[ \t>*#\-]*@e2e\s+exclude\b[ \t]*(?P<reason>.*?)\s*$"),
        "gate-25 @contract": (
            ("contract", False),
            r"@contract\s+exclude\b[ \t]*(?P<reason>.*?)\s*$"),
        "gate-26 @visual": (
            ("visual", False),
            r"@visual\s+exclude\b[ \t]*(?P<reason>.*?)\s*$"),
    }
    for label, ((tag, standalone), want) in historical.items():
        got = exclude_pattern(tag, standalone=standalone)
        check(f"{label} pattern is unchanged by the refactor", got == want,
              f"want: {want}\ngot : {got}")
    check("the whole-spec form is the ONLY anchored one — an anchor on the "
          "scenario form would silently retire inline markers",
          exclude_pattern("e2e").startswith("@")
          and exclude_pattern("e2e", standalone=True).startswith("^"))


# ---------------------------------------------------------------------------
# 3. gate-16 — check_spec_coverage.py
# ---------------------------------------------------------------------------

_PHP_HEAD = """<?php
namespace OCA\\Fx\\Service;

class SpecProbeService {
"""


def _php_method(name: str, tag_line: str) -> str:
    return f"""
    /**
     * Probe.
     *
     * {tag_line}
     */
    public function {name}(string $a): string {{
        return $a;
    }}
"""


def suite_gate16(tmp: Path) -> None:
    print("\n== gate-16 spec-coverage (check_spec_coverage.py) ==")
    base_php = _PHP_HEAD + "}\n"

    # ARM A — the defect: a full stop as the whole reason.
    app = tmp / "g16-punct"
    base = make_repo(
        app,
        {"lib/Service/SpecProbeService.php": base_php},
        {"lib/Service/SpecProbeService.php":
            _PHP_HEAD + _php_method("specReasonPunctuationProbe", "@spec exclude .") + "}\n"},
    )
    rc, out = run_checker("check_spec_coverage.py", app, base)
    check("gate-16 refuses '@spec exclude .' and names specReasonPunctuationProbe",
          "specReasonPunctuationProbe" in out and "# count=1" in out,
          f"rc={rc}\n{out}")

    # ARM B — anti-widening: a real reason must still be credited.
    #
    # THE WITNESS IS WHAT MAKES THIS NON-VACUOUS. "specReasonProseProbe is not
    # reported" is also true of a run that inspected nothing at all, which is
    # precisely how the first draft of this suite went green while its fixtures
    # were failing to build. So the same file carries an UNTAGGED method that
    # MUST be reported: count=1 naming the witness is proof the walker opened
    # the file and graded both methods.
    app = tmp / "g16-real"
    base = make_repo(
        app,
        {"lib/Service/SpecProbeService.php": base_php},
        {"lib/Service/SpecProbeService.php":
            _PHP_HEAD
            + _php_method("specReasonProseProbe",
                          "@spec exclude thin passthrough, covered by SpecProbeServiceTest")
            + _php_method("specReasonWitnessProbe", "(no tag at all)")
            + "}\n"},
    )
    rc, out = run_checker("check_spec_coverage.py", app, base)
    check("ANTI-WIDENING gate-16 still credits a real reason "
          "(specReasonProseProbe is not reported)",
          "specReasonProseProbe" not in out, f"rc={rc}\n{out}")
    check("WITNESS gate-16 did inspect that file — the untagged "
          "specReasonWitnessProbe IS reported, so the arm above is not vacuous",
          "specReasonWitnessProbe" in out and "# count=1" in out,
          f"rc={rc}\n{out}")

    # ARM B2 — the LOCAL normalisation still runs before the shared predicate.
    # A docblock close is not a reason; spec/contract strip `*/` themselves and
    # only the verdict is shared, so this must stay refused.
    app = tmp / "g16-closeonly"
    base = make_repo(
        app,
        {"lib/Service/SpecProbeService.php": base_php},
        {"lib/Service/SpecProbeService.php":
            _PHP_HEAD + _php_method("specReasonCloseOnlyProbe", "@spec exclude */") + "}\n"},
    )
    rc, out = run_checker("check_spec_coverage.py", app, base)
    check("gate-16 refuses a reason that is only the docblock close "
          "(specReasonCloseOnlyProbe) — local normalisation still precedes the "
          "shared predicate",
          "specReasonCloseOnlyProbe" in out, f"rc={rc}\n{out}")

    # ARM C — the bare marker still fails, i.e. the old path is intact.
    app = tmp / "g16-bare"
    base = make_repo(
        app,
        {"lib/Service/SpecProbeService.php": base_php},
        {"lib/Service/SpecProbeService.php":
            _PHP_HEAD + _php_method("specReasonBareProbe", "@spec exclude") + "}\n"},
    )
    rc, out = run_checker("check_spec_coverage.py", app, base)
    check("gate-16 still refuses a BARE '@spec exclude' (specReasonBareProbe) "
          "— the pre-existing branch was not disturbed",
          "specReasonBareProbe" in out and "# count=1" in out,
          f"rc={rc}\n{out}")

    # ARM D — the control the whole reproduction rests on: the two refused
    # fixtures really do differ by exactly the one character in the report.
    punct = _php_method("p", "@spec exclude .")
    bare = _php_method("p", "@spec exclude")
    check("CONTROL: the punctuation fixture is the bare fixture plus exactly "
          "one character — the reproduction in .github#400",
          punct.replace(" .", "", 1) == bare and len(punct) == len(bare) + 2,
          f"punct={punct!r}\nbare={bare!r}")


# ---------------------------------------------------------------------------
# 4. gate-19 — check_e2e_coverage.py, BOTH forms
# ---------------------------------------------------------------------------


def _spec_md(title: str, scenario: str, marker: str) -> str:
    return f"""---
status: done
---

# {title}

## Purpose

Fixture.

## Requirements

### REQ-PROBE-001: probe

#### Scenario: {scenario}

{marker}

- GIVEN a fixture
- THEN nothing
"""


def _whole_spec_md(title: str, marker: str) -> str:
    return f"""---
status: done
---

# {title}

{marker}

## Requirements

### REQ-PROBE-001: probe

#### Scenario: first probe scenario

- GIVEN a fixture
- THEN nothing

#### Scenario: second probe scenario

- GIVEN a fixture
- THEN nothing
"""


def suite_gate19(tmp: Path) -> None:
    print("\n== gate-19 e2e-coverage (check_e2e_coverage.py) ==")

    # ---- SCENARIO-LEVEL form ----
    app = tmp / "g19-scenario-punct"
    app.mkdir(parents=True)
    (app / "openspec/specs/probe").mkdir(parents=True)
    (app / "openspec/specs/probe/spec.md").write_text(
        _spec_md("Probe", "e2e scenario punctuation probe", "@e2e exclude ."),
        encoding="utf-8")
    rc, out = run_checker("check_e2e_coverage.py", app, mode="report")
    check("gate-19 refuses a scenario-level '@e2e exclude .' — "
          "e2e-scenario-punctuation-probe is NOT counted as excluded",
          '"excluded": 0' in out, out)

    app = tmp / "g19-scenario-real"
    app.mkdir(parents=True)
    (app / "openspec/specs/probe").mkdir(parents=True)
    (app / "openspec/specs/probe/spec.md").write_text(
        _spec_md("Probe", "e2e scenario punctuation probe",
                 "@e2e exclude background-only, not UI-observable"),
        encoding="utf-8")
    rc, out = run_checker("check_e2e_coverage.py", app, mode="report")
    check("ANTI-WIDENING gate-19 still credits a real scenario-level reason "
          "(e2e-scenario-punctuation-probe IS excluded)",
          '"excluded": 1' in out, out)

    # ---- WHOLE-SPEC form — the expensive one (#345 + #356) ----
    app = tmp / "g19-wholespec-punct"
    app.mkdir(parents=True)
    (app / "openspec/specs/wholespecpunctuationprobe").mkdir(parents=True)
    (app / "openspec/specs/wholespecpunctuationprobe/spec.md").write_text(
        _whole_spec_md("Whole Spec Punctuation Probe", "@e2e exclude ."),
        encoding="utf-8")
    rc, out = run_checker("check_e2e_coverage.py", app, mode="report")
    check("gate-19 refuses a WHOLE-SPEC '@e2e exclude .' — neither scenario in "
          "wholespecpunctuationprobe is credited (this is the form that can "
          "blanket a whole file, so one full stop credited them all)",
          '"scenarios": 2' in out and '"excluded": 0' in out, out)

    app = tmp / "g19-wholespec-real"
    app.mkdir(parents=True)
    (app / "openspec/specs/wholespecpunctuationprobe").mkdir(parents=True)
    (app / "openspec/specs/wholespecpunctuationprobe/spec.md").write_text(
        _whole_spec_md("Whole Spec Punctuation Probe",
                       "@e2e exclude pure backend contract, covered by Newman"),
        encoding="utf-8")
    rc, out = run_checker("check_e2e_coverage.py", app, mode="report")
    check("ANTI-WIDENING gate-19 still honours a real WHOLE-SPEC reason "
          "(both wholespecpunctuationprobe scenarios excluded)",
          '"scenarios": 2' in out and '"excluded": 2' in out, out)

    # ---- the finding TEXT, in gate mode ----
    app = tmp / "g19-gate"
    base = make_repo(
        app,
        {"openspec/specs/probe/spec.md": "# Probe\n\n## Requirements\n"},
        {"openspec/specs/probe/spec.md":
            _spec_md("Probe", "e2e scenario punctuation probe", "@e2e exclude .")},
    )
    rc, out = run_checker("check_e2e_coverage.py", app, base)
    check("gate-19 gate mode reports the punctuation marker as reasonless, "
          "naming e2e-scenario-punctuation-probe",
          rc == 1 and "e2e-scenario-punctuation-probe" in out
          and "without reason" in out, f"rc={rc}\n{out}")


# ---------------------------------------------------------------------------
# 5. gate-25 — check_contract_coverage.py
# ---------------------------------------------------------------------------

_ROUTES = """<?php
return ['routes' => [
    ['name' => 'probe#contractReasonPunctuationProbe', 'url' => '/api/probe-punct', 'verb' => 'GET'],
    ['name' => 'probe#contractReasonProseProbe', 'url' => '/api/probe-prose', 'verb' => 'GET'],
    ['name' => 'probe#contractWitnessProbe', 'url' => '/api/probe-witness', 'verb' => 'GET'],
]];
"""

_CTRL_HEAD = """<?php
namespace OCA\\Fx\\Controller;

use OCP\\AppFramework\\Controller;

class ProbeController extends Controller {
"""


def _ctrl_method(name: str, tag_line: str) -> str:
    return f"""
    /**
     * Probe endpoint.
     *
     * #[NoAdminRequired]
     * {tag_line}
     */
    #[\\OCP\\AppFramework\\Http\\Attribute\\NoAdminRequired]
    public function {name}(): \\OCP\\AppFramework\\Http\\JSONResponse {{
        return new \\OCP\\AppFramework\\Http\\JSONResponse([]);
    }}
"""


def suite_gate25(tmp: Path) -> None:
    print("\n== gate-25 contract-coverage (check_contract_coverage.py) ==")
    base_files = {
        "appinfo/routes.php": _ROUTES,
        "lib/Controller/ProbeController.php": _CTRL_HEAD + "}\n",
    }

    app = tmp / "g25-punct"
    base = make_repo(app, base_files, {
        "appinfo/routes.php": _ROUTES,
        "lib/Controller/ProbeController.php":
            _CTRL_HEAD + _ctrl_method("contractReasonPunctuationProbe",
                                      "@contract exclude .") + "}\n",
    })
    rc, out = run_checker("check_contract_coverage.py", app, base)
    # rc is checked as well as the name: EXIT_ERROR is 2, and a crashed checker
    # that echoed the fixture back would otherwise satisfy a name-only grep.
    check("gate-25 refuses '@contract exclude .' and names "
          "contractReasonPunctuationProbe",
          rc == 1 and "contractReasonPunctuationProbe" in out, f"rc={rc}\n{out}")

    # The witness makes the anti-widening arm non-vacuous — see gate-16 ARM B.
    app = tmp / "g25-real"
    base = make_repo(app, base_files, {
        "appinfo/routes.php": _ROUTES,
        "lib/Controller/ProbeController.php":
            _CTRL_HEAD + _ctrl_method(
                "contractReasonProseProbe",
                "@contract exclude internal health probe, deliberately absent "
                "from the published OAS")
            + _ctrl_method("contractWitnessProbe", "(no contract tag at all)")
            + "}\n",
    })
    rc, out = run_checker("check_contract_coverage.py", app, base)
    check("ANTI-WIDENING gate-25 still credits a real reason "
          "(contractReasonProseProbe is not reported)",
          "contractReasonProseProbe" not in out, f"rc={rc}\n{out}")
    check("WITNESS gate-25 did inspect that controller — the untagged "
          "contractWitnessProbe IS reported, so the arm above is not vacuous",
          "contractWitnessProbe" in out, f"rc={rc}\n{out}")


# ---------------------------------------------------------------------------
# 6. gate-26 — check_visual_coverage.py
# ---------------------------------------------------------------------------


def _vue(marker: str) -> str:
    return f"""<template>
  <!-- {marker} -->
  <div class="probe">probe</div>
</template>

<script>
export default {{ name: 'VisualReasonPunctuationProbe' }}
</script>
"""


def suite_gate26(tmp: Path) -> None:
    print("\n== gate-26 visual-coverage (check_visual_coverage.py) ==")
    base_files = {"src/views/ExistingView.vue": _vue("nothing here")}

    app = tmp / "g26-punct"
    base = make_repo(app, base_files, {
        "src/views/ExistingView.vue": _vue("nothing here"),
        "src/views/VisualReasonPunctuationProbe.vue": _vue("@visual exclude ."),
    })
    rc, out = run_checker("check_visual_coverage.py", app, base)
    # rc as well as the name — see the note in suite_gate25().
    check("gate-26 refuses '@visual exclude .' and names "
          "VisualReasonPunctuationProbe.vue",
          rc == 1 and "VisualReasonPunctuationProbe.vue" in out, f"rc={rc}\n{out}")

    # The witness makes the anti-widening arm non-vacuous — see gate-16 ARM B.
    app = tmp / "g26-real"
    base = make_repo(app, base_files, {
        "src/views/ExistingView.vue": _vue("nothing here"),
        "src/views/VisualReasonPunctuationProbe.vue":
            _vue("@visual exclude chart canvas renders nondeterministically"),
        "src/views/VisualWitnessProbe.vue": _vue("no marker at all"),
    })
    rc, out = run_checker("check_visual_coverage.py", app, base)
    check("ANTI-WIDENING gate-26 still credits a real reason "
          "(VisualReasonPunctuationProbe.vue is not reported)",
          "VisualReasonPunctuationProbe.vue" not in out, f"rc={rc}\n{out}")
    check("WITNESS gate-26 did inspect that page set — the unmarked "
          "VisualWitnessProbe.vue IS reported, so the arm above is not vacuous",
          "VisualWitnessProbe.vue" in out, f"rc={rc}\n{out}")


# ---------------------------------------------------------------------------
# 7. The prose control
# ---------------------------------------------------------------------------


def suite_prose_control(tmp: Path) -> None:
    print("\n== control: prose ABOUT a marker is not a marker ==")
    # Every hit in the fleet-wide scan that looked like a punctuation-only
    # reason was PROSE — a sentence discussing the mechanism, whose trailing
    # backtick or bracket became "the reason". If this suite ever starts
    # measuring its own commentary, this control is what says so.
    app = tmp / "prose-control"
    app.mkdir(parents=True)
    (app / "openspec/specs/probe").mkdir(parents=True)
    (app / "openspec/specs/probe/spec.md").write_text(
        """---
status: done
---

# Probe

## Purpose

Backend scenarios below are annotated with the e2e exclusion marker (see the
gate docs) and the frontend ones are not.

## Requirements

### REQ-PROBE-001: probe

#### Scenario: prose control scenario

- GIVEN a fixture
- THEN nothing
""", encoding="utf-8")
    rc, out = run_checker("check_e2e_coverage.py", app, mode="report")
    check("CONTROL: a spec whose Purpose merely DESCRIBES exclusion excludes "
          "nothing (0 of 1 scenarios excluded)",
          '"scenarios": 1' in out and '"excluded": 0' in out, out)


# ---------------------------------------------------------------------------


def main() -> int:
    print("== .github#400 — an exclusion reason must not be punctuation ==")
    with tempfile.TemporaryDirectory(prefix="hydra-excl-reason.") as td:
        tmp = Path(td)
        suite_predicate()
        suite_patterns()
        suite_gate16(tmp)
        suite_gate19(tmp)
        suite_gate25(tmp)
        suite_gate26(tmp)
        suite_prose_control(tmp)

    total = len(_passed) + len(_failed)
    print()
    print(f"== {len(_passed)} passed / {len(_failed)} failed / {total} run ==")
    if total < MIN_ASSERTIONS:
        print(f"FAIL — only {total} assertions ran, expected at least "
              f"{MIN_ASSERTIONS}. A short run is not a green run.")
        return 1
    if _failed:
        print("FAILED assertions:")
        for f in _failed:
            print(f"  - {f}")
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
