# Global Claude Settings (mandatory, versioned)

These files define the **mandatory** user-level Claude Code configuration for all Conduction developers. Install them once per machine; the version-check hook will alert you at the start of each session when an update is available.

Current version: see [`VERSION`](VERSION)

## Files

| File                          | Install as                                    | Purpose                                                                                                                     |
| ----------------------------- | --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `settings.json`               | `~/.claude/settings.json`                     | Permissions allowlist + hooks                                                                                               |
| `block-write-commands.sh`     | `~/.claude/hooks/block-write-commands.sh`     | Guards Bash write operations, prompts for approval                                                                          |
| `block-config-tool-writes.sh` | `~/.claude/hooks/block-config-tool-writes.sh` | Guards Write/Edit/MultiEdit calls — denies tools that write to `~/.claude/` or produce scripts that would (added in v1.7.0) |
| `check-settings-version.sh`   | `~/.claude/hooks/check-settings-version.sh`   | Warns at session start if settings are outdated                                                                             |
| `sound-notify.sh`             | `~/.claude/hooks/sound-notify.sh`             | Optional notification-sound wrapper. Reads `~/.claude/sound-config.sh` and plays a sound on question / permission / stop events. Silent by default (added in v2.2.0)         |
| `VERSION`                     | `~/.claude/settings-version`                  | Installed version tracker (semver)                                                                                          |
| `settings-repo-url.example`   | `~/.claude/settings-repo-url`                 | Codeberg repo slug for online version checking                                                                              |
| `settings-repo-ref.example`   | `~/.claude/settings-repo-ref`                 | Branch to track (defaults to `main` when absent; the Codeberg raw URL uses `/raw/branch/<ref>/`)                            |
| `sound-config.sh.example`     | `~/.claude/sound-config.sh` (optional)        | Opt-in sound configuration. Only install if you want notification sounds. User-editable — **not** `chattr +i`-locked        |

## Install

From the root of the `.github` repo (or wherever you cloned it):

```bash
REPO_ROOT="$(pwd)"

mkdir -p ~/.claude/hooks

cp "$REPO_ROOT/global-settings/settings.json" ~/.claude/settings.json
cp "$REPO_ROOT/global-settings/block-write-commands.sh" ~/.claude/hooks/block-write-commands.sh
cp "$REPO_ROOT/global-settings/block-config-tool-writes.sh" ~/.claude/hooks/block-config-tool-writes.sh
cp "$REPO_ROOT/global-settings/check-settings-version.sh" ~/.claude/hooks/check-settings-version.sh
cp "$REPO_ROOT/global-settings/sound-notify.sh" ~/.claude/hooks/sound-notify.sh
chmod +x ~/.claude/hooks/*.sh

cp "$REPO_ROOT/global-settings/VERSION" ~/.claude/settings-version
echo "$REPO_ROOT" > ~/.claude/settings-repo-path

# Online version checking via Codeberg (recommended — no local repo required):
cp "$REPO_ROOT/global-settings/settings-repo-url.example" ~/.claude/settings-repo-url

# Optional: track a branch other than main (tag or SHA also accepted).
# Defaults to "main" when this file is absent.
# To track a specific branch, copy and edit:
# cp "$REPO_ROOT/global-settings/settings-repo-ref.example" ~/.claude/settings-repo-ref
# echo "feature/your-branch" > ~/.claude/settings-repo-ref

# Finally — apply the kernel-level immutable lock (v1.7.0+).
# This is the single piece of protection that no Claude command can bypass:
# even if every other guard fails, the kernel refuses the write.
sudo chattr +i ~/.claude/settings.json ~/.claude/hooks/*.sh ~/.claude/settings-version
```

Restart Claude Code after installing. Requires `jq`, `md5sum`, `curl`, and `chattr` on `PATH` (chattr is part of `e2fsprogs` — present on every standard Linux distro).

## Online version checking

