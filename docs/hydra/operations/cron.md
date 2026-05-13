# Cron Jobs

Hydra uses a long-running supervisor daemon for build + review dispatch. A small number of cron jobs keep the daemon alive and handle periodic housekeeping.

## Setup

```bash
# Install the crontab
(crontab -l 2>/dev/null; cat <<'CRON'
* * * * * /path/to/hydra/scripts/watchdog-supervisor.sh >> /path/to/hydra/logs/watchdog.log 2>&1
*/10 * * * * /path/to/hydra/scripts/reconcile.sh >> /path/to/hydra/logs/reconcile.log 2>&1
*/30 * * * * /path/to/hydra/scripts/cron-audit.sh >> /path/to/hydra/logs/audit-cron.log 2>&1
*/10 * * * * /path/to/hydra/scripts/cron-spec-from-issue.sh >> /path/to/hydra/logs/spec-from-issue.log 2>&1
15 * * * * /path/to/hydra/scripts/cron-update-prs.sh >> /path/to/hydra/logs/update-prs-cron.log 2>&1
CRON
) | crontab -
```

Replace `/path/to/hydra` with the actual path (e.g., `/home/wilco/hydra`).

## Cron Jobs

| Script | Interval | What it does |
|--------|----------|-------------|
| `watchdog-supervisor.sh` | Every minute | Starts `hydra-supervisor.sh` if the daemon is not running |
| `reconcile.sh` | Every 10 min | Label validation + auto-recovery sweep |
| `cron-audit.sh` | Every 30 min | Full codebase audits on `ready-for-audit` issues |
| `cron-spec-from-issue.sh` | Every 10 min | Converts `needs-spec` issues into OpenSpec changes |
| `cron-update-prs.sh` | Every hour | Merges `development` into open `feature/<issue>/*` PRs that are `BEHIND` |

`scripts/cron-hydra.sh` is retained for manual dispatch runs but is **not** scheduled — the supervisor replaces it.

## Logs

| File | Content |
|------|---------|
| `logs/cron.log` | Build pipeline dispatch log |
| `logs/review-cron.log` | Review dispatch log |
| `logs/pipeline-{issue}-{timestamp}/` | Per-pipeline stage logs (builder, quality, reviewer, etc.) |
| `logs/reviews/{repo}-{pr}-{type}-{timestamp}.jsonl` | Per-review JSONL output |

## Trigger Label Configuration

The label that triggers the build pipeline is configurable via the `HYDRA_TRIGGER_LABEL` environment variable. Default: `ready-to-build`.

Set it in `secrets/.env`:
```bash
HYDRA_TRIGGER_LABEL=wilco-testing
```

Or pass it as an environment variable when running scripts directly:
```bash
HYDRA_TRIGGER_LABEL=my-custom-label ./scripts/orchestrate.sh --poll --repo-url https://github.com/ConductionNL/myapp
```

Or use the `--trigger-label` flag with `orchestrate.sh`:
```bash
./scripts/orchestrate.sh --issue-url ... --repo-url ... --trigger-label my-custom-label
```

This is useful for:
- **Testing**: Use a separate label (e.g. `wilco-testing`) to avoid interfering with production pipelines
- **Multi-environment isolation**: Run separate Hydra instances that each watch for different labels
- **Gradual rollout**: Only process issues you explicitly opt in

## Build cron (`cron-hydra.sh`)

- Searches all open issues with the trigger label (default: `ready-to-build`) across the org
- Dispatches pipelines in background (detached), up to 5 parallel slots
- Each slot gets an isolated NC port (8086-8090) and container namespace
- Exits immediately — pipelines continue in background
- Lock files in `/tmp/hydra-slots/` prevent double-dispatch

## Review dispatch (supervisor)

Review dispatch is handled continuously by `hydra-supervisor.sh`, not a cron entry.

- Supervisor scans open PRs for review labels across the org each cycle
- Uses the shared slot pool (max 5 concurrent with builders)
- Labels are on **PRs** (not issues) — this is how reviews work standalone
- After a reviewer posts its verdict, the label is removed
- Works independently from the build pipeline — any repo in the org can use it

### Standalone review usage

For a one-off manual review on a specific PR, use `scripts/manual-review.sh`:

```bash
./scripts/manual-review.sh \
    --pr-url https://github.com/ConductionNL/myapp/pull/42 \
    --review-type code
```

Results appear as PR comments.

## Verify cron is running

```bash
# Check crontab
crontab -l

# Check supervisor is alive
pgrep -f hydra-supervisor.sh

# Check recent logs
tail -20 /path/to/hydra/logs/supervisor.log
tail -20 /path/to/hydra/logs/watchdog.log
tail -20 /path/to/hydra/logs/reconcile.log

# Check active slots
ls /tmp/hydra-slots/slot-*.lock 2>/dev/null
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Cron not running | Check `crontab -l`, verify PATH in script header |
| `No PRs with review labels found` | Expected when no reviews are pending |
| Review label not removed | Check `logs/reviews/` for container errors |
| Stale slot lock | `rm /tmp/hydra-slots/slot-N.lock` (cron auto-detects dead PIDs) |
