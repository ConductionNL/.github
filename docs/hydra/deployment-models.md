# Deployment Models

Hydra has three deployment layers. The container images are identical across all three —
only the orchestrator changes.

---

## Model 1: Local (Developer Machine)

**Trigger:** cron job running `poll-board.sh` every 15 minutes, or manual `scripts/dev-run.sh`

**Runner:** Docker on developer workstation

**Use case:** development of the pipeline itself; testing new container builds locally

### secrets/ structure

Create both files in `secrets/` from their `.example` templates (gitignored):

```bash
cp secrets/.env.example secrets/.env
cp secrets/credentials.example.json secrets/credentials.json
```

`secrets/credentials.json` holds the Claude OAuth tokens (multi-account, with
auto-fallback on rate limits) and the per-role Git PAT map. `secrets/.env`
holds the GitHub PATs again (mirrored for `docker --env-file`), the org/board
config, and optional fallback Claude auth. See [`docs/operations/secrets.md`](operations/secrets.md)
for the full layout.

```bash
# secrets/.env (required values shown — see secrets/.env.example for all options)

# GitHub PATs — one per agent persona
HYDRA_BUILDER_TOKEN=ghp_...    # contents:write, pull-requests:write
HYDRA_REVIEWER_TOKEN=ghp_...   # pull-requests:write (comments only)
HYDRA_SECURITY_TOKEN=ghp_...   # pull-requests:write (comments only)

# GitHub organisation hosting the target app repos
GITHUB_ORG=ConductionNL

# GitHub Projects v2 board number — find it in the URL:
# github.com/orgs/<org>/projects/<number>
HYDRA_PROJECT_NUMBER=1
```

### docker run command (Builder example)

```bash
docker run --rm \
  --read-only \
  --tmpfs /tmp:size=512M \
  --tmpfs /workspace:size=2G \
  --security-opt no-new-privileges \
  --cap-drop ALL \
  --cap-add NET_ADMIN \
  --cpus 4 \
  --memory 8g \
  --network hydra-net \
  --env-file secrets/.env \
  -e REPO_URL="${REPO_URL}" \
  -e ISSUE_URL="${ISSUE_URL}" \
  -e SPEC_PATH="/spec" \
  -v "$(pwd)/openspec/changes/${CHANGE_NAME}:/spec:ro" \
  -e GIT_TOKEN="${HYDRA_BUILDER_TOKEN}" \
  ghcr.io/conductionnl/hydra-builder:latest
```

> `--cap-add NET_ADMIN` is needed locally so entrypoint.sh can configure iptables egress
> rules. In Kubernetes, NetworkPolicy handles egress instead and this flag is omitted.

Create the Docker network once:
```bash
docker network create hydra-net
```

### Cron setup

Add to crontab (`crontab -e`):

```
*/15 * * * * /path/to/hydra/scripts/poll-board.sh >> /var/log/hydra-poll.log 2>&1
```

---

## Model 2: GitHub Actions

**Trigger:** `issues: [labeled]` event with the trigger label (default: `ready-to-build`, configurable via `HYDRA_TRIGGER_LABEL` repository variable)

**Runner:** GitHub-hosted runner (`ubuntu-latest`)

**Use case:** team workflow — create a GitHub issue, add label, pipeline runs automatically

### GitHub Secrets to configure (at organisation level)

Set these under **Settings → Secrets and variables → Actions** in the `ConductionNL`
organisation:

| Secret name | Value | PAT scopes required |
|---|---|---|
| `HYDRA_ANTHROPIC_KEY` | Anthropic API key | — |
| `HYDRA_BUILDER_TOKEN` | PAT for Al Gorithm | `contents:write`, `pull-requests:write` on target repo |
| `HYDRA_REVIEWER_TOKEN` | PAT for Juan Claude van Damme | `pull-requests:write` on target repo |
| `HYDRA_SECURITY_TOKEN` | PAT for Clyde Barcode | `pull-requests:write` on target repo |
| `GITHUB_ORG` | `ConductionNL` | — |
| `HYDRA_PROJECT_NUMBER` | Project board number | — |

### PAT scopes per persona

**Al Gorithm (Builder):**
- `contents:write` — clone, push feature branch
- `pull-requests:write` — create draft PR, post RFI comment
- Scoped to: `ConductionNL/<target-repo>` only (fine-grained PAT preferred)

**Juan Claude van Damme (Code Reviewer):**
- `pull-requests:write` — post review comments, post verdict
- No `contents` scope — cannot push code
- Scoped to: `ConductionNL/<target-repo>` only

**Clyde Barcode (Security Reviewer):**
- `pull-requests:write` — post security findings, post verdict
- No `contents` scope — cannot push code
- Scoped to: `ConductionNL/<target-repo>` only

### Workflow chain

```
issues: labeled (<trigger-label>)
  └── hydra-build.yml
        ├── runs Builder container (35 min timeout)
        └── on success: opens draft PR on target repo

pull_request: opened/synchronize (branch: hydra/*)
  └── hydra-review.yml
        ├── Code Reviewer job (20 min timeout)  ─┐ parallel
        └── Security Reviewer job (20 min timeout) ─┘
              └── each posts verdict comment on PR
```

---

## Model 3: Self-Hosted Server (Kubernetes + ArgoCD)

**Trigger:** GitHub board card event or webhook

**Runner:** Self-hosted K8s job via `actions-runner-controller`

**Use case:** production — air-gapped, auditable, no public GitHub runner access to code

### actions-runner-controller installation

```bash
helm repo add actions-runner-controller \
  https://actions-runner-controller.github.io/actions-runner-controller

helm install actions-runner-controller \
  actions-runner-controller/actions-runner-controller \
  --namespace actions-runner-system \
  --create-namespace \
  --set authSecret.create=true \
  --set authSecret.github_token="${GITHUB_PAT}"
```

Create a `RunnerDeployment` in the `hydra` namespace:

```yaml
apiVersion: actions.summerwind.dev/v1alpha1
kind: RunnerDeployment
metadata:
  name: hydra-runner
  namespace: hydra
spec:
  replicas: 2
  template:
    spec:
      organization: ConductionNL
      labels:
        - self-hosted
        - linux
        - hydra
```

### Migration from hosted to self-hosted runner

In each workflow file, change one line:

```yaml
# Before (GitHub-hosted):
runs-on: ubuntu-latest

# After (self-hosted):
runs-on: [self-hosted, linux, hydra]
```

All other workflow configuration remains identical. The container images are pulled from GHCR
— no code is on the runner.

### ArgoCD Application definition

See `manifests/argocd-app.yaml`. The Application syncs `manifests/` from the `main` branch.

```yaml
# Key fields
spec:
  source:
    repoURL: https://github.com/ConductionNL/hydra
    targetRevision: main
    path: manifests
  destination:
    server: https://kubernetes.default.svc
    namespace: hydra
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### NetworkPolicy per Job namespace

Each container Job runs in its own namespace with a NetworkPolicy that mirrors the iptables
allowlist in `entrypoint.sh`. See `manifests/network-policy.yaml` for the full definitions.

Key principle: egress is denied by default; only HTTPS (443) to the specific allow-listed
hosts is permitted per container type.
