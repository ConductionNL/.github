#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Write gates.json: one record per declared gate of one run-hydra-gates.sh run.

The runner pipes its verdict records to stdin, one per line, tab separated:

    <gate number> TAB <gate name> TAB <verdict> TAB <reason>

where verdict is PASS, FAIL, WARNING, NOT APPLICABLE or SKIPPED. `--declared`
names the runner's inventory file (`<number> <name>` per line), so a declared
gate that emitted no verdict is still listed, as "not-run".

Each record holds gate, name, verdict, findings, findings_from, scope and
category. `findings` is
    0     for a PASS,
    n     for a FAIL or WARNING whose reason states a count (the first number
          in the reason, before any log path), findings_from "verdict",
    n     otherwise the non-empty lines of the gate's findings log
          (hydra-gate-<name>.log in the log directory), findings_from "log",
    null  when neither is available, or the gate did not judge.

Usage:
    write_gates_json.py --out FILE --scope full|diff --declared FILE
                        [--log-dir DIR] [--app NAME] [--base REF] < records
"""
import argparse
import json
import os
import re
import sys

# The quality-matrix category of every declared gate. Tests, coverage and the
# maintainability gates are "other": the matrix shows them as measures of their own.
CATEGORY = {}
for _cat, _gates in {
    "security": (5, 6, 7, 8, 9, 11, 30, 48, 50, 82, 97, 121),
    "accessibility": (12, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45),
    "architecture": (10, 14, 17, 18, 20, 23, 24, 27, 49, 54, 56, 59, 61, 64, 66, 83, 98, 106, 108, 110,
                     111, 115, 116, 119, 120),
    "specs": (16, 46, 95, 113),
    "licensing": (1, 28, 94),
    "dependencies": (4, 84, 93),
    "ui": (13, 15, 22, 51, 52, 53, 55, 60, 62, 63, 68, 69, 70, 96, 100, 102, 103, 104, 105, 107, 114),
    "other": (2, 3, 19, 21, 25, 26, 29, 47, 57, 58, 65, 67, 101, 109, 112, 122, 123),
}.items():
    for _g in _gates:
        CATEGORY[_g] = _cat

VERDICTS = {"PASS": "pass", "FAIL": "fail", "WARNING": "warning", "NOT APPLICABLE": "not-applicable",
            "SKIPPED": "skipped"}
COUNT = re.compile(r"(?<![\w./-])(\d[\d,]*)(?![\w./-])")


def count_from_reason(reason):
    """The first stand-alone number in the reason, ignoring the log path part."""
    head = re.split(r"\bsee /|\bSee /", reason, maxsplit=1)[0]
    m = COUNT.search(head)
    return int(m.group(1).replace(",", "")) if m else None


def count_from_log(log_dir, name):
    if not log_dir:
        return None
    path = os.path.join(log_dir, f"hydra-gate-{name}.log")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8", errors="replace") as fh:
        return sum(1 for line in fh if line.strip())


def record(gate, name, verdict, reason, scope, log_dir):
    findings, source = None, None
    if verdict == "pass":
        findings, source = 0, "verdict"
    elif verdict in ("fail", "warning"):
        findings = count_from_reason(reason)
        source = "verdict" if findings is not None else None
        if findings is None:
            findings = count_from_log(log_dir, name)
            source = "log" if findings is not None else None
    return {"gate": gate, "name": name, "verdict": verdict, "findings": findings, "findings_from": source,
            "scope": scope, "category": CATEGORY.get(gate, "other"), "reason": reason}


def parse_records(lines):
    """{gate: (name, verdict, reason)}; a gate that reported twice keeps its last verdict."""
    out = {}
    for line in lines:
        parts = line.rstrip("\n").split("\t", 3)
        if len(parts) < 3 or not parts[0].isdigit():
            continue
        raw = parts[2].split(" (")[0].strip()
        out[int(parts[0])] = (parts[1], VERDICTS.get(raw, raw.lower()), parts[3] if len(parts) > 3 else "")
    return out


def parse_declared(path):
    out = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            parts = line.split()
            if len(parts) >= 2 and parts[0].isdigit():
                out[int(parts[0])] = parts[1]
    return out


def build(records, declared, scope, log_dir, app=None, base=None):
    gates = []
    for gate in sorted(set(records) | set(declared)):
        if gate in records:
            name, verdict, reason = records[gate]
            gates.append(record(gate, name, verdict, reason, scope, log_dir))
        else:
            gates.append(record(gate, declared[gate], "not-run", "", scope, log_dir))
    tally = {}
    for g in gates:
        tally[g["verdict"]] = tally.get(g["verdict"], 0) + 1
    return {"schema": 1, "app": app, "scope": scope, "base": base, "declared": len(declared),
            "verdicts": tally, "gates": gates}


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--scope", required=True, choices=("full", "diff"))
    ap.add_argument("--declared", required=True)
    ap.add_argument("--log-dir")
    ap.add_argument("--app")
    ap.add_argument("--base")
    args = ap.parse_args(argv)
    doc = build(parse_records(sys.stdin), parse_declared(args.declared), args.scope, args.log_dir,
                args.app, args.base or None)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")
    print(f"[hydra-gates] gates.json: {len(doc['gates'])} gate(s) written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
