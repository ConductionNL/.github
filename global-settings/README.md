# Global Claude Settings (mandatory, versioned)

These files define the **mandatory** user-level Claude Code configuration for all Conduction developers. Install them once per machine; the version-check hook will alert you at the start of each session when an update is available.

Current version: see [`VERSION`](VERSION)

## Files

| File                          | Install as                                    | Purpose                                                                                                                     |
| ----------------------------- | --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `settings.json`               | `~/.claude/settings.json`                     | Permissions allowlist + hooks                                                                                               |
| `block-write-commands.sh`     | `~/.claude/hooks/block-write-commands.sh`     | Guards Bash write operations, prompts for approval. Hard-blocks writes against production (`kubectl`/`oc`/`helm` on a `*-prod` namespace or context, v2.6.0) |
| `block-polling.sh`            | `~/.claude/hooks/block-polling.sh`            | Blocks hand-rolled waiting: CI watch commands, poll loops, long sleeps, idle heartbeats (velocity plan item 5, 2026-09-12)   |
| `block-config-tool-writes.sh` | `~/.claude/hooks/block-config-tool-writes.sh` | Guards Write/Edit/MultiEdit calls — denies tools that write to `~/.claude/` or produce scripts that would (added in v1.7.0) |
| `check-settings-version.sh`   | `~/.claude/hooks/check-settings-version.sh`   | Warns at session start if settings are outdated                                                                             |
| `sound-notify.sh`             | `~/.claude/hooks/sound-notify.sh`             | Optional notification-sound wrapper. Reads `~/.claude/sound-config.sh` and plays a sound on question / permission / stop events. Silent by default (added in v2.2.0)         |
| `user-hooks-dispatch.sh`      | `~/.claude/hooks/user-hooks-dispatch.sh`      | Reads `~/.claude/user-hooks.json` and executes per-user hooks for every Claude Code event. Lets each user register private hooks that survive a settings update (added in v2.4.0) |
| `VERSION`                     | `~/.claude/settings-version`                  | Installed version tracker (semver)                                                                                          |
| `CHANGELOG.md`                | not installed                                 | One sentence per version; shown in the update notice as "What this update adds" (added in v2.8.0)                          |
| `settings-repo-url.example`   | `~/.claude/settings-repo-url`                 | GitHub repo slug for online version checking                                                                                |
| `settings-repo-ref.example`   | `~/.claude/settings-repo-ref`                 | Branch to track (defaults to `main` when absent; the GitHub raw URL uses `raw.githubusercontent.com/<slug>/<ref>/`)         |
| `sound-config.sh.example`     | `~/.claude/sound-config.sh` (optional)        | Opt-in sound configuration. Only install if you want notification sounds. User-editable — **not** `chattr +i`-locked        |
| `user-hooks.example.json`     | `~/.claude/user-hooks.json` (optional)        | Per-user hook config. Copy this file, list your own hooks, done. The shared settings.json will never overwrite it. Claude is blocked from editing it (deny list + guard hooks) (added in v2.4.0) |

## Install

From the root of the `.github` repo (or wherever you cloned it):

```bash
REPO_ROOT="$(pwd)"

mkdir -p ~/.claude/hooks

cp "$REPO_ROOT/global-settings/settings.json" ~/.claude/settings.json
cp "$REPO_ROOT/global-settings/block-write-commands.sh" ~/.claude/hooks/block-write-commands.sh
cp "$REPO_ROOT/global-settings/block-polling.sh" ~/.claude/hooks/block-polling.sh
cp "$REPO_ROOT/global-settings/block-config-tool-writes.sh" ~/.claude/hooks/block-config-tool-writes.sh
cp "$REPO_ROOT/global-settings/check-settings-version.sh" ~/.claude/hooks/check-settings-version.sh
cp "$REPO_ROOT/global-settings/sound-notify.sh" ~/.claude/hooks/sound-notify.sh
cp "$REPO_ROOT/global-settings/user-hooks-dispatch.sh" ~/.claude/hooks/user-hooks-dispatch.sh
chmod +x ~/.claude/hooks/*.sh

cp "$REPO_ROOT/global-settings/VERSION" ~/.claude/settings-version
echo "$REPO_ROOT" > ~/.claude/settings-repo-path

# Online version checking via GitHub (recommended — no local repo required):
cp "$REPO_ROOT/global-settings/settings-repo-url.example" ~/.claude/settings-repo-url

# Optional: track a branch other than main (tag or SHA also accepted).
# Defaults to "main" when this file is absent.
# To track a specific branch, copy and edit:
# cp "$REPO_ROOT/global-settings/settings-repo-ref.example" ~/.claude/settings-repo-ref
# echo "feature/your-branch" > ~/.claude/settings-repo-ref

# Finally — apply the kernel-level immutable lock (v1.7.0+).
# This is the single piece of protection that no Claude command can bypass:
# even if every other guard fails, the kernel refuses the write.
# Pick ONE of the two lines. (A) runs as written; for (B), comment out the (A)
# line and uncomment the (B) line.
# (A) full lock — strongest, but the VSCode model picker then fails with EPERM:
sudo chattr +i ~/.claude/settings.json ~/.claude/hooks/*.sh ~/.claude/settings-version
# (B) lock without settings.json — the picker keeps working, but the main file
#     settings.json loses the kernel lock (a real risk, see "Updating" step 4):
# sudo chattr +i ~/.claude/hooks/*.sh ~/.claude/settings-version
```

