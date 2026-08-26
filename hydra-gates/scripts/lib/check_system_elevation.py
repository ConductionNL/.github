#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Gate 96 — system-elevation-reachability (ADR-099 rule 9).

`runAsSystem()` / `SystemOperationContext::run()` runs a callable as a
trusted userless principal: no RBAC, no tenancy, no owner. It exists for
work that genuinely has nobody to act for — an installation seeding its own
shipped registers, a migration, a repair step. A schema migration runs on
nobody's behalf, and pretending otherwise would mean inventing a user.

WHAT THIS GATE IS ACTUALLY DEFENDING AGAINST

Not somebody arguing for an escalation. The failure mode is somebody
reaching for the nearest thing that makes a refusal go away.

That reach is predictable, because ADR-099 put refusals everywhere an
identity can be missing: a schedule trigger that names nobody is refused, a
delegation without a grant is refused, an agent tool acting for an absent
user is refused. Every one of those refusals sits within a few lines of a
method that would make it succeed. A developer under time pressure, staring
at "this flow run has no owner", finds `runAsSystem()` in the same service
they already have injected — and the fix works, the test goes green, and
the run now executes with every access control switched off, permanently,
for every future run of that flow.

Nothing downstream can catch it. By the time the callable executes, the
caller is gone; there is no runtime assertion the method can make about who
invoked it. So the control has to be structural, and structural controls
drift unless something checks them.

THE THREE FORBIDDEN CALLERS, AND WHY THOSE THREE

ADR-099 names flow nodes, agent tools, and inbound request handling. They
are not arbitrary — each carries USER-AUTHORED DEFINITIONS or
USER-SUPPLIED INPUT across the boundary:

  * a flow node executes a graph somebody drew in a browser;
  * an agent tool executes a call a model chose, from text it was given;
  * a controller executes a request a client sent.

Elevation reachable from any of them converts "a user can describe work"
into "a user can describe work that runs as root". The other direction —
elevation in a migration — has no user in the picture at all, which is the
whole distinction.

WHY THERE IS NO EXCLUSION ANNOTATION

Most gates in this suite take a reason-bearing `@gate exclude <why>`.
This one deliberately does not, and that is the point rather than an
omission.

