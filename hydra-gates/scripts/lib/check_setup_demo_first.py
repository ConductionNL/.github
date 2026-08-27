#!/usr/bin/env python3
"""`setup.steps[0]` must be the demo-data offer (ADR-111 rule 4).

WHAT THIS IS FOR

An app installed from the App Store opens on an empty list. The only question
its first reader actually has is "can I see this working?" — and the answer
requires demo data they have no way to author, against a schema they do not know
yet.

ADR-042 already built every piece of the mechanism: `CnSetupWizard` renders
`manifest.setup.steps[]`, the manifest schema types the six step kinds, and
`POST /api/setup/action/{action}` runs a step's privileged server-side work.
Measured 2026-08-27: ten fleet apps declare `setup.steps`, and every one of them
opens with `welcome`. Not one offers the data that would let the reader see the
app do anything.

A welcome screen tells you what an app is. The demo-data offer lets you SEE it.
There is no reason the first step cannot also say hello.

🔴 WHY THIS CHECKS THE MANIFEST AND NOT THE VUE SOURCE

The first draft of ADR-111 measured adoption by scanning `src/**/*Wizard*.vue`
and concluded one app had a walkthrough. Ten do. The walkthrough is not a file
an app writes — it is a DECLARATION an app makes, and the shared component
renders it. Counting the artefact instead of the declaration undercounted by
10×, and would have justified rebuilding a component that already exists.

Asserting on the declaration is both correct and far stronger than any heuristic
over rendered markup could be.

WHAT IT DELIBERATELY DOES NOT ENFORCE

Presence. An app with no `setup` block at all is NOT reported. Twenty of thirty
manifests have none, and failing them would block every unrelated manifest edit
in the fleet on the day this ships — which is how a gate gets switched off, and
what gate-98 did a day before this was written.

Adoption is a rollout, tracked as work. This gate holds the line on the apps
that HAVE declared setup, so the ten that exist cannot drift and new ones cannot
land wrong. Presence becomes enforceable in a follow-up once the rollout lands,
and that ordering is deliberate.

EXIT CODES
  0  every manifest in scope leads with the demo-data step (or declares no setup)
  1  at least one declares setup and does not lead with it
  4  nothing in scope
"""

from __future__ import annotations

import json
import os
import sys

DEMO_STEP_ID = "demo-data"


def _judge(path: str, manifest: dict) -> str | None:
    """The finding for one manifest, or None when it is fine."""
    setup = manifest.get("setup")
    if not isinstance(setup, dict):
        # Not adoption's judge — see the module docstring.
        return None

    if setup.get("enabled") is False:
        return None

    steps = setup.get("steps")
    if not isinstance(steps, list) or not steps:
        return (
            f"{path}: `setup` is declared with no steps, so the wizard renders "
            f"nothing. Give it a first step with id \"{DEMO_STEP_ID}\" (ADR-111 rule 4)."
        )

    first = steps[0] if isinstance(steps[0], dict) else {}
    got = str(first.get("id", "") or "")
    if got == DEMO_STEP_ID:
        return None

    return (
        f"{path}: setup.steps[0].id is \"{got or '<missing>'}\", not "
        f"\"{DEMO_STEP_ID}\" (ADR-111 rule 4). The first question a new "
        f"administrator has is whether they can see the app work; a welcome "
        f"screen answers a question nobody asked. Move the demo-data offer "
        f"first — it can still say hello."
    )


def main(argv: list[str]) -> int:
    root = argv[1] if len(argv) > 1 else "."
    changed = [line.strip() for line in sys.stdin.read().splitlines() if line.strip()]

    in_scope = [p for p in changed if os.path.basename(p) == "manifest.json"]
    if not in_scope:
        # A COUNT, PRINTED EVEN WHEN ZERO: the caller tells "ran and found
        # nothing" from "never ran" by this line alone.
        print("checked 0 manifest(s)")
        return 4

    checked = failures = 0
    for rel in sorted(set(in_scope)):
        absolute = os.path.join(root, rel)
        if not os.path.isfile(absolute):
            # Deleted in this diff.
            continue

        try:
            with open(absolute, encoding="utf-8") as handle:
                manifest = json.load(handle)
        except (OSError, ValueError) as exc:
            # An unreadable manifest is a finding, not a silent skip — a gate
            # that shrugs at a broken input reports a clean bill of health over
            # a file nothing could parse.
            failures += 1
            checked += 1
            print(f"FAIL {rel}: manifest is unreadable — {exc}")
            continue

        if not isinstance(manifest, dict):
            failures += 1
            checked += 1
            print(f"FAIL {rel}: manifest is not a JSON object")
            continue

        checked += 1
        finding = _judge(rel, manifest)
        if finding is not None:
            failures += 1
            print(f"FAIL {finding}")

    print(f"checked {checked} manifest(s)")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
