#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""ADR-082 — a publicly reachable controller method carries a volume ceiling.

🔑🔥🔥 THERE ARE TWO WAYS TO DECLARE A PUBLIC PAGE AND A GATE THAT KNOWS ONE
OF THEM REPORTS ZERO FOR THE OTHER.

    #[PublicPage]      the attribute form
    @PublicPage        the legacy annotation, still honoured by the server

Measured 2026-08-14. A fleet sweep line-anchored the ATTRIBUTE form — a
correction made for a good reason, because an earlier count had matched the
attribute name where it appeared inside docblocks. That fix was right about
docblock *mentions* and wrong about the annotation, which is not a mention of
anything. It is a live declaration, proven twice against the running server:

    openregister GraphQLController::execute   @PublicPage only -> 200 anon
    opencatalogi CatalogiController::index     @PublicPage only -> 200 anon

The sweep reported the fleet fully throttled. Re-measured counting both forms:
361 public methods, 161 throttled, **200 unthrottled** — 199 of them declared
in the form the instrument could not see. This gate exists so that number
cannot silently return.

WHAT COUNTS AS A CEILING

    #[AnonRateLimit]        anonymous volume ceiling — the control for a
                            public read or CRUD endpoint
    #[UserRateLimit]        the authenticated companion
    #[BruteForceProtection] the credential/token control

Any one of them satisfies this gate. Which is APPROPRIATE is a judgement the
gate does not make: brute-force protection on an endpoint with no credential
to check is the inert half of a two-half mechanism, and this gate would still
pass it. It measures presence of a ceiling, not fitness of one.

WHY THE BLOCK IS READ BY A BACKWARD LINE SCAN

The first checker written for this used a regex over the attached docblock and
did not flag the endpoint already proven vulnerable — an instrument built the
same way as the thing it checks, reporting zero, reading as a pass. The scan
below walks up from the `function` line collecting docblock, attribute and
comment lines until it reaches real code.

Exit codes follow the suite convention:

    0   pass
    1   findings (count them from the ``FAIL`` lines)
    3   empty scope — nothing to inspect, which is a SKIP and not a pass
    4   the app exposes no public endpoint at all

Every run ends with a ``checked N file(s)`` line. A run that stops before it is
a crash, not a clean tree.
"""

# Python on the runners may predate PEP 585 evaluation at def time; an
# annotation like `list[str]` in a signature is a TypeError at import there.
# A gate that dies at import prints nothing, and nothing reads as zero
# findings — the exact failure this file is here to prevent.
from __future__ import annotations

import argparse
import os
import re
import sys

_FUNC = re.compile(
    r'^\s*(?:final\s+|abstract\s+|static\s+)*'
    r'(?:public|protected|private)\s+(?:static\s+)?'
    r'function\s+([A-Za-z0-9_]+)\s*\('
)

# The annotation must be the whole tag on its own docblock line. Anchoring it
# this way is what keeps a prose mention out of the count.
_PUBLIC_ANNOT = re.compile(r'^\s*\*\s*@PublicPage\s*$')
_PUBLIC_ATTR = re.compile(r'^\s*#\[.*\bPublicPage\b')

_THROTTLE = re.compile(
    r'\bAnonRateLimit\b|\bUserRateLimit\b|\bBruteForceProtection\b'
)

# Lines that legitimately sit between a docblock and its function.
_ATTACHED = re.compile(r'^\s*(?:/\*|\*|\*/|#\[|//|\])')


def _read(path: str) -> str:
    try:
        with open(path, encoding='utf-8') as fh:
            return fh.read()
    except OSError:
        return ''


def _php_files(root: str, sub: str = 'lib') -> list:
    out = []
    for dirpath, _dirs, files in os.walk(os.path.join(root, sub)):
        for name in files:
            if name.endswith('.php'):
                out.append(os.path.join(dirpath, name))
    return sorted(out)


def _attached_block(lines: list, idx: int) -> list:
    """Return the docblock/attribute lines immediately above ``lines[idx]``."""
    out = []
    i = idx - 1
    while i >= 0:
        line = lines[i]
        if line.strip() == '':
            # A blank line is part of the block only if the block continues
            # above it — otherwise it is the gap after the previous member.
            if i > 0 and _ATTACHED.match(lines[i - 1]):
                out.append(line)
                i -= 1
                continue
            break
        if _ATTACHED.match(line):
            out.append(line)
            i -= 1
            continue
        break
    out.reverse()
    return out


def public_methods(src: str) -> list:
    """Yield (method, form, throttled) for every publicly reachable method."""
    lines = src.split('\n')
    found = []
    for idx, line in enumerate(lines):
        m = _FUNC.match(line)
        if not m:
            continue
        blk = _attached_block(lines, idx)
        if not blk:
            continue
        annot = any(_PUBLIC_ANNOT.match(b) for b in blk)
        attr = any(_PUBLIC_ATTR.match(b) for b in blk)
        if not (annot or attr):
            continue
        form = 'annotation' if annot and not attr else (
            'attribute' if attr and not annot else 'both')
        throttled = any(_THROTTLE.search(b) for b in blk)
        found.append((m.group(1), form, throttled))
    return found


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    # The runner invokes gates as `check_x.py .`; --root is accepted too so the
    # helper can be pointed at an app tree by hand during triage.
    parser.add_argument('root', nargs='?', default='.')
    parser.add_argument('--root', dest='root_opt', default=None)
    args = parser.parse_args(argv[1:])
    root = args.root_opt or args.root

    if not os.path.isdir(os.path.join(root, 'lib')):
        print('no lib/ directory, so no controller was inspected.')
        print('checked 0 file(s)')
        return 3

    files = _php_files(root)
    if not files:
        print('lib/ contains no PHP files, so nothing was inspected.')
        print('checked 0 file(s)')
        return 3

    findings = []
    public_total = 0
    for path in files:
        src = _read(path)
        for method, form, throttled in public_methods(src):
            public_total += 1
            if throttled:
                continue
            findings.append(
                'FAIL %s::%s is public (%s form) with no volume ceiling — add '
                '#[AnonRateLimit(limit: N, period: 60)] (ADR-082). Anonymous '
                'callers can call it without limit.'
                % (os.path.relpath(path, root), method, form)
            )

    if public_total == 0:
        print('this app declares no #[PublicPage] or @PublicPage method under '
              'lib/, so ADR-082 has no subject matter here.')
        print('checked %d file(s)' % len(files))
        return 4

    for line in findings:
        print(line)
    print('%d public method(s), %d throttled, %d unthrottled'
          % (public_total, public_total - len(findings), len(findings)))
    print('checked %d file(s)' % len(files))
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
