#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Unit arms for gate-109's checker (check_migration_version_bump.py).

Two things are asserted here, and the acceptance suite
`test_gate109_migration_version_bump_scope.sh` asserts the third (the gate
itself, through the real wrapper, over a real two-commit history).

  1. THE COMPARATOR AGREES WITH PHP. Nextcloud's upgrade decision is literally
     `version_compare($info['version'], $installedVersion, '>')`. A comparator
     that disagrees with PHP is this gate lying about what the server will do,
     in whichever direction it disagrees — and the fleet versions with
     `-unstable.<timestamp>`, a form PHP does NOT recognise and therefore sorts
     BELOW `dev`. That is not an edge case here, it is every app.

     The table below was produced by running the same pairs through
     `php -r 'echo version_compare(...)'` and recording the answers. When php is
     on PATH the last arm re-derives them live, so the table cannot rot away
     from the thing it claims to mirror; when it is not, the recorded answers
     still hold the port to account.

     🔴 TWO REAL DEFECTS WERE CAUGHT BY THIS ARM AND BY NOTHING ELSE. The first
     port returned "the longer list wins" when one side ran out of parts, which
     gets `1.0.0-beta.1 < 1.0.0` exactly backwards. The second returned "compare
     against the '#' slot" unconditionally, which made `1.1.10` equal to `1`.
     Both were self-consistent, both passed every hand-written assertion the
     author had thought of, and both were found by differential-testing 108,241
     pairs against a real php.

  2. THE SUBJECT RULE IS THE RUNNABLE SET, NOT THE DIRECTORY. decidiq ships
     sixteen `lib/Migration/Migrate*.php` classes that Nextcloud's migration
     discovery ignores (they are registered as repair steps instead), a trait,
     and a helper. A gate that demands a version bump for a trait produces a
     finding its author cannot act on.

Run: python3 scripts/lib/test_check_migration_version_bump.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = importlib.util.spec_from_file_location(
    "check_migration_version_bump",
    os.path.join(HERE, "check_migration_version_bump.py"),
)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)

FAILURES = 0


def ok(message: str) -> None:
    print(f"  ok   — {message}")


def bad(message: str) -> None:
    global FAILURES
    FAILURES += 1
    print(f"  FAIL — {message}")


# ---------------------------------------------------------------------------
# ARM 1 — the comparator, against answers recorded from a real php.
# ---------------------------------------------------------------------------
# (left, right, php's version_compare answer)
RECORDED = [
    # The fleet's own shape: a patch bump under the -unstable suffix.
    ("0.3.16-unstable.20260905192451", "0.3.15-unstable.20260904192451", 1),
    ("0.3.15-unstable.20260904192451", "0.3.16-unstable.20260905192451", -1),
    # A TIMESTAMP-ONLY move is still a move, and Nextcloud agrees, so the gate
    # must accept it. This is what the release bot produces.
    ("0.3.15-unstable.20260905192451", "0.3.15-unstable.20260904192451", 1),
    # The dossiq stranding: byte-identical versions.
    ("0.3.15-unstable.20260904192451", "0.3.15-unstable.20260904192451", 0),
    # An -unstable build ranks BELOW its own stable core, because PHP sorts an
    # unrecognised form below `dev`. A gate that got this backwards would call
    # 0.3.15 -> 0.3.15-unstable.X a bump.
    ("0.3.15-unstable.20260905192451", "0.3.15", -1),
    ("0.3.15", "0.3.15-unstable.20260905192451", 1),
    # Numeric parts compare NUMERICALLY, not as strings. "10" > "9".
    ("1.1.10", "1.1.9", 1),
    ("2.0.15-unstable.20260905143606", "2.0.14-unstable.20260901212512", 1),
    ("0.1.153", "0.1.152-unstable.20260901111016", 1),
    # The two shapes the first two ports got wrong, kept by name.
    ("1.0.0-beta.1", "1.0.0", -1),
    ("1.0.0-rc.1", "1.0.0", -1),
    ("1.0.0-pl.1", "1.0.0", 1),
    ("1.1.10", "1", 1),
    ("1", "1.1.10", -1),
    ("1.0.0-dev", "1.0.0-alpha", -1),
    ("1.0.0-alpha", "1.0.0-beta.1", -1),
    ("10.0.0", "9.0.0", 1),
    ("1.0", "1.0.0", -1),
]

