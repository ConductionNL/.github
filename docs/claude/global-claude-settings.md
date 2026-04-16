# Global Claude Code settings (`~/.claude`)

These are **mandatory** settings for anyone working on Conduction projects with Claude Code. They enforce a read-first, write-with-approval policy at the user level, ensuring Claude cannot perform destructive operations without explicit confirmation. They also version-check themselves at the start of each session so you always know when an update is available.

Project files under `.claude/` in this repo (for example `settings.json` with `enableAllProjectMcpServers` and MCP allowlists) **complement** this; they do not replace the global policy.

## Versioned canonical files

The canonical files live under **[`global-settings/`](../global-settings/)**. The version is tracked in [`global-settings/VERSION`](../global-settings/VERSION).

| File | Install as |
|------|------------|
| [`global-settings/settings.json`](../global-settings/settings.json) | `~/.claude/settings.json` |
| [`global-settings/block-write-commands.sh`](../global-settings/block-write-commands.sh) | `~/.claude/hooks/block-write-commands.sh` |
| [`global-settings/check-settings-version.sh`](../global-settings/check-settings-version.sh) | `~/.claude/hooks/check-settings-version.sh` |

## Install / update on a new machine

Run the following from the root of the `apps-extra` repo:

```bash
REPO_CLAUDE="$(pwd)/.claude"

mkdir -p ~/.claude/hooks

# Core settings and hooks
cp "$REPO_CLAUDE/global-settings/settings.json" ~/.claude/settings.json
cp "$REPO_CLAUDE/global-settings/block-write-commands.sh" ~/.claude/hooks/block-write-commands.sh
cp "$REPO_CLAUDE/global-settings/check-settings-version.sh" ~/.claude/hooks/check-settings-version.sh
chmod +x ~/.claude/hooks/block-write-commands.sh ~/.claude/hooks/check-settings-version.sh

# Version tracking
cp "$REPO_CLAUDE/global-settings/VERSION" ~/.claude/settings-version
echo "$REPO_CLAUDE" > ~/.claude/settings-repo-path
```

Requirements: **`jq`** and **`md5sum`** on `PATH`. Restart Claude Code after installing.

If `~` is not expanded in hook commands on your system, replace `~/.claude/hooks/…` with absolute paths in `~/.claude/settings.json`.

## Session-start status panel

At the start of every Claude session, a live status panel is printed to the terminal (stderr):

```
┌──────────────────────────────────────────────┐
│     Global Claude Settings Status            │
└──────────────────────────────────────────────┘
  Installed   : v1.0.0  ✓
  Local repo  : master               @ v1.0.0
  Online      : v1.0.0
```

Color coding:
- **Green** — version matches / up to date
- **Yellow** — local branch is ahead of installed (informational only, no action needed)
- **Red** — installed is behind online main (update required)

If configuration issues are detected (missing `settings-repo-path`, missing `VERSION` file, unreachable remote), they are shown in red below the panel — never silently skipped.

> **Note:** The terminal panel is only visible when using Claude Code in the terminal (CLI). In the VS Code extension, hook stderr is not shown as a visible banner — see the Claude chat message below instead.

## Session-start message in Claude chat

In addition to the terminal panel, the hook always injects a message into Claude's context at the start of every session. Claude will relay this at the top of its first response:

**Settings up to date:**
> New session started — Global Claude Settings checked. ✅ Settings are up to date (v1.0.0).

**Update required** (prominently displayed, cannot be missed):
> ⚠️ NEW SESSION — GLOBAL CLAUDE SETTINGS: UPDATE REQUIRED
> Installed: v0.1.0 ❌ | Latest: v1.0.0 ✅
> Say "update my global settings to 1.0.0" to apply the update.

**Configuration error** (prominently displayed):
> 🚨 NEW SESSION — GLOBAL CLAUDE SETTINGS: CONFIGURATION ERROR
> ❌ [description of the issue]

## Keeping settings up to date

