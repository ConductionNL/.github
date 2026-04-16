# Skill Evaluation & Measurement Guide

How to evaluate, measure, and improve Claude Code skills with data. This is the detailed reference for [Level 5: Measurement](writing-skills.md#level-5-measurement--evaluated-and-optimized-with-data) in the skill maturity framework.

---

## `evals/evals.json` Format

```json
{
  "skill_name": "create-pr",
  "version": "1.0.0",
  "created": "2025-01-15",
  "last_validated": null,
  "evals": [
    {
      "id": 1,
      "prompt": "Create a PR for the openregister feature branch",
      "expected_output": "PR targets development branch, has quality checks, proper format",
      "files": [],
      "expectations": [
        "targets development branch (not main)",
        "runs composer check:strict",
        "includes ## Summary and ## Test plan sections"
      ]
    }
  ],
  "trigger_tests": {
    "should_trigger": [
      "Create a pull request for the feature branch",
      "Open a PR from development to main",
      "Make a PR for my changes",
      "Submit this branch for review via PR",
      "Create a GitHub pull request",
      "PR this to development",
      "Open pull request for openregister branch",
      "Make a pull request for my new feature",
      "Create PR targeting the main branch",
      "Submit a pull request with these changes"
    ],
    "should_not_trigger": [
      "Can you review this code?",
      "What is the difference between git merge and rebase?",
      "How do I resolve a merge conflict?",
      "Show me the git log",
      "Commit my changes",
      "Push to the remote branch",
      "What branches are available?",
      "Help me write a commit message",
      "Show the diff for my changes",
      "Explain what a pull request is"
    ]
  }
}
```

After running evals, update `last_validated` with the run date to unlock L5 green circle status.

---

## Using the Anthropic Skill Creator

The [Anthropic Skill Creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) automates running, grading, and improving evals as a Claude Code skill.

### Installation

The Skill Creator lives at `.claude/skills/skill-creator/` in each repo (hydra and wordpress-docker). It's a vendored copy of [`anthropics/skills/skills/skill-creator/`](https://github.com/anthropics/skills/tree/main/skills/skill-creator) with one local modification: the eval workspace lives **inside** each skill rather than as a sibling folder.

### Keeping it up to date

Run `bash .claude/skills/update-skill-creator.sh` from the repo root. This script:
- Sparse-clones `anthropics/skills` to a tempdir
- Compares the upstream commit hash against `.claude/skills/skill-creator/.upstream-version`
- Backs up the current copy, rsyncs upstream files in, then re-applies `local-mods.patch`
- Updates `.upstream-version` to the new commit hash

If `local-mods.patch` no longer applies cleanly (upstream rewrote the relevant section), the script aborts and points you at the backup + `.rej` files so you can hand-merge. We use this script-based approach because `anthropics/skills` keeps `skill-creator/` as a subdirectory, which makes pure `git subtree` impractical for tracking just that one folder.

**Why we deviate from upstream:** Upstream Skill Creator writes eval results to `<skill-name>-workspace/` as a sibling to the skill folder. We patch this so results live at `<skill-dir>/evals/workspace/iteration-N/`, keeping eval artifacts adjacent to the skill they belong to. The patch is recorded in `.claude/skills/skill-creator/local-mods.patch`.

### Running evals step-by-step

1. **Invoke**: In a Claude Code session, ask Claude to evaluate the skill:
   > "Run evals on the test-app skill" or "Use the skill creator to evaluate and improve my X skill"

   Claude picks up the skill-creator and guides the process. The skill-creator's `evals/evals.json` format uses `evals[]` with `id`, `prompt`, `expected_output`, and `expectations`. We adopted this format across all our skills.

2. **What happens**: Two parallel subagents run each eval:
   - **With-skill agent**: runs the scenario with the skill active
   - **Baseline agent**: runs the same scenario without the skill
   Results are saved to `<skill-dir>/evals/workspace/iteration-N/eval-<name>/` (inside the skill folder, per our local convention).

3. **Review results**: The Skill Creator runs `eval-viewer/generate_review.py` and opens a browser tab (or generates a static HTML file with `--static`) with two tabs: **Outputs** (click through each eval, leave qualitative feedback) and **Benchmark** (pass rates, timing, tokens with-skill vs baseline).

4. **Output files** written to `<skill-dir>/evals/workspace/iteration-N/eval-<name>/`:
   - `grading.json` — assertion pass/fail with evidence per expectation
   - `timing.json` — token count and duration
   - `benchmark.json` — aggregate stats across all evals (one level up, at `iteration-N/`)
   - `eval-review-iteration-N.html` — static viewer (one level up, at `evals/workspace/`)

5. **Update `last_validated` and `baseline_score`** in `evals.json` after a successful run:
   ```json
   "last_validated": "2026-04-13",
   "baseline_score": 0.67
   ```
   `last_validated` unlocks the L5 green circle in the skill overview dashboard. `baseline_score` records the with-skill pass rate at the time of validation — used as a regression guardrail when re-running evals (see below).

6. **Improve cycle**: The Skill Creator's analyzer flags non-discriminating assertions, flaky evals, and skill improvement suggestions. Update `SKILL.md` and re-run as iteration-2 (and so on, in the same `evals/workspace/` folder).

---

## `baseline_score` — Regression Detection

Even running evals manually (no CI), `baseline_score` is useful: it's the with-skill pass rate from the most recent successful eval run, recorded in `evals/evals.json` next to `last_validated`. When you re-run evals later, compare the new pass rate against `baseline_score`:

- **New rate >= baseline_score** — skill is stable or improving. Update `baseline_score` to the new rate (and bump `last_validated`).
- **New rate < baseline_score** — regression. Investigate before updating either field. The skill change you just made may have broken something.

This gives you a paper trail of "this skill scored 0.67 on these expectations on this date" without needing CI infrastructure. The Skill Creator's own `benchmark.json` already produces the pass rate — you're just writing it back into `evals.json` as a durable marker.

---

## Eval Workspace Layout

```
<skill-dir>/
  evals/
    evals.json                          # eval definitions + trigger tests
    workspace/
      iteration-1/
        eval-basic-usage/
          grading.json
          timing.json
        eval-edge-case/
          grading.json
          timing.json
        benchmark.json                  # aggregate for this iteration
      iteration-2/                      # after improvements
        ...
      eval-review-iteration-1.html      # static viewer
```
