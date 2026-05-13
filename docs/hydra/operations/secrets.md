# Secret Management

## File Layout

```
secrets/
├── .env                       ← Git PATs + legacy vars + non-secret config (gitignored)
├── .env.example               ← Template with descriptions (committed)
├── credentials.json           ← Claude OAuth tokens + Git token mapping (gitignored)
├── credentials.example.json   ← Template with descriptions (committed)
├── claude-credentials.json    ← OPTIONAL: standalone OAuth file used only by browser tests (gitignored)
└── ...
```

All non-template files in `secrets/` are gitignored. Copy `secrets/credentials.example.json` to `secrets/credentials.json` and `secrets/.env.example` to `secrets/.env`, then fill in values.

## Credentials Configuration

### `secrets/credentials.json`

Central credential config loaded by `scripts/lib/credentials.sh`. Supports:

- **Multiple Claude OAuth accounts** in priority order (work → personal fallback)
- **Per-container Git PATs** (builder, reviewer, security can use different GitHub accounts)

```json
{
  "claude_accounts": [
    {
      "name": "work",
      "token": "sk-ant-oat01-...",
      "priority": 1
    },
    {
      "name": "personal",
      "token": "sk-ant-oat01-...",
      "priority": 2
    }
  ],
  "git_tokens": {
    "builder": "ghp_... — push access, create PRs",
    "reviewer": "ghp_... — comment on PRs",
    "security": "ghp_... — comment on PRs"
  }
}
```

**Adding a new Claude account:** Add an entry to `claude_accounts` with a lower priority number = tried first. Tokens are embedded inline (generate with `claude setup-token` while logged in to the relevant account).

**Token fallback:** When a container hits a rate limit ("You've hit your limit"), `run_container_with_fallback()` automatically retries with the next token in priority order.

### `secrets/claude-credentials.json` (optional, browser tests only)

This optional file uses the standard Claude CLI credentials format:

```json
{
  "claudeAiOauth": {
    "accessToken": "sk-ant-oat01-...",
    "expiresAt": "2030-01-01T00:00:00.000Z"
  }
}
```

It is read **only by `scripts/run-browser-tests.sh`** (the host-side Playwright runner). If absent, the browser tester falls back to `~/.claude/.credentials.json`. The pipeline scripts (orchestrate, supervisor, dev-run) do **not** use this file — they read OAuth tokens from `credentials.json` directly.

### `secrets/.env`

GitHub PATs, non-secret config, and optional Claude auth fallbacks loaded as `--env-file` by `docker run`:

```bash
# GitHub PATs — per container role
HYDRA_BUILDER_TOKEN=ghp_...   # Push access to repos, create PRs
HYDRA_REVIEWER_TOKEN=ghp_...  # Comment on PRs (can be same as builder)
HYDRA_SECURITY_TOKEN=ghp_...  # Comment on PRs (can be same as builder)

# Non-secret config (used by poll-board.sh, cron-hydra.sh)
GITHUB_ORG=ConductionNL
HYDRA_PROJECT_NUMBER=1
```

When `secrets/credentials.json` is present its `git_tokens` block takes precedence for in-container auth. If `credentials.json` is absent, `scripts/lib/credentials.sh` returns an error — `.env` alone is not sufficient for the pipeline (only the browser test runner can work without it).

## `.gitignore` Rules

```
.env / .env.* / secrets/    — environment files and all secrets
*.pem / *.key / *.crt       — certificates and keys
logs/                        — run logs (may contain token prefixes in errors)
```

## How Credentials Are Used

```
scripts/lib/credentials.sh
    ├── load_credentials()           — called once at script startup
    │   ├── reads secrets/credentials.json (or falls back to known paths)
    │   ├── populates CLAUDE_TOKENS[] array
    │   └── populates GIT_TOKEN_BUILDER/REVIEWER/SECURITY
    │
    ├── get_claude_auth_env(index)   — returns -e flag for container
    ├── get_git_token(role)          — returns PAT for builder/reviewer/security
    │
    └── run_container_with_fallback(log_file, cmd...)
        ├── tries token[0] (work account)
        ├── if rate limited → tries token[1] (personal)
        ├── if rate limited → tries token[2] (if configured)
        └── all exhausted → returns error
```

Sourced by:
- `scripts/orchestrate.sh` — builder, fix, fix-quality, fix-browser containers
- `scripts/hydra-supervisor.sh` — code review, security review, applier containers

## Per-Deployment Injection

| Variable | Local (`cron`) | GitHub Actions | Kubernetes |
|---|---|---|---|
| Claude OAuth | `secrets/credentials.json` | `secrets.CLAUDE_CODE_OAUTH_TOKEN` | K8s secret `hydra-claude-oauth` |
| GitHub PATs | `secrets/.env` | `secrets.HYDRA_*_TOKEN` | K8s secrets per agent |

## Security Notes

- OAuth tokens expire and need periodic refresh (`claude auth login`)
- Git PATs should use fine-grained tokens scoped to the org
- Never pass `ANTHROPIC_API_KEY` — always use Claude CLI with OAuth
- Container logs (JSONL) may contain token prefixes in error messages — `logs/` is gitignored