When the online (origin/main) version is bumped, Claude displays a prominent warning at the start of its first response in the new session.

To update, tell Claude: **"update my global settings to [version]"** and Claude will pull all files directly from `origin/main` using `git show` — not from your local branch. This ensures you always get the exact online version regardless of which branch your local repo is on.

> **Note:** The version check fetches `VERSION` from `origin/main` via `git fetch`. It checks the local repo's configured remote, not a separate URL. If your remote is the upstream nextcloud/server and the global-settings aren't tracked there, the online check will warn about that too.

### ⚠️ VERSION bump required on every change

**Any commit that modifies a file in `global-settings/` MUST also increment `VERSION`.** Without a bump, users will not be warned to update and their installed settings will silently fall behind.

Semver rules:
- `1.0.0 → 1.1.0` — new permissions, guards, or behavior added
- `1.0.0 → 2.0.0` — breaking change requiring manual migration

Run `/verify-global-settings-version` before creating a PR to confirm the bump is correct.

## File locations

| Path | Role |
|------|------|
| `~/.claude/settings.json` | User permissions allowlist, `PreToolUse` + `UserPromptSubmit` hooks, optional `mcpServers` |
| `~/.claude/hooks/block-write-commands.sh` | Hook script invoked for every **Bash** tool use before it runs |
| `~/.claude/hooks/check-settings-version.sh` | Hook script that warns on version mismatch at session start |
| `~/.claude/settings-version` | Installed version (semver, matches repo `VERSION`) |
| `~/.claude/settings-repo-path` | Absolute path to `apps-extra/.claude/` — tells the version hook where to find the canonical `VERSION` file |

## Shape of `~/.claude/settings.json`

### 1. `permissions.allow`

List **Bash** permission patterns you want granted **without** prompting. Keep this aligned with the hook: anything you allow here should still pass `block-write-commands.sh`, or the hook will deny the command even if it is allowlisted.

Allowed categories (all read-only; write operations are gated by the hook):

- **Inspection**: `ls`, `cat`, `head`, `tail`, `wc`, `stat`, `file`, `du`, `df`, `pwd`, `tree`, `find`, `realpath`, `basename`, `dirname`
- **Text processing**: `diff`, `grep`, `egrep`, `awk`, `tr`, `sort`, `jq`, `cut`, `uniq`, `column`
- **System info**: `which`, `whoami`, `uname`, `ps`, `free`, `lsof`, `ss`, `id`, `groups`, `uptime`, `hostname`, `env`, `date`
- **Git (read-only)**: `git log`, `git status`, `git diff`, `git show`, `git blame`, `git ls-files`, `git rev-parse`, `git describe`, `git shortlog`, `git cat-file`, `git branch`, `git remote`, `git stash list`, `git config --list`
- **`git -C`**: allow `Bash(git -C:*)` so agents can run git in arbitrary directories; the hook restricts **which** `git -C …` invocations are safe
- **Docker (read)**: `docker ps`, `docker images`, `docker logs`, `docker inspect`, `docker stats`, `docker info`, `docker network ls/inspect`, `docker volume ls/inspect`, `docker compose ps/config`
- **GitHub CLI (read)**: `gh pr list/view/checks/diff`, `gh issue list/view`, `gh repo view`, `gh run list/view`, `gh release list/view`, `gh workflow list`
- **Package managers (read)**: `composer show/validate/diagnose/check-platform-reqs`, `npm list/outdated`, `pnpm list/outdated`, `yarn list`, `pip list/show/freeze`
- **PHP**: `php -l/-m/-i/--version`
- **HTTP / API (read; hook narrows further)**: `curl`, `gh api`

Do **not** put broad `Bash(*)` allow rules here.

### 2. `hooks.PreToolUse`

```json
"PreToolUse": [
  {
    "matcher": "Bash",
    "hooks": [{ "type": "command", "command": "bash ~/.claude/hooks/block-write-commands.sh" }]
  }
]
```

