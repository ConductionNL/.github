#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Gate 94 — retired-git-host-metadata.

ConductionNL moved onto Codeberg on 2026-05-29 and moved back off it on
2026-07-23. The git layer completed: verified 2026-08-22, zero codeberg
remotes fleet-wide. What did NOT complete is the metadata that SHIPS.

23 apps still declared `<bugs>`, `<website>`, `<repository>` and
`<screenshot>` URLs pointing at `codeberg.org/Conduction/<app>` in
`appinfo/info.xml`. That file is published to the Nextcloud app store, so
the consequences are user-visible and outlive the migration:

  * `<bugs>`   — sends a bug reporter to an issue tracker nobody reads.
  * `<screenshot>` — an app-store listing whose images 404.
  * `<repository>` / `<website>` — points contributors at a dead mirror.

This gate is therefore about SHIPPED METADATA, not about prose. It reads
only the files whose contents reach a user or a package registry, and it
deliberately ignores documentation, changelogs, specs and archives — those
record what happened at the time and rewriting them would make the history
untrue. A gate that flagged every historical mention would be so noisy it
would be switched off, and then it would catch nothing at all.

FULL-TREE, deliberately NOT diff-scoped, for the reason gates 84 and 93
give: a diff-scoped version reports nothing on the ~99% of PRs that never
touch `appinfo/info.xml`, and a gate silent on nearly everything cannot
establish fleet-wide conformance — which is the entire point of it. This
matters more here than for 84/93: the drift this gate exists to catch was
introduced by a migration that touched every repo at once and is already
present in the tree. Diff-scoping would render it blind to 100% of the
debt it was written for.

WHY A REGEX AND NOT A URL PARSER: the finding is "a retired host appears in
a field that ships", and the host is a fixed literal. Parsing XML/JSON
properly per format buys nothing a substring match does not already give,
and would need three parsers for three formats.

Exit codes: 0 clean · 1 findings · 4 no shipped-metadata file in this repo.
"""
import json
import os
import re
import sys

# Hosts ConductionNL has retired. Keyed by host → why it is retired, so the
# failure message can say more than "wrong".
RETIRED_HOSTS = {
    'codeberg.org': (
        'ConductionNL left Codeberg on 2026-07-23; the org now lives at '
        'github.com/ConductionNL'
    ),
}

# Files whose contents SHIP — to the Nextcloud app store, to npm, to
# Packagist, or to a human reading the repo's front page.
SHIPPED = (
    'appinfo/info.xml',
    'package.json',
    'composer.json',
)

# Within those files, only these fields carry a URL a user follows. Matching
# the whole file would flag a dependency that legitimately lives on a Forgejo
# host, which is not this gate's business.
XML_FIELDS = ('bugs', 'website', 'repository', 'documentation', 'screenshot',
              'user', 'admin', 'developer')
JSON_FIELDS = ('repository', 'bugs', 'homepage', 'support', 'url', 'issues')

# Never walked. Two separate reasons:
#   - build/vendor output is not this repo's declaration;
#   - `custom_apps/` (and friends) are CHECKOUTS OF OTHER APPS that a dev
#     environment drops inside this one. Walking them made the gate report
#     openregister as having 69 findings, 63 of which belonged to seven other
#     apps. A gate that blames a repo for a neighbour's metadata teaches people
#     to ignore it.
SKIP_DIRS = {
    'node_modules', 'vendor', '.git', 'build', 'dist', 'coverage',
    'custom_apps', 'apps-extra', 'builds', '.docusaurus',
    'test-fixtures', 'fixtures', '.claude',
}


def _findings_in_xml(path, src):
    out = []
    for host, why in RETIRED_HOSTS.items():
        if host not in src:
            continue
        for field in XML_FIELDS:
            for m in re.finditer(
                    rf'<{field}\b[^>]*>([^<]*{re.escape(host)}[^<]*)</{field}>',
                    src, re.I):
                line = src[:m.start()].count('\n') + 1
                out.append((path, line, field, m.group(1).strip(), why))
    return out


def _walk_json(node, fields, host, path_parts=()):
    """Yield (dotted-key, value) for any string under a field of interest."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _walk_json(v, fields, host, path_parts + (str(k),))
    elif isinstance(node, list):
        for idx, v in enumerate(node):
            yield from _walk_json(v, fields, host, path_parts + (str(idx),))
    elif isinstance(node, str) and host in node:
        if any(p.lower() in fields for p in path_parts):
            yield ('.'.join(path_parts), node)


def _findings_in_json(path, src):
    out = []
    for host, why in RETIRED_HOSTS.items():
        if host not in src:
            continue
        try:
            data = json.loads(src)
        except Exception:
            # Unparseable JSON is a different problem and another gate's; do
            # not invent a finding out of it, but do not silently pass the
            # host mention either.
            out.append((path, 0, '<unparseable json>', host, why))
            continue
        for key, val in _walk_json(data, {f.lower() for f in JSON_FIELDS}, host):
            out.append((path, 0, key, val, why))
    return out


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    targets = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace(os.sep, '/')
            # `appinfo/info.xml` is ROOT-ONLY: a Nextcloud app ships exactly
            # one, and a nested one belongs to a different app that happens to
            # sit in this tree. package.json / composer.json may legitimately
            # appear at depth (workspaces, per-package design tokens), so those
            # are matched anywhere the walk still reaches.
            if rel == 'appinfo/info.xml':
                targets.append((rel, full))
            elif fn in ('package.json', 'composer.json'):
                targets.append((rel, full))

    if not targets:
        print('checked 0 shipped metadata file(s) [full tree]: 0 failure(s)')
        return 4

    findings = []
    for rel, full in sorted(targets):
        try:
            src = open(full, encoding='utf-8', errors='replace').read()
        except OSError as exc:
            print(f'FAIL  {rel} could not be read ({exc}), so its URLs are UNVERIFIED.')
            findings.append((rel, 0, '<unreadable>', '', ''))
            continue
        if rel.endswith('.xml'):
            findings += _findings_in_xml(rel, src)
        else:
            findings += _findings_in_json(rel, src)

    for path, line, field, value, why in findings:
        where = f'{path}:{line}' if line else path
        print(f'FAIL  {where} — <{field}> points at a retired git host: {value}')
        if why:
            print(f'      {why}. Repoint it at the repo\'s real GitHub URL; '
                  f'resolve the current name with '
                  f'`gh api repos/ConductionNL/<name> --jq .full_name` '
                  f'(the fleet was renamed 2026-08-21, so the directory name '
                  f'may not be the repo name).')

    print(f'\nchecked {len(targets)} shipped metadata file(s) [full tree]: '
          f'{len(findings)} failure(s)')
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())
