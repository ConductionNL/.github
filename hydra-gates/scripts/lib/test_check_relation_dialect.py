#!/usr/bin/env python3
"""test_check_relation_dialect.py — suite for check_relation_dialect.py (gate-54).

Picked up automatically by tests/run-helper-suites.sh (it globs
scripts/lib/test_*), so it runs in CI the moment it lands.

The suite is written so that EVERY assertion has a paired arm that must go the
other way. A checker test that only ever feeds it clean input passes just as
well against a checker that returns nothing at all, which is the failure mode
this file exists to rule out.

Focus: check (c), misplaced `x-relation-filter`. Before ConductionNL/.github#231
`property_ids` was built from `schema["properties"]` in one non-recursive pass,
so a correctly-shaped relation inside an array-of-objects
(`items.properties.<name>`) was reported as "placed off a property" — a finding
that could not be cleared without damaging correct schema.
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.join(HERE, "check_relation_dialect.py")

FAILURES = []
PASSES = 0


def run_checker(register_doc):
    """Run the checker over a one-file register set; return its finding lines."""
    with tempfile.TemporaryDirectory() as tmp:
        settings = os.path.join(tmp, "lib", "Settings")
        os.makedirs(settings)
        reg = os.path.join(settings, "app_register.json")
        with open(reg, "w", encoding="utf-8") as fh:
            json.dump(register_doc, fh, indent=2)
        log = os.path.join(tmp, "findings.log")
        subprocess.run(
            [sys.executable, CHECKER, log, reg],
            capture_output=True,
            text=True,
            check=False,
        )
        if not os.path.exists(log):
            return []
        with open(log, encoding="utf-8") as fh:
            return [ln for ln in fh.read().splitlines() if ln.strip()]


def check(label, condition, detail=""):
    global PASSES
    if condition:
        PASSES += 1
    else:
        FAILURES.append(f"{label}{(' — ' + detail) if detail else ''}")


def misplaced(lines):
    return [ln for ln in lines if "placed off a property" in ln]


RELATION = {
    "type": "string",
    "format": "uuid",
    "$ref": "skill",
    "x-relation-filter": {"setting": "@object.setting"},
    "title": "Skill",
}


def register(character_props):
    return {
        "components": {
            "registers": {"app": {"slug": "app", "schemas": ["character", "skill"]}},
            "schemas": {
                "skill": {"slug": "skill", "title": "Skill", "type": "object", "properties": {}},
                "character": {
                    "slug": "character",
                    "title": "Character",
                    "type": "object",
                    "properties": character_props,
                },
            },
        }
    }


# --------------------------------------------------------------------------
# 1. Top-level relation — the shape that always worked. Positive control for
#    the whole suite: if this reports "misplaced", the harness is wrong, not
#    the checker.
# --------------------------------------------------------------------------
lines = run_checker(register({"skill": dict(RELATION)}))
check(
    "top-level relation with x-relation-filter is accepted",
    misplaced(lines) == [],
    f"got {misplaced(lines)}",
)

# --------------------------------------------------------------------------
# 2. THE REGRESSION (.github#231). Same relation, nested in an array of
#    objects. Must be accepted for exactly the same reason as case 1.
# --------------------------------------------------------------------------
nested = {
    "skillOverrides": {
        "type": "array",
        "title": "Skill overrides",
        "items": {
            "type": "object",
            "properties": {
                "skill": dict(RELATION),
                "reason": {"type": "string", "title": "Reason"},
            },
        },
    }
}
lines = run_checker(register(nested))
check(
    "relation inside items.properties is accepted (gate-54 nested FP)",
    misplaced(lines) == [],
    f"got {misplaced(lines)}",
)

# --------------------------------------------------------------------------
# 3. CAN-FAIL for case 2. The check must still catch a genuinely misplaced
#    filter. Here the filter rides on the ARRAY WRAPPER's `items` dict, which
#    is not a property — the real rule-6 violation.
# --------------------------------------------------------------------------
genuinely_misplaced = {
    "skillOverrides": {
        "type": "array",
        "title": "Skill overrides",
        "items": {
            "type": "object",
            "x-relation-filter": {"setting": "@object.setting"},
            "properties": {"reason": {"type": "string", "title": "Reason"}},
        },
    }
}
lines = run_checker(register(genuinely_misplaced))
check(
    "x-relation-filter on a non-property node is still reported",
    len(misplaced(lines)) == 1,
    f"expected exactly 1 misplaced finding, got {misplaced(lines)}",
)

# --------------------------------------------------------------------------
# 4. CAN-FAIL, second form. A filter parked in an arbitrary x-* block is not
#    on a property and must still be caught.
# --------------------------------------------------------------------------
doc = register({"skill": dict(RELATION)})
doc["components"]["schemas"]["character"]["x-openregister-extras"] = {
    "x-relation-filter": {"setting": "@object.setting"}
}
lines = run_checker(doc)
check(
    "x-relation-filter inside a schema-level x-* block is still reported",
    len(misplaced(lines)) == 1,
    f"expected exactly 1 misplaced finding, got {misplaced(lines)}",
)

# --------------------------------------------------------------------------
# 5. Deeply nested (array of objects containing an array of objects). The
#    collector recurses, so this is accepted too.
# --------------------------------------------------------------------------
deep = {
    "groups": {
        "type": "array",
        "title": "Groups",
        "items": {
            "type": "object",
            "properties": {
                "entries": {
                    "type": "array",
                    "title": "Entries",
                    "items": {"type": "object", "properties": {"skill": dict(RELATION)}},
                }
            },
        },
    }
}
lines = run_checker(register(deep))
check(
    "relation nested two array levels deep is accepted",
    misplaced(lines) == [],
    f"got {misplaced(lines)}",
)

# --------------------------------------------------------------------------
# 6. The recursion is bounded. A register file is JSON, so it can never hold a
#    true cycle — the realistic hazard is pathological DEPTH. Nest well past
#    the collector's limit and require the run to terminate and stay sane:
#    the deep relation sits below the bound so it is NOT registered, and the
#    filter riding on it is reported rather than silently swallowed. That is
#    the safe direction for a bounded walk (over-report, never under-report).
# --------------------------------------------------------------------------
deep_prop = dict(RELATION)
for _ in range(14):
    deep_prop = {
        "type": "array",
        "items": {"type": "object", "properties": {"inner": deep_prop}},
    }
lines = run_checker(register({"veryDeep": dict(deep_prop, title="Very deep")}))
check(
    "a pathologically deep schema terminates and over-reports rather than hanging",
    len(misplaced(lines)) >= 1,
    f"expected the beyond-bound relation to be reported, got {misplaced(lines)}",
)

# --------------------------------------------------------------------------
print(f"test_check_relation_dialect: {PASSES} passed, {len(FAILURES)} failed")
for f in FAILURES:
    print(f"  FAIL {f}")
sys.exit(1 if FAILURES else 0)
