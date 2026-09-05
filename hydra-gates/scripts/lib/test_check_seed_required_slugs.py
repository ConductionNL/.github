#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Tests for check_seed_required_slugs (gate 109). Run with:

    python3 scripts/lib/test_check_seed_required_slugs.py

WHY THIS SUITE EXISTS
---------------------
The defect this gate catches is invisible in the place people look. When the
seed's required-schema list names a slug that was renamed away, the seed exits
before Playwright starts and EVERY SPEC REPORTS AS NOT RUN — so the leg reads as
one broken seed, and the tally says `1 failed` when the truth is `0 of 340 ran`.
A gate that quietly stopped working would restore exactly that silence.

Two failure modes, and running it against real repositories reveals neither:

  1. It goes quiet. Every arm below plants a real rename and asserts the gate
     names the slug.

  2. It goes loud on legitimate input. A `register.d` fragment addresses an
     existing schema by its dict KEY and carries no `slug` — larpinq ships one
     against the schema keyed `skill`, whose slug is `larping_skill`. Reading
     that key as a claim makes the RENAMED-AWAY word resolve against it, and the
     gate passes a tree that is broken. That bug was in the first draft of this
     checker; the acceptance fixture caught it, and `test_fragment_key_*` keeps
     it caught.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.join(HERE, 'check_seed_required_slugs.py')

SEED = """#!/usr/bin/env bash
set -euo pipefail
python3 - <<PY
required = {
    "registers": ["demoapp"],
    "schemas": [%s],
}["schemas"]
PY
"""


def _tree(tmp, schemas_by_file, required, base=('lib', 'Settings')):
    """Write a fixture app: descriptors plus a seed requiring `required`.

    `base` is where the descriptors go. It defaults to the conventional
    `lib/Settings`; the discovery arm below moves it, because an app is allowed
    to keep its register elsewhere and one in this fleet does.
    """
    for rel, schemas in schemas_by_file.items():
        path = os.path.join(tmp, *base, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump({'components': {'schemas': schemas}}, fh)

    seed = os.path.join(tmp, 'tests', 'e2e', 'ci-seed.sh')
    os.makedirs(os.path.dirname(seed), exist_ok=True)
    with open(seed, 'w', encoding='utf-8') as fh:
        fh.write(SEED % ', '.join(f"'{s}'" for s in required))
    return tmp


def _run(app_dir):
    proc = subprocess.run(
        [sys.executable, CHECKER, app_dir],
        capture_output=True, text=True, check=False,
    )
    return proc.returncode, proc.stdout


FAILURES = []


def check(name, condition, detail=''):
    if condition:
        print(f'  ok   {name}')
    else:
        print(f'  FAIL {name} {detail}')
        FAILURES.append(name)


def test_renamed_slug_is_named():
    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp,
              {'app_register.json': {'TimeEntry': {'slug': 'plannedTimeEntry'}}},
              ['plannedTimeEntry', 'timeEntry'])
        rc, out = _run(tmp)
        check('renamed slug fails', rc == 1, f'rc={rc}')
        check('renamed slug is NAMED', "'timeEntry'" in out, out)
        check('terminal summary printed', 'checked 2 required slug' in out, out)


def test_all_present_passes():
    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp,
              {'app_register.json': {'Task': {'slug': 'task'},
                                     'project': {'title': 'Project'}}},
              ['task', 'project'])
        rc, out = _run(tmp)
        check('all present passes', rc == 0, f'rc={rc} {out}')


def test_fragment_key_is_not_a_claim():
    """THE REGRESSION THIS SUITE EXISTS FOR.

    A fragment addresses `TimeEntry` by key to add a property and declares no
    slug. A file-by-file union reads that key as a slug, and then the
    renamed-away `timeEntry` resolves against it case-insensitively — so the
    broken tree PASSES. The merged view is what makes this fail correctly.
    """
    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp,
              {'app_register.json': {'TimeEntry': {'slug': 'plannedTimeEntry'}},
               os.path.join('register.d', '40-adds-a-property.json'):
                   {'TimeEntry': {'properties': {'note': {'type': 'string'}}}}},
              ['timeEntry'])
        rc, out = _run(tmp)
        check('fragment key does not excuse a renamed slug', rc == 1,
              f'rc={rc} {out}')


def test_key_counts_when_no_slug_field():
    """A schema with no `slug` anywhere IS claimed by its key."""
    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp, {'app_register.json': {'project': {'title': 'Project'}}},
              ['project'])
        rc, out = _run(tmp)
        check('bare key counts as a slug', rc == 0, f'rc={rc} {out}')


def test_case_only_difference_is_not_a_finding():
    """`SchemaMapper::find()` matches LOWER(slug), so case resolves at run time."""
    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp, {'app_register.json': {'T': {'slug': 'plannedTimeEntry'}}},
              ['plannedtimeentry'])
        rc, out = _run(tmp)
        check('case-only difference passes', rc == 0, f'rc={rc} {out}')


def test_descriptor_outside_lib_settings_is_read():
    """THE REGRESSION THAT SHIPPED.

    zaakafhandelapp keeps its whole register at `tests/e2e/ci-register.json`
    and has no descriptor under `lib/Settings` at all. Looking only in the
    conventional place made this gate answer SKIPPED (wiring) there — and a
    skip under `--require-full-coverage` is a job FAILURE, so a gate written to
    catch a rename turned into a red build on an app it had simply not read.

    Both halves are asserted, because reading the file is only useful if the
    verdict it produces is still right: a present slug passes, and a renamed
    one is still named.
    """
    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp, {'ci-register.json': {'zaak': {'slug': 'zaak'}}},
              ['zaak'], base=('tests', 'e2e'))
        rc, out = _run(tmp)
        check('a descriptor outside lib/Settings is read, not skipped',
              rc == 0 and 'WIRING' not in out, f'rc={rc} {out}')

    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp, {'ci-register.json': {'zaak': {'slug': 'zaak'}}},
              ['zaakType'], base=('tests', 'e2e'))
        rc, out = _run(tmp)
        check('and still names a renamed slug it finds there',
              rc == 1, f'rc={rc} {out}')


def test_no_seed_is_na_not_pass():
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, 'lib', 'Settings'))
        rc, out = _run(tmp)
        check('absent seed reports NA', rc == 0 and out.startswith('NA:'), out)


def test_seed_without_descriptors_is_wiring_not_pass():
    """A seed requiring schemas with nothing to resolve against is a WIRING
    verdict: reporting PASS there is the .github#374 defect."""
    with tempfile.TemporaryDirectory() as tmp:
        seed = os.path.join(tmp, 'tests', 'e2e', 'ci-seed.sh')
        os.makedirs(os.path.dirname(seed))
        with open(seed, 'w', encoding='utf-8') as fh:
            fh.write(SEED % "'task'")
        rc, out = _run(tmp)
        check('no descriptors reports wiring', rc == 2, f'rc={rc} {out}')


if __name__ == '__main__':
    for fn in (test_renamed_slug_is_named, test_all_present_passes,
               test_fragment_key_is_not_a_claim,
               test_key_counts_when_no_slug_field,
               test_case_only_difference_is_not_a_finding,
               test_descriptor_outside_lib_settings_is_read,
               test_no_seed_is_na_not_pass,
               test_seed_without_descriptors_is_wiring_not_pass):
        print(fn.__name__)
        fn()
    print()
    if FAILURES:
        print(f'{len(FAILURES)} check(s) failed: {", ".join(FAILURES)}')
        sys.exit(1)
    print('all checks passed')
