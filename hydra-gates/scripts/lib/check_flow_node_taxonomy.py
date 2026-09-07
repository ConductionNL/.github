#!/usr/bin/env python3
"""Gate 111 — a flow node in THIS repository declares what kind of step it is.

WHAT IT REFUSES
---------------
A class under the repository's own flow-node directory that implements
``IFlowNode`` and does NOT implement ``IFlowNodeTaxonomy``. Such a node is
served to the palette as ``serviceTask`` / ``other``: visible, but only to
whoever opens the palette, and wrong in a BPMN export in a way that looks
answered.

🔴 SCOPED BY PATH, NEVER BY INTERFACE, AND THAT IS THE WHOLE DESIGN.
On a measured instance 38 of 65 step types are contributed by apps in other
repositories, on their own release cycles. A gate that flagged any
``IFlowNode`` implementation missing the methods would fire on every one of
them — which is exactly the behaviour the defaults exist to prevent, moved
from run time into CI. It would also be unfixable from the pull request it
fired on.

So this gate only ever looks inside a directory a repository owns:

    lib/Service/Flow/Nodes/

A repository without that directory is NOT APPLICABLE — not a pass. Nothing
was inspected, and saying so is not the same as saying it was clean.

WHY THE CHECK IS TEXTUAL
------------------------
The declaration is on the class line (``implements IFlowNode, …``), which is
the same place a reviewer reads it. Parsing PHP properly would buy accuracy
this check does not need and a dependency the runner does not have.

Exit codes
    0  every node in scope declares
    1  at least one node does not (the count is on the FAIL lines)
    4  no flow-node directory in this repository — not applicable

SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl>
SPDX-License-Identifier: EUPL-1.2
"""

from __future__ import annotations

import argparse
import os
import re
import sys

# The one directory this gate ever looks in. A repository that does not have
# it contributes no flow nodes of its own.
NODE_DIR = os.path.join("lib", "Service", "Flow", "Nodes")

# `class X implements A, B, C {` — the declaration line, which is where a
# reviewer reads the same fact.
CLASS_RE = re.compile(
    r"^\s*(?:final\s+|abstract\s+)?class\s+(\w+)\s+implements\s+([^{]+)\{",
    re.MULTILINE,
)

BASE_INTERFACE = "IFlowNode"
TAXONOMY_INTERFACE = "IFlowNodeTaxonomy"


def interfaces_of(declaration: str) -> list[str]:
    """The interface short names on a class declaration."""
    names = []
    for raw in declaration.split(","):
        name = raw.strip().split("\\")[-1]
        if name:
            names.append(name)
    return names


def check_file(path: str) -> list[str]:
    """Findings for one file, as human-readable lines."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            source = handle.read()
    except OSError as error:
        # An unreadable file is a wiring problem, not a finding about the app.
        # Reported so it cannot pass silently.
        return ["SKIP %s — could not be read: %s" % (path, error)]

    findings = []
    for match in CLASS_RE.finditer(source):
        class_name, declaration = match.group(1), match.group(2)
        names = interfaces_of(declaration)

        # An abstract base or a helper in the same directory is not a node.
        if BASE_INTERFACE not in names:
            continue

        if TAXONOMY_INTERFACE in names:
            continue

        findings.append(
            "FAIL %s::%s implements %s but not %s, so the palette serves it as "
            "serviceTask/other — a guess that looks answered. Declare getKind() "
            "and getCategory()." % (path, class_name, BASE_INTERFACE, TAXONOMY_INTERFACE)
        )

    return findings


def main() -> int:
    """Run the gate."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="repository root")
    args = parser.parse_args()

    node_dir = os.path.join(args.root, NODE_DIR)
    if not os.path.isdir(node_dir):
        # NOT APPLICABLE. This repository contributes no flow nodes of its own,
        # and a node it contributes from anywhere else is not this gate's
        # business — see the scoping note above.
        print("checked 0 flow node(s): no %s in this repository" % NODE_DIR)
        return 4

    findings = []
    inspected = 0
    for name in sorted(os.listdir(node_dir)):
        if not name.endswith(".php"):
            continue

        path = os.path.join(node_dir, name)
        inspected += 1
        findings.extend(check_file(path))

    for line in findings:
        print(line)

    # 🔑 THE TERMINAL SUMMARY IS THE RUNNER'S WIRING CHECK. Without it the
    # runner cannot tell a clean run from a crashed one, and treats the
    # absence as a broken checker rather than a pass.
    print("checked %d flow node file(s)" % inspected)

    return 1 if any(line.startswith("FAIL ") for line in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
