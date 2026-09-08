#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Gate-113 exclusion-evidence — an exclusion that names a test nobody can find.

WHY THIS EXISTS
===============

``exclusion_reason.py`` draws a deliberately narrow line: it rejects a reason
that is STRUCTURALLY degenerate, a marker that cannot be naming anything at
all. Its own docstring says what it will not do, and why:

    The standing rule is that an exemption's reason is a testable claim:
    reasons naming a *test artifact* hold, reasons naming a *state of the
    world* rot. That is a SEMANTIC property, and no character count can
    measure it. ... Judging that needs a purpose-built check, not a ``len()``.

This is that check.

MEASURED 2026-09-08 across the 21 core apps. 19,591 of 27,045 scenarios (72%)
are excluded from gate-19 with a reason. Of the 5,563 distinct reason strings
behind them:

    665   name something artifact-shaped (a *Test class, a ::method, a
          .spec file, a collection, a gate number)          12%
    4,898 do not                                            88%

The 88% is not prose nobody bothered to write. It is mostly a real claim
pitched one level too high to check: "asserted by PHPUnit", "covered by unit
tests", "backend, server-side". Those are almost certainly true. Nothing can
confirm any of them, nothing notices when the named test is deleted, and the
reader who inherits the scenario has no thread to pull.

WHAT IT REPORTS
===============

**V1 — RESOLVED.** The reason names an artifact and the artifact is here. This
is the shape every exclusion should reach. Not a finding; counted so the
migration has a numerator.

**V2 — UNRESOLVED.** The reason names an artifact-shaped token and NOTHING in
this repo answers to it. The exclusion reads as verified and is not. This is
the only finding gate mode fails on, because it is the only one that is
provably wrong rather than merely unverifiable. A renamed or deleted test
lands here the day it moves.

**V3 — UNVERIFIABLE.** The reason claims a tier without naming a member of it:
"covered by PHPUnit", "unit tested", "asserted in vitest". Probably true,
permanently uncheckable. Reported as the migration worklist, never failed on:
4,898 findings on day one is a gate nobody can turn on, and the fix is a
mechanical annotation pass rather than a code change.

**V4 — NO CLAIM.** The reason names no evidence of any kind. "depends on test
data state", "requires existing article", "below". These describe a state of
the world, which is exactly the shape ``exclusion_reason.py`` predicted would
rot.

WHAT COUNTS AS RESOLUTION
=========================

A reason resolves when a token in it matches something on disk:

    FooServiceTest              a class in any tests/**/*Test.php
    FooServiceTest::testBar     that class AND that method
    foo.spec.ts / foo.spec.js   a file under tests/ or src/
    x.postman_collection.json   a committed collection
    gate-N                      a two- or three-digit gate number

Deliberately generous. The question is "can a reader find what this names",
not "is this the best possible citation".

Usage::

    python3 scripts/lib/check_exclusion_evidence.py [app-dir]
    python3 scripts/lib/check_exclusion_evidence.py [app-dir] --mode report
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exclusion_reason import exclude_pattern, is_reason_bearing  # noqa: E402

GATE_NUM = 113
GATE_NAME = "exclusion-evidence"

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_ERROR = 2
EXIT_NOT_APPLICABLE = 4

RESOLVED = "resolved"
UNRESOLVED = "unresolved"
UNVERIFIABLE = "unverifiable"
NO_CLAIM = "no-claim"
CROSS_REPO = "cross-repo"

