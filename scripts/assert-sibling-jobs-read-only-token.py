#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Assert that every quality.yml job which runs another repository's code holds
a read-only token, and that no checkout in it leaves a token on disk.

WHY
---
The phpunit, newman, playwright and journeydoc-capture jobs clone the caller's
`additional-apps` / `e2e-additional-apps` (for example integriq and
openregister at `development`) and run their composer scripts, migrations and
app bootstrap. Those jobs declared no `permissions:`, so they inherited the
caller's grant, which on most fleet callers is `contents: write`, and every
actions/checkout in them wrote that token into `.git/config`. A bad commit on a
sibling's development branch could therefore push to the CALLING repository
(keepiq#881).

WHAT THIS ASSERTS
-----------------
For every job whose definition references `inputs.additional-apps`,
`inputs.e2e-additional-apps` or a `git clone`:

  * the job declares its own `permissions:` (inheriting is the defect);
  * no scope in it is `write`, unless the job is listed in WRITE_ALLOWED with
    the reason it writes;
  * every actions/checkout step sets `persist-credentials: false`;
  * no job-level `env:` exposes `github.token` / `secrets.GITHUB_TOKEN` to
    every step (a writing job must hand the token to the one step that
    writes).

It also refuses to pass if it finds fewer than three such jobs: a parser that
stopped recognising the jobs would otherwise report a clean, empty pass.

POSITIVE CONTROL
----------------
``--positive-control`` applies one known-bad mutation at a time to the parsed
workflow (drop a job's permissions, grant newman `contents: write`, drop
`persist-credentials`, put the token in a job-level env) and requires every
mutant to be caught. A check that cannot fail is not a check.

Usage::

    assert-sibling-jobs-read-only-token.py .github/workflows/quality.yml
    assert-sibling-jobs-read-only-token.py --positive-control .github/workflows/quality.yml
"""

from __future__ import annotations

import argparse
import copy
import json
import sys

import yaml

# Jobs that legitimately write, and why. Everything else that runs sibling
# code must be read-only.
WRITE_ALLOWED = {
    "journeydoc-capture": "commits refreshed screenshots back and dispatches the docs deploy",
}

SIBLING_MARKERS = ("inputs.additional-apps", "inputs.e2e-additional-apps", "git clone")
TOKEN_MARKERS = ("github.token", "secrets.GITHUB_TOKEN")
MIN_SIBLING_JOBS = 3


def sibling_jobs(wf: dict) -> list[str]:
    out = []
    for name, job in (wf.get("jobs") or {}).items():
        text = json.dumps(job)
        if any(m in text for m in SIBLING_MARKERS):
            out.append(name)
    return out


def findings(wf: dict) -> list[str]:
    errs: list[str] = []
    jobs = wf.get("jobs") or {}
    names = sibling_jobs(wf)
    if len(names) < MIN_SIBLING_JOBS:
        errs.append(
            f"only {len(names)} job(s) recognised as running sibling apps "
            f"({names}); expected at least {MIN_SIBLING_JOBS}. The detector is broken, not the workflow clean."
        )
    for name in names:
        job = jobs[name]
        perms = job.get("permissions")
        if perms is None:
            errs.append(f"{name}: declares no `permissions:`, so it inherits the caller's (often write) token")
        elif isinstance(perms, str):
            if perms != "read-all" and name not in WRITE_ALLOWED:
                errs.append(f"{name}: `permissions: {perms}` is not read-only")
        else:
            writes = sorted(k for k, v in perms.items() if str(v) == "write")
            if writes and name not in WRITE_ALLOWED:
                errs.append(f"{name}: grants write on {writes} while running sibling apps' code")
        for step in job.get("steps") or []:
            uses = str(step.get("uses", ""))
            if not uses.startswith("actions/checkout@"):
                continue
            pc = (step.get("with") or {}).get("persist-credentials")
            if pc is not False and str(pc).lower() != "false":
                errs.append(
                    f"{name}: checkout step {step.get('name', uses)!r} does not set `persist-credentials: false`"
                )
        job_env = json.dumps(job.get("env") or {})
        if any(t in job_env for t in TOKEN_MARKERS):
            errs.append(f"{name}: job-level `env:` hands the token to every step, including sibling code")
    return errs


def mutants(wf: dict):
    def m(fn):
        w = copy.deepcopy(wf)
        fn(w)
        return w

    yield "phpunit inherits the caller's permissions", m(lambda w: w["jobs"]["phpunit"].pop("permissions", None))
    yield "newman is granted contents: write", m(lambda w: w["jobs"]["newman"].__setitem__("permissions", {"contents": "write"}))

    def drop_pc(w):
        for s in w["jobs"]["playwright"]["steps"]:
            if str(s.get("uses", "")).startswith("actions/checkout@"):
                s.get("with", {}).pop("persist-credentials", None)
                return

    yield "a playwright checkout persists its token", m(drop_pc)
    yield "journeydoc-capture puts the token in a job-level env", m(
        lambda w: w["jobs"]["journeydoc-capture"].__setitem__("env", {"GH_TOKEN": "${{ github.token }}"})
    )
    yield "the detector recognises no jobs", m(
        lambda w: w.__setitem__("jobs", {k: v for k, v in w["jobs"].items() if k not in ("phpunit", "newman", "playwright")})
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("workflow")
    ap.add_argument("--positive-control", action="store_true")
    args = ap.parse_args()
    with open(args.workflow) as fh:
        wf = yaml.safe_load(fh)

    if args.positive_control:
        if findings(wf):
            print("::error::the real workflow already fails; a positive control needs a clean baseline")
            for e in findings(wf):
                print(f"  {e}")
            return 1
        survived = 0
        for label, mutant in mutants(wf):
            got = findings(mutant)
            print(f"{'caught  ' if got else 'SURVIVED'} {label}")
            if not got:
                survived += 1
        if survived:
            print(f"::error::{survived} mutant(s) survived: this assertion cannot see that defect")
            return 1
        print("positive control: every mutant caught")
        return 0

    errs = findings(wf)
    print(f"jobs running sibling apps: {', '.join(sibling_jobs(wf))}")
    if errs:
        for e in errs:
            print(f"::error::{e}")
        return 1
    print("every job that runs sibling apps holds a read-only token (or a listed reason) and persists none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
