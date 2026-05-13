# Retrospective — decidesk#44/#45 and the Phase G rollout

**Date:** 2026-04-23
**Subjects:** decidesk#44 (Minutes and Decisions — Core T3), decidesk#45 (Minutes and Decisions — Other T1)
**Outcome:** Phase G (scope-to-diff) landed + four related pipeline bugs fixed as validation surfaced them.

---

## Why this retrospective exists

Two decidesk issues — #44 and #45 — were stuck for multiple days. Each cycle they went through the pipeline, each cycle they escalated to `needs-input`. The surface cause was always "reviewer/applier fail". The underlying causes turned out to be a stack of five distinct bugs, each hidden behind the previous one. Every fix revealed the next.

This doc captures the whole stack, in the order we found it, because the failure modes are likely to recur in other forms:

1. Supervisor comment-spam on terminal-state issues (infrastructure)
2. Gates scan the whole repo instead of the PR diff — Phase G (design)
3. Applier `/workspace` root-owned, claude user can't write (container build)
4. `secrets/.env` documented but never actually sourced (doc-code drift)
5. Bounded-fix scope defined by line count fails for common auth patterns (policy)

The larger lesson: **the no-loop pipeline is very unforgiving of infrastructure gaps**. There's no retry budget to absorb a broken prefetch or a silently-failing chown. One missed `chown` in a Dockerfile looks identical from the outside to a sophisticated applier judgment call ("fail, 0 findings").

---

## How the pipeline is supposed to work

For context, the intended flow for a yolo-labelled spec issue:

```
trigger label (ready-to-build)
  → Supervisor picks up, assigns slot 1-5
  → Builder (Al Gorithm, Haiku)
      · reads spec, writes code, opens draft PR
      · Rule 0b wrapper runs composer check:strict + phpunit + 8 hydra-gates
      · commits + pushes
  → Code Review (Juan Claude van Damme, Sonnet)
      · re-runs hydra-gates
      · applies bounded fixes, emits verdict JSON
  → Security Review (Clyde Barcode, Sonnet)
      · runs Semgrep + composer/npm audit + gitleaks + manual OWASP
      · applies bounded security fixes, emits verdict JSON
  → Either reviewer fail → needs-input (applier skipped)
  → Both reviewers pass + ≥1 fix applied → Applier (Axel Pliér)
      · reads final state, emits binary pass/fail
      · pass → yolo merge
      · fail → needs-input
  → Both reviewers pass + zero fixes → ready to merge (skip applier)
```

No iteration at any stage. Every terminal outcome is either merge or `needs-input`. The only levers are human-applied `retry:queued` (single-shot fixer pass) or `rebuild:queued` (hard reset).

---

## Timeline

### Before this session

decidesk#44 and #45 had been through **8+ pipeline cycles** each over 2026-04-19 to 2026-04-22. Both kept landing on `needs-input`. The surface verdicts varied — sometimes code-review:fail, sometimes security-review:fail, sometimes applier:fail — but the underlying findings were the same small set repeating.

Earlier sessions had landed Phases A through F of the "no-Claude-git" rollout — moving every git/gh operation out of Claude's turn into the entrypoint so the agents never need write credentials. Phase F specifically pre-installed composer + npm + merged development in the builder entrypoint to remove ~10 turns of build-env setup.

Phase G was the proposed next step: scope mechanical checks to the PR diff so inherited debt in unchanged files doesn't block new PRs.

### Session start

First decidesk status check showed:

```
[supervisor] handle_completions: review fail on decidesk#45 — escalating to needs-input
[supervisor] handle_completions: review fail on decidesk#44 — escalating to needs-input
...  (same two lines every ~40s)
```

Two supervisor processes running in parallel — both spamming the issues with fresh `**Pipeline escalation**` comments every cycle. Since yesterday: **134 comments on #44, 99 on #45**. Label-set was idempotent but comment-post wasn't, and the completion-handler had no terminal-state guard.

This was bug #1: **supervisor spam** ([ADR in CLAUDE.md "Terminal-state guards"](../../CLAUDE.md#terminal-state-guards)). Both supervisors killed, fix bundled into Phase G's PR.