# A CITATION THIS REPO CANNOT REACH IS NOT A BROKEN CITATION.
#
# This gate only ever looks in the app's own tree, and the fleet's specs
# legitimately cite tests in SIBLING repositories:
#
#   hermiq   "covered by nextcloud-vue `tests/components/CnFlowEdge.spec.js`"
#            -> nextcloud-vue/tests/components/CnFlowEdge.spec.js  EXISTS
#   hermiq   "the warning is produced by OpenRegister's save response,
#            covered by FlowDeadEndTest"
#            -> openregister/tests/Unit/Service/Flow/FlowDeadEndTest.php EXISTS
#   filinq   "asserted in OpenRegister (ProcessingLogController ...)"
#            -> openregister/tests/Unit/Controller/ProcessingLogControllerTest.php
#
# Measured 2026-09-08: 7 of the 28 remaining findings, a quarter of them, are
# this. Reporting them as "cites a test nothing answers to" accuses a correct
# citation, which is the same defect #711 fixed for a cited SUBJECT.
#
# They are DOWNGRADED, not suppressed. The bucket is printed on every run, so a
# reader still sees the claim and can go and check the other repo. What it no
# longer does is fail the gate, because this repo cannot resolve it either way
# and a checkout of it will never contain the answer.
#
# The short forms count too. pipelinq writes "engine-level behaviour covered by
# nc-vue `useWalkthrough.spec.js`", and nextcloud-vue/tests/composables/
# useWalkthrough.spec.js exists. Matching only the long name accused that one.
_CROSS_REPO_RE = re.compile(
    r"\b(?:openregister|open ?register|nextcloud-vue|nc-vue|opencatalogi|"
    r"openconnector|integriq|conduction/[a-z-]+)\b",
    re.I,
)

_SKIP_PARTS = ("node_modules", "vendor", ".git", "dist", "build", "coverage")

# The tags whose exclusions this gate judges. All four share
# `exclusion_reason.exclude_pattern`, so they share this check too.
_TAGS = ("e2e", "spec", "contract", "visual")

# --- artifact-shaped tokens in a reason ------------------------------------
# `FooServiceTest::testBarIsRejected` or bare `FooServiceTest`
_PHP_TEST_RE = re.compile(r"\b([A-Z][A-Za-z0-9_]*Test)(?:\.php)?(?:::(\w+))?\b")
# `bankStatementWizard.spec.js`, `useGridManager.spec.ts`
_JS_SPEC_RE = re.compile(r"\b([A-Za-z0-9_.\-]+\.spec\.[cm]?[jt]s)\b")
_COLLECTION_RE = re.compile(r"\b([A-Za-z0-9_.\-]+\.postman_collection\.json)\b")
_GATE_RE = re.compile(r"\bgate-(\d{1,3})\b")

# --- a tier claimed but not cited ------------------------------------------
# Ordered: the first match wins, purely for the reported label.
_TIER_CLAIMS = (
    ("phpunit", re.compile(r"\bphpunit\b|\bcontroller test\b|\bservice test\b", re.I)),
    ("unit", re.compile(r"\bvitest\b|\bjest\b|\bunit test(s|ed|ing)?\b", re.I)),
    ("gate", re.compile(r"\bgate\b|\bmechanical check\b", re.I)),
    ("api", re.compile(r"\bpostman\b|\bnewman\b|\bcollection\b|\bapi test\b", re.I)),
    ("e2e", re.compile(r"\be2e\b|\bplaywright\b", re.I)),
)


def _walk(root: Path, pattern: str):
    for p in root.rglob(pattern):
        if p.is_file() and not any(part in _SKIP_PARTS for part in p.parts):
            yield p


