# Global Claude Settings (mandatory, versioned)

These files define the **mandatory** user-level Claude Code configuration for all Conduction developers. Install them once per machine; the version-check hook will alert you at the start of each session when an update is available.

Current version: see [`VERSION`](VERSION)

## Files

| File | Install as | Purpose |
|------|-----------|---------|
| `settings.json` | `~/.claude/settings.json` | Permissions allowlist + hooks |
| `block-write-commands.sh` | `~/.claude/hooks/block-write-commands.sh` | Guards write operations, prompts for approval |
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
cp "$REPO_ROOT/global-settings/check-settings-version.sh" ~/.claude/hooks/check-settings-version.sh
chmod +x ~/.claude/hooks/block-write-commands.sh ~/.claude/hooks/check-settings-version.sh

cp "$REPO_ROOT/global-settings/VERSION" ~/.claude/settings-version
echo "$REPO_ROOT" > ~/.claude/settings-repo-path

# Online version checking via GitHub API (recommended — no local repo required):
cp "$REPO_ROOT/global-settings/settings-repo-url.example" ~/.claude/settings-repo-url

# Optional: track a branch other than main (tag or SHA also accepted).
# Defaults to "main" when this file is absent.
# To track a specific branch, copy and edit:
# cp "$REPO_ROOT/global-settings/settings-repo-ref.example" ~/.claude/settings-repo-ref
# echo "feature/your-branch" > ~/.claude/settings-repo-ref
```

Restart Claude Code after installing. Requires `jq`, `md5sum`, and `gh` (GitHub CLI) on `PATH`.

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

1. In your own terminal (not through Claude), unlock the config files:
   ```bash
   chmod 644 $HOME/.claude/settings-version $HOME/.claude/settings-repo-path $HOME/.claude/hooks/*.sh
   ```
2. Then say: **"update my global settings to \<version\>"** and Claude will pull the latest files from GitHub.

## ⚠️ Bumping the version — REQUIRED on every change

**Any commit that modifies a file in `global-settings/` MUST also increment `VERSION`.**

Failing to bump the version means users will not be warned to update, and their installed settings will silently fall behind.

Semver rules:
- `1.0.0 → 1.1.0` — new permissions, guards, or behavior added
- `1.0.0 → 2.0.0` — breaking change requiring manual migration (e.g. settings restructure)

Use the `/verify-global-settings-version` command to check whether a version bump is needed before creating a PR.

## Full documentation

See [`docs/claude/global-claude-settings.md`](../docs/claude/global-claude-settings.md) for the complete reference including the permissions list, hook behavior table, and troubleshooting.
