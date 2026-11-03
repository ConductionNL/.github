#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Split the helper suites over N shards, balanced by their measured run time.

Reads suite names on stdin, one per line, and prints `<shard>\t<name>` for
every one of them, so each suite lands on exactly one shard. The split is
longest-first: suites are taken in descending weight (name breaks ties) and
each goes to the shard with the least weight so far (lowest index breaks
ties). The output depends only on the names, the weights and N.

Weights come from helper-suite-timings.tsv (`<name>\t<seconds>`, measured in
CI). A suite missing from the table still runs: it gets DEFAULT_WEIGHT, so a
stale table can only make the shards less even, never drop a suite.

Usage: partition_helper_suites.py <timings.tsv> <shards>  < names
"""

from __future__ import annotations

import sys

DEFAULT_WEIGHT = 20


def read_weights(path: str) -> dict[str, int]:
    weights: dict[str, int] = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                parts = line.rstrip("\n").split("\t")
                if len(parts) == 2 and parts[1].isdigit():
                    weights[parts[0]] = int(parts[1])
    except OSError:
        pass
    return weights


def partition(names: list[str], weights: dict[str, int], shards: int) -> list[tuple[int, str]]:
    load = [0] * shards
    out = []
    order = sorted(set(names), key=lambda n: (-weights.get(n, DEFAULT_WEIGHT), n))
    for name in order:
        shard = min(range(shards), key=lambda i: (load[i], i))
        load[shard] += weights.get(name, DEFAULT_WEIGHT)
        out.append((shard, name))
    return sorted(out, key=lambda row: row[1])


def main(argv: list[str]) -> int:
    if len(argv) != 3 or not argv[2].isdigit() or int(argv[2]) < 1:
        print("usage: partition_helper_suites.py <timings.tsv> <shards>", file=sys.stderr)
        return 2
    names = [line.strip() for line in sys.stdin if line.strip()]
    for shard, name in partition(names, read_weights(argv[1]), int(argv[2])):
        print(f"{shard}\t{name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