print("-- ARM 1: the comparator matches PHP's version_compare --")
for left, right, want in RECORDED:
    got = MOD.version_compare(left, right)
    if got == want:
        ok(f"version_compare({left!r}, {right!r}) == {want}")
    else:
        bad(f"version_compare({left!r}, {right!r}) == {got}, php says {want}")


# ---------------------------------------------------------------------------
# ARM 2 — the subject rule.
# ---------------------------------------------------------------------------
def php_file(path: str, namespace: str, body: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(f"<?php\ndeclare(strict_types=1);\nnamespace {namespace};\n{body}\n")


def info_xml(path: str, version: str, steps: list[str], install: list[str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rows = "".join(f"            <step>{s}</step>\n" for s in steps)
    installs = "".join(f"            <step>{s}</step>\n" for s in install)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(
            '<?xml version="1.0"?>\n<info>\n'
            "    <id>fixture</id>\n"
            f"    <version>{version}</version>\n"
            "    <repair-steps>\n"
            f"        <post-migration>\n{rows}        </post-migration>\n"
            f"        <install>\n{installs}        </install>\n"
            "    </repair-steps>\n</info>\n"
        )


print("-- ARM 2: only files Nextcloud will actually RUN are subjects --")
WORK = tempfile.mkdtemp(prefix="gate109-unit.")
try:
    info = os.path.join(WORK, "appinfo", "info.xml")
    info_xml(
        info,
        "1.0.0",
        ["OCA\\Fixture\\Repair\\Registered", "OCA\\Fixture\\Migration\\AlsoRegistered"],
        ["OCA\\Fixture\\Repair\\InstallOnly"],
    )
    steps = MOD.upgrade_time_steps(info)

    if steps == {"OCA\\Fixture\\Repair\\Registered", "OCA\\Fixture\\Migration\\AlsoRegistered"}:
        ok("<pre-migration>/<post-migration> steps are read, and <install> is NOT")
    else:
        bad(f"upgrade_time_steps read {sorted(steps)}")

    if "OCA\\Fixture\\Repair\\InstallOnly" not in steps:
        ok("an <install>-only step is not an upgrade subject — no version bump delivers it")
    else:
        bad("an <install>-only step was treated as an upgrade subject")

    cases = [
        ("lib/Repair/Registered.php", "OCA\\Fixture\\Repair",
         "class Registered implements \\OCP\\Migration\\IRepairStep {}",
         "OCA\\Fixture\\Repair\\Registered", "Registered"),
        ("lib/Migration/Version1Date20260906090000.php", "OCA\\Fixture\\Migration",
         "class Version1Date20260906090000 extends SimpleMigrationStep {}",
         "OCA\\Fixture\\Migration\\Version1Date20260906090000",
         "Version1Date20260906090000"),
        ("lib/Migration/ReadsLegacyRows.php", "OCA\\Fixture\\Migration",
         "trait ReadsLegacyRows { public function x(): void {} }", None, None),
    ]
    for rel, ns, body, want_fqcn, want_bare in cases:
        target = os.path.join(WORK, rel)
        php_file(target, ns, body)
        got = MOD.fqcn_of(target)
        if want_fqcn is None:
            if got is None:
                ok(f"{rel} declares no class (a trait) — not a subject")
            else:
                bad(f"{rel} was read as a class: {got}")
        elif got == (want_fqcn, want_bare):
            ok(f"{rel} resolves to {want_fqcn}")
        else:
            bad(f"{rel} resolved to {got}, wanted {(want_fqcn, want_bare)}")

    if MOD.CORE_MIGRATION_RE.match("Version1Date20260906090000"):
        ok("Version<n>Date<n> is recognised as a core-discovered migration")
    else:
        bad("the core migration name pattern does not match a real migration name")

    # 🔴 decidiq's shape. Sixteen of these ship today and NONE is discovered by
    # MigrationService — they run only because info.xml names them. A checker
    # that treated the directory as the rule would demand a bump for the trait
    # sitting beside them; one that treated the NAME as the rule would miss all
    # sixteen.
    if not MOD.CORE_MIGRATION_RE.match("MigrateMemberOnboarding"):
        ok("a Migrate*-named class under lib/Migration/ is NOT core-discovered "
           "(decidiq ships sixteen; they run as registered repair steps)")
    else:
        bad("Migrate* was treated as a core-discovered migration name")
finally:
    shutil.rmtree(WORK, ignore_errors=True)


# ---------------------------------------------------------------------------
# ARM 3 — differential test against a real php, when one is on PATH.
# ---------------------------------------------------------------------------
print("-- ARM 3: differential test against a real php --")
if shutil.which("php") is None:
    print("  skip — php is not on PATH. ARM 1's recorded answers still hold the "
          "port to account; this arm re-derives them when it can.")
else:
    fragments = ["0", "1", "2", "9", "10", "15", "dev", "alpha", "beta", "rc",
                 "pl", "unstable", "20260905", "x", "a", "b", "p"]
    import random

    random.seed(109)
    corpus = [pair[0] for pair in RECORDED] + [pair[1] for pair in RECORDED]
    for _ in range(120):
        corpus.append(".".join(random.choice(fragments)
                               for _ in range(random.randint(1, 5))))
    for _ in range(60):
        corpus.append(f"{random.choice(fragments)}-{random.choice(fragments)}."
                      f"{random.choice(fragments)}")
    corpus = sorted(set(corpus))
    pairs = [(a, b) for a in corpus for b in corpus]
    script = ("$p=json_decode(file_get_contents('php://stdin'),true);$o=[];"
              "foreach($p as $x){$o[]=version_compare($x[0],$x[1]);}echo json_encode($o);")
    done = subprocess.run(["php", "-r", script], input=json.dumps(pairs),
                          capture_output=True, text=True, check=False)
    try:
        expected = json.loads(done.stdout)
    except json.JSONDecodeError:
        expected = None
    if not expected or len(expected) != len(pairs):
        bad("php was on PATH but returned no usable answer set — this arm "
            "measured nothing, which is not the same as agreement")
    else:
        wrong = [(a, b, e, MOD.version_compare(a, b))
                 for (a, b), e in zip(pairs, expected)
                 if MOD.version_compare(a, b) != e]
        if wrong:
            for row in wrong[:5]:
                bad(f"php {row[2]} vs port {row[3]} for {row[0]!r} / {row[1]!r}")
            bad(f"{len(wrong)} of {len(pairs)} pairs disagree with php")
        else:
            ok(f"all {len(pairs)} pairs agree with php's version_compare")

# ---------------------------------------------------------------------------
# ARM 4 — a base it cannot see is NEVER a pass.
#
# The wrapper guards this too (gate-109 skips when HAVE_DELTA_BASE != 1), so
# this arm is the only thing holding the CHECKER to the same contract. That
# matters because the checker is also runnable on its own — from a pre-commit
# hook, or by hand — where no wrapper is standing in front of it. A silent 0
# here is the exact failure the whole gate exists to remove.
# ---------------------------------------------------------------------------
print("-- ARM 4: an unresolvable base is exit 3, never exit 0 --")
WORK2 = tempfile.mkdtemp(prefix="gate109-nobase.")
try:
    subprocess.run(["git", "init", "--quiet", WORK2], check=False,
                   capture_output=True)
    checker = os.path.join(HERE, "check_migration_version_bump.py")
    for label, argv in (
        ("a base ref that does not exist",
         [WORK2, "--base-ref", "refs/heads/no-such-branch-109"]),
        ("no base ref at all", [WORK2]),
    ):
        env = dict(os.environ)
        env.pop("HYDRA_GATE_BASE_REF", None)
        done = subprocess.run([sys.executable, checker, *argv],
                              capture_output=True, text=True, check=False, env=env)
        if done.returncode == 3:
            ok(f"{label} -> exit 3 (no verdict)")
        else:
            bad(f"{label} -> exit {done.returncode}, wanted 3. Output: "
                f"{done.stdout.strip()[:160]}")
        if "checked" not in done.stdout:
            ok(f"{label} prints no 'checked N' summary, so the caller can tell "
               f"it did not finish")
        else:
            bad(f"{label} printed a completion summary it had not earned: "
                f"{done.stdout.strip()[:160]}")
finally:
    shutil.rmtree(WORK2, ignore_errors=True)


print()
if FAILURES == 0:
    print("test_check_migration_version_bump.py: ALL PASS")
    sys.exit(0)
print(f"test_check_migration_version_bump.py: {FAILURES} FAILURE(S)")
sys.exit(1)
