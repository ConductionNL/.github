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

The Skill Creator lives at `.claude/skills/skill-creator/` in the hydra repo. It's a vendored copy of [`anthropics/skills/skills/skill-creator/`](https://github.com/anthropics/skills/tree/main/skills/skill-creator) with local modifications: the eval workspace lives **inside** each skill rather than as a sibling folder, and the long-form eval-runner protocol is extracted from `SKILL.md` into `references/eval-runner.md` to keep `SKILL.md` lean.

### Keeping it up to date

Run `bash .claude/skills/skill-creator/update.sh` for a dry-run preview, then `--apply` to write changes. The script delegates to `update_from_upstream.py`, which performs a per-file 3-way merge between three trees:

- **base** — upstream snapshot at the pin recorded in `.upstream-version`
- **theirs** — upstream HEAD
- **ours** — your current local files

For each file path it picks the right outcome (add, modify, delete, conflict, keep, unchanged) using `git merge-file`, so local edits, local additions (e.g. `references/eval-runner.md`), and locally-deleted files are all preserved without a separate patch file. Conflicts are listed in the dry-run report; running `--apply` alone leaves conflicting files untouched, while `--apply --force-conflicts` writes standard `<<<<<<<` markers into them for editor-driven resolution.

The previous `local-mods.patch` mechanism is gone — the merge replaces it. If you find that file in an old checkout, delete it. The new flow needs no manual patch maintenance: as long as `.upstream-version` accurately records the last applied commit, the merge is reproducible.

**Why we deviate from upstream:** Upstream Skill Creator writes eval results to `<skill-name>-workspace/` as a sibling to the skill folder. We keep them at `<skill-dir>/evals/workspace/iteration-N/` so eval artifacts stay adjacent to the skill they belong to.

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

The workspace is bounded to **3 live iterations max**. Older iterations are summarized into `archived-iterations/` automatically at the end of every eval cycle (Step 6 in `references/eval-runner.md`).

```
<skill-dir>/
  evals/
    evals.json                          # eval definitions + trigger tests
    workspace/
      archived-iterations/              # sorts above iteration-N alphabetically
        INDEX.md                        # one-line-per-iteration summary table
        index.json                      # machine-readable equivalent
        iteration-1/
          summary.json                  # pass rates, tokens, durations, failed assertions
          benchmark.json                # preserved verbatim
          benchmark.md
          embedded_data.json            # extracted from HTML viewer; re-render on demand
          notable/                      # full eval dirs ONLY for regressions
            eval-some-name/...          # OR same_as.json pointer if dedup'd vs earlier archive
      iteration-5/                      # live (full data)
        eval-basic-usage/
          eval_metadata.json
          with_skill/run-1/{grading,timing}.json + outputs/
          without_skill/run-1/{grading,timing}.json + outputs/
        eval-edge-case/...
        benchmark.json
      iteration-6/...                   # live
      iteration-7/...                   # live (current)
      eval-review-iteration-7.html      # static viewer for current iteration
```

**Rotation rules** (run by `python -m scripts.rotate_workspace <workspace> --keep 3` at end of each eval cycle):
- Iterations beyond the keep window are archived into `archived-iterations/iteration-N/` and removed from the live tree.
- Iteration numbering keeps incrementing forever — `iteration-8`, `iteration-9` — never reused.
- "Notable" detection (which evals get full output preserved in `notable/`): a regression vs. the previous iteration (assertion that passed before now fails, OR `with_skill` pass_rate dropped). For iteration 1 the fallback is "any failed assertion".
- **Dedup across archives:** if an earlier archived iteration already preserved the same eval with an identical with_skill failed-assertion signature, a new notable entry is replaced by a `same_as.json` pointer to that earlier iteration — no duplicated outputs.
- The rendered HTML viewer is NOT preserved as HTML — only its `EMBEDDED_DATA` JSON is. To inspect an archived iteration in the browser, feed `embedded_data.json` back through `eval-viewer/generate_review.py`.

Typical archived iteration size: ~30-50 KB (vs. ~250 KB for a live one).
