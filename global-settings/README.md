# Global Claude Settings (mandatory, versioned)

These files define the **mandatory** user-level Claude Code configuration for all Conduction developers. Install them once per machine; the version-check hook will alert you at the start of each session when an update is available.

Current version: see [`VERSION`](VERSION)

## Files

| File | Install as | Purpose |
|------|-----------|---------|
| `settings.json` | `~/.claude/settings.json` | Permissions allowlist + hooks |
| `block-write-commands.sh` | `~/.claude/hooks/block-write-commands.sh` | Guards Bash write operations, prompts for approval |
| `block-config-tool-writes.sh` | `~/.claude/hooks/block-config-tool-writes.sh` | Guards Write/Edit/MultiEdit calls — denies tools that write to `~/.claude/` or produce scripts that would (added in v1.7.0) |
| `check-settings-version.sh` | `~/.claude/hooks/check-settings-version.sh` | Warns at session start if settings are outdated |
| `VERSION` | `~/.claude/settings-version` | Installed version tracker (semver) |
| `settings-repo-url.example` | `~/.claude/settings-repo-url` | GitHub repo slug for online version checking |
| `settings-repo-ref.example` | `~/.claude/settings-repo-ref` | Branch/tag/SHA to track (defaults to `main` when absent) |

## Install

From the root of the `.github` repo (or wherever you cloned it):

```bash
REPO_ROOT="$(pwd)"

mkdir -p ~/.claude/hooks

cp "$REPO_ROOT/global-settings/settings.json" ~/.claude/settings.json
cp "$REPO_ROOT/global-settings/block-write-commands.sh" ~/.claude/hooks/block-write-commands.sh
cp "$REPO_ROOT/global-settings/block-config-tool-writes.sh" ~/.claude/hooks/block-config-tool-writes.sh
cp "$REPO_ROOT/global-settings/check-settings-version.sh" ~/.claude/hooks/check-settings-version.sh
chmod +x ~/.claude/hooks/*.sh

cp "$REPO_ROOT/global-settings/VERSION" ~/.claude/settings-version
echo "$REPO_ROOT" > ~/.claude/settings-repo-path

# Online version checking via GitHub API (recommended — no local repo required):
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

Restart Claude Code after installing. Requires `jq`, `md5sum`, `gh` (GitHub CLI), and `chattr` on `PATH` (chattr is part of `e2fsprogs` — present on every standard Linux distro).

## Online version checking

When `~/.claude/settings-repo-url` is configured, the version check uses the GitHub API (`gh api`) as its primary method. This means you get accurate online version checks even without a local clone of the `.github` repo.

If the GitHub API is unavailable or `gh` is not installed, the hook falls back to `git fetch` via `~/.claude/settings-repo-path` (if configured).

The status panel at session start shows which method was used:

```
│     Global Claude Settings Status            │
  Installed  : v1.4.0 ✓
  Local repo : (not configured)
  Online     : v1.4.0  (via GitHub API)
```

## Updating

When you see a version warning at session start:

1. In your own terminal (not through Claude), clear the immutable bit:
   ```bash
   sudo chattr -i $HOME/.claude/settings.json $HOME/.claude/hooks/*.sh $HOME/.claude/settings-version
   ```
2. Then say: **"update my global settings to \<version\>"** — Claude will pull the latest files from GitHub.
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
3. **Tool hook** (`block-config-tool-writes.sh`, added in v1.7.0) — runs on Write/Edit/MultiEdit tool calls. Denies tools whose `file_path` is a protected `~/.claude/` config file, and denies tools that would create a *script* whose body, when executed, would write to a protected path. Closes the "write a script then run it" bypass.
4. **Kernel immutability** (`chattr +i`, the new authoritative layer in v1.7.0) — once set, the kernel refuses every write to the file regardless of permissions, regardless of which process attempts it, regardless of any hook outcome. Only `root` can clear the bit, and only `sudo chattr -i` (which Claude is hard-blocked from running) toggles it.

The earlier layers intentionally overlap. Removing one because another "already handles it" weakens the chain — keep them all. **Layer 4 is the only guarantee** that survives a fully compromised hook chain; layers 1–3 ensure that a single forgetful `sudo chattr -i` doesn't leave the entire window open.

### Why both hook and kernel layers?

A regex hook is fundamentally limited against an adaptive LLM that can write arbitrary scripts (encoded content, runtime path construction, process substitution, etc.). The kernel layer (`chattr +i`) has no such limitation — the syscall returns `EPERM` regardless of how clever the script is. The hook layers cover the period when `chattr -i` has been cleared for a legitimate update.

## Full documentation

See [`docs/claude/global-claude-settings.md`](../docs/claude/global-claude-settings.md) for the complete reference including the permissions list, hook behavior table, and troubleshooting.
