<!--
SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
SPDX-License-Identifier: EUPL-1.2
-->

# Proposal: check the surface, not just the name

Status: proposed, not built. Written 2026-09-09 so the next person does not
have to rediscover the argument.

## The gap

Gate-114 (`stale-fleet-app-id`) catches an app naming another app by an id or
namespace that app no longer answers to. It reads names. It cannot read the
other app's method or route surface, and it says so on every run.

That leaves a second failure mode uncovered, and it is the more dangerous of
the two, because a fix for the first one can walk straight into it.

## Why this is not theoretical

Two independent sweeps hit this in one day.

**The clearest case has no rename in it at all.** Launchpad's cross-app
GraphQL layer builds `/apps/<app>/graphql`. No fleet app publishes that route
under any name; OpenRegister serves GraphQL at `/apps/openregister/api/graphql`.
Every name in that call site is current, so a name-only check reads it as
clean, and it has never worked. That is the whole argument in one line: the
name half and the surface half are different problems, and being clean on the
first says nothing about the second.

**A named app can have no app id at all.** The same launchpad map,
`SPEND_SOURCES`, has exactly two entries: `procest`, a retired id, and
`financeq`. `ConductionNL/financeq` is a real repository, archived, last
pushed 2026-07-16, described as a bookkeeping engine with specs pending. It
carries no `appinfo/` directory on `main` or `development` and no `info.xml`
anywhere, so it has no app id, nothing mounts it, and `/apps/financeq/...`
cannot resolve on any instance. It exists as specs and was never an
installable app. Both halves of that widget's data layer were therefore
written against a fleet that does not exist in this shape, which is a
provenance question about the feature rather than a naming one. It is also
why repointing `procest` there would have been cosmetic.

Note what this costs a checker. "Is this id retired" is answerable from a
rename map. "Does any installed app answer to this id" is not, because apps
outside the fleet are legitimate targets: `libresign`, `theming` and
`admin_notifications` all appear in fleet code and none of them is ours. So
an unknown id cannot simply be failed, and telling the two apart needs the
same fleet-wide surface knowledge the rest of this proposal argues for.

Dossiq PR #2061 then fixed seven cross-app defects. Gate-114 would have caught
five. The two it misses are the two that look like fixes.

**A method that never existed.** `BeschikkingGenerationService` asked the
container for `OCA\Docudesk\Service\DocumentService` and called
`generateFromTemplate()` on it. Filinq is docudesk renamed. Repointing the
namespace to `OCA\Filinq` is correct and gate-114 would demand it. It also
changes nothing: filinq's `DocumentService` has never published
`generateFromTemplate()`. The call throws into the same catch, produces the
same text stub in place of every generated PDF, and the diff reads as a
repair.

**An FQCN wrong on three axes at once.** launchpad's `LiveTileService`
resolved `OCA\OpenConnector\Service\DashboardDataSourceService` and called
`resolveDashboardValue()` on it. The real class is
`OCA\Integriq\Service\Datasource\DashboardDatasourceService`: a different
app id, a namespace segment shorter, a capital S out, and the method is
`resolve()`. `git log -S` over openconnector's full 3944-commit history shows
neither the class nor the method has ever existed under either name.
Connector-mode live tiles have therefore never worked, and the rename merely
added a second reason for the same silence. Correcting the namespace prefix,
which is all a name-only check can ask for, leaves it exactly as dark. The
practical rule for anyone repointing an FQCN by hand is to open the class
file rather than fix the prefix; the point of this proposal is that a check
should do that for them.

**A route that was retired, not renamed.** `PdokService` called
`linkToRoute('openconnector.pdok.parcel')` behind an
`isInstalled('openconnector')` guard. Integriq publishes four PDOK routes and
parcel is not among them. Here the stale name was the only thing keeping the
crash off: on a current instance the guard answers false and the method
returns early. Correcting the id alone, which is exactly what gate-114 asks
for, turns a quiet empty list into an uncaught `RouteNotFoundException`.

So a gate that clears only the name half can make a repo worse, and it will
report green doing it.

**A signature that cannot be satisfied.** openregister's `PdokGeocoder`
resolves the right class under the right name and calls
`$callService->call(null, ...)`. Integriq's `call()` takes a non-nullable
`ObjectEntity $source`. Correct app, correct namespace, correct method, a call
that can never succeed, and the surrounding catch swallows it. Nothing about
that site is a naming defect, and a name-only check reports it clean.

**"The class was removed" and "the class was renamed" look identical.** The
same file resolves `OCA\OpenConnector\Db\SourceMapper`. Integriq has no
`lib/Db` at all: its `SynchronizationService` reimplements
`SourceMapper::findOrCreateByLocation()` over object storage, and its own test
carries a comment recording the removal. A name-only check can only ask for
the prefix to be corrected, which swaps a lookup that misses for one that
misses identically.

## What would close it

Read the other side. Two artefacts are enough for most of the surface:

1. **`appinfo/routes.php`** gives every route name and URL an app publishes.
   A `linkToRoute('<app>.<controller>.<method>')` or a `/apps/<app>/<path>`
   literal can be resolved against it exactly. This also catches a route that
   changed SHAPE rather than name: dossiq asked for `/lookup?id=` where
   integriq mounts `/lookup/{id}`, and a missing path segment 404s just as
   silently as a wrong app name.
2. **The public method surface of a resolved class.** A
   `$container->get('OCA\X\Service\Y')` followed by `->z()` is a checkable
   claim: does `Y::z()` exist and is it public? PHP reflection over the other
   app's checkout answers it without running anything.

Gate-67 (`openregister-contract-parity`) already reads another repo to judge
this one, so the mechanism exists and the precedent is set. This proposal is
that shape pointed at the fleet's peer apps rather than at the engine.

## The hard part, stated honestly

**Which checkout, and at which ref.** An app's consumers are on many releases
at once. Parity against the target's `development` reports a break that no
released instance has yet, and parity against `main` misses one that
`development` already shipped. Both are wrong for someone. The least wrong
answer is probably: judge against the target's `main`, warn against its
`development`, and say which in the message. That decision needs making
before any code.

**A resolver defeats reflection on purpose.** `FleetAppId::getService()`
returns `object|null` by design, so the call site has no declared type and
static analysis cannot say which class `->z()` lands on. The checker would
have to follow the canonical name and relative class name passed to the
resolver, which is tractable because both are literals, but it is not a
general solution and it will not survive someone building the FQCN by
concatenation.

**Cost.** Every fleet repo would need the other 20 available at check time.
That is a real CI expense and the thing most likely to sink this. A cheaper
first cut: check only the routes, only for the peers a repo actually names,
resolved from a small manifest of route tables published by each app rather
than by cloning it.

## Recommendation

Do not build this as a blocking gate. Build the route half first, warning
only, on the peers a repo already names. Measure the false-positive rate the
way gate-114's was measured: run it against a commit where the defect is
known to exist and against the commit that fixed it, and report both numbers.
If the route half earns its keep, the method half is the same machinery
pointed at a class instead of a URL.

Until then, gate-114 prints its own blind spot on every run, and this file is
what that line points at.
