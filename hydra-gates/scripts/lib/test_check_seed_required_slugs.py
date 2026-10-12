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


def _run(app_dir, apps=None, siblings=None):
    """Run the checker. `apps` / `siblings` set the two CI hand-off variables;
    left None they are REMOVED from the environment, so a developer's shell
    cannot make a test pass."""
    env = {k: v for k, v in os.environ.items()
           if k not in ('HYDRA_GATE_ADDITIONAL_APPS', 'HYDRA_GATE_SIBLINGS_DIR')}
    if apps is not None:
        env['HYDRA_GATE_ADDITIONAL_APPS'] = apps
    if siblings is not None:
        env['HYDRA_GATE_SIBLINGS_DIR'] = siblings
    proc = subprocess.run(
        [sys.executable, CHECKER, app_dir],
        capture_output=True, text=True, check=False, env=env,
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


# ---------------------------------------------------------------------------
# External owner annotation. Every arm that expects a FAIL has a control that
# expects a PASS on the same tree with ONE thing changed, so a pass cannot be
# the annotation being ignored and a fail cannot be an unrelated error.
# ---------------------------------------------------------------------------
ANNOTATION = '# hydra-gate-109 external: %s owner=%s\n'
APPS = '[{"repo":"ConductionNL/openregister","app":"openregister","ref":"development"}]'


def _app_with_annotation(tmp, required, annotations):
    _tree(tmp, {'app_register.json': {'Task': {'slug': 'task'}}}, required)
    seed = os.path.join(tmp, 'tests', 'e2e', 'ci-seed.sh')
    with open(seed, encoding='utf-8') as fh:
        body = fh.read()
    with open(seed, 'w', encoding='utf-8') as fh:
        fh.write(body + ''.join(ANNOTATION % a for a in annotations))


def _owner(sib, slugs, name='openregister'):
    path = os.path.join(sib, name, 'lib', 'Settings', 'reg.json')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump({'components': {'schemas': {s: {'slug': s} for s in slugs}}}, fh)


def test_owner_declares_it_passes_and_misspelling_fails():
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as sib:
        _app_with_annotation(tmp, ['task', 'decision-table'],
                             [('decision-table', 'openregister')])
        _owner(sib, ['decision-table', 'other'])
        rc, out = _run(tmp, APPS, sib)
        check('owner declares the slug: passes', rc == 0, f'rc={rc} {out}')
        check('and says one was resolved externally',
              '1 via external owner' in out, out)

    # CONTROL: the same tree, the owner declares a near-miss (typo in slug).
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as sib:
        _app_with_annotation(tmp, ['task', 'decision-table'],
                             [('decision-table', 'openregister')])
        _owner(sib, ['decision-tabel'])
        rc, out = _run(tmp, APPS, sib)
        check('owner does not declare the slug: fails', rc == 1, f'rc={rc} {out}')
        check('and names slug and owner',
              "'decision-table'" in out and "owner 'openregister'" in out, out)

    # CONTROL: the typo is in the SEED annotation, not the owner.
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as sib:
        _app_with_annotation(tmp, ['task', 'decision-table'],
                             [('decision-tabel', 'openregister')])
        _owner(sib, ['decision-table'])
        rc, out = _run(tmp, APPS, sib)
        check('misspelt annotation slug fails', rc == 1, f'rc={rc} {out}')
        check('the required slug is reported unresolved',
              "requires schema slug 'decision-table'" in out, out)
        check('the unused annotation is reported stale', 'STALE' in out, out)


def test_owner_unreadable_fails_naming_what_was_missing():
    cases = (
        ('no siblings dir given', 'none', 'HYDRA_GATE_SIBLINGS_DIR'),
        ('owner dir absent', 'empty', 'does not exist'),
        ('owner dir has no descriptors', 'bare', 'no descriptor'),
    )
    for label, mode, needle in cases:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as sib:
            _app_with_annotation(tmp, ['task', 'decision-table'],
                                 [('decision-table', 'openregister')])
            if mode == 'bare':
                os.makedirs(os.path.join(sib, 'openregister'))
            rc, out = _run(tmp, APPS, None if mode == 'none' else sib)
            check(f'unreadable owner fails ({label})', rc == 1, f'rc={rc} {out}')
            check(f'and names what it could not read ({label})', needle in out, out)

    # CONTROL for all three: make the owner readable and the same tree passes.
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as sib:
        _app_with_annotation(tmp, ['task', 'decision-table'],
                             [('decision-table', 'openregister')])
        _owner(sib, ['decision-table'])
        rc, out = _run(tmp, APPS, sib)
        check('control: readable owner passes', rc == 0, f'rc={rc} {out}')


def test_additional_apps_not_provided_fails_not_passes():
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as sib:
        _app_with_annotation(tmp, ['task', 'decision-table'],
                             [('decision-table', 'openregister')])
        _owner(sib, ['decision-table'])
        rc, out = _run(tmp, None, sib)
        check('additional-apps list not provided fails', rc == 1, f'rc={rc} {out}')
        check('and names the variable', 'HYDRA_GATE_ADDITIONAL_APPS' in out, out)


def test_owner_not_installed_fails():
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as sib:
        _app_with_annotation(tmp, ['task', 'decision-table'],
                             [('decision-table', 'openregister')])
        _owner(sib, ['decision-table'])  # on disk, but not installed by CI
        other = '[{"repo":"ConductionNL/integriq","app":"integriq"}]'
        rc, out = _run(tmp, other, sib)
        check('owner absent from additional-apps fails', rc == 1, f'rc={rc} {out}')
        check('and says it is not installed',
              'not in this app\'s CI additional-apps' in out, out)
        rc, out = _run(tmp, '[]', sib)
        check('an EMPTY additional-apps list also fails', rc == 1, f'rc={rc} {out}')
        # CONTROL: e2e list concatenated as an array of arrays still counts.
        rc, out = _run(tmp, '[' + other + ',' + APPS + ']', sib)
        check('control: owner present among several passes', rc == 0,
              f'rc={rc} {out}')


def test_stale_annotation_is_reported_not_failed():
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as sib:
        _app_with_annotation(tmp, ['task'], [('decision-table', 'openregister')])
        _owner(sib, ['decision-table'])
        rc, out = _run(tmp, APPS, sib)
        check('annotation nothing requires is reported STALE', 'STALE' in out
              and 'decision-table' in out, out)
        check('stale alone does not fail', rc == 0, f'rc={rc} {out}')
    # CONTROL: a required, claimed slug is not stale.
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as sib:
        _app_with_annotation(tmp, ['task', 'decision-table'],
                             [('decision-table', 'openregister')])
        _owner(sib, ['decision-table'])
        rc, out = _run(tmp, APPS, sib)
        check('control: a used annotation is not stale', 'STALE' not in out, out)
    # Declared locally AND annotated: the annotation is dead weight.
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as sib:
        _app_with_annotation(tmp, ['task'], [('task', 'openregister')])
        _owner(sib, ['task'])
        rc, out = _run(tmp, APPS, sib)
        check('annotation for a locally declared slug is STALE',
              'declares it itself' in out and rc == 0, f'rc={rc} {out}')


def test_unannotated_foreign_slug_still_fails_as_before():
    """Annotation support must not loosen the plain case, even with a perfectly
    readable owner that declares the slug."""
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as sib:
        _tree(tmp, {'app_register.json': {'Task': {'slug': 'task'}}},
              ['task', 'decision-table'])
        _owner(sib, ['decision-table'])
        rc, out = _run(tmp, APPS, sib)
        check('unannotated foreign slug fails', rc == 1, f'rc={rc} {out}')
        check('with the original message',
              "FAIL tests/e2e/ci-seed.sh: requires schema slug 'decision-table', "
              "which no descriptor under lib/Settings declares." in out, out)
    # CONTROL: add only the annotation line and it passes.
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as sib:
        _app_with_annotation(tmp, ['task', 'decision-table'],
                             [('decision-table', 'openregister')])
        _owner(sib, ['decision-table'])
        rc, out = _run(tmp, APPS, sib)
        check('control: same tree plus the annotation passes', rc == 0,
              f'rc={rc} {out}')


def test_malformed_directive_fails():
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as sib:
        _app_with_annotation(tmp, ['task', 'decision-table'], [])
        seed = os.path.join(tmp, 'tests', 'e2e', 'ci-seed.sh')
        with open(seed, 'a', encoding='utf-8') as fh:
            fh.write('# hydra-gate-109 extrnal: decision-table owner=openregister\n')
        _owner(sib, ['decision-table'])
        rc, out = _run(tmp, APPS, sib)
        check('a misspelt directive fails', rc == 1, f'rc={rc} {out}')
        check('and says it could not parse it', 'unparseable' in out, out)


if __name__ == '__main__':
    for fn in (test_renamed_slug_is_named, test_all_present_passes,
               test_fragment_key_is_not_a_claim,
               test_key_counts_when_no_slug_field,
               test_case_only_difference_is_not_a_finding,
               test_descriptor_outside_lib_settings_is_read,
               test_no_seed_is_na_not_pass,
               test_seed_without_descriptors_is_wiring_not_pass,
               test_owner_declares_it_passes_and_misspelling_fails,
               test_owner_unreadable_fails_naming_what_was_missing,
               test_additional_apps_not_provided_fails_not_passes,
               test_owner_not_installed_fails,
               test_stale_annotation_is_reported_not_failed,
               test_unannotated_foreign_slug_still_fails_as_before,
               test_malformed_directive_fails):
        print(fn.__name__)
        fn()
    print()
    if FAILURES:
        print(f'{len(FAILURES)} check(s) failed: {", ".join(FAILURES)}')
        sys.exit(1)
    print('all checks passed')