class _Artifacts:
    """What this repo can actually be asked to resolve a reason against."""

    def __init__(self, app_dir: Path) -> None:
        self.php_tests: dict[str, set[str]] = {}
        self.js_specs: set[str] = set()
        self.collections: set[str] = set()

        for p in _walk(app_dir, "*Test.php"):
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            methods = set(re.findall(r"function\s+(\w+)\s*\(", text))
            # Index by class name AND by file stem: the fleet's reasons cite
            # both, and they agree in every PSR-4 repo anyway.
            for cls in re.findall(r"\bclass\s+(\w+)", text) or [p.stem]:
                self.php_tests.setdefault(cls, set()).update(methods)
            self.php_tests.setdefault(p.stem, set()).update(methods)

        for pattern in ("*.spec.ts", "*.spec.js", "*.spec.mjs", "*.spec.cjs"):
            for p in _walk(app_dir, pattern):
                self.js_specs.add(p.name)
        for p in _walk(app_dir, "*.postman_collection.json"):
            self.collections.add(p.name)

    def resolve(self, reason: str) -> tuple[bool, list[str], list[str]]:
        """Does *reason* name something that exists here?

        :param reason: The exclusion reason text.
        :return: ``(names_an_artifact, resolved_tokens, missing_tokens)``.
        """
        resolved: list[str] = []
        missing: list[str] = []

        for cls, method in _PHP_TEST_RE.findall(reason):
            token = f"{cls}::{method}" if method else cls
            known = self.php_tests.get(cls)
            if known is None:
                missing.append(token)
                continue
            # A CITED SUBJECT IS NOT A MISSING TEST.
            #
            # `AcknowledgementServiceTest::isOutstanding` names the method
            # UNDER test, not a test method, and that is a legitimate and
            # common way to write the citation — the class does assert it, in
            # `testIsOutstandingReackOnChangeChecksCurrentVersion`. Demanding a
            # `function isOutstanding()` inside the test class accuses a
            # correct citation, and a finding that is wrong even occasionally
            # is a finding nobody works.
            #
            # So the method half is only checked when it is spelled as a test:
            # `::testFoo` missing from a class that exists is the rename this
            # gate is for, and shillinq's `SettingsControllerTest::testLoad`
            # (the class has `testLoadReturnsConfigurationResult`) is exactly
            # that. `::someSubject` resolves on the class alone.
            #
            # Measured on the two it got wrong: launchpad's
            # AcknowledgementServiceTest::isOutstanding and decidiq's
            # BoardMeetingServiceTest::getNoticeDeadlineInfo, 2 of 33 findings.
            if method and method.startswith("test") and method not in known:
                missing.append(token)
            else:
                resolved.append(token)

        for name in _JS_SPEC_RE.findall(reason):
            (resolved if name in self.js_specs else missing).append(name)
        for name in _COLLECTION_RE.findall(reason):
            (resolved if name in self.collections else missing).append(name)
        # A gate number is registered in ConductionNL/.github, not here, so it
        # cannot be resolved from an app checkout. Treat it as named-and-fine
        # rather than inventing a failure this repo cannot answer.
        resolved.extend(f"gate-{n}" for n in _GATE_RE.findall(reason))

        return bool(resolved or missing), resolved, missing


def _spec_files(app_dir: Path) -> list[Path]:
    """Both OpenSpec file shapes, matching gate-19."""
    root = app_dir / "openspec" / "specs"
    if not root.is_dir():
        return []
    found = list(root.glob("*/spec.md"))
    found += [
        p for p in root.glob("*.md")
        if p.is_file() and p.name.lower() != "readme.md"
    ]
    return sorted(set(found))


def classify(reason: str, artifacts: _Artifacts) -> tuple[str, dict]:
    """Sort one exclusion reason into the four buckets.

    :param reason: The reason text, already stripped by the caller.
    :param artifacts: The repo's resolvable artifacts.
    :return: ``(bucket, detail)``.
    """
    named, resolved, missing = artifacts.resolve(reason)
    if named and missing and not resolved:
        return UNRESOLVED, {"missing": missing}
    if named and resolved:
        return RESOLVED, {"resolved": resolved, "missing": missing}
    for label, rex in _TIER_CLAIMS:
        if rex.search(reason):
            return UNVERIFIABLE, {"tier": label}
    return NO_CLAIM, {}