When `~/.claude/settings-repo-url` is configured, the version check uses Codeberg's raw URL (`https://codeberg.org/<slug>/raw/branch/<ref>/global-settings/VERSION`) as its primary method. This means you get accurate online version checks even without a local clone of the `.github` repo.

If Codeberg is unreachable or `curl` is not installed, the hook falls back to `git fetch` via `~/.claude/settings-repo-path` (if configured).

The status panel at session start shows which method was used:

```
│     Global Claude Settings Status            │
  Installed  : v2.0.0 ✓
  Local repo : (not configured)
  Online     : v2.0.0  (via Codeberg)
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

## Updating

When you see a version warning at session start:

1. In your own terminal (not through Claude), clear the immutable bit:
   ```bash
   sudo chattr -i $HOME/.claude/settings.json $HOME/.claude/hooks/*.sh $HOME/.claude/settings-version
   ```
2. Then say: **"update my global settings to \<version\>"** — Claude will pull the latest files from Codeberg.
3. After Claude finishes, re-apply the immutable lock:
   ```bash
   sudo chattr +i $HOME/.claude/settings.json $HOME/.claude/hooks/*.sh $HOME/.claude/settings-version
   ```

> ⚠️ Don't skip step 3. Without it, the kernel-level protection stays off until the next time you run `sudo chattr +i`. The hooks still defend in depth, but the strongest layer is unarmed.

## ⚠️ Bumping the version — REQUIRED on every change

**Any commit that modifies a file in `global-settings/` MUST also increment `VERSION`.**

Failing to bump the version means users will not be warned to update, and their installed settings will silently fall behind.

Semver rules:

- `1.0.0 → 1.1.0` — new permissions, guards, or behavior added
- `1.0.0 → 2.0.0` — breaking change requiring manual migration (e.g. settings restructure)

Use the `/verify-global-settings-version` command to check whether a version bump is needed before creating a PR.

## Security model — defense in depth

The settings use four independent layers of protection, each catching what the others miss:

1. **Deny-list** (`settings.json` deny rules) — hard-blocks Edit/Write to `~/.claude/` config files and destructive Bash commands. These cannot be overridden from within a Claude session.
2. **Bash hook** (`block-write-commands.sh`) — runs on every Bash command. Catches write operations, command chaining, obfuscation, symlink attacks, and (since v1.7.0) `chattr` attempts on protected paths plus script-body scans for invoked scripts that target `~/.claude/`. Can deny (hard block) or ask (prompt the user).
3. **Tool hook** (`block-config-tool-writes.sh`, added in v1.7.0) — runs on Write/Edit/MultiEdit tool calls. Denies tools whose `file_path` is a protected `~/.claude/` config file, and denies tools that would create a _script_ whose body, when executed, would write to a protected path. Closes the "write a script then run it" bypass.
4. **Kernel immutability** (`chattr +i`, the new authoritative layer in v1.7.0) — once set, the kernel refuses every write to the file regardless of permissions, regardless of which process attempts it, regardless of any hook outcome. Only `root` can clear the bit, and only `sudo chattr -i` (which Claude is hard-blocked from running) toggles it.

The earlier layers intentionally overlap. Removing one because another "already handles it" weakens the chain — keep them all. **Layer 4 is the only guarantee** that survives a fully compromised hook chain; layers 1–3 ensure that a single forgetful `sudo chattr -i` doesn't leave the entire window open.

### Why both hook and kernel layers?

A regex hook is fundamentally limited against an adaptive LLM that can write arbitrary scripts (encoded content, runtime path construction, process substitution, etc.). The kernel layer (`chattr +i`) has no such limitation — the syscall returns `EPERM` regardless of how clever the script is. The hook layers cover the period when `chattr -i` has been cleared for a legitimate update.

## Full documentation

See [`docs/claude/global-claude-settings.md`](../docs/claude/global-claude-settings.md) for the complete reference including the permissions list, hook behavior table, and troubleshooting.
