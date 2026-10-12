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
* Whether an app SHOULD own a slug. That is gate 106's subject. This gate
  only asks that the seed's requirement can be met.

A SLUG ANOTHER APP OWNS: THE ANNOTATION, AND THE CLAIM IS VERIFIED

A seed may legitimately require a schema a sibling app declares (buildiq's
export bundler reads hermiq's `agent`; since decision 196 buildiq's seed reads
openregister's `decision-table`). The seed says so on a line of its own:

    # hydra-gate-109 external: decision-table owner=openregister

The same `hydra-gate-<n> <verb>:` shape as the `hydra-gate-98 held:` marker in
info.xml. An annotation is a CLAIM, and the gate checks it rather than trusting
it:

  * the owner must be in the app's CI `additional-apps` / `e2e-additional-apps`
    (the workflow hands the gate that list as HYDRA_GATE_ADDITIONAL_APPS);
  * the owner's descriptors, read from the checkout the workflow made at the ref
    it installs (HYDRA_GATE_SIBLINGS_DIR/<owner>), must really declare the slug,
    by the same merged-view resolution used for the app's own;
  * if any of that cannot be read the gate FAILS and names what it could not
    read. A check that did not run looks exactly like one that passed.

An annotation nothing in the seed needs (the slug is not required, or the app
declares it itself) is reported as STALE. That is a warning, not a failure.
A `hydra-gate-109` line that does not parse is a failure: a typo in the
directive must not turn into an unchecked requirement.

Exit codes: 0 pass, 1 findings, 2 usage/wiring.
"""
import argparse
import json
import os
import re
import sys

ENV_APPS = 'HYDRA_GATE_ADDITIONAL_APPS'
ENV_SIBLINGS = 'HYDRA_GATE_SIBLINGS_DIR'

SEED = os.path.join('tests', 'e2e', 'ci-seed.sh')

# The required-schema list, as every app in the fleet spells it:
#     'schemas': ['task', 'project', ...],
# possibly wrapped across lines, inside the python heredoc the seed runs.
_REQUIRED_RE = re.compile(
    r"['\"]schemas['\"]\s*:\s*\[(?P<body>[^\]]*)\]",
    re.MULTILINE,
)
_SLUG_RE = re.compile(r"['\"]([A-Za-z0-9_.\-]+)['\"]")


# Where an app may keep the register descriptor the seed imports.
#
# `lib/Settings/` is the convention and covers most of the fleet, but it is a
# convention rather than a rule: zaakafhandelapp keeps its whole register at
# `tests/e2e/ci-register.json` and has no descriptor under lib/Settings at all.
# Looking only in the conventional place made this gate SKIP there — and a skip
# under `--require-full-coverage` is a job failure, so a gate written to catch
# a rename turned into a red build on an app it could not read.
#
# Ordered widest-last so the conventional location is still what usually
# answers, and every match is merged rather than the first one winning.
DESCRIPTOR_DIRS = (
    os.path.join('lib', 'Settings'),
    os.path.join('tests', 'e2e'),
    os.path.join('appinfo',),
)


def _descriptor_paths(app_dir):
    """Every JSON file that could declare this app's schemas.

    A descriptor is recognised by SHAPE, not by name: `components.schemas` as
    an object. That keeps fixtures, mock payloads and manifests out of the
    answer without maintaining a filename list, which would drift the moment an
    app named its register something new.
    """
    paths = []
    for rel in DESCRIPTOR_DIRS:
        root_dir = os.path.join(app_dir, rel)
        if not os.path.isdir(root_dir):
            continue
        for root, _dirs, files in os.walk(root_dir):
            for name in sorted(files):
                if name.endswith('.json'):
                    paths.append(os.path.join(root, name))
    return paths


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
    paths = _descriptor_paths(app_dir)
    if not paths:
        return set()

    # key -> declared slug, or None when no file has declared one yet.
    by_key = {}
    for path in paths:
        try:
            with open(path, encoding='utf-8') as fh:
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


# `# hydra-gate-109 external: <slug> owner=<app>`
_ANNOTATION_RE = re.compile(
    r"^\s*#\s*hydra-gate-109\s+external:\s*(?P<slug>[A-Za-z0-9_.\-]+)"
    r"\s+owner=(?P<owner>[A-Za-z0-9_.\-]+)\s*$"
)
_DIRECTIVE_RE = re.compile(r"^\s*#\s*hydra-gate-109\b")


def _annotations(app_dir):
    """(claims, malformed): claims is a list of (slug, owner, lineno).

    Malformed lines are returned, never skipped: a misspelt directive that is
    silently ignored leaves the slug as an unannotated finding at best and, at
    worst, an annotation nobody checks.
    """
    path = os.path.join(app_dir, SEED)
    claims, malformed = [], []
    if not os.path.isfile(path):
        return claims, malformed
    with open(path, encoding='utf-8') as fh:
        for n, line in enumerate(fh, 1):
            if not _DIRECTIVE_RE.match(line):
                continue
            m = _ANNOTATION_RE.match(line.rstrip('\n'))
            if m:
                claims.append((m.group('slug'), m.group('owner'), n))
            else:
                malformed.append((n, line.strip()))
    return claims, malformed


def _installed_apps():
    """Names in the CI additional-apps lists, or None when not supplied.

    None and [] are different answers and must stay different: None means the
    gate was not told, so it cannot say whether the owner is installed.
    """
    raw = os.environ.get(ENV_APPS)
    if raw is None or not raw.strip():
        return None
    try:
        doc = json.loads(raw)
    except ValueError:
        return None
    names = set()
    # The workflow passes the two lists concatenated; accept either a flat
    # array or an array of arrays.
    stack = [doc]
    while stack:
        item = stack.pop()
        if isinstance(item, list):
            stack.extend(item)
        elif isinstance(item, dict) and item.get('app'):
            names.add(str(item['app']))
    return names


def _verify_claim(slug, owner, installed):
    """None when the owner really declares `slug`, else why it does not."""
    if installed is None:
        return (f"cannot verify owner '{owner}': {ENV_APPS} was not provided, "
                f"so the gate does not know what this app's CI installs")
    if owner not in installed:
        return (f"owner '{owner}' is not in this app's CI additional-apps / "
                f"e2e-additional-apps, so it is not installed when the seed runs")
    base = os.environ.get(ENV_SIBLINGS, '')
    if not base:
        return (f"cannot read owner '{owner}': {ENV_SIBLINGS} was not provided "
                f"(the workflow checks installed apps out there)")
    owner_dir = os.path.join(base, owner)
    if not os.path.isdir(owner_dir):
        return f"cannot read owner '{owner}': {owner_dir} does not exist"
    declared = _declared_slugs(owner_dir)
    if not declared:
        return (f"cannot read owner '{owner}': no descriptor under {owner_dir} "
                f"(lib/Settings, tests/e2e, appinfo) declares any schema")
    if slug.lower() not in {d.lower() for d in declared}:
        return (f"owner '{owner}' declares {len(declared)} schema slug(s) and "
                f"none is '{slug}'")
    return None


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
    claims, malformed = _annotations(args.app_dir)
    lowered_local = {d.lower() for d in declared}
    lowered_required = {r.lower() for r in required}
    installed = _installed_apps() if claims else None

    external = 0
    extra = []
    for n, text in malformed:
        extra.append(f"FAIL {SEED}:{n}: unparseable hydra-gate-109 directive "
                     f"'{text}'. Expected "
                     f"'# hydra-gate-109 external: <slug> owner=<app>'.")
    claimed = set()
    for slug, owner, n in claims:
        low = slug.lower()
        if low not in lowered_required:
            print(f"STALE {SEED}:{n}: annotation for '{slug}' "
                  f"(owner={owner}) but the seed does not require it.")
            continue
        if low in lowered_local:
            print(f"STALE {SEED}:{n}: annotation for '{slug}' "
                  f"(owner={owner}) but this app declares it itself.")
            continue
        claimed.add(low)
        why = _verify_claim(slug, owner, installed)
        if why is None:
            external += 1
        else:
            extra.append(f"FAIL {SEED}:{n}: annotation '{slug}' "
                         f"owner={owner}: {why}.")

    # An annotated slug is judged by its claim above, not by the local list.
    findings = [f for f in findings if f.lower() not in claimed]
    for slug in findings:
        print(f"FAIL {SEED}: requires schema slug '{slug}', which no "
              f"descriptor under lib/Settings declares. The seed exits before "
              f"Playwright starts, so every spec would report as NOT RUN.")
    for line in extra:
        print(line)
    findings = findings + extra

    # 🔴 A TERMINAL SUMMARY, SO A CRASH IS NOT READ AS A FINDING. The runner
    # checks for this line before believing a non-zero exit (.github#374): a
    # checker that dies half way through otherwise reports as a clean failure
    # with however many findings it managed to print.
    print(f'checked {len(required)} required slug(s) against '
          f'{len(declared)} declared ({external} via external owner)')

    if args.mode == 'report':
        return 0
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())
