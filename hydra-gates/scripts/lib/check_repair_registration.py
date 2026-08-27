#!/usr/bin/env python3
"""Every repair step must be NAMED in appinfo/info.xml, not merely written.

WHAT THIS CATCHES

`OCA\\OpenRegister\\Repair\\ImportFlowRegister` was complete — constructor,
version gate, error handling, and a docblock explaining that it exists so a flow
can live in OpenRegister itself. It appeared **zero times** in
`appinfo/info.xml`: not in `<post-migration>`, not in `<install>`. Nextcloud
therefore never invoked it, and the `flows` register never existed on any
instance. Two e2e suites died in `beforeAll` on `registers slug=flows`, which
reads like a broken test, and an `occ upgrade` reported complete success over an
instance missing 8 of 15 declared registers.

ADR-005 Rule 1 already says a register descriptor MUST be accompanied by a
`lib/Repair/` step, and warns in its own Consequences that a descriptor without
one "silently never appears — a recurring author error this ADR exists to
prevent". 🔴 THE CLASS COMPLIED. THE REGISTRATION DID NOT, and the rule does not
mention registration at all — so a reviewer asking "is there a Repair step for
this?" gets a yes and moves on.

Grepping for the class finds the class. Only the declaration file decides
whether it runs.

WHY THIS IS DIFF-SCOPED

The claim worth making is "the step you just added is wired", which is a claim
about the diff. A full-tree version would additionally redden every branch cut
before it shipped, for steps their authors never touched — the pattern that took
one app's gate-16 to 102 findings in a single rename.

An unregistered step that predates this gate is real debt, but it is debt this
gate cannot ask a passing PR to pay.

USAGE
  <changed files on stdin> check_repair_registration.py <root>

EXIT CODES
  0  every repair step in scope is registered
  1  at least one is not
  4  nothing in scope (no repair steps in the diff, or no info.xml)
"""

from __future__ import annotations

import os
import re
import sys
import xml.etree.ElementTree as ET

# `class Foo ... implements ... IRepairStep` — the interface may sit among
# several, and the class may extend something first.
CLASS_RE = re.compile(
    r"^\s*(?:final\s+|abstract\s+)?class\s+(\w+)\b(?P<rest>[^{]*)\{",
    re.MULTILINE,
)
NAMESPACE_RE = re.compile(r"^\s*namespace\s+([^;]+);", re.MULTILINE)


def declared_steps(info_xml: str) -> set[str]:
    """Every FQCN named in <repair-steps>, from BOTH blocks.

    Read from every block, not just <post-migration>: a step registered only for
    install and not for upgrade is a different defect, but it is not THIS one,
    and reporting it here would be a finding the gate's name does not describe.
    """
    try:
        root = ET.parse(info_xml).getroot()
    except (ET.ParseError, OSError):
        return set()

    return {
        (step.text or "").strip().lstrip("\\")
        for step in root.iterfind(".//repair-steps//step")
        if (step.text or "").strip()
    }


# A step can be deliberately WITHHELD. shillinq's RetireSubsidieSchema is the
# case that forced this: it irreversibly deletes the source rows an earlier step
# folded, so it must lag that fold by at least one release to leave a rollback
# window. Its registration is commented out in info.xml with that reasoning
# written above it — and a commented-out <step> is, correctly, "named nowhere":
# Nextcloud will not run it. The gate was right about the mechanism and wrong
# about the intent, and it had no way to tell those apart.
#
# 🔴 THE HATCH IS NOT A MUTE BUTTON. Three properties keep it from becoming one:
#   - it names ONE class, so it can never become a blanket exemption;
#   - it requires a REASON, and a marker without a real one still FAILS, so the
#     cheapest way out is still to wire the step up;
#   - a held step is PRINTED as HELD, so it stays visible in the run instead of
#     vanishing into a pass. A check that detects something and then says
#     nothing is not a check.
MIN_REASON_CHARS = 30

HELD_RE = re.compile(
    r"hydra-gate-98\s+held:\s*\\?(?P<fqcn>[A-Za-z_][\w\\]*)"
    r"\s*(?:\u2014|--|:)\s*(?P<reason>.*?)(?=-->|\Z)",
    re.DOTALL,
)