An escape hatch on this rule would be used exactly when somebody is trying
to make a refusal go away — the case the gate exists for — and a
reason-bearing comment written in that moment ("needed for the migration
path") is indistinguishable from a legitimate one to every reviewer who
reads it afterwards. Green bought with a plausible sentence is worse than
red, because it ends the conversation.

If this gate fires on something that is genuinely legitimate, the answer is
to move the elevation OUT of the forbidden caller — into a repair step, a
migration, or a service the caller invokes without passing user input to it
— or to fix this gate. Both leave a visible diff. A comment does not.

WHAT IT CANNOT SEE

A dynamically dispatched call (`$svc->{$method}()`, a callable stored in a
variable, a container lookup by string) is invisible to it, exactly as it
is to the PHPUnit boundary test this generalises. It is a guard against
DRIFT, not a proof of absence — and it is stated here so nobody reads a
green as the stronger claim. The control that actually holds the line is
that the elevating service is not injected into node, tool or endpoint
classes.

FULL-TREE, deliberately NOT diff-scoped. A diff-scoped version reports
nothing on the ~99% of PRs that never open a node or a controller, so it
could not establish that the boundary holds — which is the only claim worth
making about a boundary. The finding set is small enough that noise is not
a risk: on a clean repo it is empty.

Exit codes: 0 clean · 1 findings · 4 no PHP under lib/ in this repo.
"""
import os
import re
import sys

# The calls that elevate. Matched as method calls / static calls rather than
# as bare words, so a docblock sentence about `runAsSystem` does not fire —
# comments and strings are masked out anyway, but two independent guards
# against a false positive are cheap and a false positive on this gate is
# what would get it switched off.
ELEVATION_RX = re.compile(
    r'(?:->\s*runAsSystem\s*\(|SystemOperationContext\s*::\s*run\s*\()'
)

# Directory prefixes a call may NOT appear under, and the reason each is
# forbidden. The reason travels into the failure message: "forbidden" alone
# tells a developer they are blocked, not what to do instead.
FORBIDDEN = (
    (
        'lib/Service/Flow/Nodes/',
        'a flow node executes a graph a user drew, so elevation here lets a '
        'user describe work that runs with every access control off',
    ),
    (
        'lib/Flow/',
        'a flow node executes a graph a user drew, so elevation here lets a '
        'user describe work that runs with every access control off',
    ),
    (
        'lib/Controller/',
        'a controller handles an inbound request, so elevation here runs '
        'caller-supplied input as a trusted userless principal',
    ),
    (
        'lib/Service/Mcp/',
        'an agent tool executes a call a model chose from text it was given, '
        'so elevation here is reachable from a document',
    ),
    (
        'lib/Mcp/',
        'an agent tool executes a call a model chose from text it was given, '
        'so elevation here is reachable from a document',
    ),
    (
        'lib/Tool/',
        'an agent tool executes a call a model chose from text it was given, '
        'so elevation here is reachable from a document',
    ),
    (
        'lib/Tools/',
        'an agent tool executes a call a model chose from text it was given, '
        'so elevation here is reachable from a document',
    ),
)

# Where a legitimate elevation lives. Not an allowlist of files — an
# allowlist of KINDS, so a new repair step needs no gate change while a new
# controller still fails. Work in these places has no user to act for by
# construction: nobody is present during a migration.
PERMITTED = (
    'lib/Migration/',
    'lib/Repair/',
    'lib/Command/',
    'lib/BackgroundJob/',
    'lib/Cron/',
)


def _mask(src: str) -> str:
    """Blank out comments and string literals, preserving line structure.

    A gate that reads raw text reports the sentence describing the rule as a
    violation of it — this file's own docblock would fail this gate. Newlines
    survive so reported line numbers stay true.
    """
    out = []
    i = 0
    n = len(src)
    while i < n:
        ch = src[i]
        nxt = src[i + 1] if (i + 1) < n else ''
        if ch == '/' and nxt == '/':
            while i < n and src[i] != '\n':
                out.append(' ')
                i += 1
            continue
        if ch == '#' and nxt != '[':
            # `#[Attribute]` is code; `# comment` is not.
            while i < n and src[i] != '\n':
                out.append(' ')
                i += 1
            continue
        if ch == '/' and nxt == '*':
            while i < n and not (src[i] == '*' and (i + 1) < n and src[i + 1] == '/'):
                out.append('\n' if src[i] == '\n' else ' ')
                i += 1
            out.append('  ')
            i += 2
            continue
        if ch in ('"', "'"):
            quote = ch
            out.append(' ')
            i += 1
            while i < n and src[i] != quote:
                if src[i] == '\\':
                    out.append(' ')
                    i += 1
                    if i < n:
                        out.append('\n' if src[i] == '\n' else ' ')
                        i += 1
                    continue
                out.append('\n' if src[i] == '\n' else ' ')
                i += 1
            out.append(' ')
            i += 1
            continue
        out.append(ch)
        i += 1
    return ''.join(out)


def _php_files(root: str):
    """Every tracked-looking PHP file under lib/, sorted for a stable report."""
    lib = os.path.join(root, 'lib')
    if not os.path.isdir(lib):
        return []

    found = []
    for dirpath, dirnames, filenames in os.walk(lib):
        dirnames[:] = [d for d in dirnames if d not in ('vendor', 'node_modules')]
        for name in filenames:
            if name.endswith('.php'):
                full = os.path.join(dirpath, name)
                found.append(os.path.relpath(full, root).replace(os.sep, '/'))
    return sorted(found)


def _forbidden_reason(rel: str):
    """Why this path may not elevate, or None when it may."""
    for prefix, why in FORBIDDEN:
        if rel.startswith(prefix):
            return why
    return None


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    files = _php_files(root)

    if not files:
        print('checked 0 PHP file(s) under lib/ [full tree]: '
              'this repo ships no server code that could elevate')
        return 4

    findings = []
    elevating = 0

    for rel in files:
        try:
            with open(os.path.join(root, rel), 'r', encoding='utf-8', errors='replace') as handle:
                src = handle.read()
        except OSError as exc:
            # UNREADABLE IS NOT CLEAN. A file that could not be read is a file
            # whose elevation is unverified, and reporting it as a pass would
            # make the gate's green mean less than it claims.
            print(f'FAIL  {rel} could not be read ({exc}), so its elevation is UNVERIFIED.')
            findings.append(rel)
            continue

        masked = _mask(src)
        hits = [
            idx + 1
            for idx, line in enumerate(masked.split('\n'))
            if ELEVATION_RX.search(line)
        ]
        if not hits:
            continue

        elevating += 1
        why = _forbidden_reason(rel)
        if why is None:
            continue

        for line_no in hits:
            print(f'FAIL  {rel}:{line_no} — elevates to a trusted userless '
                  f'principal from a forbidden caller.')
            print(f'      {why}.')
            findings.append(rel)

    if findings:
        permitted = ', '.join(PERMITTED)
        print()
        print('      ADR-099 rule 9: elevation is code-initiated only. Move the '
              'work into a migration, repair step, command or background job '
              f'({permitted}) — or refuse, naming the missing identity. There is '
              'deliberately no exclusion annotation for this rule: an escape '
              'hatch would be used exactly when somebody is making a refusal go '
              'away, which is the case this gate exists for.')

    print(f'\nchecked {len(files)} PHP file(s) under lib/ [full tree]: '
          f'{elevating} elevate, {len(findings)} failure(s)')
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())
