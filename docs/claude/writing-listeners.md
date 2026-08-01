# Writing OpenRegister Object Listeners

Reference for authoring listeners on OpenRegister object lifecycle events in Conduction apps. Consolidates ADR-078 (work placement), ADR-076 (per-request setup cost) and ADR-020 (diff-scoped gates). Read this before adding a listener or converting an existing one.

Enforced mechanically by **gate 61 `listener-work-placement`** in `scripts/run-hydra-gates.sh`.

## The one rule

**Post-`*ed` work is asynchronous by default. Synchronous is the exception, and it must be named.**

The event suffix already encodes the line:

| Suffix | Events | The write has… | Placement |
|---|---|---|---|
| `*ing` (pre) | `ObjectCreatingEvent`, `ObjectUpdatingEvent`, `ObjectDeletingEvent` | …not happened | **Synchronous.** This is the only place a listener can veto or mutate. |
| `*ed` (post) | `ObjectCreatedEvent`, `ObjectUpdatedEvent`, `ObjectDeletedEvent` | …already happened | **Asynchronous.** Nothing you do can change the write. Every millisecond is latency the user pays for a result they already earned. |

**134 of the fleet's 149 object-lifecycle registrations are post-events.** That is the population this rule governs.

Choosing `*ing` because "I need it to run first" is the wrong reason — a pre-event listener holds the write open and its exception can fail the save. Use `*ing` only when the listener genuinely needs to veto or mutate.

## Deferring the work

Route it through OpenRegister's `ListenerDeferralService`:

```php
use OCA\OpenRegister\Service\Deferral\ListenerDeferralService;

public function __construct(
    private readonly ListenerDeferralService $deferral,
) {
}

public function handle(Event $event): void {
    if (!$event instanceof ObjectCreatedEvent) {
        return;
    }

    $this->deferral->defer(
        jobClass: MyRollupJob::class,
        entry: [
            'uuid'     => $event->getObject()->getUuid(),
            'register' => $event->getObject()->getRegister(),
            'schema'   => $event->getObject()->getSchema(),
        ],
        dedupeKey: $event->getObject()->getUuid(),
    );
}
```

`defer()` buffers per job class, coalesces on `dedupeKey` (N bulk writes to one schema become one job), flushes full chunks immediately and the remainder at request shutdown, and is fail-soft — a capture or enqueue failure is logged and never breaks the save that triggered it.

### ⚠️ A deferred path MUST carry the acting user

This is the failure mode that costs the most time, because it produces no evidence at all.

**A background job has no session.** `IUserSession::getUser()` returns `null` in a cron worker. If your deferred work does not carry the acting user forward, then inside the job:

- the user-scoped query returns nothing,
- the RBAC/multitenancy filter matches nothing,
- the handler walks an empty result set,
- the job completes, throws nothing, logs nothing, produces zero effects, and **reports success.**

A flawless no-op. Green pipeline, green job queue, green logs, and the feature does not exist.

`ListenerDeferralService` exists precisely to close this: it captures the acting context (user + organisation) **once per request** on the first `defer()` call, and enqueues `ActorForwardedJob` subclasses that re-establish it. Do not hand-roll `IJobList::add()` and assume the job inherits a user — it does not.

A `null` userId is legitimate when the write itself came from `occ` or cron. Null *because you never captured it* is not, and the two are indistinguishable from inside the job. Capture at the registration/dispatch site, not at the consumption site.

## When synchronous is legitimate — the four CLOSED categories

ADR-078 D2 defines exactly four. The set is closed: a fifth needs an ADR amendment, not a new string in a docblock.

| Category | Meaning | Example |
|---|---|---|
| `realtime` | the listener *is* the latency channel; deferring it defeats its purpose | `NotifyPushListener` |
| `sapi-memory` | state lives in per-SAPI shared memory, so a cron worker writes a **different segment** | `GraphQLSubscriptionListener` → `SubscriptionService::pushEvent()` → `apcu_store()` |
| `cheap-bounded` | one bounded statement; a job row plus a cron round-trip costs more than the work | `ObjectMetricsListener` (one fail-soft INSERT) |
| `correctness` | delayed execution is not merely late, it is **wrong** | `NotificationDedupePruneListener` — a prune landing after a same-UUID re-create wipes freshly-armed state |

The `sapi-memory` case is worth internalising because it inverts the usual intuition: deferring it does not make the listener slower, it **silently breaks it**. APCu is per-SAPI. The cron worker's `apcu_store()` writes a segment the web SAPI's SSE reader never reads. No error, no log — the subscription just never fires. "Defer if slow" would have gotten this exactly backwards, which is why the categories are about *mechanism*, not duration.

### The annotation

Put it in the docblock of the **handler method**:

```php
/**
 * @listener-placement inline sapi-memory — SubscriptionService::pushEvent stores
 *  via apcu_store, and APCu is per-SAPI; a cron worker writes a different segment
 *  than the SSE reader, so deferring does not delay this listener, it breaks it.
 */
public function handleObjectCreated(ObjectCreatedEvent $event): void
```

A reason wrapping onto the next docblock line still counts.

**All three of these FAIL gate 61**, each with its own message:

```php
/** @listener-placement inline */                        // bare — no category
/** @listener-placement inline performance — it's fast */ // not one of the four
/** @listener-placement inline cheap-bounded */           // category, no reason
```

Same auditable shape as `@spec exclude <reason>` (gate 16) and `@e2e exclude <reason>` (gate 19): the escape hatch is visible to a reviewer, never silent.

## Declaring register/schema interest