### Phase G implementation

The idea: the 8 mechanical hydra-gates (`scripts/run-hydra-gates.sh`) iterate `lib/**/*.php` repo-wide. When a PR edits some files and leaves others untouched, pre-existing debt in the untouched files still shows up as FAIL. decidesk#44 and #45 were both being blocked by 2 findings in `lib/Controller/SettingsController.php` — a file neither PR touched. The reviewer could see the failures but couldn't bound-fix them (out of diff scope). Result: every cycle re-bounced on the same debt.

Phase G added `--scope-to-diff [--base BRANCH]` to `run-hydra-gates.sh`:
- Derive `CHANGED_FILES = git diff --name-only --diff-filter=ACMR BASE...HEAD` once
- Every gate's file loop filters through `_in_scope "$f" || continue`
- Gate 4 (composer-audit) skips entirely unless `composer.json`/`composer.lock` is in diff
- Gate 6 (orphan-auth) scopes the *defining* file but keeps caller grep repo-wide

All four pipeline positions that invoke gates use the new flag (builder Rule 0b + reviewer pre/post-flight + security pre/post-flight). The applier doesn't invoke gates — it consumes verdicts.

Smoke test on PR#131 (feature/47 branch):
- Full-repo scan: 2 FAIL (`SettingsController.php`, unchanged)
- `--scope-to-diff --base origin/development`: **ALL 8 GATES GREEN** on the 19 changed files

