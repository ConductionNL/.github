#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Decide `Package invariants` from the verdicts of every helper-suite shard.

A sharded run must not read green when a suite ran on no shard, ran twice,
failed, or when a shard never reported. So this checks, against a fresh
discovery of scripts/lib/test_*:

  * every shard 0..N-1 left its report (helper-suites-shard-<i>.tsv);
  * every discovered suite has exactly one verdict, across all shards;
  * every verdict is PASS or QUARANTINED, and no report names an unknown suite;
  * the shard matrix itself succeeded.

Usage: check-helper-shard-reports.py <lib-dir> <reports-dir> <shards> <matrix-result>
Exit:  0 all hold, 1 otherwise (each problem printed).
"""

from __future__ import annotations

import os
import sys


def discover(lib: str) -> set[str]:
    return {n for n in os.listdir(lib) if n.startswith("test_") and os.path.isfile(os.path.join(lib, n))}


def problems(lib: str, reports: str, shards: int, matrix_result: str) -> list[str]:
    found = []
    if matrix_result != "success":
        found.append(f"the shard matrix ended '{matrix_result}', not 'success'")
    seen: dict[str, list[str]] = {}
    for i in range(shards):
        path = os.path.join(reports, f"helper-suites-shard-{i}.tsv")
        if not os.path.isfile(path):
            found.append(f"shard {i} left no report ({path})")
            continue
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                parts = line.rstrip("\n").split("\t")
                if len(parts) != 2:
                    continue
                verdict, name = parts
                seen.setdefault(name, []).append(f"{verdict} on shard {i}")
                if verdict not in ("PASS", "QUARANTINED"):
                    found.append(f"{name}: {verdict} on shard {i}")
    suites = discover(lib)
    if not suites:
        found.append(f"discovered zero suites under {lib}")
    for name in sorted(suites - seen.keys()):
        found.append(f"{name} ran on no shard")
    for name in sorted(seen.keys() - suites):
        found.append(f"{name} was reported but is not a discovered suite")
    for name, verdicts in sorted(seen.items()):
        if len(verdicts) > 1:
            found.append(f"{name} ran {len(verdicts)} times: {', '.join(verdicts)}")
    return found


def main(argv: list[str]) -> int:
    if len(argv) != 5 or not argv[3].isdigit():
        print(__doc__, file=sys.stderr)
        return 1
    found = problems(argv[1], argv[2], int(argv[3]), argv[4])
    for line in found:
        print(f"::error::{line}")
    if found:
        return 1
    print(f"OK: {len(discover(argv[1]))} suites, each with one passing verdict, over {argv[3]} shards.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
