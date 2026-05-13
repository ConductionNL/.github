# Context — Hydra Platform

This document captures the operational context of the Hydra platform: how it is positioned
within Conduction B.V., how it receives work, and how credentials flow through the pipeline.

---

## Purpose

Hydra takes structured OpenSpec change proposals and turns them into validated, security-
scanned code on a feature branch — ready for a single human approval.

It is the factory, not the product. The applications it builds live under `ConductionNL`.

---

## Secrets & Tokens

### Overview

Each container receives exactly the credentials it needs — no more. No shared org-admin
tokens exist in the pipeline.

| Container | Token variable | PAT scope | What it can do |
|---|---|---|---|
| Builder | `GIT_TOKEN` = `HYDRA_BUILDER_TOKEN` | `contents:write`, `pull-requests:write` | Clone, push branch, create draft PR, post issue comments |
| Code Reviewer | `GIT_TOKEN` = `HYDRA_REVIEWER_TOKEN` | `pull-requests:write` | Post PR review comments only |
| Security Reviewer | `GIT_TOKEN` = `HYDRA_SECURITY_TOKEN` | `pull-requests:write` | Post PR review comments only |

All containers also receive `ANTHROPIC_API_KEY` (same key, all containers).

### Injection method per deployment model

#### Local (Docker)

Secrets are loaded from `secrets/.env` (gitignored). The `docker run` command injects them
via `--env-file`:

```bash
docker run \
  --env-file secrets/.env \
  -e GIT_TOKEN="${HYDRA_BUILDER_TOKEN}" \
  ...
```

The `orchestrate.sh` script reads `secrets/.env` and maps the correct token to `GIT_TOKEN`
based on which stage is running:

```bash
# Builder stage:
GIT_TOKEN="${HYDRA_BUILDER_TOKEN}"

# Review stage:
GIT_TOKEN="${HYDRA_REVIEWER_TOKEN}"

# Security stage:
GIT_TOKEN="${HYDRA_SECURITY_TOKEN}"
```

See `secrets/.env.example` for the complete variable reference.

#### GitHub Actions

Secrets are stored in the GitHub organisation under **Settings → Secrets and variables →
Actions**. Each workflow step injects the token for the specific container via `env:`:

```yaml
- name: Run Builder
  env:
    ANTHROPIC_API_KEY: ${{ secrets.HYDRA_ANTHROPIC_KEY }}
    GIT_TOKEN: ${{ secrets.HYDRA_BUILDER_TOKEN }}
```

GitHub Actions secrets are never echoed in logs. Each job only receives its own token.

#### Kubernetes (phase 3)

Secrets are stored as Kubernetes `Secret` objects in the `hydra` namespace, managed by
ArgoCD via sealed secrets or external secrets operator. Each Job manifest mounts only the
secret it needs via `env.valueFrom.secretKeyRef`:

```yaml
env:
  - name: GIT_TOKEN
    valueFrom:
      secretKeyRef:
        name: hydra-builder-token
        key: token
  - name: ANTHROPIC_API_KEY
    valueFrom:
      secretKeyRef:
        name: hydra-anthropic-key
        key: key
```

Secrets are never mounted as files — always injected as environment variables.

### What is NOT a secret

The following are not secrets and may appear in logs:

- `REPO_URL` — the GitHub URL of the target repository
- `ISSUE_URL` — the GitHub issue URL triggering the build
- `PR_URL` — the PR URL (Reviewers only)
- `SPEC_PATH` — path to the OpenSpec change inside the container
- `GITHUB_ORG`, `HYDRA_PROJECT_NUMBER` — organisation metadata

---

## Input Contract

Every container receives its inputs as environment variables (never as command-line args
or mounted config files, to avoid leakage via `/proc`):

| Variable | Required by | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | all | Claude API key |
| `GIT_TOKEN` | all | Scoped PAT for this persona |
| `REPO_URL` | all | `https://github.com/ConductionNL/<app>` |
| `ISSUE_URL` | Builder | GitHub issue that triggered the build |
| `PR_URL` | Reviewers | GitHub PR to review |
| `SPEC_PATH` | Builder | Path to `openspec/changes/<change-name>/` inside the container |
