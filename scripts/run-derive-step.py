#!/usr/bin/env python3
"""Run quality.yml's OWN matrix-derivation code against a fixture manifest.

quality-resolve-probe.yml used to prove the derivation by invoking
`icewind1991/nextcloud-version-matrix` directly, which was correct while
quality.yml also invoked that action. quality.yml now derives the range with
inline Python (see the long comment on its `derive` step), and a probe that
kept calling the action would have gone on passing while testing something the
fleet no longer runs — a check aimed at a subject that has moved.

So this reaches the subject the way the shipping code does: it reads the
`derive` step out of .github/workflows/quality.yml, pulls the Python out of its
heredoc, and executes THAT. There is no second copy of the logic to drift.

The extraction is deliberately strict. Every way this can fail to find the real
code raises instead of falling back, because a harness that quietly runs
nothing looks exactly like a harness whose subject passed.

Usage:
    INFO_PATH=<fixture.xml> GITHUB_OUTPUT=<file> python3 scripts/run-derive-step.py
"""

from __future__ import annotations

import os
import pathlib
import sys

import yaml

WORKFLOW = pathlib.Path(".github/workflows/quality.yml")
STEP_ID = "derive"
HEREDOC_OPEN = "<<'PY'"


def find_step_run(workflow: pathlib.Path, step_id: str) -> str:
    """Return the `run:` body of the uniquely-identified step."""
    if not workflow.is_file():
        raise SystemExit(f"{workflow} does not exist — run this from the repo root.")

    data = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    matches = [
        step
        for job in (data.get("jobs") or {}).values()
        for step in (job.get("steps") or [])
        if step.get("id") == step_id
    ]

    if len(matches) != 1:
        raise SystemExit(
            f"expected exactly one step with id '{step_id}' in {workflow}, found "
            f"{len(matches)}. The probe cannot know which one ships."
        )

    step = matches[0]
    if "uses" in step:
        raise SystemExit(
            f"the '{step_id}' step is a `uses:` action again ({step['uses']}). "
            "This harness only knows how to run an inline `run:` block; update "
            "the probe deliberately rather than letting it assert nothing."
        )

    run = step.get("run")
    if not run:
        raise SystemExit(f"the '{step_id}' step has no `run:` body to execute.")
    return run


def extract_python(run_body: str) -> str:
    """Pull the Python out of the step's `python3 - <<'PY' ... PY` heredoc."""
    if HEREDOC_OPEN not in run_body:
        raise SystemExit(
            f"the '{STEP_ID}' step no longer contains a {HEREDOC_OPEN} heredoc, so "
            "this harness would be testing an empty string."
        )

    after = run_body.split(HEREDOC_OPEN, 1)[1]
    lines = after.split("\n")

    body: list[str] = []
    for line in lines[1:]:
        if line.strip() == "PY":
            break
        body.append(line)
    else:
        raise SystemExit("the heredoc opened but never closed with a bare 'PY'.")

    source = "\n".join(body)
    if not source.strip():
        raise SystemExit("the extracted derivation body is empty.")

    # The workflow indents the heredoc; textwrap.dedent is not enough on its own
    # because the first line carries the same indent as the rest.
    indent = min(
        (len(ln) - len(ln.lstrip()) for ln in body if ln.strip()),
        default=0,
    )
    if indent:
        source = "\n".join(ln[indent:] if ln.strip() else ln for ln in body)

    return source


def main() -> int:
    for required in ("INFO_PATH", "GITHUB_OUTPUT"):
        if not os.environ.get(required):
            raise SystemExit(f"{required} must be set for this harness to run.")

    source = extract_python(find_step_run(WORKFLOW, STEP_ID))
    print(
        f"running {WORKFLOW}:{STEP_ID} ({len(source.splitlines())} lines) "
        f"against {os.environ['INFO_PATH']}",
        file=sys.stderr,
    )

    compiled = compile(source, f"{WORKFLOW}:{STEP_ID}", "exec")
    exec(compiled, {"__name__": "__main__"})  # noqa: S102 - that is the point
    return 0


if __name__ == "__main__":
    sys.exit(main())
