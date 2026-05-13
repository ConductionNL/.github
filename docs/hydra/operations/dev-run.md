# Running Locally

## Full pipeline — `/local-run`

From Claude Code, run the entire pipeline (builder → reviewer + security) in one command:

```
/local-run --spec-dir /tmp/todo-mvp-spec --repo-url https://github.com/algorithm-conduction/todo-app
```

This creates a fresh GitHub repo, uploads the openspec, builds all images, runs all three
stages, and prints a summary with costs. Previous repos are renamed with a timestamp
(museum pattern).

A standalone shell script (`scripts/smoke-test.sh`) is also available for use outside
Claude Code or in CI.

## Single stage — `dev-run.sh`

Run one container directly, bypassing orchestration:

```bash
# Builder
./scripts/dev-run.sh <spec-path> builder --repo-url <url> [--issue-url <url>]

# Reviewer
./scripts/dev-run.sh - reviewer --repo-url <url> --pr-url <url>

# Security
./scripts/dev-run.sh - security --repo-url <url> --pr-url <url>
```

## Container flags

| Flag | Purpose |
|---|---|
| `--rm` | Remove container after exit |
| `--tmpfs /tmp:size=512M` | Ephemeral temp storage |
| `--tmpfs /workspace:size=2G` | Ephemeral workspace (default) |
| `--cap-drop ALL` | Drop all Linux capabilities |
| `--cap-add SETUID,SETGID,DAC_OVERRIDE` | Required for `gosu` user switching |
| `--cpus 4 --memory 8g` | Resource limits |
| `--network hydra-net` | Isolated bridge network |

**Note:** `NET_ADMIN` is intentionally omitted. Internal iptables doesn't work reliably
in rootless containers (conntrack in user namespaces). Egress is controlled by the
container network in local dev and by NetworkPolicies in Kubernetes.

## Trigger label

The pipeline trigger label defaults to `ready-to-build` but can be overridden. Set `HYDRA_TRIGGER_LABEL` in your environment or `secrets/.env`:

```bash
# Via env var
HYDRA_TRIGGER_LABEL=wilco-testing ./scripts/dev-run.sh <spec-path> builder --repo-url <url>

# Via secrets/.env (loaded automatically by orchestrate.sh)
echo 'HYDRA_TRIGGER_LABEL=wilco-testing' >> secrets/.env
```

When using `orchestrate.sh` directly, you can also pass `--trigger-label`:
```bash
./scripts/orchestrate.sh --issue-url ... --repo-url ... --trigger-label wilco-testing
```

## Persistent workspace (debugging)

By default, `/workspace` is a tmpfs — everything is lost when the container exits. To keep
the workspace for inspection:

```bash
export HYDRA_WORKSPACE_DIR=/tmp/hydra-workspace
./scripts/dev-run.sh ...
# After exit: ls /tmp/hydra-workspace/repo/
```
