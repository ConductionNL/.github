# Global Claude Code settings (`~/.claude`)

These are **mandatory** settings for anyone working on Conduction projects with Claude Code. They enforce a read-first, write-with-approval policy at the user level, ensuring Claude cannot perform destructive operations without explicit confirmation. They also version-check themselves at the start of each session so you always know when an update is available.

Project files under `.claude/` in this repo (for example `settings.json` with MCP allowlists) **complement** this; they do not replace the global policy.

## Versioned canonical files

The canonical files live under **[`global-settings/`](../../global-settings/)**. The version is tracked in [`global-settings/VERSION`](../../global-settings/VERSION).

| File | Install as |
|------|------------|
| [`global-settings/settings.json`](../../global-settings/settings.json) | `~/.claude/settings.json` |
| [`global-settings/block-write-commands.sh`](../../global-settings/block-write-commands.sh) | `~/.claude/hooks/block-write-commands.sh` |
| [`global-settings/check-settings-version.sh`](../../global-settings/check-settings-version.sh) | `~/.claude/hooks/check-settings-version.sh` |

## Install / update

See [`global-settings/README.md`](../../global-settings/README.md) for install commands, update instructions, and the VERSION bump policy.

## Session-start status panel

At the start of every Claude session, a live status panel is printed to the terminal (stderr):

```
┌──────────────────────────────────────────────┐
│     Global Claude Settings Status            │
└──────────────────────────────────────────────┘
  Installed   : v1.0.0  ✓
  Local repo  : main                 @ v1.0.0
  Online      : v1.0.0  (via GitHub API)
```

Color coding:
- **Green** — version matches / up to date
- **Yellow** — local branch is ahead of installed (informational only)
- **Red** — installed is behind online main (update required)

The "Online" line shows the fetch method used:
- **(via GitHub API)** — fetched directly from GitHub using `gh api` (primary method, uses `settings-repo-url`)
- **(via git fetch)** — fetched from `origin/main` of the local repo clone (fallback method, uses `settings-repo-path`)

If no local repo is configured, "Local repo" shows "(not configured)" instead of branch info.

If configuration issues are detected (missing config files, unreachable remote, `gh` not installed), they are shown in red below the panel — never silently skipped.

> **Note:** The terminal panel is only visible when using Claude Code in the terminal (CLI). In the VS Code extension, hook stderr is not shown as a visible banner — see the Claude chat message below instead.

## Session-start message in Claude chat

In addition to the terminal panel, the hook always injects a message into Claude's context at the start of every session. Claude will relay this at the top of its first response:

**Settings up to date:**
> New session started — Global Claude Settings checked. Settings are up to date (v1.0.0).

**Update required** (prominently displayed, cannot be missed):
> NEW SESSION — GLOBAL CLAUDE SETTINGS: UPDATE REQUIRED
> Installed: v0.1.0 (outdated) | Latest: v1.0.0 (on origin/main)
> Say "update my global settings to 1.0.0" to apply the update.

**Configuration error** (prominently displayed):
> NEW SESSION — GLOBAL CLAUDE SETTINGS: CONFIGURATION ERROR
> [description of the issue]

## Online version checking

The version check supports two methods for fetching the online version, tried in order:

### 1. GitHub API (primary — recommended)

If `~/.claude/settings-repo-url` contains a GitHub repo slug (e.g. `ConductionNL/.github`), the hook fetches `VERSION` via `gh api` from the configured ref (default: `main`). This method:

- Does **not** require a local clone of the repo
- Uses the authenticated `gh` CLI (requires `gh auth login`)
- Is faster than `git fetch` (single HTTP request)
- Falls back gracefully if `gh` is not installed or the API call fails

### 2. Git fetch (fallback)

If the GitHub API method is not configured or fails, and `~/.claude/settings-repo-path` points to a valid local clone, the hook falls back to `git fetch origin <ref> --depth=1` followed by `git show origin/<ref>:...`. This is the original method.

### Tracking a non-default branch

By default, both methods track the `main` branch. To track a different branch, tag, or SHA, write it to `~/.claude/settings-repo-ref`:

```bash
echo "feature/claude-code-tooling" > ~/.claude/settings-repo-ref
```

When absent, the ref defaults to `main`.

### Configuration options

| Config file | Required? | Purpose |
|-------------|-----------|---------|
| `~/.claude/settings-repo-url` | Optional (recommended) | GitHub repo slug for online API check |
| `~/.claude/settings-repo-path` | Optional (fallback) | Path to the root of the canonical repo for git-based check |
| `~/.claude/settings-repo-ref` | Optional | Branch/tag/SHA to track (defaults to `main`) |

You can configure:
- **Both URL and path** (recommended): GitHub API is tried first, local git as fallback
- **Only `settings-repo-url`**: Works without any local clone; no fallback if GitHub is unreachable
- **Only `settings-repo-path`**: Original behavior; requires a local clone
- **Neither**: Version check cannot run; a configuration warning is shown

