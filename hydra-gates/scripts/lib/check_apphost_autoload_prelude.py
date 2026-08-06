#!/usr/bin/env python3
"""Detect AppHost adoption without the OpenRegister autoload prelude (ADR-040).

THE DEFECT
----------
`OC_App::getEnabledApps()` does `sort($apps)` (lib/private/legacy/OC_App.php),
and `Coordinator::registerApps()` walks THAT sorted list calling
`OC_App::registerAutoloading($appId, $path)` and then `$application->register()`
for ONE APP AT A TIME.

So every app's `register()` runs BEFORE the PSR-4 prefix of every
alphabetically-LATER app exists. Any leaf whose app id sorts before
`openregister` reaches `register()` while `OCA\\OpenRegister\\` is not
autoloadable — on a completely healthy instance, with OpenRegister enabled.

It has two shapes, and both are quiet:

  guarded     `class_exists('OCA\\OpenRegister\\AppHost\\...')` answers FALSE,
              so the generic AppHost plumbing is skipped. Classes that exist
              ONLY as Bootstrap DI aliases (Controller\\HealthController aliasing
              AppHost\\Controller\\GenericHealthController, ...) then fail to
              resolve and their endpoints return 500 — not 404.

  unguarded   the resulting \\Error aborts the ENTIRE register(). Every
              registerEventListener below it never runs. Coordinator catches the
              Throwable, logs an `emergency` and `continue`s, so the app stays
              enabled and keeps serving: nothing in the UI says half its wiring
              is missing.

WHY IT NEEDS A GATE
-------------------
This bug class is invisible to ordinary testing because it depends on WHICH
APPS HAPPEN TO BE INSTALLED. Any app that pulls OpenRegister's autoloader in
registers the prefix PROCESS-WIDE, masking the defect for every app that
registers after it. On a dev instance with such an app present, everything
resolves; in CI with a minimal app set, it does not. A masking app makes the
failure vanish exactly where you would test for it.

Measured twice, independently:
  * doriath   — the audit listener recorded ZERO dispatched events, because the
                unguarded Bootstrap reference aborted register() before it.
  * openconnector — its own source records `class_exists at register(): false`
                on a clean install; removing the guard took the flow-node
                registry from 10 nodes to 12.

THE REQUIRED PRELUDE
--------------------
    try {
        $orPath = \\OCP\\Server::get(\\OCP\\App\\IAppManager::class)->getAppPath('openregister');
        \\OC_App::registerAutoloading('openregister', $orPath);
    } catch (\\Throwable) {
        // OpenRegister absent/disabled — fall through to the degraded path.
    }

`registerAutoloading()` touches ONLY the autoloader and is idempotent (it
early-returns on an `$alreadyRegistered` key). `IAppManager::loadApp()` is NOT
an acceptable substitute: it sets `loadedApps[..]=true` and calls
`Coordinator::bootApp()`, booting OpenRegister before its own register() has
run — so this gate rejects it explicitly rather than accepting it as a prelude.

WHAT FAILS
----------
Anything under lib/AppInfo/ that, without the prelude:
  1. references `OCA\\OpenRegister\\AppHost\\Bootstrap` (import, FQCN or quoted
     string), or
  2. calls `class_exists()` on a literal `OCA\\OpenRegister\\AppHost\\...` name.

Both are resolved DURING register(). Lazy service closures that merely mention
an AppHost class are NOT flagged: their bodies run at resolution time, long
after every app has registered.

OpenRegister itself is exempt — it owns AppHost.

Suppress a deliberate case with a reason-bearing comment:
    apphost-prelude exclude <reason>
A bare annotation with no reason fails, same as gate 16's `@spec exclude`.

Exit 0 when clean, 1 when an app adopts AppHost without the prelude.

SPDX-License-Identifier: EUPL-1.2
SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl>
"""

from __future__ import annotations

import os
import re
import sys

# The prelude: registerAutoloading(...) whose arguments name 'openregister'.
# Tolerant of named arguments (app: 'openregister') and of `OC_App::` /
# `\OC_App::` / an imported alias, because all three appear in this fleet.
PRELUDE = re.compile(r"registerAutoloading\s*\(([^)]*)\)", re.S)
OPENREGISTER_LITERAL = re.compile(r"""['"]openregister['"]""")

