# Authentication

Hydra containers need two types of auth: **Claude** (for AI) and **GitHub** (for git/PR operations).

## Claude auth — resolution order

The pipeline reads Claude OAuth tokens from `secrets/credentials.json` (the
orchestrator config) and falls back to env vars only when that file is absent:

| Priority | Source | Auto-refresh | Use case |
|---|---|---|---|
| 1 | `secrets/credentials.json` `claude_accounts[]` (multiple, sorted by priority field) | Per token | Standard local setup with multi-account fallback on rate limits |
| 2 | `CLAUDE_CODE_OAUTH_TOKEN` in `secrets/.env` | No — expires ~24h | CI, static injection (K8s) |
| 3 | `ANTHROPIC_API_KEY` in `secrets/.env` | N/A — no expiry | Pay-per-token billing |

`scripts/lib/credentials.sh` is the single source of truth for token loading.
If `secrets/credentials.json` doesn't exist, the script errors out and the
pipeline won't start. (The host-side browser test runner has a separate path
through `secrets/claude-credentials.json` → `~/.claude/.credentials.json` —
see `docs/operations/secrets.md`.)

**Generating tokens:** Run `claude setup-token` while logged in to the relevant
Max account, then copy the printed token into `credentials.json`. To regenerate
expired tokens, repeat the process.

**Generating a token manually:**

```bash
claude setup-token
# Opens browser → log in to your Max account → token is stored in ~/.claude/.credentials.json
```

**For Kubernetes:** create a secret with a static token. It will expire; rotation is a
future improvement (see Changelog).

```bash
kubectl create secret generic hydra-claude-oauth \
  --from-literal=token=sk-ant-oat01-... -n hydra
```

## GitHub PATs — per-agent scoping

Each agent persona gets its own GitHub Personal Access Token with minimal scopes:

| Agent | Token variable | Required scopes |
|---|---|---|
| Al Gorithm (Builder) | `HYDRA_BUILDER_TOKEN` | `contents:write`, `pull-requests:write` |
| Juan Claude van Damme (Reviewer) | `HYDRA_REVIEWER_TOKEN` | `pull-requests:write` (no contents write) |
| Clyde Barcode (Security) | `HYDRA_SECURITY_TOKEN` | `pull-requests:write` (no contents write) |

Prefer fine-grained PATs scoped to specific repositories. Rotate at least every 90 days.

## How git auth works inside containers

Each entrypoint configures git to embed the token transparently:

```bash
git config --global url."https://x-access-token:${GIT_TOKEN}@github.com/".insteadOf "https://github.com/"
export GH_TOKEN="${GIT_TOKEN}"
export GITHUB_PERSONAL_ACCESS_TOKEN="${GIT_TOKEN}"
```

This means `git clone`, `git push`, and `gh` CLI all work without the agent needing to
handle credentials. The agent prompt never sees the token.
