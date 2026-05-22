# Retry and Rebuild Runbook

When a Hydra pipeline issue is stuck at `needs-input`, there are two human-triggered recovery labels: `retry:queued` (single-shot fixer) and `rebuild:queued` (hard reset). This guide explains when to use each and exactly which labels to clean up first.

## Decision guide

| Situation | Use |
|---|---|
| Reviewers flagged concrete findings that the builder can address (missing headers, style violations, clear logic bugs) | `retry:queued` |
| The build output is fundamentally wrong — wrong approach, stub implementation, or the builder missed the spec entirely | `rebuild:queued` |
| Development moved forward (new lint rules, new dependencies) and the open PR is just stale | Merge `development → PR` (free — no rebuild) |

## retry:queued — single-shot fixer

The orchestrator compiles a `feedback.md` from `hydra.json` (unfixed findings + applier blockers), dispatches the builder in `HYDRA_MODE=fix` scope-limited to the flagged files, then re-queues both reviewers on the fixed code. If the fixer can't clear everything in one pass, it escalates back to `needs-input`. There is no loop.

### Checklist

Before applying `retry:queued`:

1. Remove `needs-input` (or `<prefix>-needs-input` if using `HYDRA_LABEL_PREFIX`)
2. Remove `code-review:fail` (and `<prefix>-code-review:fail` if present)
3. Remove `security-review:fail` (and `<prefix>-security-review:fail` if present)
4. Apply `retry:queued` (or `<prefix>-retry:queued`)

Using `hydra-label.sh` (recommended — keeps the board in sync):

```bash
# 1. Remove stale fail labels
./scripts/hydra-label.sh ConductionNL/<app> <issue> remove needs-input
./scripts/hydra-label.sh ConductionNL/<app> <issue> remove code-review:fail
./scripts/hydra-label.sh ConductionNL/<app> <issue> remove security-review:fail

# 2. Apply retry trigger
./scripts/hydra-label.sh ConductionNL/<app> <issue> add retry:queued
```

If using a label prefix (e.g. `HYDRA_LABEL_PREFIX=wilco`), also remove the prefixed versions:

```bash
./scripts/hydra-label.sh ConductionNL/<app> <issue> remove wilco-needs-input
./scripts/hydra-label.sh ConductionNL/<app> <issue> remove wilco-code-review:fail
./scripts/hydra-label.sh ConductionNL/<app> <issue> remove wilco-security-review:fail
./scripts/hydra-label.sh ConductionNL/<app> <issue> add wilco-retry:queued
```

### What happens next

`retry:queued → retry:running` (fixer runs) → `code-review:queued` (both reviewers re-queued) or `needs-input` (fixer couldn't clear all findings).

The supervisor **will not pick up `retry:queued` while `needs-input` is still on the issue.** Remove `needs-input` first.

## rebuild:queued — full reset

The orchestrator closes the open PR, hard-resets the feature branch to `development`, strips every pipeline label, and drops `build:queued`. The next cycle starts from scratch.

### Checklist

Before applying `rebuild:queued`:

1. Remove `needs-input` (and prefixed variant)
2. Remove any `code-review:fail`, `security-review:fail`, `applier:fail` (and prefixed variants)
3. Apply `rebuild:queued` (or `<prefix>-rebuild:queued`)

Do **not** close the PR manually — the orchestrator closes it as part of the rebuild sequence. If you already closed it, `reconcile.sh` will detect the closed PR + stale labels and auto-set `build:queued` within 10 minutes.

### What happens next

`rebuild:queued` → orchestrator closes PR + resets branch → `build:queued` → full pipeline re-runs from build.

## Label reference during recovery

| Label | Set by | Cleared by |
|---|---|---|
| `needs-input` | Orchestrator (escalation) | **Human manually** before retry/rebuild |
| `code-review:fail` | Orchestrator (review result) | **Human manually** before retry; or orchestrator on rebuild |
| `security-review:fail` | Orchestrator (review result) | **Human manually** before retry; or orchestrator on rebuild |
| `retry:queued` | **Human manually** | Orchestrator (transitions to `retry:running`) |
| `retry:running` | Orchestrator | Orchestrator (transitions to `code-review:queued` or `needs-input`) |
| `rebuild:queued` | **Human manually** | Orchestrator (transitions to `build:queued`) |

## Tip: use hydra-label.sh, not gh issue edit

`hydra-label.sh` routes through `scripts/lib/labels.sh` helpers, which keep the GitHub Projects board in sync. Direct `gh issue edit --add-label` / `--remove-label` bypasses the board sync and leaves the card in the wrong column until `reconcile.sh` catches up (~10 min).