Listeners register **globally**. Every listener in every enabled app is invoked on every object write instance-wide and then self-filters — procest's `BezwaarLifecycleListener` wakes up when you create a larpingapp character. Deferral moves those wakeups off the request; it does not remove them. Narrowing does.

**Declare the interest at the REGISTRATION SITE**, not inside the handler.

### ⚠️ The declaring call MUST be in `boot()`, NOT `register()`

`OC\AppFramework\Bootstrap\Coordinator::registerApps()` loops over the enabled apps and, for each one, **enables that app's autoloader immediately before calling that app's own `register()`** — inside the same iteration:

```php
foreach ($appIds as $appId) {
    // First, we have to enable the app's autoloader
    OC_App::registerAutoloading($appId, $path);
    // Next we check if there is an application class …  ->register($context)
}
```

OpenRegister sits at index **51 of 92** in that order (measured on the development instance). Every app earlier in the list runs its `register()` before OpenRegister's autoloader exists. So a narrowing declaration written in `register()` that guards on `class_exists(ObjectEventSubscription::class)` sees **`false`**, takes the fallback branch, and registers **unfiltered** — with no error, no warning and no log line.

**This silently no-op'd 7 conversions.** They looked done, passed review, and changed nothing.

`boot()` runs after every app's `register()` has completed, so the class is there. Put the declaring call in `boot()`.

```php
public function boot(IBootContext $context): void {
    // Safe here: every app's autoloader is enabled by the time boot() runs.
    if (class_exists(\OCA\OpenRegister\Event\ObjectEventSubscription::class)) {
        // …declare register/schema interest…
    }
}
```

If you write the `class_exists()` guard, prove which branch you took. A guard that always takes the fallback is indistinguishable from a guard that is never needed.

## Verifying a listener — a positive control is MANDATORY

This is the section that matters most.

The standard way a listener conversion is declared done and is not: the test asserts that **the handler returns early for an unrelated schema**.

That assertion passes identically against:

- a listener that is correctly narrowed, **and**
- a listener that does nothing at all,
- a listener that was never registered,
- a listener whose app is disabled,
- a listener whose deferred job no-ops for want of an actor.

A negative-only assertion cannot distinguish "correctly filtered" from "dead". It is the single cheapest false green in the codebase.

This is not hypothetical. **74 listeners across the fleet have never run** — scholiq 42 of 43, shillinq 19 of 19 — and every existing test and every gate stayed green the entire time.

**So: prove the handler runs and produces its effect for a MATCHING input first.** Only then is the early-return assertion meaningful, because only then do you know there is something to return early *from*.

A usable order:

1. **Positive control.** Write a matching object. Assert the listener's *effect* — the row, the job, the file, the notification. Not that the handler was entered; that the world changed.
2. **Negative control.** Write a non-matching object. Assert the effect did **not** happen.
3. **Actor control** (deferred paths only). Run the enqueued job the way cron runs it — no session — and assert the effect still happens. If it only works when you run it inline, the actor is not being forwarded.

### "Mounted" ≠ "enabled" ≠ "running"

Three separate facts, and each one can be true while the next is false:

- the checkout is bind-mounted into the container — **mounted**
- `occ app:list` shows it under Enabled — **enabled**
- the listener's effect is observable after a write — **running**

Planix was mounted with a correct checkout and still completely inert, because the app was **disabled**. Everything read as green.

Check all three. The only one that means anything is the third.

## Honest limits

State these rather than let them be mistaken for coverage:

- **Roughly half the fleet's listeners cannot be statically declared.** Their register/schema interest comes from runtime configuration or an admin UI, so no registration-site declaration can express it. They will keep waking up on every write. Deferral still applies; narrowing does not.
- **`ObjectUpdatingEvent` has no `getObject()`.** It is the only object event without one — it exposes `getNewObject()` / `getOldObject()` instead. Any narrowing proxy that reads `getObject()` to decide whether to invoke a listener therefore **fail-opens** on it, which makes narrowing on `ObjectUpdatingEvent` **inert**. Do not count it as covered.
- **Gate 61 is a heuristic, not a proof.** It sees outbound I/O, writes, and unbounded `findAll()`. A post-event handler that burns 400 ms of pure CPU passes it cleanly.
- **A `function_exists()` probe run under `occ` measures the CLI SAPI** and tells you nothing about `fpm-fcgi` or `apache2handler`. SAPI-dependent behaviour must be probed from a real web request.

## Checklist

Before opening the PR:

- [ ] Registered on `*ed` unless the listener genuinely vetoes or mutates.
- [ ] Work routed through `ListenerDeferralService::defer()`, **or** annotated `@listener-placement inline <category> — <reason>` with one of the four closed categories.
- [ ] Register/schema interest declared at the registration site, in **`boot()`**.
- [ ] Positive control written and passing — the effect is observable for a matching input.
- [ ] Negative control written and passing.
- [ ] Deferred job proven to work with **no session**.
- [ ] `./scripts/run-hydra-gates.sh` green on gate 61, and the run reached its summary line.

## References

- **ADR-078** — object-event listener work placement (the source rule).
- **ADR-076** — the predecessor: setup work off the per-request path. Its Rule 5 (a cheap-looking predicate MUST NOT reach an expensive aggregate) is the ancestor of the `OpenRegisterFlowResolver` finding.
- **ADR-020** — gates scope to the PR diff, not the whole repo.
- Skill: `hydra-gate-listener-work-placement` — the gate's fix actions.
- Companion: [writing-controllers.md](writing-controllers.md).