def held_steps(info_xml: str) -> dict[str, str]:
    """FQCN -> reason, for steps a marker deliberately withholds.

    Read from the RAW TEXT, not the parsed tree: the marker lives in an XML
    comment, and ElementTree discards comments entirely. Parsing here would find
    nothing and silently report every held step as a failure.
    """
    try:
        with open(info_xml, encoding="utf-8", errors="replace") as handle:
            raw = handle.read()
    except OSError:
        return {}

    return {
        match.group("fqcn").strip().lstrip("\\"): " ".join(match.group("reason").split())
        for match in HELD_RE.finditer(raw)
    }


def repair_classes(path: str) -> list[tuple[str, str]]:
    """(fqcn, class_name) for each IRepairStep implementation in one file."""
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            source = handle.read()
    except OSError:
        return []

    ns_match = NAMESPACE_RE.search(source)
    if ns_match is None:
        return []
    namespace = ns_match.group(1).strip()

    found = []
    for match in CLASS_RE.finditer(source):
        # 🔴 The INTERFACE decides, not the directory. A helper or a value object
        # under lib/Repair/ is not a repair step and must not be demanded of
        # info.xml — a gate that fails on files the framework never looks for
        # teaches people to stop reading it.
        if "IRepairStep" not in match.group("rest"):
            continue
        found.append((f"{namespace}\\{match.group(1)}", match.group(1)))

    return found


def main(argv: list[str]) -> int:
    root = argv[1] if len(argv) > 1 else "."

    # 🔴 STDIN ONLY. An earlier draft carried an `--all` mode so the generic
    # gate-acceptance bundle — which runs against a directory that is not a git
    # repository — could exercise the gate. That was backwards twice over: it
    # gave the gate a full-tree path CI would then take by default, and it meant
    # the fixture exercised a mode CI never uses. A fixture that covers the
    # wrong mode is not coverage.
    #
    # Delta-gate acceptance belongs in a suite with a REAL two-commit history,
    # the way gate-16's does; see test_gate98_repair_registration_scope.sh.
    changed = [line.strip() for line in sys.stdin.read().splitlines() if line.strip()]
    in_scope = [
        p for p in changed
        if p.startswith("lib/Repair/") and p.endswith(".php")
    ]

    info_xml = os.path.join(root, "appinfo", "info.xml")
    if not in_scope or not os.path.isfile(info_xml):
        # 🔴 A COUNT, PRINTED EVEN WHEN ZERO. The caller distinguishes "ran and
        # found nothing" from "never ran" by this line; without it a crash and a
        # clean repo are the same observation.
        print("checked 0 repair step(s)")
        return 4

    declared = declared_steps(info_xml)
    held = held_steps(info_xml)
    checked = 0
    failures = 0

    for rel in sorted(in_scope):
        absolute = os.path.join(root, rel)
        if not os.path.isfile(absolute):
            # Deleted in this diff. A removed step SHOULD leave info.xml, but a
            # leftover <step> naming a class that no longer exists is a separate
            # defect with a separate blast radius.
            continue

        for fqcn, name in repair_classes(absolute):
            checked += 1
            if fqcn in declared:
                continue

            if fqcn in held:
                reason = held[fqcn]
                if len(reason) >= MIN_REASON_CHARS:
                    print(
                        f"HELD {rel}: {name} is deliberately not registered — {reason}"
                    )
                    continue

                failures += 1
                print(
                    f"FAIL {rel}: {name} carries a `hydra-gate-98 held:` marker with no "
                    f"real reason ({len(reason)} chars; at least {MIN_REASON_CHARS} are "
                    f"required). Withholding a step is a decision, and the marker is where "
                    f"it gets recorded — say why it is held and when it should be wired up, "
                    f"or register it."
                )
                continue

            failures += 1
            print(
                f"FAIL {rel}: {name} implements IRepairStep and is named nowhere in "
                f"appinfo/info.xml <repair-steps>, so Nextcloud will never run it. "
                f"Add <step>{fqcn}</step> to <post-migration> and, if it should also "
                f"run on a fresh install, to <install>. If it is withheld ON PURPOSE, "
                f"record that in info.xml as `hydra-gate-98 held: {fqcn} — <why, and "
                f"what would let it be wired up>`."
            )

    print(f"checked {checked} repair step(s)")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
