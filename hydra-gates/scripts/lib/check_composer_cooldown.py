#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Gate 93 — composer-cooldown-config.

Composer has no native "reject a package published in the last N days"
mechanism — unlike npm's `min-release-age` (gate 84), which this gate is
deliberately modeled on. `composer/composer#12847` tracks the upstream
request; unreleased as of this gate's authorship. Two third-party
install-time plugins were evaluated as a stopgap and rejected (ADR-093):
one requires `php ^8.4`, which breaks `composer install` on the PHP 8.3 leg
every core app's CI matrix tests; the other is PHP-compatible but, like the
first, is a ~3-month-old single-maintainer package. Installing a young,
code-executing Composer plugin fleet-wide specifically to defend against
young/malicious dependencies was left to a human decision rather than
defaulted into.

What ships instead is GitHub Dependabot's own native `cooldown:` key on the
`composer` package-ecosystem entry in `.github/dependabot.yml`. This gate
verifies it is configured, and configured correctly:

  1. a `composer` package-ecosystem entry exists at all
  2. its `cooldown.default-days` is >= 2
  3. its `cooldown.exclude` contains `conduction/*`

WHY MANDATORY, NOT SKIP-UNTIL-ADOPTED: gate 84's own history is the reason.
A gate that only checks configuration IF it happens to already be present
is a gate that never catches the repo that never adopted it — which is
"declared gate, enforced nowhere," the exact shape gate 84 itself replaced.
Once a repo has a `composer.json` (i.e. is a PHP/Composer app in this
fleet), it is expected to have adopted this — same posture gate 84 takes
for any repo with a `package.json`.

FULL-TREE, not diff-scoped — same reasoning as gate 84: a diff-scoped
version would report nothing on every PR that doesn't touch
`dependabot.yml`, almost all of them, and a gate silent on 99% of PRs
cannot establish fleet-wide conformance, which is the entire point of it.

WHY A HAND-ROLLED SCANNER, NOT PyYAML: `hydra-gates` ships zero third-party
Python packages across its ~50 helper modules. `dependabot.yml`'s shape for
this purpose — a `- package-ecosystem:` list item, sibling keys at a fixed
deeper indent, a `cooldown:` block one level deeper still, `exclude:` items
one level deeper than that — is regular enough that a narrow
indentation-aware scanner covers it correctly without a general YAML parser
this package has never needed. It does not handle flow-style YAML or
anchors; none of the fleet's dependabot.yml files use either, and a scan
that comes back structurally empty in an abnormal way reports itself as
`FAIL ... could not locate a cooldown: block` rather than a silent pass —
a wrong answer that names itself is recoverable, a wrong answer wearing the
right shape is not.

Exit codes follow the package convention: 0 clean, 1 findings, 4 not
applicable (no composer.json — this repo has no Composer surface to
harden).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

EXIT_NOT_APPLICABLE = 4

MIN_COOLDOWN_DAYS = 2
REQUIRED_EXCLUDE = 'conduction/*'

ENTRY_START = re.compile(r'^  - package-ecosystem:\s*["\']?([\w.-]+)["\']?\s*$')
UPDATES_KEY = re.compile(r'^updates:\s*$')
COOLDOWN_KEY = re.compile(r'^(\s+)cooldown:\s*$')
DEFAULT_DAYS = re.compile(r'^\s+default-days:\s*(\d+)\s*$')
EXCLUDE_KEY = re.compile(r'^(\s+)exclude:\s*$')
LIST_ITEM = re.compile(r'^(\s+)-\s*(.+?)\s*$')


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(' '))


def _block_lines(lines: list[str], start: int, own_indent: int) -> list[str]:
    """Lines after `start` that are more deeply indented than `own_indent`,
    stopping at the first line that returns to `own_indent` or shallower
    (blank lines don't count as a return)."""
    out = []
    for line in lines[start:]:
        if not line.strip():
            continue
        if _indent(line) <= own_indent:
            break
        out.append(line)
    return out


def _composer_entry_body(lines: list[str]) -> list[str] | None:
    """The body lines of the FIRST `composer` package-ecosystem entry under
    `updates:`, or None if `updates:` or a composer entry is absent."""
    updates_at = None
    for i, line in enumerate(lines):
        if UPDATES_KEY.match(line):
            updates_at = i
            break
    if updates_at is None:
        return None

    for i in range(updates_at + 1, len(lines)):
        m = ENTRY_START.match(lines[i])
        if m and m.group(1) == 'composer':
            return _block_lines(lines, i + 1, 2)
    return None


