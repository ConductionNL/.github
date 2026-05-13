# Container Entrypoint Flow

Each container runs an `entrypoint.sh` that sets up the environment before handing off to Claude Code.

## Builder (`images/builder/entrypoint.sh`)

1. Validate env vars: `GIT_TOKEN`, `REPO_URL`, `ISSUE_URL`, `SPEC_PATH`
2. Attempt iptables egress allowlist (skipped in rootless mode — see [networking.md](networking.md))
3. Fix `~/.claude` ownership for session data writes
4. Pre-flight check: verify `GIT_TOKEN` has push access to `REPO_URL` via GitHub API
5. Configure git auth (url.insteadOf + token exports)
6. Build prompt with spec path, repo URL, issue URL
7. Exec Claude Code as `claude` user (via `gosu` or direct exec in rootless)

**Max turns:** 80. **Tools:** Read, Write, Edit, Bash, Glob, Grep.

## Reviewer (`images/reviewer/entrypoint.sh`)

1. Validate env vars: `GIT_TOKEN`, `REPO_URL`, `PR_URL`
2. Attempt iptables egress allowlist
3. Fix `~/.claude` ownership
4. Configure git auth
5. Build prompt with PR URL and repo URL
6. Exec Claude Code — read-only (no Write/Edit tools)

**Max turns:** 25. **Tools:** Read, Bash, Grep, Glob.

## Security Reviewer (`images/security/entrypoint.sh`)

1. Validate env vars: `GIT_TOKEN`, `REPO_URL`, `PR_URL`
2. Attempt iptables egress allowlist
3. Fix `~/.claude` ownership
4. **Clone the PR branch** into `/workspace/repo`
5. **Run SAST tools before Claude starts:**
   - Semgrep (`p/security-audit`, `p/secrets`, `p/owasp-top-ten`) → `/tmp/semgrep-results.json`
   - Gitleaks → `/tmp/gitleaks-results.json`
   - Trivy (conditional: Dockerfile → `fs` scan, Helm/K8s → `config` scan) → `/tmp/trivy-results.json`
6. Configure git auth
7. Build prompt referencing the pre-computed SAST results
8. Exec Claude Code — read-only

**Max turns:** 20. **Tools:** Read, Bash.

## `gosu` fallback

In real-root environments (K8s, rootful Docker/Podman), `gosu` drops privileges to the
`claude` user. In rootless mode, container "root" is already the host user — `gosu` setuid
fails, so the entrypoint falls back to `exec` directly.
