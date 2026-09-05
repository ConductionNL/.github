#!/usr/bin/env python3
"""Gate 109: the e2e seed must not require a schema slug the app does not declare.

WHY THIS GATE EXISTS

`tests/e2e/ci-seed.sh` verifies, before Playwright starts, that the schemas the
suite needs actually imported. It does that against a hard-coded list of slugs.
When a slug is renamed and that list is not, the seed exits non-zero and takes
Playwright with it — so **every spec is reported as NOT RUN rather than as
failing**, and the leg reads as one broken seed instead of a suite that never
executed. The tally looks like `1 failed` when the truth is `0 of 340 ran`.

Measured 2026-09-05, three apps in one afternoon:

  * planninq — `timeEntry` -> `plannedTimeEntry` (#575, three apps declared a
    `timeEntry`; a slug is global per organisation). The seed still asked for
    the old name. `plannedTimeEntry` was sitting in the "schemas present" line
    directly above the error.
  * buildiq — `agent` -> `buildAgent` (#686, collided with hermiq's). Same
    miss, and `agent-run` was in the present-list one line above.
  * decidiq — an action id renamed weeks earlier; the seed's POST had been
    answering 404 the whole time, and the tolerant error handling hid it.

Each rename was careful. planninq's and buildiq's both shipped a repair step in
`<post-migration>` AND `<install>`, because the import matches on
(application, slug) and its not-found branch would otherwise create a second
schema and orphan every existing row. They were thorough about the data and
missed one list in the test harness.

Gate 106 stops an app NEWLY claiming a slug another app owns. Nothing checked
the follow-through once a rename resolved such a collision. This does.

WHAT IT CHECKS

For every slug named in the seed's `required` schema list: some descriptor
under `lib/Settings/**` declares it, by `slug` field or — where no slug field
is given — by schema key. That is the same resolution the importer performs.

WHAT IT DELIBERATELY DOES NOT CHECK

* It takes no view on whether the list is COMPLETE. A suite may reasonably not
  assert every schema it touches, and guessing which ones matter would be wrong
  in both directions.
* It does not look at registers, only schemas. The register list is a different
  shape and a different failure.
* A slug another app owns is gate 106's subject, not this one's. A seed may
  legitimately require a schema a sibling app declares — buildiq's export
  bundler reads hermiq's `agent` on purpose — so a slug this app does not
  declare is reported only when the app declares NOTHING resembling it. See
  `_unresolved` for the exact rule.

Exit codes: 0 pass, 1 findings, 2 usage/wiring.
"""
import argparse
import json
import os
import re
import sys

SEED = os.path.join('tests', 'e2e', 'ci-seed.sh')

# The required-schema list, as every app in the fleet spells it:
#     'schemas': ['task', 'project', ...],
# possibly wrapped across lines, inside the python heredoc the seed runs.
_REQUIRED_RE = re.compile(
    r"['\"]schemas['\"]\s*:\s*\[(?P<body>[^\]]*)\]",
    re.MULTILINE,
)
_SLUG_RE = re.compile(r"['\"]([A-Za-z0-9_.\-]+)['\"]")


def _declared_slugs(app_dir):
    """Every schema slug the app's descriptors declare.

    🔴 THE MERGED VIEW, NOT A FILE-BY-FILE UNION. A schema's slug is its `slug`
    field wherever any file declares one, and its KEY only when no file does —
    the same resolution the importer performs after `register.d/` fragments are
    merged onto the monolith.

    Taking the union per file gets this wrong, and the acceptance fixture is
    built to catch it: a fragment addresses a schema by KEY to add one property
    and declares no slug. Reading that key as a claim made the planted arm PASS,
    because the renamed-away word `timeEntry` matched the key `TimeEntry` of the
    schema whose real slug is `plannedTimeEntry`. That is the same shape gate
    106's fixture records — larpinq ships exactly it against `skill`, whose slug
    is `larping_skill`.
    """
    settings = os.path.join(app_dir, 'lib', 'Settings')
    if not os.path.isdir(settings):
        return set()

    # key -> declared slug, or None when no file has declared one yet.
    by_key = {}
    for root, _dirs, files in os.walk(settings):
        for name in sorted(files):
            if not name.endswith('.json'):
                continue
            try:
                with open(os.path.join(root, name), encoding='utf-8') as fh:
                    doc = json.load(fh)
            except (OSError, ValueError):
                # Not a descriptor, or not readable. `check:manifest` and the
                # import own that finding; reporting it here would be a second
                # voice on someone else's subject.
                continue

            schemas = ((doc.get('components') or {}).get('schemas') or {})
            if not isinstance(schemas, dict):
                continue
            for key, value in schemas.items():
                key = str(key)
                slug = value.get('slug') if isinstance(value, dict) else None
                if slug:
                    by_key[key] = str(slug)
                else:
                    by_key.setdefault(key, None)

    return {slug if slug else key for key, slug in by_key.items()}


def _required_slugs(app_dir):
    """The slugs the seed asserts are present, or None when it asserts none."""
    path = os.path.join(app_dir, SEED)
    if not os.path.isfile(path):
        return None
    with open(path, encoding='utf-8') as fh:
        body = fh.read()

    match = _REQUIRED_RE.search(body)
    if match is None:
        return None
    return [m for m in _SLUG_RE.findall(match.group('body'))]


def _unresolved(required, declared):
    """Required slugs this app declares nothing for.

    Case-insensitive, because `SchemaMapper::find()` matches `LOWER(slug)` and
    a case-only difference resolves at run time — reporting it would be noise.
    """
    lowered = {s.lower() for s in declared}
    return [s for s in required if s.lower() not in lowered]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('app_dir', nargs='?', default='.')
    parser.add_argument('--mode', default='gate', choices=('gate', 'report'))
    args = parser.parse_args()

    required = _required_slugs(args.app_dir)
    if required is None:
        print('NA: no tests/e2e/ci-seed.sh, or it asserts no schema list — '
              'nothing was inspected, which is not the same as passing.')
        return 0

    declared = _declared_slugs(args.app_dir)
    if not declared:
        print('WIRING: the seed requires schemas but no descriptor under '
              'lib/Settings declares any, so NO slug could be resolved and a '
              'renamed one would pass unseen.')
        return 2

    findings = _unresolved(required, declared)
    for slug in findings:
        print(f"FAIL {SEED}: requires schema slug '{slug}', which no "
              f"descriptor under lib/Settings declares. The seed exits before "
              f"Playwright starts, so every spec would report as NOT RUN.")

    # 🔴 A TERMINAL SUMMARY, SO A CRASH IS NOT READ AS A FINDING. The runner
    # checks for this line before believing a non-zero exit (.github#374): a
    # checker that dies half way through otherwise reports as a clean failure
    # with however many findings it managed to print.
    print(f'checked {len(required)} required slug(s) against '
          f'{len(declared)} declared')

    if args.mode == 'report':
        return 0
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())
