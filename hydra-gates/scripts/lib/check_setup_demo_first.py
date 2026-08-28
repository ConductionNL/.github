#!/usr/bin/env python3
"""`setup.steps` must open `welcome`, then the demo-data offer (ADR-111 rule 4).

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
Both belong at the front, in that order: step 1 says hello, step 2 offers the
data that makes the app show something.

CORRECTED 2026-08-28. The first version of this gate demanded demo-data at
step 0 and treated `welcome` as a question nobody asked. That was wrong twice
over. The wizard is the CONFIGURATION wizard, where an orientation step earns
its place, and the demo-data offer is the second thing an administrator wants,
not the first. Measured under the corrected rule, ALL SEVEN fleet apps that
declare `setup.steps` fail it — including the two the old rule called compliant,
which lead with demo-data and put `welcome` second. A rule that inverts who
passes is a rule worth stating carefully.

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
WELCOME_STEP_ID = "welcome"

# Two findings, two severities. An app that HAS both steps in the wrong order has
# a defect it can fix by editing its manifest, and that blocks. An app with no
# demo-data step at all cannot fix this in a manifest: the step calls
# `install-demo-data`, and declaring it without that action ships a wizard step
# that ERRORS on a fresh install — worse than the finding. That warns, so the
# fleet is not held red for a feature each app still has to build.
SEVERITY_FAIL = "FAIL"
SEVERITY_WARN = "WARN"


def _judge(path: str, manifest: dict) -> tuple[str, str] | None:
    """The (severity, finding) for one manifest, or None when it is fine."""
    setup = manifest.get("setup")
    if not isinstance(setup, dict):
        # Not adoption's judge — see the module docstring.
        return None

    if setup.get("enabled") is False:
        return None

    steps = setup.get("steps")
    if not isinstance(steps, list) or not steps:
        return (
            SEVERITY_FAIL,
            f"{path}: `setup` is declared with no steps, so the wizard renders "
            f"nothing. Give it \"{WELCOME_STEP_ID}\" then \"{DEMO_STEP_ID}\" "
            f"(ADR-111 rule 4).",
        )

    ids = [str(s.get("id", "") or "") if isinstance(s, dict) else "" for s in steps]
    has_demo = DEMO_STEP_ID in ids

    if ids[0] != WELCOME_STEP_ID:
        return (
            SEVERITY_FAIL,
            f"{path}: setup.steps[0].id is \"{ids[0] or '<missing>'}\", not "
            f"\"{WELCOME_STEP_ID}\" (ADR-111 rule 4). The configuration wizard "
            f"opens by saying what this app is; the demo-data offer is step 2.",
        )

    if not has_demo:
        return (
            SEVERITY_WARN,
            f"{path}: setup declares no \"{DEMO_STEP_ID}\" step (ADR-111 rule 4). "
            f"An app installed from the App Store opens on an empty list, and the "
            f"reader has no way to author data against a schema they do not know "
            f"yet. This WARNS rather than fails because the step runs "
            f"`install-demo-data`: declaring it without that action ships a "
            f"wizard step that errors. Build the demo data, then add the step.",
        )

    if ids[1] != DEMO_STEP_ID:
        return (
            SEVERITY_FAIL,
            f"{path}: setup.steps[1].id is \"{ids[1] or '<missing>'}\", not "
            f"\"{DEMO_STEP_ID}\" (ADR-111 rule 4). The app HAS a demo-data step, "
            f"at index {ids.index(DEMO_STEP_ID)} — move it to step 2, directly "
            f"after welcome. Nothing between them answers a question the reader "
            f"has yet.",
        )

    return None


def main(argv: list[str]) -> int:
    root = argv[1] if len(argv) > 1 else "."
    changed = [line.strip() for line in sys.stdin.read().splitlines() if line.strip()]

    in_scope = [p for p in changed if os.path.basename(p) == "manifest.json"]
    if not in_scope:
        # A COUNT, PRINTED EVEN WHEN ZERO: the caller tells "ran and found
        # nothing" from "never ran" by this line alone.
        print("checked 0 manifest(s)")
        return 4

    checked = failures = warnings = 0
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
        verdict = _judge(rel, manifest)
        if verdict is not None:
            severity, finding = verdict
            print(f"{severity} {finding}")
            if severity == SEVERITY_FAIL:
                failures += 1
            else:
                warnings += 1

    # BOTH counts, printed even when zero: a reader distinguishes "ran and found
    # nothing" from "never ran", and a warning that is never counted is a
    # finding nobody schedules.
    print(f"checked {checked} manifest(s), {warnings} warning(s)")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
