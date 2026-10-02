# Global settings changelog

One entry per released `VERSION`, newest first. The heading is the version number and the date it reached `main` (`## X.Y.Z — YYYY-MM-DD`). The first line under it is **one sentence** that says what the update adds or fixes, in words a developer understands without opening the code.

`check-settings-version.sh` shows that sentence in the session-start UPDATE REQUIRED notice for every version between the installed one and the latest (since v2.8.0). The details live in the commit and the pull request. When a user asks for more, Claude looks those up from the version number. This file is not installed into `~/.claude/` and needs no `VERSION` bump of its own, but every `VERSION` bump needs an entry here (see [Bumping the version](README.md#️-bumping-the-version--required-on-every-change)).

Versions 1.0.0 to 1.3.0 were released from the now archived `ConductionNL/claude-code-config` repository, and their date is the day they reached that repository's `main`. A few versions reached `main` together with the next one instead of on their own; their entry says so, and carries the date they reached `main`. Numbers that `main` never carried (1.5.0, 1.5.2, 1.5.3, 2.4.3) are listed under a `###` heading with a note on where their changes went. The update notice reads only `##` headings, so it skips them.

## 2.8.0 — 2026-10-02

The update notice is now short at session start and says in one sentence what each pending version adds. Ask Claude how to update for the full steps, or for the details of the changes with links to the pull requests.

## 2.7.2 — 2026-10-01

An unauthorized `git push` is now denied in every form, including `git -C <path> push`, `git -c k=v push` and a push chained after a command Claude was asked to approve.

## 2.7.1 — 2026-10-01

Picking a model or an effort level no longer reports `settings.json` as out of sync, because the keys Claude Code itself writes for that choice are ignored in the file check.

## 2.7.0 — 2026-10-01

The update notice now installs every hook `settings.json` registers instead of a hand-kept list, and a session start checks that the installed files match the canonical copies.

## 2.6.0 — 2026-09-29

Changes to production (`kubectl`, `oc` or `helm` writes against a `*-prod` namespace or context) are now hard-blocked, and text inside commit messages or heredocs no longer counts as a command.

## 2.5.2 — 2026-09-28

The relock step now offers two options, a full lock or a lock without `settings.json`, so the VSCode model picker can keep working.

## 2.5.1 — 2026-09-28

A push phrase typed next to a pasted image is recognised again, and a skill's text can no longer authorize a push by itself.

## 2.5.0 — 2026-09-12

Hand-rolled waiting (CI watch commands, poll loops, long sleeps and idle heartbeats) is now blocked.

## 2.4.6 — 2026-09-11

The unlock step now includes the `chmod u+w` that every update after the first needs, so an update no longer stalls halfway with `Permission denied`.

## 2.4.5 — 2026-09-10

Seven `Write(...)` deny rules that Claude Code never applied are removed; the `Edit(...)` rules next to them already cover every file-editing tool.

## 2.4.4 — 2026-09-10

The in-place edit guard no longer hard-denies a chain of harmless commands because the tool, its `-i` flag and the protected path came from different commands.

### 2.4.3 — never released

Two pull requests both took 2.4.3 on 2026-09-08, and `main` never carried it. Each branch was renumbered when `main` was merged into it, before its own merge on 2026-09-10. The destructive-guard fix ([#720](https://github.com/ConductionNL/.github/pull/720)) shipped as 2.4.4 and the removal of the inert `Write(...)` deny rules ([#716](https://github.com/ConductionNL/.github/pull/716)) as 2.4.5.

## 2.4.2 — 2026-09-08

The update notice now also installs `sound-notify.sh` and `user-hooks-dispatch.sh`, which it had left out since they were added.

## 2.4.1 — 2026-09-08

The `mcpServers` block is removed from `settings.json`, because Claude Code never read it there and the browsers it listed never loaded.

## 2.4.0 — 2026-09-04

You can register your own hooks in `~/.claude/user-hooks.json`, and they survive every settings update.

## 2.3.1 — 2026-09-04

The "up to date" message names its source ("via GitHub") again.

## 2.3.0 — 2026-09-04

The canonical source moves back from Codeberg to GitHub (`ConductionNL/.github`), for the version check and for the update itself.

## 2.2.2 — 2026-07-10

The permission-request sound now plays, because it is wired to the event Claude Code actually fires for a permission dialog.

## 2.2.1 — 2026-07-09

Short notification sounds are no longer cut off when the hook exits.

## 2.2.0 — 2026-07-09

Optional notification sounds when Claude asks a question, needs a permission or finishes, off by default and set in `~/.claude/sound-config.sh`.

## 2.1.0 — 2026-06-12

`--legacy-peer-deps` is hard-denied for npm, pnpm, yarn and bun installs.

## 2.0.0 — 2026-06-12

Breaking: the canonical source moves from GitHub to Codeberg (`codeberg.org/Conduction/.github`), so the version check and the update pull from there.

It was committed on 2026-05-29 on the `feature/codeberg-global-settings-flip` branch and reached `main` in the same merge as 2.1.0, so `main` went from 1.7.0 straight to 2.1.0.

## 1.7.0 — 2026-05-13

Claude's config files get a kernel-level lock (`chattr +i`), and a new hook stops the Write and Edit tools from changing them.

## 1.6.1 — 2026-05-12

A push phrase now stays valid after Claude has run other tools in the same turn.

## 1.6.0 — 2026-05-04

Tighter guards on writes to `~/.claude/`, `settings-repo-path` is no longer unlocked during an update, and the guard hook gets a test suite.

### 1.5.3 — never released

This number appears only in the commit message of the 1.6.0 change ("Bump VERSION 1.5.3 → 1.6.0"). That commit changed `VERSION` from 1.5.1 to 1.6.0, and no commit with `VERSION` 1.5.3 exists, so its changes are the ones listed under 1.6.0.

### 1.5.2 — never released

The push-phrase fix first took 1.5.2 on 2026-05-07, on a branch of a copy of `global-settings` kept in another repository. That branch was never merged. The same fix reached `main` here as 1.6.1 ([#43](https://github.com/ConductionNL/.github/pull/43)).

## 1.5.1 — 2026-05-04

You can track a branch other than `main` with `~/.claude/settings-repo-ref`, and destructive commands such as `sudo`, `rm -rf /`, `git reset --hard` and `gh pr merge` are denied.

It reached `main` together with 1.6.0, in [#22](https://github.com/ConductionNL/.github/pull/22), so `main` went from 1.4.0 straight to 1.6.0.

### 1.5.0 — never released

On 2026-04-13 a copy of `global-settings` kept in another repository took 1.5.0 for the destructive-command deny rules and went to 1.5.1 the same day. This repository went from 1.4.0 straight to 1.5.1, so those deny rules shipped as part of 1.5.1.

## 1.4.0 — 2026-04-16

The version check reads the latest version straight from GitHub (`~/.claude/settings-repo-url`), with the local clone as fallback.

## 1.3.0 — 2026-04-08

Write requests through `curl` are caught in more forms, including combined flags such as `-sX POST` and a `curl` behind a pipe.

## 1.2.2 — 2026-04-03

`gh pr`, `gh issue`, `gh repo`, `gh release`, `gh workflow` and `gh run` write commands now ask for approval, also when chained after a read.

## 1.2.1 — 2026-04-03

More read-only commands run without a prompt, and any output redirect to a file now asks for approval.

It reached `main` of `claude-code-config` together with 1.2.2 (PR #20 there), so that `main` went from 1.2.0 straight to 1.2.2.

## 1.2.0 — 2026-03-28

Claude can no longer change its own settings files or make them writable, and the version check retries once when the remote is briefly unreachable.

## 1.1.0 — 2026-03-28

Commands that would leave the WSL workspace (Windows drives under `/mnt/<drive>/`, `.exe` programs, `wsl`) are hard-blocked.

## 1.0.0 — 2026-03-27

The first mandatory, versioned global settings: a shared `settings.json`, the write-guard hook and a session-start version check.
