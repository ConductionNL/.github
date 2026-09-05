#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""A migration that ships without a version bump reaches nobody.

WHAT THIS CATCHES

Nextcloud decides whether to run an app's migrations and its upgrade-time
repair steps by comparing the `<version>` in `appinfo/info.xml` against the
`installed_version` it recorded for that app. Equal versions mean "already up
to date": `occ upgrade` answers `No upgrade required.`, exits 0, and the files
on disk are never read. Nothing is logged. Nothing fails. The repair simply
does not happen.

MEASURED, 2026-09-05, on a throwaway NC 34.0.3 rig with openregister
2.0.15-unstable.20260905134511 installed from its release tarball
(openregister#3451):

    added lib/Migration/Version1Date20260906090000.php (creates a table),
    left <version> alone, ran `occ upgrade`
      -> "No upgrade required."     exit 0
      -> table not created, no row in oc_migrations
    then changed NOTHING but <version>, and re-ran
      -> "Updated <openregister> to 2.0.16", table created

So the version string is the whole gate, and the same code either ships or does
not depending on one line of XML.

🔴 `occ migrations:status` CANNOT WARN YOU. Its "Pending Migrations" field is
built by `MigrationService::describeMigrationStep()`, which drops every step
whose `name()` is empty — and `SimpleMigrationStep::name()` returns `''`, which
every one of ours inherits, so the field reads `None` unconditionally. Its "New
Migrations" and "Executed Unavailable Migrations" fields are worse: core's
`StatusCommand` calls `array_keys()` on `getAvailableVersions()`, which returns
a LIST, so both compare version strings against the integers `0..n` and report
the full count every time. The only honest pair in that output is Executed vs
Available.

AND IT HAS ALREADY BITTEN, TWICE, IN DIFFERENT SHAPES. openregister found it
with a migration. dossiq shipped `lib/Repair/RealignStatutoryVocabulary` — the
step that puts corrupted confidentiality values back — in #1839 with `<version>`
untouched at `0.3.15-unstable.20260904192451`, so `occ upgrade` skipped dossiq
entirely and 18 cases plus 7 caseTypes stayed corrupted on a live instance.

WHAT COUNTS AS A SUBJECT, AND WHY IT IS NOT "EVERY FILE IN THE DIRECTORY"

The claim this gate makes is "the thing you just added will actually run". Only
two kinds of added file will:

  1. a `lib/Migration/` class named `Version<n>Date<n>` — the ONLY shape
     `MigrationService::findMigrations()` discovers. It needs no registration.
  2. any class under `lib/Migration/` or `lib/Repair/` NAMED in
     `appinfo/info.xml` under `<repair-steps><pre-migration>` or
     `<post-migration>` — the two blocks Nextcloud runs on UPGRADE.

Everything else in those directories is deliberately out of scope, and the
fleet is full of it: decidiq ships sixteen `lib/Migration/Migrate*.php` classes,
NONE of them `Version…Date…`-named, all of them registered as repair steps —
plus `ReadsLegacyRows.php`, a trait, and `AgendaItemTypeResolver.php`, a helper.
Demanding a version bump for a trait is a finding an author cannot act on, and a
gate that produces those is a gate people learn to override.

`<install>` is excluded on purpose. A step registered ONLY there runs on a fresh
install, where there is no installed_version to compare against — so no version
bump would deliver it and asking for one would be wrong.

A step under those directories that is registered NOWHERE does not run either,
but that is gate-98's finding (repair-step-registration), with its own message
and its own remedy. Reporting it here as well would give one defect two names.

WHY THIS IS DIFF-SCOPED

The claim is about what the change ADDS. A full-tree version would demand a
version bump on every branch cut before this gate shipped, for steps their
authors never touched — the fleet's most repeated gate trap, and the one that
took a single app's gate-16 to 102 findings in one rename.

The eight apps carrying stranded steps on 2026-09-05 (buildiq, decidiq, dossiq,
hermiq, humaniq, integriq, pipelinq, planninq — 31 files between them) are real
debt, and they are being fixed by name in their own pull requests. They are not
debt this gate can ask an unrelated PR to pay.

USAGE
  check_migration_version_bump.py <root> --base-ref <ref>

EXIT CODES
  0  something runnable was added AND <version> moved past the merge base
  1  something runnable was added and <version> did NOT move
  3  no verdict — the base does not resolve, or info.xml has no <version>.
     🔴 NOT 0. A check that cannot see its base has no verdict to give, and a
     silent pass is the exact failure this file exists to remove.
  4  nothing in scope — this delta adds no runnable migration or repair step
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

NAMESPACE_RE = re.compile(r"^\s*namespace\s+([^;]+);", re.MULTILINE)
CLASS_RE = re.compile(
    r"^\s*(?:final\s+|abstract\s+|readonly\s+)*class\s+(\w+)\b",
    re.MULTILINE,
)
# The one shape MigrationService::findMigrations() discovers.
CORE_MIGRATION_RE = re.compile(r"^Version\d+Date\d+$")

# `-unstable.<ts>` and friends: PHP's version_compare special forms, in its own
# order. Anything NOT in this table sorts BELOW `dev`, which is why
# `0.3.15-unstable.X` < `0.3.15` — exactly as Nextcloud sees it.
SPECIAL_FORMS = [
    ("dev", 0),
    ("alpha", 1),
    ("a", 1),
    ("beta", 2),
    ("b", 2),
    ("RC", 3),
    ("rc", 3),
    ("#", 4),
    ("pl", 5),
    ("p", 5),
]


def canonicalize(version: str) -> list[str]:
    """Split a version the way PHP's version_compare does.

    Ported rather than approximated, because Nextcloud's own upgrade decision is
    `version_compare($info['version'], $installedVersion, '>')` — so any
    disagreement between this function and PHP is this gate lying about what the
    server will do. `scripts/lib/test_check_migration_version_bump.py` asserts
    the port against a table of pairs cross-checked with a real `php -r`.
    """
    out: list[str] = []
    buf = ""
    previous = ""
    for char in version:
        if not char.isalnum():
            if buf:
                out.append(buf)
                buf = ""
            previous = ""
            continue
        if previous and (
            (previous.isdigit() and not char.isdigit())
            or (not previous.isdigit() and char.isdigit())
        ):
            if buf:
                out.append(buf)
            buf = char
        else:
            buf += char
        previous = char
    if buf:
        out.append(buf)
    return out


def _order(part: str) -> int:
    """PHP's compare_special_version_forms: -1 for anything unrecognised."""
    if part.isdigit():
        return 4  # the '#' slot numbers occupy
    for name, rank in SPECIAL_FORMS:
        if part.startswith(name):
            return rank
    return -1


def _cmp_part(left: str, right: str) -> int:
    if left.isdigit() and right.isdigit():
        return (int(left) > int(right)) - (int(left) < int(right))
    lo, ro = _order(left), _order(right)
    return (lo > ro) - (lo < ro)


def version_compare(left: str, right: str) -> int:
    """-1, 0 or 1, matching PHP's version_compare()."""
    lp, rp = canonicalize(left), canonicalize(right)
    for index in range(max(len(lp), len(rp))):
        # One side ran out. PHP compares the surviving part against the '#'
        # slot — which is why `1.0.0-beta.1` < `1.0.0` (beta ranks 2, '#' ranks
        # 4) while `1.0.0-pl.1` > `1.0.0` (pl ranks 5). Returning a flat "the
        # longer one wins" here gets four of the SPECIAL_FORMS backwards, and
        # `-unstable` is the form this whole fleet versions with.
        if index >= len(lp):
            return -1 if rp[index].isdigit() else _cmp_part("#", rp[index])
        if index >= len(rp):
            return 1 if lp[index].isdigit() else _cmp_part(lp[index], "#")
        verdict = _cmp_part(lp[index], rp[index])
        if verdict:
            return verdict
    return 0


def git(root: str, args: list[str]) -> str | None:
    """Trimmed stdout, or None when git said no."""
    try:
        done = subprocess.run(
            ["git", "-c", "safe.directory=*", "-C", root, *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if done.returncode != 0:
        return None
    return done.stdout.strip()


def version_from(xml: str | None) -> str | None:
    """The <version> text, read by regex on purpose.

    This must read the file as it stands at an ARBITRARY git revision, where the
    surrounding document may not be well formed. A DOM parse would report a
    malformed document as "no version", which this gate treats as "no verdict" —
    the same word for two different states.
    """
    if xml is None:
        return None
    match = re.search(r"<version>\s*([^<\s][^<]*?)\s*</version>", xml)
    return match.group(1) if match else None


def upgrade_time_steps(info_xml_path: str) -> set[str]:
    """Every FQCN Nextcloud runs on UPGRADE: <pre-migration> and <post-migration>.

    <install> is excluded — see the module docstring.
    """
    try:
        root = ET.parse(info_xml_path).getroot()
    except (ET.ParseError, OSError):
        return set()
    found: set[str] = set()
    for block in ("pre-migration", "post-migration"):
        for step in root.iterfind(f".//repair-steps/{block}/step"):
            text = (step.text or "").strip().lstrip("\\")
            if text:
                found.add(text)
    return found


def fqcn_of(path: str) -> tuple[str, str] | None:
    """(fully qualified class name, bare class name) for a PHP file."""
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            source = handle.read()
    except OSError:
        return None
    klass = CLASS_RE.search(source)
    if not klass:
        return None
    namespace = NAMESPACE_RE.search(source)
    bare = klass.group(1)
    if not namespace:
        return bare, bare
    return f"{namespace.group(1).strip().lstrip(chr(92))}\\{bare}", bare


def added_files(root: str, merge_base: str) -> list[str]:
    """Files this branch ADDS under lib/Migration/ or lib/Repair/.

    Three ways a file can be present and new, and all three count. The committed
    case is what CI sees; the other two are what a developer has in front of them
    before pushing, which is where this is cheapest to fix.

    `--no-renames` is deliberate. Renaming an already-applied migration makes
    Nextcloud re-run it under its new name, so a rename IS an addition and must
    move the version too.
    """
    seen: dict[str, bool] = {}
    for args in (
        ["diff", "--diff-filter=A", "--no-renames", "--name-only",
         f"{merge_base}..HEAD", "--", "lib/Migration", "lib/Repair"],
        ["diff", "--diff-filter=A", "--no-renames", "--name-only",
         merge_base, "--", "lib/Migration", "lib/Repair"],
        ["ls-files", "--others", "--exclude-standard", "--",
         "lib/Migration", "lib/Repair"],
    ):
        out = git(root, args)
        if not out:
            continue
        for line in out.splitlines():
            line = line.strip()
            if line.endswith(".php"):
                seen[line] = True
    return sorted(seen)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--base-ref", dest="base_ref", default="")
    args = parser.parse_args(argv[1:])

    root = git(args.root, ["rev-parse", "--show-toplevel"])
    if not root:
        print(f"NOVERDICT {args.root} is not a git repository, so there is no "
              f"base to compare a version against.")
        return 3

    base = args.base_ref or os.environ.get("HYDRA_GATE_BASE_REF", "")
    if not base:
        print("NOVERDICT no base ref was given (--base-ref or HYDRA_GATE_BASE_REF). "
              "This gate judges what a change ADDS; with no base it has nothing "
              "to judge, and saying so is not the same as passing.")
        return 3

    base_sha = git(root, ["rev-parse", "--verify", "--quiet", f"{base}^{{commit}}"])
    if not base_sha:
        base_sha = git(root, ["rev-parse", "--verify", "--quiet",
                              f"origin/{base}^{{commit}}"])
    if not base_sha:
        print(f"NOVERDICT cannot resolve base ref {base!r}. Fetch it first, or pass "
              f"--base-ref. A base this check cannot see is not the same as a "
              f"clean branch, so it refuses to report one.")
        return 3

    merge_base = git(root, ["merge-base", base_sha, "HEAD"]) or base_sha

    added = added_files(root, merge_base)

    steps = upgrade_time_steps(os.path.join(root, "appinfo", "info.xml"))

    subjects: list[tuple[str, str]] = []  # (path, why)
    for rel in added:
        absolute = os.path.join(root, rel)
        if not os.path.isfile(absolute):
            continue
        names = fqcn_of(absolute)
        if names is None:
            # A trait, an interface, or a file with no class at all. Nextcloud
            # runs none of those, so no version bump would deliver it.
            continue
        fqcn, bare = names
        if fqcn in steps:
            subjects.append((rel, f"{bare} is registered in <repair-steps>, so "
                                  f"Nextcloud runs it on upgrade"))
        elif rel.startswith("lib/Migration/") and CORE_MIGRATION_RE.match(bare):
            subjects.append((rel, f"{bare} is a core-discovered migration "
                                  f"(Version<n>Date<n>)"))

    if not subjects:
        # 🔴 A COUNT, PRINTED EVEN WHEN ZERO. The caller distinguishes "ran and
        # found nothing" from "never ran" by this line; without it a crash and a
        # delta with no migrations are the same observation.
        print(f"checked 0 added migration/repair step(s) "
              f"({len(added)} added file(s) under lib/Migration|lib/Repair, none "
              f"of them runnable on upgrade)")
        return 4

    base_version = version_from(git(root, ["show", f"{merge_base}:appinfo/info.xml"]))
    head_xml_path = os.path.join(root, "appinfo", "info.xml")
    try:
        with open(head_xml_path, encoding="utf-8", errors="replace") as handle:
            head_version = version_from(handle.read())
    except OSError:
        head_version = None

    if base_version is None:
        print(f"NOVERDICT no <version> in appinfo/info.xml at "
              f"{merge_base[:8]} — nothing to compare against.")
        return 3
    if head_version is None:
        print("NOVERDICT no <version> in appinfo/info.xml on this branch — "
              "nothing to compare.")
        return 3

    if version_compare(head_version, base_version) > 0:
        print(f"OK <version> moved {base_version} -> {head_version}")
        print(f"checked {len(subjects)} added migration/repair step(s)")
        return 0

    for rel, why in subjects:
        print(
            f"FAIL {rel}: {why}, but appinfo/info.xml <version> is still "
            f"{head_version} ({base_version} at the merge base). Nextcloud runs an "
            f"app's migrations and its <pre-migration>/<post-migration> repair "
            f"steps only when <version> is GREATER than the installed_version it "
            f"recorded. Left like this, `occ upgrade` answers \"No upgrade "
            f"required.\", exits 0, and runs none of them on any instance that "
            f"already has this app — nothing logged, nothing failed. Bump "
            f"<version> in this same change. Do not wait for the release-bump "
            f"pull request: between releases, `development` is what people deploy."
        )
    print(f"checked {len(subjects)} added migration/repair step(s)")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
