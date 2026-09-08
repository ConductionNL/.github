# Global Claude Code settings (`~/.claude`)

These are **mandatory** settings for anyone working on Conduction projects with Claude Code. They enforce a read-first, write-with-approval policy at the user level, ensuring Claude cannot perform destructive operations without explicit confirmation. They also version-check themselves at the start of each session so you always know when an update is available.

Project files under `.claude/` in this repo (for example `settings.json` with MCP allowlists) **complement** this; they do not replace the global policy.

## Versioned canonical files

The canonical files live under **[`global-settings/`](../../global-settings/)**. The version is tracked in [`global-settings/VERSION`](../../global-settings/VERSION).

| File                                                                                           | Install as                                  |
| ---------------------------------------------------------------------------------------------- | ------------------------------------------- |
| [`global-settings/settings.json`](../../global-settings/settings.json)                         | `~/.claude/settings.json`                   |
| [`global-settings/block-write-commands.sh`](../../global-settings/block-write-commands.sh)     | `~/.claude/hooks/block-write-commands.sh`   |
| [`global-settings/block-config-tool-writes.sh`](../../global-settings/block-config-tool-writes.sh) | `~/.claude/hooks/block-config-tool-writes.sh` |
| [`global-settings/check-settings-version.sh`](../../global-settings/check-settings-version.sh) | `~/.claude/hooks/check-settings-version.sh` |
| [`global-settings/sound-notify.sh`](../../global-settings/sound-notify.sh)                     | `~/.claude/hooks/sound-notify.sh` (optional sound wrapper — silent by default; see [Optional: notification sounds](#optional-notification-sounds-opt-in)) |

## Install / update

See [`global-settings/README.md`](../../global-settings/README.md) for install commands, update instructions, and the VERSION bump policy.

## Session-start status panel

At the start of every Claude session, a live status panel is printed to the terminal (stderr):

```
┌──────────────────────────────────────────────┐
│     Global Claude Settings Status            │
└──────────────────────────────────────────────┘
  Installed   : v2.0.0  ✓
  Local repo  : main                 @ v2.0.0
  Online      : v2.0.0  (via GitHub)
```

Color coding:

- **Green** — version matches / up to date
- **Yellow** — local branch is ahead of installed (informational only)
- **Red** — installed is behind online main (update required)

The "Online" line shows the fetch method used:

- **(via GitHub)** — fetched directly from GitHub using `curl` against the raw URL (primary method, uses `settings-repo-url`)
- **(via git fetch)** — fetched from `origin/main` of the local repo clone (fallback method, uses `settings-repo-path`)

If no local repo is configured, "Local repo" shows "(not configured)" instead of branch info.

If configuration issues are detected (missing config files, unreachable remote, `curl` not installed), they are shown in red below the panel — never silently skipped.

> **Note:** The terminal panel is only visible when using Claude Code in the terminal (CLI). In the VS Code extension, hook stderr is not shown as a visible banner — see the Claude chat message below instead.

## Session-start message in Claude chat

In addition to the terminal panel, the hook always injects a message into Claude's context at the start of every session. Claude will relay this at the top of its first response:

**Settings up to date:**

> New session started — Global Claude Settings checked. Settings are up to date (v2.3.1, via GitHub).

The source name is included so a stale mirror is visible at a glance: `GitHub` for the raw-URL method; for the git-fetch fallback the host is inferred from the local clone's `origin` URL (`GitHub` / `GitLab` / `Codeberg` / `git origin`).

**Update required** (prominently displayed, cannot be missed):

> NEW SESSION — GLOBAL CLAUDE SETTINGS: UPDATE REQUIRED
> Installed: v0.1.0 (outdated) | Latest: v1.0.0 (on origin/main)
> Say "update my global settings to 1.0.0" to apply the update.

**Configuration error** (prominently displayed):

> NEW SESSION — GLOBAL CLAUDE SETTINGS: CONFIGURATION ERROR
> [description of the issue]

## Online version checking

The version check supports two methods for fetching the online version, tried in order:

### 1. GitHub raw URL (primary — recommended)

If `~/.claude/settings-repo-url` contains a GitHub repo slug (e.g. `ConductionNL/.github`), the hook fetches `VERSION` via `curl` from `https://raw.githubusercontent.com/<slug>/<ref>/global-settings/VERSION` (default ref: `main`). This method:

- Does **not** require a local clone of the repo
- Uses unauthenticated `curl` against the public raw URL (no token needed for public repos)
- Is faster than `git fetch` (single HTTP request)
- Falls back gracefully if `curl` is not installed or the HTTP fetch fails

The GitHub `raw.githubusercontent.com/<slug>/<ref>/` path resolves to the tip of `<ref>` — tag and SHA tracking are not supported via this method; configure `settings-repo-path` and use the git-fetch fallback for those cases.

### 2. Git fetch (fallback)

If the GitHub method is not configured or fails, and `~/.claude/settings-repo-path` points to a valid local clone, the hook falls back to `git fetch origin <ref> --depth=1` followed by `git show origin/<ref>:...`. This is the original method.

### Tracking a non-default branch

By default, both methods track the `main` branch. To track a different branch, write it to `~/.claude/settings-repo-ref`:

```bash
echo "feature/claude-code-tooling" > ~/.claude/settings-repo-ref
```

When absent, the ref defaults to `main`.

### Configuration options

| Config file                    | Required?              | Purpose                                                    |
| ------------------------------ | ---------------------- | ---------------------------------------------------------- |
| `~/.claude/settings-repo-url`  | Optional (recommended) | GitHub repo slug for online raw-URL check                  |
| `~/.claude/settings-repo-path` | Optional (fallback)    | Path to the root of the canonical repo for git-based check |
| `~/.claude/settings-repo-ref`  | Optional               | Branch to track (defaults to `main`)                       |

You can configure:

- **Both URL and path** (recommended): GitHub is tried first, local git as fallback
- **Only `settings-repo-url`**: Works without any local clone; no fallback if GitHub is unreachable
- **Only `settings-repo-path`**: Original behavior; requires a local clone
- **Neither**: Version check cannot run; a configuration warning is shown

## File locations

| Path                                            | Role                                                                                                            |
| ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `~/.claude/settings.json`                       | User permissions allowlist, hooks (`PreToolUse`, `UserPromptSubmit`, `PermissionRequest`, `Stop`) |
| `~/.claude/hooks/block-write-commands.sh`       | Hook script invoked for every **Bash** tool use before it runs                                                  |
| `~/.claude/hooks/block-config-tool-writes.sh`   | Hook script invoked for every **Write/Edit/MultiEdit** tool use before it runs                                  |
| `~/.claude/hooks/check-settings-version.sh`     | Hook script that shows the status panel and warns on version mismatch                                           |
| `~/.claude/hooks/sound-notify.sh`               | Optional sound-notification wrapper. Reads `~/.claude/sound-config.sh` and plays a sound on question / permission / stop events (v2.2.0+) |
| `~/.claude/sound-config.sh`                     | **User-editable, not `chattr`-locked.** Absent by default (opt-in). Toggles sounds and points at sound files    |
| `~/.claude/hooks/user-hooks-dispatch.sh`        | Per-user hook dispatcher. Registered once for every Claude Code event; reads `~/.claude/user-hooks.json` and fires the hooks listed there (v2.4.0+) |
| `~/.claude/user-hooks.json`                     | **User-owned, Claude-blocked.** Absent by default (opt-in). Lists the user's private hooks. Never overwritten by a settings update; deny-listed + guard-hook protected, optionally `chattr +i` |
| `~/.claude/settings-version`                    | Installed version (semver, matches repo `VERSION`)                                                              |
| `~/.claude/settings-repo-url`                   | GitHub repo slug for online version checking (e.g. `ConductionNL/.github`)                                      |
| `~/.claude/settings-repo-path`                  | Absolute path to the root of the canonical repo (fallback for git-based check)                                  |
| `~/.claude/settings-repo-ref`                   | Branch/tag/SHA to track for version checks (defaults to `main`)                                                 |

## Shape of `~/.claude/settings.json`

### 1. `permissions.deny`

Hard-blocked patterns — Claude cannot perform these even with user approval:

- **Config files**: `Edit`/`Write` of `~/.claude/settings.json`, `hooks/*`, `settings-version`, `settings-repo-path`, `settings-repo-url`, `settings-repo-ref`, `user-hooks.json`
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

### 5. `hooks.PreToolUse` — `AskUserQuestion` matcher (sound wrapper)

```json
{
  "matcher": "AskUserQuestion",
  "hooks": [{ "type": "command", "command": "bash ~/.claude/hooks/sound-notify.sh question" }]
}
```

Fires when Claude uses the `AskUserQuestion` tool. Wrapper is silent unless the user has opted in — see [Optional: notification sounds](#optional-notification-sounds-opt-in).

### 6. `hooks.PermissionRequest`

```json
"PermissionRequest": [
  {
    "hooks": [{ "type": "command", "command": "bash ~/.claude/hooks/sound-notify.sh permission" }]
  }
]
```

Fires when Claude shows an allow/deny permission prompt. (v2.2.0 used `Notification` for this — empirical testing on Claude Code showed `PermissionRequest` is the actual event name; fixed in v2.2.2.)

### 7. `hooks.Stop`

```json
"Stop": [
  {
    "hooks": [{ "type": "command", "command": "bash ~/.claude/hooks/sound-notify.sh stop" }]
  }
]
```

Fires when Claude finishes its turn.

### 8. `hooks.*` — `user-hooks-dispatch.sh` (per-user custom hooks, v2.4.0+)

Every hook event in the shared `settings.json` carries **one** extra entry that hands off to a dispatcher:

```json
"UserPromptSubmit": [
  { "hooks": [{ "type": "command", "command": "bash ~/.claude/hooks/check-settings-version.sh" }] },
  { "hooks": [{ "type": "command", "command": "bash ~/.claude/hooks/user-hooks-dispatch.sh UserPromptSubmit" }] }
]
```

The same pattern is repeated for `PreToolUse`, `PostToolUse`, `SessionStart`, `PermissionRequest`, `Stop`, `SubagentStop`, `PreCompact` and `Notification` — the event name is passed as `$1`.

**Why a dispatcher instead of editing `settings.json`?** The shared `settings.json` is copy-overwritten on every version update, so any hook a user adds there is wiped out on the next "update my global settings". The dispatcher decouples the two: the shared file only ever holds the dispatcher registration, and the actual per-user hook list lives in `~/.claude/user-hooks.json`, which an update never touches.

**How it works at runtime.** The dispatcher reads `~/.claude/user-hooks.json`, picks the array under the key matching `$1`, and for each entry:

1. Applies the optional `matcher` (anchored ERE against `tool_name` — only meaningful for `PreToolUse` / `PostToolUse`; ignored for the other events).
2. Runs `command` with the original hook JSON payload on stdin.
3. Forwards the hook's stdout back to Claude Code (so a `UserPromptSubmit` user hook can inject prompt context exactly like a shared one).
4. Propagates **exit 2** (hard-deny) immediately. Swallows every other non-zero exit with a stderr warning — a broken personal hook can never wedge a session.

If the file is absent, empty, or malformed, the dispatcher exits 0 silently.

**Schema of `~/.claude/user-hooks.json`:**

```json
{
  "PreToolUse":        [ { "matcher": "Bash", "command": "bash ~/my-hooks/extra-guard.sh" } ],
  "PostToolUse":       [],
  "UserPromptSubmit":  [ { "command": "bash ~/.claude/projects/<slug>/plans/hooks/plan-context.sh" } ],
  "SessionStart":      [],
  "PermissionRequest": [],
  "Stop":              [ { "command": "bash ~/my-hooks/notify-done.sh" } ],
  "SubagentStop":      [],
  "PreCompact":        [],
  "Notification":      []
}
```

`global-settings/user-hooks.example.json` ships this skeleton plus a `$examples` block with worked entries; copy it into place and fill it in.

**Enabling** (once, in your own terminal):

```bash
cp "$REPO_ROOT/global-settings/user-hooks.example.json" ~/.claude/user-hooks.json
chmod 600 ~/.claude/user-hooks.json
sudo chattr +i ~/.claude/user-hooks.json        # recommended, mirrors the other locked files
```

Restart Claude Code or run `/hooks`. From then on your hooks fire alongside the shared ones, and survive every settings update.

**Claude is blocked from editing `user-hooks.json`.** A user hook can register itself in front of every tool call, so letting Claude write this file would hand it a way to weaken the shared guards from inside a session. The file therefore sits under the same three protection layers as the other config files: the `permissions.deny` list, the protected-path regex in `block-config-tool-writes.sh` and `block-write-commands.sh`, and (recommended) `chattr +i`. Users edit it by hand — the `sudo chattr -i … / edit / sudo chattr +i …` dance is the same as for `settings.json`.

**Disabling:** empty the arrays, or delete the file. The dispatcher exits 0 in both cases.

### 9. MCP servers — not configured here

`settings.json` does not read an `mcpServers` key ([Claude Code docs](https://code.claude.com/docs/en/debug-your-config#check-common-causes)), so MCP servers are **not** part of the global settings. Versions up to 2.4.0 shipped a dead `mcpServers` block with 7 Playwright browsers; it never loaded anything and was removed in 2.4.1. Configure MCP servers at one of the two supported scopes instead:

- **Project scope** — `.mcp.json` at the repository root, committed so the whole team gets the same servers. Hydra ships one with the 7-browser pool; a workspace that symlinks Hydra's `.claude/skills` symlinks its `.mcp.json` the same way. See [playwright-setup.md](playwright-setup.md).
- **User scope** — `claude mcp add --scope user …`, stored in `~/.claude.json` and loaded in every project on your machine. See [playwright-setup.md → User scope](playwright-setup.md#user-scope-all-projects-on-this-machine).

When both define the same server name, the project-scope entry wins.

---

## What `block-write-commands.sh` does

- Reads **JSON from stdin** once into a variable, then extracts `cmd` and `transcript_path`.
- On deny, prints `permissionDecision: "deny"` JSON. On ask, prints `permissionDecision: "ask"` JSON. On allow, exits `0`.

| Area                         | Allowed silently                                                          | Prompts for approval                                                    | Hard blocked                                        |
| ---------------------------- | ------------------------------------------------------------------------- | ----------------------------------------------------------------------- | --------------------------------------------------- |
| **curl**                     | —                                                                         | All curl write commands (data/output flags); canonical GitHub raw URL passes when wrapped in a config-file write | —                                                   |
| **gh api**                   | —                                                                         | All gh api commands (not auto-approved)                                 | —                                                   |
| **git push**                 | Last user message contains authorized phrase                              | —                                                                       | Blocked otherwise                                   |
| **git -C**                   | Read-only subcommands                                                     | Write subcommands, branch/remote writes                                 | `push` (phrase-authorized)                          |
| **git branch** (bare)        | `--list`, `-a`, `-v` (auto-approved)                                      | `-d/-D/-m/-M/-c/-C`, `--delete`, `--move`, `--copy`                     | —                                                   |
| **git remote** (bare)        | `-v`, `show` (auto-approved)                                              | `add`, `remove`, `rename`, `set-url`, `prune`, `update`                 | —                                                   |
| **env**                      | `env` alone or `VAR=value`                                                | Using `env` to execute another command                                  | —                                                   |
| **date**                     | Display time                                                              | —                                                                       | `-s` / `--set` (system clock)                       |
| **cat**                      | Normal stdout                                                             | Shell redirection `>` / `>>`                                            | —                                                   |
| **find**                     | Normal traversal                                                          | `-delete`, `-exec`, `-execdir`                                          | —                                                   |
| **sort**                     | Normal sort                                                               | `-o` / `--output`, shell `>` / `>>`                                     | —                                                   |
| **awk**                      | —                                                                         | All awk commands (not auto-approved); `system()` and file output caught | —                                                   |
| **hostname**                 | Read hostname                                                             | Setting a new hostname (bare name argument)                             | —                                                   |
| **rm**                       | —                                                                         | All `rm` commands                                                       | `rm -rf` / `rm -Rf` (deny-list)                     |
| **ln**                       | —                                                                         | All `ln` commands                                                       | Symlinks/hardlinks to `~/.claude/`                  |
| **sed -i**                   | —                                                                         | In-place file editing                                                   | —                                                   |
| **chown**                    | —                                                                         | All `chown` commands                                                    | —                                                   |
| **install**                  | —                                                                         | All `install` commands                                                  | —                                                   |
| **Pipe-to-shell**            | —                                                                         | `\| bash`, `\| sh`, `base64 -d`, `eval`                                 | —                                                   |
| **WSL boundary**             | —                                                                         | —                                                                       | All paths/executables escaping the Linux filesystem |
| Config writes (`~/.claude/`) | `git show origin/main:` from canonical repo; `curl` from canonical GitHub raw URL   | —                                                                       | All other methods                                   |

Most guards use `(^|[;&|]\s*)cmd\b` patterns to catch commands both at the start of a line and when chained via `&&`, `;`, or `||`. The exception is the canonical-source check for config-file writes (Method 2 — GitHub `curl`), which validates via a URL-prefix match rather than a segment-boundary anchor, and is additionally hardened by a decoy-detection check that rejects any non-canonical http(s) URL present in the same command.

Authorized git push phrases (case-insensitive): `push for me`, `commit and push`, `please git push`, `push my changes`.

## What `check-settings-version.sh` does

- Fires once per session (keyed to the transcript path via a flag file in `$XDG_RUNTIME_DIR` or `~/.claude/`, with `chmod 600`).
- **Validates all config values** from files before use — `tracking_ref` against `^[a-zA-Z0-9._/-]+$`, `online_repo_slug` against `^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$`, versions against `^[0-9]+\.[0-9]+\.[0-9]+$`. Invalid values are refused with a warning.
- Reads the installed version from `~/.claude/settings-version`.
- Reads the tracking ref from `~/.claude/settings-repo-ref` (defaults to `main` when absent).
- **Online check (primary):** If `~/.claude/settings-repo-url` is set, fetches `VERSION` via `curl` from the GitHub raw URL `https://raw.githubusercontent.com/<slug>/<ref>/global-settings/VERSION`.
- **Git fetch (fallback):** If the GitHub method is not configured or fails, and `~/.claude/settings-repo-path` points to a valid local clone, fetches via `git fetch origin <ref> --depth=1` and reads the `VERSION` file from that ref.
- Reads the local branch version from `$REPO_DIR/global-settings/VERSION` (if a local repo is configured).
- Compares all versions using semver and prints a colored status panel to stderr (visible in the terminal/CLI).
- Always injects a session-start message into Claude's context via stdout — "up to date", "update required", or "configuration error" — which Claude relays at the top of its first response.
- Never silently skips: configuration issues (missing config files, unreachable remote, `curl` not installed) are shown in the panel and forwarded to Claude.

## Optional: notification sounds (opt-in)

Since v2.2.0 the shared settings ship a lightweight wrapper (`sound-notify.sh`) that can play a sound on three events. **It is silent by default** — no sound plays until the user opts in by creating `~/.claude/sound-config.sh`.

### How it is wired

Three hook entries in `settings.json` invoke the same wrapper with different arguments:

| Event                                | Wrapper argument | Fires when                                          |
| ------------------------------------ | ---------------- | --------------------------------------------------- |
| `PreToolUse` matcher `AskUserQuestion` | `question`     | Claude asks you a multiple-choice question          |
| `PermissionRequest`                  | `permission`     | Claude shows an allow/deny permission prompt        |
| `Stop`                               | `stop`           | Claude finishes its turn                            |

### What the wrapper does

- Exits `0` immediately if the event arg is not one of `question` / `permission` / `stop`.
- Exits `0` immediately if `~/.claude/sound-config.sh` does not exist.
- Sources the config file into whitelisted variables only — `SOUND_ENABLED`, `SOUND_QUESTION_FILE`, `SOUND_PERMISSION_FILE`, `SOUND_STOP_FILE`. It does **not** eval command strings.
- If `SOUND_ENABLED != 1`, exits `0`.
- Detects an available player in order: `paplay` → `afplay` → `aplay` → `powershell.exe` (WSL).
- Plays the sound in the background so the hook never blocks Claude's turn. Detaches the audio player from the hook's process group (`setsid` when available, otherwise `nohup`) so short sounds (<~500ms) survive Claude Code tearing down the hook — a bare `&` + `disown` is not enough. (Fixed in v2.2.1; observed in v2.2.0 as: `complete.oga` played, `dialog-information.oga` was silent.)
- Always exits `0` — a broken sound never delays Claude.

### Enabling sounds

```bash
# On minimal Linux / WSL2 Ubuntu installs the freedesktop sound theme isn't
# installed by default. Install it so the shipped defaults exist:
sudo apt install sound-theme-freedesktop

cp global-settings/sound-config.sh.example ~/.claude/sound-config.sh
${EDITOR:-nano} ~/.claude/sound-config.sh   # flip SOUND_ENABLED=1
```

The example ships **Linux paths as the default** (freedesktop sound theme) — most likely to work for the standard Conduction WSL2 Ubuntu setup once the theme package is installed. macOS and WSL-Windows alternatives are commented in place if you need to switch. The `sound-theme-freedesktop` apt install is only needed if you keep the shipped Linux paths; point the `SOUND_*_FILE` variables at your own files and you can skip it.

### Disabling sounds

```bash
# Flip the toggle:
sed -i 's/^SOUND_ENABLED=1/SOUND_ENABLED=0/' ~/.claude/sound-config.sh
# Or fully remove:
rm ~/.claude/sound-config.sh
```

### What's blocked from Claude, what isn't

| File                              | Deny-list rule                  | Content hook            | `chattr +i`             |
| --------------------------------- | ------------------------------- | ----------------------- | ----------------------- |
| `~/.claude/hooks/sound-notify.sh` | ✅ `Edit/Write(~/.claude/hooks/*)` | ✅ matches `hooks/?` regex | ✅ applied on install     |
| `~/.claude/sound-config.sh`       | ❌ (intentional — user preference) | ❌ (not in protected list) | ❌ (not applied)         |

The wrapper is protected the same way every other hook script is — Claude cannot Edit or Write it, cannot use a Bash `cat > ...` trick to overwrite it, and the kernel refuses even root writes while the immutable bit is set.

The config file is intentionally **not** protected because:

- It's a **user preference file**, not security policy. It never affects what commands Claude can run.
- The wrapper reads only whitelisted file-path variables from it — it never `eval`s command strings, so tampering with the file cannot produce shell injection.
- Locking it would force a `sudo chattr -i / +i` dance for every sound tweak, defeating the point of a user-configurable feature.
- The [`update-config` skill](commands.md) uses `Edit`/`Write` to modify `~/.claude/` config on user request; keeping `sound-config.sh` unprotected lets that skill help users enable/tune sounds naturally.

If you personally want to prevent Claude from touching `sound-config.sh` in your local setup, add `"Edit(~/.claude/sound-config.sh)"` and `"Write(~/.claude/sound-config.sh)"` to a **project** `.claude/settings.json` deny list — that overlays on top of the global settings without needing a global settings change.

## Relationship to this repo's `.claude/settings.json`

Project `settings.json` in `.claude/` enables MCP servers and project-specific permissions. That is separate from the global Bash policy above:

1. Global `~/.claude/settings.json` + hooks for Bash safety and version checking.
2. Project `.claude/settings.json` (and `settings.local.json` if used) for workspace-specific MCP, per-project permission grants, and your per-repo model default (see [Troubleshooting](#troubleshooting)).

## Verification

After installing (see [README](../../global-settings/README.md)), verify:

- `curl` should prompt (not auto-approved)
- `find . -exec` should prompt
- `rm -rf` should be hard-blocked
- Status panel appears at session start

## Troubleshooting

### `/model` or the model picker fails with `EPERM: operation not permitted, open '~/.claude/settings.json'`

**Symptom.** Switching models in the VSCode extension — via the model picker or by typing `/model <name>` — pops an error notification:

```
Failed to set model: EPERM: operation not permitted, open '/home/<user>/.claude/settings.json'
```

**Cause.** This is the kernel immutable lock (protection layer 4 from the [README's security model](../../global-settings/README.md#security-model--defense-in-depth)) doing exactly what it is meant to do — it just has a side effect the install steps don't mention. The VSCode extension persists every model switch by rewriting `~/.claude/settings.json` with `{"model": "<name>"}`. That write is hard-wired to the user-settings file; it does not consult the project or local settings scopes. With the immutable bit set, the kernel refuses the write and the extension surfaces the `EPERM`.

What still works and what does not, while the lock is on:

| Action                                 | Effect                                                                                                                                                                                                                                  |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Typing `/model <name>` in the chat     | **Works for the session.** Claude Code applies the switch in memory, then tries to persist it; when the locked file refuses the write it reports "Set model to … for this session only" and moves on. Nothing is lost.                  |
| The model picker in the UI             | **Does nothing, and this is what raises the toast.** The extension writes the settings file *before* pushing the switch to the CLI, so the failed write aborts the switch. It is the only code path that reports `Failed to set model`. |
| Claude Code's startup model migrations | Silently log `Failed to migrate … model setting` — harmless.                                                                                                                                                                            |

**Fix — pin your default model in project-local settings (recommended).** `model` is a regular settings key ("Override the default model used by Claude Code") and the local scope takes precedence over the user scope, so the shared locked file never needs to change. Pin the model you want *every* session to start on — `opus` is the sensible default; more expensive models are then an explicit per-session choice (next paragraph):

```bash
# Run from anywhere inside the repo you work in.
# Claude Code resolves the local-settings scope to the *git root*, not the cwd
# (observed with Claude Code 2.1.263, 2026-09) — so write it there.
# In a linked git worktree, --show-toplevel gives the worktree while Claude Code's
# canonical scope is the main repo root (git rev-parse --git-common-dir). Both are
# read, but the canonical root is the durable place to put it.
ROOT="$(git rev-parse --show-toplevel)"
mkdir -p "$ROOT/.claude"
cat > "$ROOT/.claude/settings.local.json" <<'JSON'
{
  "model": "opus"
}
JSON
```

Append `[1m]` to the value (`"opus[1m]"`) if you want the 1M-context variant — a bare `"opus"` in the local scope overrides an `"opus[1m]"` in the user scope and silently drops you back to the standard context window.

Merge the key into the file if it already exists (Claude Code stores per-project permission grants there too). The file is meant to stay out of git — check with `git check-ignore -v "$ROOT/.claude/settings.local.json"`; add `**/.claude/settings.local.json` to your global ignore file (`~/.config/git/ignore`) if it isn't.

This file is **not** covered by the deny list, the guard hooks, or the immutable lock — all three protect `~/.claude/` only, so Claude can edit it. That is deliberate, for the same reason as `sound-config.sh` (see [What's blocked from Claude, what isn't](#whats-blocked-from-claude-what-isnt)): your model choice is a cost-and-capability preference, not security policy, and it never affects which commands Claude may run. The deny rules and hooks stay in the kernel-locked user file.

Restart the session and verify which model is actually served:

```bash
# The VSCode extension ships its own CLI and does not put `claude` on your PATH.
# If `command -v claude` comes up empty, point at the bundled binary instead:
CLAUDE="$(command -v claude || echo ~/.vscode-server/extensions/anthropic.claude-code-*/resources/native-binary/claude)"
"$CLAUDE" -p "Reply with exactly the word ok" --output-format json | jq '.modelUsage | keys'
```

The result should list the model you pinned (e.g. `["claude-opus-5"]`). Swapping the value to `"sonnet"` and re-running is a quick control test that the file is what decides.

`"env": {"ANTHROPIC_MODEL": "opus"}` in the same file also works, and takes precedence over `model` rather than being equivalent to it. Prefer `model`: it is a first-class settings key, so `/model` reports it back to you as the workspace default.

**Switching to another model for one session (e.g. Fable).** Type the command in the chat — don't use the picker:

```
/model fable
```

The CLI confirms with "Set model to Fable 5.1 for this session only" and the switch is live. The `Failed to set model: EPERM` toast that follows is the extension's failed attempt to *persist* the choice — ignore it; nothing was lost, and the next session starts on your pinned default again. That is the intended behaviour under this setup: the default stays the cheaper model, using a heavier one is a deliberate, visible act each time.

**Fix — one-off switch.** If you only need to change the persisted model once, run the unlock step from [README → Updating](../../global-settings/README.md#updating) in your own terminal, switch the model in Claude Code, then run the relock step. Don't skip the relock.

**What not to do.**

- Don't leave the lock off "because the picker is annoying" — that disarms the only protection layer that survives a compromised hook chain.
- Don't add `model` to the shared `global-settings/settings.json`. It is a per-user preference, it would be overwritten on every settings update, and the file is still locked — the picker would keep failing.