def analyse(app_dir: Path) -> dict:
    """Classify every exclusion in the app's specs.

    :param app_dir: The app root.
    :return: A report dict.
    """
    artifacts = _Artifacts(app_dir)
    patterns = {tag: re.compile(exclude_pattern(tag)) for tag in _TAGS}

    buckets: dict[str, list[dict]] = {
        RESOLVED: [], UNRESOLVED: [], UNVERIFIABLE: [], NO_CLAIM: [],
        CROSS_REPO: [],
    }
    for spec in _spec_files(app_dir):
        rel = spec.relative_to(app_dir).as_posix()
        try:
            lines = spec.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for n, line in enumerate(lines, 1):
            for tag, rex in patterns.items():
                m = rex.search(line)
                if not m:
                    continue
                reason = (m.group("reason") or "").strip()
                if not is_reason_bearing(reason or None):
                    # A bare marker is gate-16/19's finding, not this gate's.
                    continue
                bucket, detail = classify(reason, artifacts)
                # An unresolvable token in a reason that names another
                # repository is out of this checkout's reach, not wrong.
                if bucket == UNRESOLVED and _CROSS_REPO_RE.search(reason):
                    bucket = CROSS_REPO
                buckets[bucket].append({
                    "file": rel, "line": n, "tag": tag,
                    "reason": reason[:200], **detail,
                })

    total = sum(len(v) for v in buckets.values())
    return {
        "app": app_dir.name,
        "totals": {
            "exclusions": total,
            RESOLVED: len(buckets[RESOLVED]),
            UNRESOLVED: len(buckets[UNRESOLVED]),
            CROSS_REPO: len(buckets[CROSS_REPO]),
            UNVERIFIABLE: len(buckets[UNVERIFIABLE]),
            NO_CLAIM: len(buckets[NO_CLAIM]),
        },
        "resolved_pct": round(100 * len(buckets[RESOLVED]) / total, 1) if total else None,
        "unresolved": buckets[UNRESOLVED],
        "cross_repo": buckets[CROSS_REPO],
        "unverifiable": buckets[UNVERIFIABLE][:200],
        "no_claim": buckets[NO_CLAIM][:200],
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app_dir", nargs="?", default=".")
    parser.add_argument("--mode", choices=("gate", "report"), default="gate")
    args = parser.parse_args(argv[1:])

    app_dir = Path(args.app_dir).resolve()
    if not app_dir.is_dir():
        print(
            f"[gate-{GATE_NUM}] {GATE_NAME}: ERROR — {app_dir} is not a "
            f"readable directory, so nothing was inspected."
        )
        return EXIT_ERROR

    try:
        result = analyse(app_dir)
    except Exception as exc:  # noqa: BLE001 — a crash must not read as PASS
        print(f"[gate-{GATE_NUM}] {GATE_NAME}: ERROR — {type(exc).__name__}: {exc}")
        return EXIT_ERROR

    if args.mode == "report":
        print(json.dumps(result, indent=2))
        return EXIT_PASS

    t = result["totals"]
    if t["exclusions"] == 0:
        print(
            f"[gate-{GATE_NUM}] {GATE_NAME}: NOT APPLICABLE — no reason-bearing "
            f"@e2e/@spec/@contract/@visual exclusion in openspec/specs, so "
            f"there is no evidence claim to check."
        )
        return EXIT_NOT_APPLICABLE

    # The worklist is printed on every run, pass or fail. A gate that only
    # speaks when it fails leaves the migration invisible.
    print(
        f"[gate-{GATE_NUM}] {GATE_NAME}: {t['exclusions']} exclusion(s) — "
        f"{t[RESOLVED]} name a test that is here, {t[CROSS_REPO]} name one in "
        f"another repository, {t[UNVERIFIABLE]} claim a tier without naming a "
        f"member of it, {t[NO_CLAIM]} name no evidence at all."
    )

    if not result["unresolved"]:
        print(
            f"[gate-{GATE_NUM}] {GATE_NAME}: PASS — every exclusion that names "
            f"an artifact names one that exists."
        )
        return EXIT_PASS

    print(
        f"[gate-{GATE_NUM}] {GATE_NAME}: FAIL — {t[UNRESOLVED]} exclusion(s) "
        f"cite a test nothing in this repo answers to. They read as verified "
        f"and are not."
    )
    for f in result["unresolved"][:40]:
        print(f"  {f['file']}:{f['line']}  @{f['tag']} exclude -> "
              f"{', '.join(f['missing'])} not found")
        print(f"      {f['reason'][:120]}")
    if len(result["unresolved"]) > 40:
        print(f"  ... and {len(result['unresolved']) - 40} more")
    print(
        "  NOTE: this gate reads a bare `SomethingTest` token ANYWHERE in the "
        "reason as a claim, so a sentence REPORTING that a class is gone "
        "re-triggers this finding. Describe the deleted class rather than "
        "naming it — \"the app-local health controller and its PHPUnit class\" "
        "passes where \"...together with HealthControllerTest\" does not. "
        "Narrowing this to a claim-versus-mention rule (gate-19's "
        "`is_directive`) needs a positive list of claiming verbs, and the "
        "blacklist alternative would silently drop real findings, so it is not "
        "guessed at here.\n"
        "  Fix: correct the citation, or restore the test it names. A renamed "
        "test lands here the day it moves, which is the point."
    )
    return EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main(sys.argv))