# A name BOUND to the literal 'openregister' in the same blob. Three spellings:
#   const OPENREGISTER_APP_ID = 'openregister';
#   define('OPENREGISTER_APP_ID', 'openregister');
#   $openRegisterAppId = 'openregister';
# The binding must be to the EXACT literal — this resolves names, it does not
# guess at them, and a name bound to anything else is not a match.
CONST_BINDING = re.compile(
    r"""(?:
          const\s+(?P<name1>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*['"]openregister['"]
        | define\s*\(\s*['"](?P<name2>[A-Za-z_][A-Za-z0-9_]*)['"]\s*,\s*['"]openregister['"]
        | \$(?P<name3>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*['"]openregister['"]
    )""",
    re.X,
)


def _binding_name(match: "re.Match[str]") -> str:
    return match.group("name1") or match.group("name2") or match.group("name3")


# A name USED as a call argument: `self::NAME`, `static::NAME`, `Cls::NAME`,
# a bare `NAME`, or `$var`. Matched against the bound names above, never
# accepted on its own.
ARG_NAME = re.compile(
    r"""(?:(?:self|static|parent|[A-Za-z_][A-Za-z0-9_\\]*)\s*::\s*)?"""
    r"""\$?(?P<name>[A-Za-z_][A-Za-z0-9_]*)""",
)

# loadApp('openregister') is a WRONG fix, not a prelude — it boots OpenRegister
# before its own register() has run. Named so the reader is told why.
LOAD_APP = re.compile(r"""loadApp\s*\(\s*['"]openregister['"]\s*\)""")

# Rule 1 — any reference to the AppHost Bootstrap entry point. Covers
# `use OCA\OpenRegister\AppHost\Bootstrap;`, `\OCA\OpenRegister\AppHost\Bootstrap::`
# and the escaped string form 'OCA\\OpenRegister\\AppHost\\Bootstrap'.
BOOTSTRAP_REF = re.compile(r"OpenRegister\\{1,2}AppHost\\{1,2}Bootstrap")

# Rule 2 — class_exists() on a literal AppHost name. This is the probe that
# answers FALSE on a healthy instance.
CLASS_EXISTS_APPHOST = re.compile(
    r"class_exists\s*\(\s*['\"][^'\"]*OpenRegister\\{1,2}AppHost\\{1,2}[^'\"]*['\"]",
    re.S,
)

# OpenRegister owns AppHost; it cannot need a prelude for its own namespace.
OWN_NAMESPACE = re.compile(r"namespace\s+OCA\\OpenRegister\b")

# The reason must be on the SAME LINE as the annotation. `\s` would match a
# newline, which let a BARE `apphost-prelude exclude` swallow the next line of
# source as its "reason" — a suppression that explains nothing, accepted.
SUPPRESS = re.compile(r"apphost-prelude[ \t]+exclude[ \t]*(?P<reason>[^\n]*)")


def _sources(app_dir: str) -> dict[str, str]:
    """Every PHP file under lib/AppInfo/, path -> text."""
    out: dict[str, str] = {}
    root_dir = os.path.join(app_dir, "lib", "AppInfo")
    for root, _dirs, files in os.walk(root_dir):
        for name in sorted(files):
            if not name.endswith(".php"):
                continue
            path = os.path.join(root, name)
            try:
                with open(path, encoding="utf-8", errors="replace") as handle:
                    out[path] = handle.read()
            except OSError:
                continue
    return out


def openregister_aliases(text: str) -> set[str]:
    """Names bound to the literal 'openregister' somewhere in this text.

    WHY THIS EXISTS. The prelude used to be recognised only as a QUOTED literal
    inside the call parentheses:

        \\OC_App::registerAutoloading('openregister', $path);        accepted
        \\OC_App::registerAutoloading(self::OPENREGISTER_APP_ID, $path);  REJECTED

    The second form is the same call with the app id given a name, which is the
    better of the two — and doriath, which does exactly that, was reported as
    having NO prelude while its prelude sat four lines above the call. A gate
    that fails the tidier spelling of the thing it is asking for teaches people
    to write the untidy one, and its finding is not about the defect at all.

    Resolution is deliberately SHALLOW and LITERAL: a name counts only when
    this same source blob binds it to the exact string 'openregister'. We do
    not follow imports, and we do not accept a name we cannot see bound. An
    unresolvable name is still a finding — see test_unknown_constant_still_FAILS
    and test_constant_bound_to_another_app_still_FAILS, which are what stop this
    from becoming "any argument at all satisfies the gate".
    """
    return {_binding_name(m) for m in CONST_BINDING.finditer(text)} - {""}


def has_prelude(text: str) -> bool:
    """True when text calls registerAutoloading() for the openregister app.

    Accepts the app id as a quoted literal, or as any name this same blob binds
    to that literal (a class constant, a define(), or a plain variable).
    """
    aliases = openregister_aliases(text)
    for m in PRELUDE.finditer(text):
        args = m.group(1)
        if OPENREGISTER_LITERAL.search(args):
            return True
        for ref in ARG_NAME.finditer(args):
            if ref.group("name") in aliases:
                return True
    return False