## File locations

| Path | Role |
|------|------|
| `~/.claude/settings.json` | User permissions allowlist, `PreToolUse` + `UserPromptSubmit` hooks, optional `mcpServers` |
| `~/.claude/hooks/block-write-commands.sh` | Hook script invoked for every **Bash** tool use before it runs |
| `~/.claude/hooks/check-settings-version.sh` | Hook script that shows the status panel and warns on version mismatch |
| `~/.claude/settings-version` | Installed version (semver, matches repo `VERSION`) |
| `~/.claude/settings-repo-url` | GitHub repo slug for online version checking (e.g. `ConductionNL/.github`) |
| `~/.claude/settings-repo-path` | Absolute path to the root of the canonical repo (fallback for git-based check) |
| `~/.claude/settings-repo-ref` | Branch/tag/SHA to track for version checks (defaults to `main`) |

## Shape of `~/.claude/settings.json`

### 1. `permissions.deny`

Hard-blocked patterns — Claude cannot perform these even with user approval:

- **Config files**: `Edit`/`Write` of `~/.claude/settings.json`, `hooks/*`, `settings-version`, `settings-repo-path`, `settings-repo-url`, `settings-repo-ref`
- **System**: `sudo`, `su`, `shutdown`, `reboot`, `halt`, `poweroff`, `mkfs`, `dd if=`
- **GitHub destructive**: `gh pr merge`, `gh repo delete`, `gh release delete`
- **Git destructive**: `git reset --hard`, `git clean -f/-fd/-fdx`, `git filter-branch`, `git filter-repo`, `git reflog expire/delete`, `git update-ref -d`, `git config --global`, `git checkout --`, `git restore --` (file restore; `git restore --staged` is allowed), `git push --force/-f`, `git rebase`
- **Filesystem destructive**: `rm -rf`, `rm -Rf`
- **Package managers (arbitrary code execution)**: `pip install`, `npm install`

### 2. `permissions.allow`

Bash permission patterns granted **without** prompting. Keep this aligned with the hook: anything allowed here should still pass `block-write-commands.sh`, or the hook will deny the command even if it is allowlisted.

Allowed categories (all read-only; write operations are gated by the hook):

- **Inspection**: `ls`, `cat`, `head`, `tail`, `wc`, `stat`, `file`, `du`, `df`, `pwd`, `tree`, `find`, `realpath`, `basename`, `dirname`
- **Text processing**: `diff`, `grep`, `egrep`, `tr`, `sort`, `jq`, `cut`, `uniq`, `column`
- **System info**: `which`, `whoami`, `uname`, `ps`, `free`, `lsof`, `ss`, `id`, `groups`, `uptime`, `hostname`, `env`, `date`
- **Checksums / misc**: `sha256sum`, `md5sum`, `nproc`, `printenv`
- **Git (read-only)**: `git log`, `git status`, `git diff`, `git show`, `git blame`, `git ls-files`, `git ls-tree`, `git rev-parse`, `git describe`, `git shortlog`, `git cat-file`, `git branch --list/-a/-v`, `git remote -v/show`, `git fetch`, `git stash list`, `git stash show`, `git config --list`, `git config --get`
- **Navigation**: `cd`
- **Docker (read)**: `docker ps`, `docker images`, `docker image inspect`, `docker logs`, `docker inspect`, `docker stats`, `docker info`, `docker network ls/inspect`, `docker volume ls/inspect`, `docker --version`, `docker compose ps/config/logs/version`
- **GitHub CLI (read)**: `gh pr list/view/checks/diff`, `gh issue list/view`, `gh repo view`, `gh run list/view`, `gh release list/view`, `gh workflow list/view`, `gh auth status`
- **Package managers (read)**: `composer --version/show/validate/diagnose/audit/check-platform-reqs`, `node --version`, `npm --version/list/outdated/audit`, `pnpm list/outdated`, `yarn list`, `pip list/show/freeze`
- **PHP**: `php -l/-m/-i/--version`
- **Logs**: `Read(**/.claude/logs/**)`

**Not auto-approved** (hook or user prompt required): `curl`, `gh api`, `awk`, `git -C`, broad `git branch`/`git remote` — these commands have dangerous modes that the hook cannot fully distinguish from safe usage. They go through the hook for write detection and prompt the user when needed.

Do **not** put broad `Bash(*)` allow rules here.

### 3. `hooks.PreToolUse`

```json
"PreToolUse": [
  {
    "matcher": "Bash",
    "hooks": [{ "type": "command", "command": "bash ~/.claude/hooks/block-write-commands.sh" }]
  }
]
```

### 4. `hooks.UserPromptSubmit`

