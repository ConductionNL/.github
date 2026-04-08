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

## Install

From the root of the `apps-extra` repo:

```bash
REPO_CLAUDE="$(pwd)/.claude"

mkdir -p ~/.claude/hooks

cp "$REPO_CLAUDE/global-settings/settings.json" ~/.claude/settings.json
cp "$REPO_CLAUDE/global-settings/block-write-commands.sh" ~/.claude/hooks/block-write-commands.sh
cp "$REPO_CLAUDE/global-settings/check-settings-version.sh" ~/.claude/hooks/check-settings-version.sh
chmod +x ~/.claude/hooks/block-write-commands.sh ~/.claude/hooks/check-settings-version.sh

cp "$REPO_CLAUDE/global-settings/VERSION" ~/.claude/settings-version
echo "$REPO_CLAUDE" > ~/.claude/settings-repo-path
```

Restart Claude Code after installing. Requires `jq` and `md5sum` on `PATH`.

## Updating

When you see a version warning at session start, re-run the install commands above and the warning will stop.

## ⚠️ Bumping the version — REQUIRED on every change

**Any commit that modifies a file in `global-settings/` MUST also increment `VERSION`.**

Failing to bump the version means users will not be warned to update, and their installed settings will silently fall behind.

Semver rules:
- `1.0.0 → 1.1.0` — new permissions, guards, or behavior added
- `1.0.0 → 2.0.0` — breaking change requiring manual migration (e.g. settings restructure)

Use the `/verify-global-settings-version` command to check whether a version bump is needed before creating a PR.

## Full documentation

See [`docs/global-claude-settings.md`](../docs/global-claude-settings.md) for the complete reference including the permissions list, hook behavior table, and troubleshooting.