def suppression_reason(text: str) -> str | None:
    """Return the reason of a reason-bearing suppression, else None.

    A BARE `apphost-prelude exclude` with no reason is not a suppression — it
    is an unexplained one, and it fails like any other unguarded adoption.
    """
    m = SUPPRESS.search(text)
    if m is None:
        return None
    reason = m.group("reason").strip().strip("*/ ").strip()
    return reason or None


def scan_app(app_dir: str) -> list[tuple[str, str]]:
    """Return [(path, why)] for AppHost adoptions with no prelude."""
    sources = _sources(app_dir)
    if not sources:
        return []

    # OpenRegister owns AppHost — exempt by namespace, not by directory name,
    # so a checkout under any directory name is still recognised.
    if any(OWN_NAMESPACE.search(text) for text in sources.values()):
        return []

    blob = "\n".join(sources.values())

    # The prelude may legitimately live in a sibling composition-root file that
    # register() calls, so look for it across the whole of lib/AppInfo/.
    if has_prelude(blob):
        return []

    if suppression_reason(blob):
        return []

    findings: list[tuple[str, str]] = []
    for path, text in sorted(sources.items()):
        if BOOTSTRAP_REF.search(text):
            findings.append(
                (path, "references OCA\\OpenRegister\\AppHost\\Bootstrap")
            )
        elif CLASS_EXISTS_APPHOST.search(text):
            findings.append(
                (path, "calls class_exists() on an OCA\\OpenRegister\\AppHost\\ class")
            )

    if findings and LOAD_APP.search(blob):
        findings.append(
            (
                os.path.join(app_dir, "lib", "AppInfo"),
                "uses IAppManager::loadApp('openregister'), which is NOT a prelude: "
                "it marks OpenRegister loaded and calls Coordinator::bootApp(), "
                "booting it before its own register() has run",
            )
        )

    return findings


APP_ID = re.compile(r"<id>\s*([a-z0-9_\-]+)\s*</id>", re.I)


def app_id(target: str) -> str:
    """The app's real id, from appinfo/info.xml, falling back to the dir name.

    The id — not the checkout directory — is what Nextcloud sorts on, so it is
    what decides whether this app is live-exposed or merely latent.
    """
    info = os.path.join(target, "appinfo", "info.xml")
    try:
        with open(info, encoding="utf-8", errors="replace") as handle:
            m = APP_ID.search(handle.read())
        if m:
            return m.group(1)
    except OSError:
        pass
    return os.path.basename(os.path.abspath(target))


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    targets = argv[1:] or ["."]
    failures = 0

    for target in targets:
        app = app_id(target)
        # Nextcloud sorts app ids with sort(), so a plain string comparison is
        # the same question it asks. Sorting after `openregister` means the
        # prefix is already on the autoloader by the time register() runs.
        live = app < "openregister"
        if live:
            severity = (
                f"LIVE-EXPOSED: '{app}' sorts BEFORE 'openregister', so this "
                f"resolves on a healthy instance to FALSE (guarded — the plumbing "
                f"is skipped and Bootstrap-aliased endpoints 500) or throws and "
                f"aborts the whole register() (unguarded)"
            )
        else:
            severity = (
                f"LATENT: '{app}' sorts AFTER 'openregister', so this happens to "
                f"work today — by alphabet alone, not by design. Renaming the app, "
                f"or moving this code into one that sorts earlier, breaks it "
                f"silently"
            )
        for path, why in scan_app(target):
            rel = os.path.relpath(path, target)
            print(
                f"FAIL {app}: {rel} {why}, but nothing under lib/AppInfo/ registers "
                f"OpenRegister's autoloader first. {severity}. Apps register in "
                f"sorted order: getEnabledApps() sort()s the list and "
                f"Coordinator::registerApps() calls registerAutoloading() then "
                f"register() one app at a time. Add the ADR-040 prelude: "
                f"$p = \\OCP\\Server::get(\\OCP\\App\\IAppManager::class)"
                f"->getAppPath('openregister'); \\OC_App::registerAutoloading("
                f"'openregister', $p); wrapped in try/catch(\\Throwable). Or add a "
                f"comment 'apphost-prelude exclude <reason>'."
            )
            failures += 1

    if failures:
        print(f"\n{failures} AppHost adoption(s) without the autoload prelude.")
        return 1

    print("apphost-autoload-prelude: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
