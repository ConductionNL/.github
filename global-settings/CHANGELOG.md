# Global settings changelog

One entry per released `VERSION`, newest first. The heading is the bare version number. The first line under it is **one sentence** that says what the update adds or fixes, in words a developer understands without opening the code.

`check-settings-version.sh` shows that sentence in the session-start UPDATE REQUIRED notice for every version between the installed one and the latest (since v2.8.0). The details live in the commit and the pull request. When a user asks for more, Claude looks those up from the version number. This file is not installed into `~/.claude/` and needs no `VERSION` bump of its own, but every `VERSION` bump needs an entry here (see [Bumping the version](README.md#️-bumping-the-version--required-on-every-change)).

## 2.8.0

The update notice now says in one sentence what each pending version adds, and Claude can explain the changes in more detail, with links to the pull requests, when you ask.

## 2.7.2

An unauthorized `git push` is now denied in every form, including `git -C <path> push`, `git -c k=v push` and a push chained after a command Claude was asked to approve.

## 2.7.1

Picking a model or an effort level no longer reports `settings.json` as out of sync, because the keys Claude Code itself writes for that choice are ignored in the file check.

## 2.7.0

The update notice now installs every hook `settings.json` registers instead of a hand-kept list, and a session start checks that the installed files match the canonical copies.

## 2.6.0

Changes to production (`kubectl`, `oc` or `helm` writes against a `*-prod` namespace or context) are now hard-blocked, and text inside commit messages or heredocs no longer counts as a command.

## 2.5.2

The relock step now offers two options, a full lock or a lock without `settings.json`, so the VSCode model picker can keep working.

## 2.5.1

A push phrase typed next to a pasted image is recognised again, and a skill's text can no longer authorize a push by itself.

## 2.5.0

Hand-rolled waiting (CI watch commands, poll loops, long sleeps and idle heartbeats) is now blocked.