Shipped as [PR#133](https://github.com/ConductionNL/hydra/pull/133) + [ADR-020](../../openspec/architecture/adr-020-gate-scope-to-pr-diff.md).

### First post-Phase-G validation

Applied `retry:queued` to #44 and #45 (stripped `needs-input` + `code-review:fail` + `security-review:fail`, set `code-review:queued`). Rebuilt all 5 images locally (nextcloud-test + builder + reviewer + security + applier), set `HYDRA_IMAGE_PREFIX=localhost/hydra` + `HYDRA_IMAGE_TAG=test` in `secrets/.env`, restarted supervisor.

First observation: supervisor dispatched reviewers on **`ghcr.io/conductionnl/hydra-reviewer:latest`** — not the local images. My `.env` edit had no effect.

**Bug #2: `secrets/.env` was documented but not sourced.** `hydra-supervisor.sh` and `orchestrate.sh` both have `# Reads: secrets/.env` in their header comments, but neither actually sourced the file. HYDRA_IMAGE_PREFIX / HYDRA_IMAGE_TAG overrides were silently ignored unless exported in the parent shell first.

Fixed by adding `set -a; . secrets/.env; set +a` at the top of both scripts. Shipped as [PR#134](https://github.com/ConductionNL/hydra/pull/134).

### Phase G validation — first pass

After restart on local images:

```
[INFO] Pre-flight hydra-gates: 0 failing gate(s)   # on decidesk#44
[INFO] Pre-flight hydra-gates: 0 failing gate(s)   # on decidesk#45
```

Both issues cleared code review. The `SettingsController` debt that had been blocking them for days was now correctly out of scope. Phase G was working.

Then:
- #44 → `code-review:pass` → `security-review:pass` → `applier:running` → **`applier:fail`**
- #45 → `code-review:pass` → **`security-review:fail`**

Two different failure modes. The applier was supposed to be the backstop; what happened?

### The applier 0-turn bug

Applier verdict JSON for #44:

```json
{"ran": true, "pass": null, "blocking": [], "turns": 0, "cost_usd": 0.0}
```

Zero turns. Claude never completed a message. Checking the transcript:

```
[INFO] Config loaded: container=hydra-applier max_turns=20 tools=Read,Bash
[prefetch] Fetching PR #127 context from ConductionNL/decidesk...
/usr/local/lib/hydra/entrypoint-common.sh: line 426:
    /workspace/pr-context/diff.patch: No such file or directory
```

`mkdir -p /workspace/pr-context 2>/dev/null || true` and all the subsequent `>` redirects silently failed. No PR diff, no inline comments, no summary comments, no `/workspace/claude-output.jsonl` sink for Claude's output.

Reason: `/workspace` was `root:root 0755` in the applier image. Applier runs as `claude:claude` (uid 1000) with a minimum cap set — no `DAC_OVERRIDE`, no `SETUID`. The other personas (builder / reviewer / security) run with those caps and chown `/workspace` in the entrypoint; the applier can't chown at runtime and has no privilege to bypass the read-only ownership.

**Bug #3: applier `/workspace` not pre-chowned at image build time.**

Smoke test confirmed:
```
$ docker run --rm --user claude:claude --entrypoint sh localhost/hydra-applier:test \
    -c 'touch /workspace/.test && mkdir -p /workspace/pr-context'
touch: cannot touch '/workspace/.test': Permission denied
```

Fix (in the Dockerfile, not the entrypoint, because the applier CANNOT chown at runtime):

```dockerfile
RUN mkdir -p /workspace && chown claude:claude /workspace && chmod 0775 /workspace
```

This is the [container capability profiles section of ADR-013](../../openspec/architecture/adr-013-container-pool.md#container-capability-profiles) — **minimum-cap personas must be pre-chowned at image build**. Shipped as [PR#135](https://github.com/ConductionNL/hydra/pull/135).

### The security-review:fail on #45

Different story. Clyde's verdict on #45:

- ✅ composer audit / npm audit / gitleaks / semgrep / all 8 hydra gates — clean
- ❌ Manual OWASP review: 2 WARNING findings + 1 SUGGESTION
- Verdict: FAIL (WARNINGs unfixed)

The WARNINGs: `authorizeAssignment()` and `authorizeReminder()` in `DecisionApprovalService` accept `$uid` but never use it. Any authenticated user could trigger them on any decision.

The fix was obvious from reading the file: `transitionLifecycle()` five methods above had the exact pattern — `checkUserRole($uid, ['chair','secretary'])` in a try/catch, converting to `OCSForbiddenException`. Mirror that. Maybe 5–7 lines.

Clyde had declined across **eight review cycles** between 2026-04-21 and 2026-04-23, each time citing "exceeds 3-line bounded fix scope" or "architectural decision needed". Clyde was following the rule honestly — the rule said fixes must be "1–3 lines in one file" and this was 5–10.

**Bug #5: bounded-fix scope was defined by line count, which is wrong-shaped for common auth patterns.**

Meanwhile — a sub-observation about the **builder**: the builder in earlier retry cycles had been playing whack-a-mole with gate-7 (no-admin-IDOR). Gate-7 checks that `@NoAdminRequired` methods have an in-body auth guard (regex for `->authorize*` / `->require*` / `->ensure*` calls). When the gate fired on `assignReviewer`, the builder added `$this->approvalService->authorizeAssignment()` in the controller body AND created the empty stub method on the service to make that compile. Gate-7 passed (call exists). Clyde's semantic review caught that the method was a stub. Builder didn't have to implement real auth to pass the gate — only to call a method with the right name.

Fix (this retrospective's ADR-021): **scope by change shape, not line count.** The new rule:

> If a sibling method in the same class demonstrates the fix, the "architectural decision" escape hatch does NOT apply.

`transitionLifecycle` exists → `authorizeAssignment` must mirror it → mechanical → Clyde fixes.

Shipped as [PR#136](https://github.com/ConductionNL/hydra/pull/136) + [ADR-021](../../openspec/architecture/adr-021-bounded-fix-scope-by-shape.md).

---

## The builder's "minimum to clear the gate" anti-pattern

The decidesk#45 story exposed a subtler failure mode I want to call out separately because it's likely to recur.

When the builder is in `HYDRA_MODE=fix` (retry cycle), it reads `feedback.md` — a digest of the previous cycle's findings. For findings of the form "gate-X failed on method Y", the builder's cheapest path is:

1. Parse the gate's failure message: "missing auth check in `assignReviewer`"
2. Add the minimum code that clears the gate: `$this->approvalService->authorizeAssignment()` on line Y
3. Create an empty stub method if the call target doesn't exist

Gate-7's regex just looks for the call syntax. It doesn't verify the target method actually enforces authorization. So the empty stub clears the gate. Builder commits. Code-review:queued. Juan passes. Security:queued. Clyde reads the stub and correctly flags it as empty.

**The anti-pattern**: deterministic gates that check form, not substance, let the builder minimize effort in a way that's visible only to semantic review. This is harmless if the reviewer catches it AND can fix it — but with the old bounded-fix rule, the reviewer couldn't fix it either ("architectural").

**The counter-measure** (not yet implemented, noted for future work): harden gate-7 to detect stub-shape auth methods — method body that accepts a `$uid` parameter but never references it. A rough grep: `function authorize(...$uid,...).*\{ *[^}]*\}` that doesn't contain `$uid`. This closes the minimum-to-clear path at the gate level.

---

## What we shipped

- [PR#133](https://github.com/ConductionNL/hydra/pull/133) — Phase G (`--scope-to-diff` + supervisor spam guard)
- [PR#134](https://github.com/ConductionNL/hydra/pull/134) — `secrets/.env` sourcing + banner glitch cosmetic
- [PR#135](https://github.com/ConductionNL/hydra/pull/135) — Applier `/workspace` Dockerfile chown
- [PR#136](https://github.com/ConductionNL/hydra/pull/136) — Bounded-fix scope by change shape

Four PRs, all admin-merged to `development`. Three new rules formalised ([ADR-020](../../openspec/architecture/adr-020-gate-scope-to-pr-diff.md), [ADR-021](../../openspec/architecture/adr-021-bounded-fix-scope-by-shape.md), and the [Container capability profiles section of ADR-013](../../openspec/architecture/adr-013-container-pool.md#container-capability-profiles)). Two CLAUDE.md rules documented (config override contract, terminal-state guards).

---

## Lessons

1. **Silent error suppression in entrypoints masks ownership bugs.** `mkdir -p ... 2>/dev/null || true` and `> file 2>/dev/null` patterns are meant to tolerate transient failures, but they also hide fundamental ownership issues that make the whole flow non-functional. A non-fatal error that happens on EVERY run is not transient — it's a bug. Prefer `mkdir -p ... 2>&1 | tee /tmp/mkdir.log; test -d ...` or explicit assertions for things that must exist.

2. **Documented behaviour ≠ implemented behaviour.** Both `hydra-supervisor.sh` and `orchestrate.sh` claimed to read `secrets/.env` in their header comments, but neither did. Headers rot. If the behaviour matters, test for it — a `.env.example` with a recognisable sentinel that fails the build if the entrypoint doesn't surface it would have caught this instantly.

3. **Deterministic gates that check form, not substance, can be mechanically satisfied.** Builder exploited gate-7's regex-based check to create stub methods. Gate design matters: gate what the system semantically needs (an auth method that uses the UID), not what it syntactically expects (a call at a certain line).

4. **The no-loop policy has zero tolerance for infrastructure gaps.** In a loop-based pipeline you can retry through a transient mkdir failure. In a no-loop pipeline, one `root:root` directory turns into `applier:fail` and a human escalation. This is the right trade-off — it forces us to build rock-solid infrastructure — but it means every infrastructure edge case that would be papered over in other systems shows up as a hard verdict here.

5. **"Architectural" is a category, not an escape hatch.** When a reviewer says a fix is "architectural", the real question is: *does this require a NEW decision, or does it apply an existing one?* If the pattern exists in the same file, there's no new decision. The old bounded-fix rule treated "5 lines" as architectural; the new rule treats "new concept" as architectural. Much better.

6. **Retrospectives are cheap. Write them.** This session found and fixed five distinct pipeline bugs, each worth a paragraph of future-me context. Without writing it down, the next pipeline contributor relearns the whole stack the hard way.

---

## Open follow-ups

- Harden gate-7 against stub-shape auth methods (the builder's "minimum-to-clear" path)
- Phase G.1: scope `composer check:strict` / `phpunit` / `npm run lint` to the PR diff too. Currently still full-repo because `composer`/`phpunit` don't accept per-file args cleanly. Deferred; the reviewer's manual scope filter still works as safety net.
- Consider a "gate coverage test" skill that asserts each gate catches the patterns it claims to. Currently we find gate gaps only when a PR exploits one.