### 3. `hooks.UserPromptSubmit`

```json
"UserPromptSubmit": [
  {
    "hooks": [{ "type": "command", "command": "bash ~/.claude/hooks/check-settings-version.sh" }]
  }
]
```

### 4. `mcpServers` (optional)

7 Playwright browser instances (`browser-1` through `browser-7`). `browser-6` runs headed (no `--headless`). Adjust the count to match your actual usage.

---

## What `block-write-commands.sh` does

- Reads **JSON from stdin** once into a variable, then extracts `cmd` and `transcript_path`.
- On deny, prints `permissionDecision: "deny"` JSON. On ask, prints `permissionDecision: "ask"` JSON. On allow, exits `0`.

| Area | Allowed silently | Prompts for approval | Hard blocked |
|------|-----------------|---------------------|--------------|
| **curl** | GET without file output | Non-GET methods, data flags, `-o` / `--output` | — |
| **gh api** | GET | POST/PUT/PATCH/DELETE, `--input`, `--field` / `--raw-field` | — |
| **git push** | Last user message contains authorized phrase | — | Blocked otherwise |
| **git -C** | Read-only subcommands (`log`, `status`, `diff`, etc.) | Write subcommands, branch/remote writes, stash modifications, config writes | `push` (phrase-authorized) |
| **git branch** (bare) | Listing | `-d/-D/-m/-M/-c/-C`, `--delete`, `--move`, `--copy` | — |
| **git remote** (bare) | Listing, `show`, `get-url` | `add`, `remove`, `rename`, `set-url`, `prune`, `update` | — |
| **env** | `env` alone or `VAR=value` assignments | Using `env` to execute another command | — |
| **date** | Display time | — | `-s` / `--set` (system clock) |
| **cat** | Normal stdout | Shell redirection `>` / `>>` to a file | — |
| **find** | Normal path traversal | `-delete`, `-exec`, `-execdir` | — |
| **sort** | Normal sort to stdout | `-o` / `--output`, shell `>` / `>>` | — |
| **awk** | Normal processing | `print >` / `print >>` in script, shell `>` after script | — |
| **hostname** | Read current hostname (no args) | Setting a new hostname (bare name argument) | — |

Authorized git push phrases (case-insensitive): `push for me`, `commit and push`, `please push`, `push my changes`.

## What `check-settings-version.sh` does

- Fires once per session (keyed to the transcript path via `/tmp/` flag file).
- Reads the installed version from `~/.claude/settings-version`.
- Reads the local branch version from `$REPO_DIR/global-settings/VERSION` (repo path from `~/.claude/settings-repo-path`).
- Fetches the online version from `origin/main` via `git fetch --depth=1` and reads the `VERSION` file from that ref.
- Compares all three versions using semver and prints a colored status panel to stderr (visible in the terminal/CLI).
- Always injects a session-start message into Claude's context via stdout — "up to date", "update required", or "configuration error" — which Claude relays at the top of its first response.
- Never silently skips: configuration issues (missing `settings-repo-path`, missing `VERSION` file, unreachable remote) are shown in the panel and forwarded to Claude.

## Relationship to this repo's `.claude/settings.json`

Under `apps-extra/.claude/`, project `settings.json` can enable project MCP servers and list allowed MCP tool names. That is separate from the **global** Bash policy above. For a consistent setup, use both:

1. Global `~/.claude/settings.json` + hooks for Bash safety and version checking.
2. Project `.claude/settings.json` (and `settings.local.json` if used) for workspace-specific MCP and permissions.

## Checklist for a new machine

1. Run the install commands above (copies settings, hooks, version files).
2. Confirm `jq` and `md5sum` are on `PATH`.
3. Restart Claude Code so settings reload.
4. Test: a denied pattern (e.g. `curl -X POST`) should be blocked with a clear reason. A `find . -exec` should prompt for approval.
5. Verify the version hook fires: open a new session and confirm no warning (or update if one appears).