Restart Claude Code after installing. Requires `jq`, `md5sum`, `curl`, and `chattr` on `PATH` (chattr is part of `e2fsprogs` — present on every standard Linux distro).

> **Known side effect of the lock — model switching.** The model picker fails with `Failed to set model: EPERM: operation not permitted` and does nothing, because the VSCode extension persists every switch by rewriting the locked `~/.claude/settings.json`. This is the lock working as designed, not a broken install. There are two ways out. The first is to relock with option (B), which takes the kernel lock off `settings.json` (see [Updating](#updating) step 4 for what that costs). The recommended way is to keep (A) and pin your default model in the project-local settings file, which the lock does not cover. Steps, verification and what not to do: [global-claude-settings.md → Troubleshooting](../docs/claude/global-claude-settings.md#troubleshooting).

## Online version checking

When `~/.claude/settings-repo-url` is configured, the version check uses GitHub's raw URL (`https://raw.githubusercontent.com/<slug>/<ref>/global-settings/VERSION`) as its primary method. This means you get accurate online version checks even without a local clone of the `.github` repo.

If GitHub is unreachable or `curl` is not installed, the hook falls back to `git fetch` via `~/.claude/settings-repo-path` (if configured).

The status panel at session start shows which method was used:

```
│     Global Claude Settings Status            │
  Installed  : v2.0.0 ✓
  Local repo : (not configured)
  Online     : v2.0.0  (via GitHub)
```

## Optional: notification sounds (opt-in)

Since v2.2.0 the shared settings wire three Claude Code events to a `sound-notify.sh` wrapper:

| Event                          | Wrapper argument | Fires when                                          |
| ------------------------------ | ---------------- | --------------------------------------------------- |
| `PreToolUse` / `AskUserQuestion` | `question`     | Claude asks you a multiple-choice question          |
| `PermissionRequest`            | `permission`     | Claude shows an allow/deny permission prompt        |
| `Stop`                         | `stop`           | Claude finishes its turn                            |

**Sounds are silent by default.** The wrapper only plays anything when a `~/.claude/sound-config.sh` file exists AND sets `SOUND_ENABLED=1` AND points at a readable sound file. Fresh installs make no noise unless the user explicitly turns them on.

### Enabling sounds

```bash
# On minimal Linux / WSL2 Ubuntu installs the freedesktop sound theme isn't
# installed by default. Install it so the shipped defaults exist:
sudo apt install sound-theme-freedesktop

# Copy the example config into place — this is the opt-in step.
cp "$REPO_ROOT/global-settings/sound-config.sh.example" ~/.claude/sound-config.sh

# Then edit it and flip SOUND_ENABLED=1. The Linux block is active by default;
# macOS and WSL alternatives are commented in place if you need to switch.
${EDITOR:-nano} ~/.claude/sound-config.sh
```

Restart Claude Code (or run `/hooks` to reload). Trigger any of the three events to verify.

> **Note:** the `sound-theme-freedesktop` apt package is only needed if you keep the shipped Linux defaults (`/usr/share/sounds/freedesktop/stereo/*.oga`). If you point the `SOUND_*_FILE` variables at your own files (e.g. under `/mnt/c/Windows/Media/*.wav` on WSL, or `/System/Library/Sounds/*.aiff` on macOS) you can skip the apt install.

### Why is the config file not `chattr +i`-locked?

- `~/.claude/sound-config.sh` is a **user preference file**, not a security-critical config. It never affects what commands Claude can run; the wrapper only reads file paths from it and invokes an audio player it detects at runtime (`paplay` / `afplay` / `aplay` / `powershell.exe`). Tampering with the file cannot produce shell injection.
- Locking it would defeat the point — every sound change would need the `sudo chattr -i / -i` dance.
- The `sound-notify.sh` wrapper itself **is** installed to `~/.claude/hooks/` and `chattr +i`-locked with the other hooks. Users configure via `sound-config.sh`; they do not modify the wrapper.

### Disabling sounds

Two ways:

```bash
# Method 1 — flip the toggle in the config file:
sed -i 's/^SOUND_ENABLED=1/SOUND_ENABLED=0/' ~/.claude/sound-config.sh

# Method 2 — delete the config file entirely. The wrapper exits 0 silently
# when the file is absent, so this fully disables the feature:
rm ~/.claude/sound-config.sh
```

The wrapper never blocks Claude regardless of state — a broken sound never delays a turn.

## Optional: per-user custom hooks (opt-in, added in v2.4.0)

The shared `settings.json` is copy-overwritten on every version update, so any per-user hook you add there is wiped out the next time you run "update my global settings". Since v2.4.0 that problem is decoupled cleanly:

- The shared `settings.json` registers a single **dispatcher** (`user-hooks-dispatch.sh`) once for every Claude Code hook event.
- The dispatcher reads **`~/.claude/user-hooks.json`** at runtime and fires whatever the user listed there.
- `~/.claude/user-hooks.json` is user-owned, never touched by an update, and Claude is blocked from editing it (deny list + guard hooks).

### Enabling per-user hooks

```bash
# Copy the example config into place — this is the opt-in step.
cp "$REPO_ROOT/global-settings/user-hooks.example.json" ~/.claude/user-hooks.json
chmod 600 ~/.claude/user-hooks.json

# (recommended) mirror the kernel lock used for the other hooks so a
# runaway process cannot rewrite it either:
sudo chattr +i ~/.claude/user-hooks.json
```

Then edit the file **in your own terminal** and add entries under the relevant event keys. Every top-level key mirrors a Claude Code hook event (`PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `SessionStart`, `PermissionRequest`, `Stop`, `SubagentStop`, `PreCompact`, `Notification`). Each entry is `{ "command": "…" }` with an optional `"matcher"` (ERE against `tool_name`, only relevant for the two `*ToolUse` events).

Restart Claude Code (or run `/hooks` to reload) — that's it. When the shared `settings.json` is next bumped and re-installed, `user-hooks.json` is left untouched and your hooks keep firing.

### Editing after `chattr +i`

Same dance as the other locked files:

```bash
sudo chattr -i ~/.claude/user-hooks.json
${EDITOR:-nano} ~/.claude/user-hooks.json
sudo chattr +i ~/.claude/user-hooks.json
```

### Why is Claude blocked from editing `user-hooks.json`?

A user hook can silently register itself before every tool call. If Claude could rewrite this file it could weaken the shared guards from inside a session — the exact bypass the deny list + guard hooks + `chattr +i` triangle is designed to prevent. So `user-hooks.json` sits under the same three layers as the other config files (deny list in `settings.json`, `block-config-tool-writes.sh` / `block-write-commands.sh` protected-path regex, optional `chattr +i`). The user configures it by hand; Claude never touches it.

### Disabling per-user hooks

Two ways:

```bash
# Method 1 — empty the arrays inside ~/.claude/user-hooks.json. The
# dispatcher fast-paths through empty arrays with zero side effects.

# Method 2 — delete the file entirely. The dispatcher exits 0 silently
# when the file is absent, so this fully disables the feature:
sudo chattr -i ~/.claude/user-hooks.json   # only needed if you locked it
rm ~/.claude/user-hooks.json
```

The dispatcher never blocks Claude regardless of state — a broken personal hook exits with a warning to stderr and Claude keeps going.

### Optional: personal hooks you can borrow

[`hooks/` in ConductionNL/readonly-mirror-wilco-claude-plans](https://github.com/ConductionNL/readonly-mirror-wilco-claude-plans/tree/main/hooks) holds one developer's personal hooks, run through this dispatcher. They add to the guards here and are not part of the global settings: nothing in this directory depends on them, and you can take any of them or none. The repo is a private, read-only mirror; Conduction developers can read it and fork it.

- `tool-context.sh` (`PreToolUse`, `PostToolUse`, `Stop`, `PreCompact`) refuses the first write to certain files until the matching guide in [`docs/claude/`](../docs/claude/) has been read in that session. The files and guides are: a hydra skill → `writing-skills.md`, `lib/Controller/*.php` → `writing-controllers.md`, an openspec `spec.md` → `writing-specs.md`, `evals.json` → `skill-evals.md`, an ADR → `writing-adrs.md`, and `src/**/*.vue` → `frontend-standards.md`. It also re-runs `update-skill-overview.sh` after hydra skill edits, and gates hotfix tags and releases behind a playbook.
- `plan-context.sh` (`UserPromptSubmit`) points Claude at those guides, and at notes in that repo, when your prompt is about such work.
- `read-markers.sh` is the read log both scripts share. It records which parts of a file were read, so a guide that was only partly read does not count as read.

[`hooks/README.md`](https://github.com/ConductionNL/readonly-mirror-wilco-claude-plans/blob/main/hooks/README.md) describes every rule and the `user-hooks.json` entries. The scripts are written for that developer's own setup. The paths, the plans tree and the role lines in the messages are theirs, so adapt them before you register a copy (see [Enabling per-user hooks](#enabling-per-user-hooks)). The production read-only guard started there and has been part of `block-write-commands.sh` since v2.6.0.

## Not part of the global settings: your own `~/.claude/CLAUDE.md`

The global settings decide what Claude is *allowed* to do. How Claude should *work* for you — scope, handover format, commit language, when to ask first — goes in your personal `~/.claude/CLAUDE.md`, which Claude Code loads in every session. That file is deliberately not shipped from this directory: it is not versioned, not `chattr +i`-locked, and an update never touches it.

A starting point is [`docs/claude/examples/global-CLAUDE.md.example`](../docs/claude/examples/global-CLAUDE.md.example). Copy it only when you have no `~/.claude/CLAUDE.md` yet; otherwise merge the sections you want by hand:

```bash
[ -e ~/.claude/CLAUDE.md ] || cp "$REPO_ROOT/docs/claude/examples/global-CLAUDE.md.example" ~/.claude/CLAUDE.md
```

Then fill in the placeholders and delete what you don't want. Its "org-wide" section on the push-authorization phrases describes how `block-write-commands.sh` behaves, so update the template when that hook's phrases change.

## Updating

When you see a version warning at session start:

1. In your own terminal (not through Claude), unlock the files. **Two** things need clearing — the kernel immutable flag *and* the read-only file mode:
   ```bash
   sudo chattr -i $HOME/.claude/settings.json $HOME/.claude/hooks/*.sh $HOME/.claude/settings-version
   chmod u+w $HOME/.claude/settings.json $HOME/.claude/hooks/*.sh $HOME/.claude/settings-version
   ```
   The `chmod` needs no `sudo` — you own the files. It is required because the *previous* update installed the hooks as `555` and `settings-version` as `444` (see [the update contract](#the-update-contract)), and `block-write-commands.sh` hard-denies Claude making a protected file writable again. Skip it and every write in step 3 fails with `Permission denied`, even though the `chattr` unlock itself succeeded.
2. Verify **both** cleared — no `i` in the `lsattr` flags, and a `w` in the owner bits:
   ```bash
   lsattr $HOME/.claude/settings.json $HOME/.claude/hooks/*.sh $HOME/.claude/settings-version
   ls -l  $HOME/.claude/settings.json $HOME/.claude/hooks/*.sh $HOME/.claude/settings-version
   ```
   Worth doing: a glob that silently matched nothing, or a partially-pasted command, otherwise shows up halfway through the update as a half-installed `~/.claude/`.
3. Then say: **"update my global settings to \<version\>"** — Claude will pull the latest files from GitHub.
4. After Claude finishes, re-apply the immutable lock. Pick **one** of the two:

   **(A) Full lock**: every file, all four protection layers. This is the strongest option:
   ```bash
   sudo chattr +i $HOME/.claude/settings.json $HOME/.claude/hooks/*.sh $HOME/.claude/settings-version
   ```

   **(B) Lock without `settings.json`**: keeps the VSCode model picker working:
   ```bash
   sudo chattr +i $HOME/.claude/hooks/*.sh $HOME/.claude/settings-version
   ```

   **Why (B) exists.** The VSCode extension saves every model switch by rewriting `~/.claude/settings.json`. Under (A) that write gets `EPERM`, so the picker shows `Failed to set model` and does nothing.

   **What (B) costs.** `settings.json` is the main file the whole setup hangs off. It holds `permissions.deny` and registers every guard hook, and (B) takes the kernel lock off exactly that file. What stays in front of it:

   - **Layer 1 is no separate barrier.** `permissions.deny` lives inside the file you just unlocked.
   - **Layers 2–3, the guard hooks** (`block-write-commands.sh`, `block-config-tool-writes.sh`), deny Claude's edits to `settings.json`, and their scripts stay kernel-locked. But they are regex checks, which the [security model](#security-model--defense-in-depth) calls bypassable. They also run only because `settings.json` registers them, so one write that slips past them can unregister them for the next session.
   - **Nothing stops other processes.** The guard hooks only police Claude's tool calls. Any other process running as you, such as an `npm install` or `composer install` script, can rewrite `settings.json` under (B).

   That makes (B) a limited but real risk, not a free one. It is a reasonable choice if you use the picker a lot and accept that trade.

   **The recommendation stays (A) plus a model pin in project-local settings.** That keeps all four layers and still lets you switch models. Both routes, and the trade-off in full, are in [global-claude-settings.md → Troubleshooting](../docs/claude/global-claude-settings.md#troubleshooting).

> ⚠️ Don't skip step 4. Without it, the kernel-level protection stays off until the next time you run `sudo chattr +i`. The hooks still defend in depth, but the strongest layer is unarmed. (B) unlocks one file on purpose. Leaving `hooks/*.sh` unlocked as well disarms the guards themselves.

### Which files the notice installs, and what "up to date" means (v2.7.0)

The file blocks in the notice are not a hand-maintained list. `check-settings-version.sh` reads the canonical `settings.json` from the same source it took `VERSION` from and emits one block per hook script it registers, plus `settings.json` itself first and `VERSION` last. A hook that is wired is therefore a hook that gets installed. Before v2.7.0 the list lived in the script and fell behind `settings.json` twice: v2.4.1 added two hooks it had missed, and `block-polling.sh`, registered since v2.5.0, was never on it, so following the notice left that guard uninstalled while the version read as current.

When the installed version already matches the online one, the hook also compares every managed file with its canonical copy:

- hook scripts by `sha256`, ignoring trailing newlines (the `printf '%s\n'` install writes exactly one, the `git show` install copies the bytes verbatim; neither is drift);
- `settings.json` as parsed JSON, without the top-level keys Claude Code itself writes there when you pick a model or an effort level (v2.7.1; v2.7.0 skipped only `model`). Under relock option (B) these writes land in the file, and a model choice is a preference, not policy:

  | Key | Written by |
  | --- | --- |
  | `model` | the VSCode model picker and `/model` |
  | `modelSettings` | `/effort` and the effort picker, saved per model as `modelSettings.<model>.effortLevel` |
  | `effortLevel` | the same choice when it cannot be keyed by model |
  | `fastMode` | `/fast` |
  | `advisorModel` | `/advisor` |
  | `switchModelsOnFlag` | the VSCode toggle that switches model when a safeguard flags a message |

  Every other difference in that file counts, and the notice names the top-level keys that differ.

A missing or changed file turns the session-start message into **FILES OUT OF SYNC**. It names the files, the phrase for step 3 is **"repair my global settings"**, and the unlock, contract and relock steps are the same as for an update. Only the affected files are rewritten; `VERSION` is left alone. On the GitHub path the check costs two extra fetches per session (`settings.json`, then every registered hook in one `curl` call); on the git-fetch path it costs none. A canonical file that could not be fetched is reported as not verified, never as fine.

### What the update adds (v2.8.0)

The UPDATE REQUIRED notice has a **What this update adds** block under the version lines: one sentence per version after the installed one, up to the latest, newest first, taken from [`CHANGELOG.md`](CHANGELOG.md). It shows at most five versions and counts the rest. A version without an entry is listed as such, not left out. If `CHANGELOG.md` cannot be fetched, the block says so, and the update itself is unaffected. On the GitHub path this costs one extra fetch, and only when an update is pending.

Ask Claude for more details and it looks up the commit that set `VERSION` to each listed version, reads its message, changed files and pull request, and explains the change with a link to that pull request (or the commit when none merged it). The notice gives Claude the `gh api` and `git log` commands for this, so the answer comes from the history, not from the summary sentence.

The notice is printed by the *installed* hook, so the block first appears when you update **from** v2.8.0 or later to a newer version.

### The update contract

Claude reinstalls each file with `chmod 555` (hooks) or `chmod 444` (`settings-version`) because `block-write-commands.sh` permits only those two modes on protected paths — `chmod 644`, `chmod u+w` and `chattr` are all hard-denied to Claude, by design, so it can never widen its own access. The consequence is the one step 1 covers: read-only mode is *sticky* across updates and only you can clear it.

If Claude reports `Permission denied` mid-update, that is this and nothing else. The correct response is to run the step-1 `chmod u+w` and let Claude continue — not to have it work around the block with `rm`/`mv`/`cp` (all denied on protected paths too, and a half-removed hook is worse than a stale one).

## Production is read-only (v2.6.0)

`block-write-commands.sh` hard-denies `kubectl` / `oc` with a mutating verb (`apply`, `create`, `delete`, `edit`, `patch`, `replace`, `scale`, `set`, `label`, `annotate`, `exec`, `cp`, `drain`, `cordon`, `uncordon`, `taint`, `run`, `expose`, `autoscale`, `debug`, `attach`, `rollout` except `status`/`history`) and `helm install|upgrade|uninstall|delete|rollback`, whenever the same command segment names a `*-prod` namespace or context. No phrase unlocks it: Claude gives you the filled-in command and you run it. Reads (`get`, `describe`, `logs`, `top`, `rollout status`) and every non-prod namespace are not this guard's business.

The check runs **before** every `ask` guard. An ask exits the hook, so a production write chained after, for example, `gh pr create` would otherwise get through on one approval of the gh prompt.

### Data is not a command

The production check and the `git push` check read the command with the *data* taken out (`data_free_cmd`), so a commit message or PR body that mentions `git push` is no longer hard-denied as a push. Removed, and nothing else:

- the body of a heredoc fed to a data sink (`cat`, `tee`, `git`, `gh`, `jq`, `wc`, `sort`, `head`, `tail`, `grep`, `less`, `more`) on a line without a pipe or command substitution;
- the quoted value of `-m`/`--message`/`-b`/`--body`/`-t`/`--title`/`--notes` on a `git commit|tag|notes` (git's global options such as `-C <path>` may sit in between, since v2.7.2) or `gh pr|issue|release` line — single-quoted always, double-quoted only without `$(` or a backtick.

Still seen: a push or production write inside `bash -c`, `eval`, `$(…)`, backticks, a heredoc fed to `bash`/`sh`/`python`/…, and `cat <<EOF | bash`. The config guard is **not** part of this change: it keeps scanning the full command, because there a false deny is cheaper than a gap.

## `git push` needs the phrase in every form (v2.7.2)

Without an authorization phrase in your last message, `block-write-commands.sh` hard-denies a `git push` however it is written:

- with git's global options before `push`: `git -C <path> push`, `git -c key=value push`, `git --no-pager push`, `git -P push`, `git --git-dir <path> push`, `git --work-tree <path> push`;
- chained after a command that prompts: `git -C repo commit -m … && git push`, `gh pr create … && git push`, `curl -X POST … ; git push`.

Before v2.7.2 the push check ran after the `git -C`, `gh`, `curl` and `docker` prompts. An ask exits the hook, so approving that prompt also ran the chained push without the phrase. The check now runs before every `ask`, like the production guard, and with the phrase the hook still asks about the rest of the command.

## ⚠️ Bumping the version — REQUIRED on every change

**Any commit that modifies an *installed artifact* in `global-settings/` MUST also increment `VERSION`.** An installed artifact is anything the [Install](#install) steps copy into `~/.claude/` — `settings.json`, the hook scripts, and the `.example` files.

Failing to bump the version means users will not be warned to update, and their installed settings will silently fall behind.

**Every bump also adds an entry to [`CHANGELOG.md`](CHANGELOG.md)**: a `## X.Y.Z` heading with one sentence under it that says what the update adds, in words a developer understands without opening the code. The update notice shows that sentence. A missing entry fails the version-check tests.

Changes to `global-settings/README.md` alone do **not** require a bump: nothing installed changes, so a bump would push every developer through the unlock/relock cycle to copy a file they don't have. Documentation under `docs/claude/` is likewise never a trigger.

Semver rules:

- `1.0.0 → 1.1.0` — new permissions, guards, or behavior added
- `1.0.0 → 2.0.0` — breaking change requiring manual migration (e.g. settings restructure)

Use the `/verify-global-settings-version` command to check whether a version bump is needed before creating a PR.

## Security model — defense in depth

The settings use four independent layers of protection, each catching what the others miss:

1. **Deny-list** (`settings.json` deny rules) — hard-blocks file edits to `~/.claude/` config files and destructive Bash commands. These cannot be overridden from within a Claude session. The rules are `Edit(...)` only: one `Edit(path)` rule covers every file-editing tool (Write, MultiEdit, NotebookEdit), while a `Write(path)` rule is not matched by file-permission checks at all — the seven inert `Write(...)` twins were dropped in v2.4.5.
2. **Bash hook** (`block-write-commands.sh`) — runs on every Bash command. Catches write operations, command chaining, obfuscation, symlink attacks, and (since v1.7.0) `chattr` attempts on protected paths plus script-body scans for invoked scripts that target `~/.claude/`. Can deny (hard block) or ask (prompt the user). Since v2.6.0 it also hard-blocks production writes and ignores *data* in two checks — see [Production is read-only](#production-is-read-only-v260). Since v2.7.2 the `git push` check, too, runs before every prompt — see [`git push` needs the phrase in every form](#git-push-needs-the-phrase-in-every-form-v272).
3. **Tool hook** (`block-config-tool-writes.sh`, added in v1.7.0) — runs on Write/Edit/MultiEdit tool calls. Denies tools whose `file_path` is a protected `~/.claude/` config file, and denies tools that would create a _script_ whose body, when executed, would write to a protected path. Closes the "write a script then run it" bypass. Since v2.4.6 the body scan exempts the canonical sources in this repo's `global-settings/` directory (matched by their exact filenames, plus `tests/*.sh`) — those files *are* the update mechanism, so their bodies necessarily contain the operations the scan looks for, and without the exemption Claude could never maintain them. The exemption matches on a canonicalized path (`realpath -m`, plus an outright refusal to exempt any path still carrying a `..` component), so neither a traversal nor a symlinked parent can reach an exempt pattern while landing on an installed file. The exemption covers staging only. What still holds after it: the installed copies stay covered by this hook's `file_path` guard and by layer 4, and layer 2 catches the common invocation shapes (`bash <path>`, `source <path>`, bare-path execution) if such a script is run. Layer 2's script-body scan is not exhaustive — it reads the first token of each command segment, so wrapper forms like `nohup bash <path>` or `timeout 5 bash <path>` slip past it. That limit is not introduced here: staging an executable payload was already possible pre-exemption via any path a script-extension check doesn't cover (`/tmp/x.txt` with no shebang, then `bash /tmp/x.txt`). Layer 4 is what actually closes it, which is why the relock matters.
4. **Kernel immutability** (`chattr +i`, the new authoritative layer in v1.7.0) — once set, the kernel refuses every write to the file regardless of permissions, regardless of which process attempts it, regardless of any hook outcome. Only `root` can clear the bit, and only `sudo chattr -i` (which Claude is hard-blocked from running) toggles it.

The earlier layers intentionally overlap. Removing one because another "already handles it" weakens the chain — keep them all. **Layer 4 is the only guarantee** that survives a fully compromised hook chain; layers 1–3 ensure that a single forgetful `sudo chattr -i` doesn't leave the entire window open.

### Why both hook and kernel layers?

A regex hook is fundamentally limited against an adaptive LLM that can write arbitrary scripts (encoded content, runtime path construction, process substitution, etc.). The kernel layer (`chattr +i`) has no such limitation — the syscall returns `EPERM` regardless of how clever the script is. The hook layers cover the period when `chattr -i` has been cleared for a legitimate update.

## Full documentation

See [`docs/claude/global-claude-settings.md`](../docs/claude/global-claude-settings.md) for the complete reference including the permissions list, hook behavior table, and troubleshooting.