def _cooldown_fails(body: list[str]) -> list[str]:
    fails: list[str] = []

    cooldown_at = None
    cooldown_indent = None
    for i, line in enumerate(body):
        m = COOLDOWN_KEY.match(line)
        if m:
            cooldown_at = i
            cooldown_indent = len(m.group(1))
            break

    if cooldown_at is None:
        fails.append(
            'dependabot.yml: the composer package-ecosystem entry has no '
            '`cooldown:` block, so nothing delays a freshly-published '
            'package from reaching this repo\'s dependency PRs.')
        return fails

    block = _block_lines(body, cooldown_at + 1, cooldown_indent)

    days = None
    for line in block:
        m = DEFAULT_DAYS.match(line)
        if m:
            days = int(m.group(1))
            break
    if days is None:
        fails.append(
            'dependabot.yml: the composer `cooldown:` block has no '
            f'`default-days`. Set `default-days: {MIN_COOLDOWN_DAYS}`.')
    elif days < MIN_COOLDOWN_DAYS:
        extra = (' `0` does not weaken the window, it DISABLES it.'
                 if days == 0 else '')
        fails.append(
            f'dependabot.yml: composer `cooldown.default-days: {days}` is '
            f'below the fleet minimum of {MIN_COOLDOWN_DAYS} days.{extra}')

    exclude_at = None
    exclude_indent = None
    for i, line in enumerate(block):
        m = EXCLUDE_KEY.match(line)
        if m:
            exclude_at = i
            exclude_indent = len(m.group(1))
            break

    excludes: list[str] = []
    if exclude_at is not None:
        for line in _block_lines(block, exclude_at + 1, exclude_indent):
            m = LIST_ITEM.match(line)
            if m:
                excludes.append(m.group(2).strip('"\''))

    if REQUIRED_EXCLUDE not in excludes:
        fails.append(
            f'dependabot.yml: composer `cooldown.exclude` does not contain '
            f'`{REQUIRED_EXCLUDE}`. Without it the cooldown does not fail '
            f'loudly on a fresh first-party release — it silently delays '
            f'our OWN packages the same as anyone else\'s, which is the '
            f'inverse of what the exclude exists to prevent (see gate 84\'s '
            f'identical failure mode, measured 2026-08-15 on '
            f'@conduction/nextcloud-vue).')

    return fails


def main() -> int:
    parser = argparse.ArgumentParser(description='Gate 93 — composer-cooldown-config')
    parser.add_argument('repo', nargs='?', default='.')
    parser.add_argument('--base', default='', help='accepted for runner symmetry; unused (full-tree gate)')
    parser.add_argument('--all', action='store_true', help='accepted for runner symmetry')
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    composer_json = repo / 'composer.json'
    if not composer_json.is_file():
        print('checked 0 composer cooldown setting(s) — no composer.json, this repo has no Composer surface.')
        return EXIT_NOT_APPLICABLE

    dependabot_path = repo / '.github' / 'dependabot.yml'
    fails: list[str] = []
    checked = 1  # "is there a composer entry at all" is itself the first setting checked

    if not dependabot_path.is_file():
        fails.append(
            'no .github/dependabot.yml. This repo has a composer.json but no '
            'Dependabot config at all, so its composer dependencies get no '
            'cooldown. Create the file with a composer package-ecosystem entry.')
    else:
        try:
            src = dependabot_path.read_bytes().decode('utf-8', errors='replace')
        except OSError as exc:
            print(f'FAIL  .github/dependabot.yml could not be read ({exc}), so no '
                  f'composer cooldown setting could be verified.')
            print('\nchecked 1 composer cooldown setting(s) [full tree]: 1 failure(s)')
            return 1

        lines = src.split('\n')
        body = _composer_entry_body(lines)
        if body is None:
            fails.append(
                '.github/dependabot.yml declares no composer package-ecosystem '
                'entry, so composer dependencies get no cooldown at all.')
        else:
            checked += 2  # default-days + exclude, the two settings within the entry
            fails.extend(_cooldown_fails(body))

    for f in fails:
        print(f'FAIL  {f}')

    print(f'\nchecked {checked} composer cooldown setting(s) [full tree]: '
          f'{len(fails)} failure(s)')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
