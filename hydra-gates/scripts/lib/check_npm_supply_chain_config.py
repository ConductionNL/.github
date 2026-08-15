#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Gate 84 — npm-supply-chain-config.

The fleet's supply-chain cooldown is THREE settings that only work together,
and any one of them alone is a configuration that looks like protection and
is not:

  1. `.npmrc`        `min-release-age=<days>`  — the window itself
  2. `.npmrc`        `min-release-age-exclude[]=@conduction/*`
  3. `package.json`  `engines.npm` admitting ONLY npm 11 or newer

WHY ALL THREE, measured on 2026-08-15:

* **The option does not exist in npm 10.** Not rejected, not warned about:
  `npm config get min-release-age` answers `undefined`. Every Node 22 release
  bundles npm 10 (22.23.2, the latest, ships 10.9.8), so a repo whose declared
  toolchain is npm 10 has the cooldown READ BY NOTHING. 13 of 19 apps were in
  exactly that state while carrying a comment describing a 24h guard.

* **Without the exclusion the cooldown does not fail loudly — it silently
  resolves BACKWARDS.** Installing `@conduction/nextcloud-vue` on release day
  under `min-release-age=1` with no exclusion resolved **2.0.7 instead of
  2.3.0**, and exited 0. A green install of months-old code is a worse failure
  than a red one, and no signal distinguishes it from a correct install.

So a repo with the window but no exclusion silently pins stale first-party
code; a repo with both but declaring npm 10 has no window at all. This gate
fails unless the three agree.

FULL-TREE, not diff-scoped: this is a conformance property of the repository,
not a property of a change. A diff-scoped version would report nothing for
every PR that does not touch `.npmrc`, which is almost all of them — and a
gate that is silent on 99% of PRs cannot establish fleet-wide conformance,
which is the entire point of it.

Exit codes follow the package convention: 0 clean, 1 findings, 4 not
applicable (no package.json — a PHP-only repo has no npm surface to harden).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

EXIT_NOT_APPLICABLE = 4

MIN_DAYS = 2
REQUIRED_EXCLUDE = '@conduction/*'

# `key=value`, ignoring comments and blank lines. npm's array syntax is
# `key[]=value`, which is why the bracket is part of the name, not the value.
SETTING = re.compile(r'^\s*([A-Za-z0-9_.-]+(?:\[\])?)\s*=\s*(.*?)\s*$')


def read_npmrc(path: Path) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        if not line.strip() or line.lstrip().startswith('#') or line.lstrip().startswith(';'):
            continue
        m = SETTING.match(line)
        if m:
            out.setdefault(m.group(1), []).append(m.group(2))
    return out


def npm_range_is_11_plus(spec: str) -> bool:
    """True only when the range cannot be satisfied by npm 10 or older.

    Deliberately conservative and deliberately DUMB: this is a security
    control, so anything it cannot prove excludes npm 10 is treated as not
    excluding it. A clever partial semver implementation that guesses wrong
    in the permissive direction would hand back the exact silent-inertness
    this gate exists to end.
    """
    spec = spec.strip()
    if not spec:
        return False
    # Reject anything admitting a major below 11 anywhere in the range.
    for major in re.findall(r'(\d+)(?:\.\d+)*', spec):
        if int(major) < 11:
            return False
    return bool(re.match(r'^[\^>=~]*\s*\d+', spec)) or '||' in spec


def main() -> int:
    parser = argparse.ArgumentParser(description='Gate 84 — npm-supply-chain-config')
    parser.add_argument('repo', nargs='?', default='.')
    parser.add_argument('--base', default='', help='accepted for runner symmetry; unused')
    parser.add_argument('--all', action='store_true', help='accepted for runner symmetry')
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    pkg_path = repo / 'package.json'
    if not pkg_path.is_file():
        print('checked 0 npm supply-chain setting(s) — no package.json, this repo has no npm surface.')
        return EXIT_NOT_APPLICABLE

    fails: list[str] = []
    checked = 0

    try:
        pkg = json.loads(pkg_path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError) as exc:
        # A package.json that will not parse is a wiring problem, not a clean
        # repo. Fail rather than report zero settings.
        print(f'FAIL  package.json could not be parsed ({exc}), so no npm '
              f'supply-chain setting could be read. Nothing was verified.')
        print('\nchecked 0 npm supply-chain setting(s): 1 failure(s)')
        return 1

    npmrc = read_npmrc(repo / '.npmrc')

    # 1 — the window
    checked += 1
    raw = npmrc.get('min-release-age', [])
    if not raw:
        fails.append(
            '.npmrc: no `min-release-age`. Without it npm installs a version the '
            'moment it is published, so a compromised release reaches this repo '
            f'before anyone can pull it. Set `min-release-age={MIN_DAYS}`.')
    else:
        try:
            days = int(raw[-1])
        except ValueError:
            days = -1
        if days < MIN_DAYS:
            shown = raw[-1]
            extra = (' `0` does not weaken the window, it DISABLES it.'
                     if shown.strip() == '0' else '')
            fails.append(
                f'.npmrc: `min-release-age={shown}` is below the fleet minimum of '
                f'{MIN_DAYS} days.{extra} The unit is DAYS.')

    # 2 — the first-party exclusion
    checked += 1
    excludes = npmrc.get('min-release-age-exclude[]', []) + npmrc.get('min-release-age-exclude', [])
    if REQUIRED_EXCLUDE not in [e.strip() for e in excludes]:
        fails.append(
            f'.npmrc: no `min-release-age-exclude[]={REQUIRED_EXCLUDE}`. Without it '
            f'the cooldown does not fail loudly on a fresh first-party release — it '
            f'SILENTLY RESOLVES BACKWARDS. Measured 2026-08-15: an install of '
            f'@conduction/nextcloud-vue on release day picked 2.0.7 instead of 2.3.0 '
            f'and exited 0.')

    # 3 — a toolchain that can actually read settings 1 and 2
    checked += 1
    engines = pkg.get('engines') or {}
    npm_spec = engines.get('npm')
    if not npm_spec:
        fails.append(
            'package.json: no `engines.npm`. `min-release-age` is npm 11+ only and '
            'does not exist in npm 10 — `npm config get min-release-age` answers '
            '`undefined` there — so without a declared floor the .npmrc above is '
            'read by nothing and the cooldown is inert. Declare `"npm": "^11.0.0"`.')
    elif not npm_range_is_11_plus(npm_spec):
        fails.append(
            f'package.json: `engines.npm` is {npm_spec!r}, which admits npm 10. '
            f'npm 10 does not implement `min-release-age` at all, so on that '
            f'toolchain the .npmrc cooldown is silently inert while looking '
            f'configured. Require `^11.0.0` or newer.')

    for f in fails:
        print(f'FAIL  {f}')

    print(f'\nchecked {checked} npm supply-chain setting(s) [full tree]: '
          f'{len(fails)} failure(s)')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
