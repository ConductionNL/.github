#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Gate-33 axe-core: judge a ``tests/axe/report.json``.

The ONE helper both consumers of the report call, so the verdict cannot drift
between them:

* ``run-hydra-gates.sh`` gate-33, when the report sits in the tree it is run
  against (a local run, or a caller that produced the file some other way);
* the ``Hydra Gates (axe)`` job of the shared quality workflow, which is where
  the report lands in CI since the gates/axe split of 2026-09-12. That job
  waits on Playwright so the sixty-odd static gates no longer have to.

Usage::

    check_axe_report.py <report.json> <findings.log>

Exit status is a STATUS, never a count (the same rule as gate-19, .github#209):

    0   the report is an axe result object and carries no serious/critical
        violation. The count of violations present is printed, so a PASS is a
        pass over that number rather than over silence.
    1   at least one serious/critical violation; one line per violation is
        written to <findings.log> (rule, impact, node count, help URL, up to
        three targets).
    2   the file is not a readable axe result object: unreadable, not JSON,
        not an object, or without a ``violations`` list. The reason is written
        as the single line of <findings.log>.

``{}`` IS NOT "NO VIOLATIONS" (.github#148). A report that is PRESENT but
carries no ``violations`` key at all used to be read as a clean result, so a
crashed capture step, a truncated artifact or a placeholder file turned the
loud skip into a silent PASS, which is strictly worse than never having run.
Every real axe result object HAS the key (axe-core always emits ``violations``,
even when empty); its absence means the producer never got that far.
"""
from __future__ import annotations

import json
import sys


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        sys.stderr.write("usage: check_axe_report.py <report.json> <findings.log>\n")
        return 2
    path, log = argv[1], argv[2]
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:  # noqa: BLE001 — every failure to read is the same verdict
        with open(log, "w", encoding="utf-8") as out:
            out.write(f"axe-report-unreadable: {exc}\n")
        return 2
    if not isinstance(data, dict) or "violations" not in data:
        with open(log, "w", encoding="utf-8") as out:
            out.write(
                "axe-report-shapeless: %s parses as JSON but has no `violations` key, "
                "so it is not an axe result object. axe-core always emits that key, "
                "empty or not — its absence means the run that was supposed to "
                "produce this file never reached the assertion.\n" % path
            )
        return 2
    violations = data.get("violations") or []
    if not isinstance(violations, list):
        with open(log, "w", encoding="utf-8") as out:
            out.write("axe-report-shapeless: `violations` is not a list\n")
        return 2
    blocking = [
        v for v in violations
        if isinstance(v, dict) and v.get("impact") in ("serious", "critical")
    ]
    with open(log, "w", encoding="utf-8") as out:
        for v in blocking:
            rule = v.get("id", "?")
            impact = v.get("impact", "?")
            help_url = v.get("helpUrl", "")
            targets = []
            for node in v.get("nodes", [])[:3]:
                target = node.get("target", [])
                targets.append(" > ".join(target) if isinstance(target, list) else str(target))
            out.write(
                f"axe-rule={rule} impact={impact} nodes={len(v.get('nodes', []))} "
                f"help={help_url} targets={targets}\n"
            )
    print(
        "[hydra-gates] gate-33 axe-core: report read — %d violation(s) present, "
        "%d serious/critical. A PASS here is a PASS over that number, not over "
        "silence." % (len(violations), len(blocking))
    )
    return 0 if not blocking else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