```json
"UserPromptSubmit": [
  {
    "hooks": [{ "type": "command", "command": "bash ~/.claude/hooks/check-settings-version.sh" }]
  }
]
```

### 5. `mcpServers` (optional)

7 Playwright browser instances (`browser-1` through `browser-7`). `browser-6` runs headed (no `--headless`). Adjust the count to match your actual usage.

---

## What `block-write-commands.sh` does

- Reads **JSON from stdin** once into a variable, then extracts `cmd` and `transcript_path`.
- On deny, prints `permissionDecision: "deny"` JSON. On ask, prints `permissionDecision: "ask"` JSON. On allow, exits `0`.

| Area | Allowed silently | Prompts for approval | Hard blocked |
|------|-----------------|---------------------|--------------|
| **curl** | — | All curl commands (not auto-approved) | — |
| **gh api** | — | All gh api commands (not auto-approved) | — |
| **git push** | Last user message contains authorized phrase | — | Blocked otherwise |
| **git -C** | Read-only subcommands | Write subcommands, branch/remote writes | `push` (phrase-authorized) |
| **git branch** (bare) | `--list`, `-a`, `-v` (auto-approved) | `-d/-D/-m/-M/-c/-C`, `--delete`, `--move`, `--copy` | — |
| **git remote** (bare) | `-v`, `show` (auto-approved) | `add`, `remove`, `rename`, `set-url`, `prune`, `update` | — |
| **env** | `env` alone or `VAR=value` | Using `env` to execute another command | — |
| **date** | Display time | — | `-s` / `--set` (system clock) |
| **cat** | Normal stdout | Shell redirection `>` / `>>` | — |
| **find** | Normal traversal | `-delete`, `-exec`, `-execdir` | — |
| **sort** | Normal sort | `-o` / `--output`, shell `>` / `>>` | — |
| **awk** | — | All awk commands (not auto-approved); `system()` and file output caught | — |
| **hostname** | Read hostname | Setting a new hostname (bare name argument) | — |
| **rm** | — | All `rm` commands | `rm -rf` / `rm -Rf` (deny-list) |
| **ln** | — | All `ln` commands | Symlinks/hardlinks to `~/.claude/` |
| **sed -i** | — | In-place file editing | — |
| **chown** | — | All `chown` commands | — |
| **install** | — | All `install` commands | — |
| **Pipe-to-shell** | — | `\| bash`, `\| sh`, `base64 -d`, `eval` | — |
| **WSL boundary** | — | — | All paths/executables escaping the Linux filesystem |
| Config writes (`~/.claude/`) | `git show origin/main:` from canonical repo; `gh api` from canonical repo | — | All other methods |

All guards use `(^|[;&|]\s*)cmd\b` patterns to catch commands both at the start of a line and when chained via `&&`, `;`, or `||`.

Authorized git push phrases (case-insensitive): `push for me`, `commit and push`, `please push`, `push my changes`.

## What `check-settings-version.sh` does

- Fires once per session (keyed to the transcript path via a flag file in `$XDG_RUNTIME_DIR` or `~/.claude/`, with `chmod 600`).
- **Validates all config values** from files before use — `tracking_ref` against `^[a-zA-Z0-9._/-]+$`, `online_repo_slug` against `^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$`, versions against `^[0-9]+\.[0-9]+\.[0-9]+$`. Invalid values are refused with a warning.
- Reads the installed version from `~/.claude/settings-version`.
- Reads the tracking ref from `~/.claude/settings-repo-ref` (defaults to `main` when absent).
- **Online check (primary):** If `~/.claude/settings-repo-url` is set, fetches `VERSION` via `gh api` from the GitHub repo's configured ref.
- **Git fetch (fallback):** If the GitHub API method is not configured or fails, and `~/.claude/settings-repo-path` points to a valid local clone, fetches via `git fetch origin <ref> --depth=1` and reads the `VERSION` file from that ref.
- Reads the local branch version from `$REPO_DIR/global-settings/VERSION` (if a local repo is configured).
- Compares all versions using semver and prints a colored status panel to stderr (visible in the terminal/CLI).
- Always injects a session-start message into Claude's context via stdout — "up to date", "update required", or "configuration error" — which Claude relays at the top of its first response.
- Never silently skips: configuration issues (missing config files, unreachable remote, `gh` not installed) are shown in the panel and forwarded to Claude.

## Relationship to this repo's `.claude/settings.json`

Project `settings.json` in `.claude/` enables MCP servers and project-specific permissions. That is separate from the global Bash policy above:

1. Global `~/.claude/settings.json` + hooks for Bash safety and version checking.
2. Project `.claude/settings.json` (and `settings.local.json` if used) for workspace-specific MCP.

## Verification

After installing (see [README](../../global-settings/README.md)), verify:
- `curl` should prompt (not auto-approved)
- `find . -exec` should prompt
- `rm -rf` should be hard-blocked
- Status panel appears at session start
