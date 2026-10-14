#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""gate-120 helper: a register version change needs an app version change.

An app's register configuration (lib/Settings/<app>_register.json and its
lib/Settings/register.d/*.json fragments) reaches an existing instance only
through the app's InitializeSettings repair step. Nextcloud runs repair steps
on install and on `occ upgrade`, and `occ upgrade` does nothing while
appinfo/info.xml <version> matches the installed version.

So a PR that raises the register's `info.version` without raising the app's
<version> ships a register change that no existing instance ever imports.
That happened twice in one week of October 2026 (portaliq #1549, pipelinq
#2471): the register was closed to a staff group in the file, and every
running instance kept the open register until a follow-up release PR.

WHAT COUNTS
-----------
The documents are every lib/Settings/*_register.json and every
lib/Settings/register.d/*.json. Two kinds of version move count:

  * a document's top-level `info.version` differs between the base and the
    change (an added document counts when it carries one, a deleted one not);
  * a register's EFFECTIVE version differs: `components.registers.<slug>.version`
    resolved the way the settings loaders merge, base documents first, then
    register.d in sorted order, the last declaration winning. pipelinq #2471
    raised `pipelinq` from 1.0.0 to 1.1.0 in a NEW register.d fragment that has
    no `info.version` at all, so the first kind alone does not see it.

A mock (`x-openregister.type: mock`) does not count. Mocks are sample data an
administrator imports on demand, never through a repair step.

THE RULE
--------
  * no base ref              -> NOT APPLICABLE (exit 4). This is a delta rule.
  * no appinfo/info.xml      -> NOT APPLICABLE (exit 4). Not a Nextcloud app.
  * register versions moved, app <version> did not -> FAIL, one finding per
                                document, naming both versions.
  * otherwise                -> PASS.

Usage:
    check_register_version_bump.py <app-dir> --base <ref> [--ref <ref>]

  --ref   read the change from a git ref instead of the working tree.

Output always ends in one of
    [gate-120] register-version-needs-app-version: checked N document(s), M version change(s)
    [gate-120] register-version-needs-app-version: FAIL: K finding(s)
and the exit status is 0 clean, 1 findings, 4 not applicable, 2 the checker
could not run. A traceback is exit 1 with no summary line, which the runner
reports as WIRING, never as a finding.
"""

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys

INFO_XML = "appinfo/info.xml"
SETTINGS = "lib/Settings"
PATTERNS = ("lib/Settings/*_register.json", "lib/Settings/register.d/*.json")
VERSION_RE = re.compile(r"<version>\s*([^<\s]+)\s*</version>")
TAG = "[gate-120] register-version-needs-app-version"


def _git(app, *args):
    return subprocess.run(["git", "-c", "safe.directory=*", "-C", app] + list(args),
                          capture_output=True, text=True)


def is_register_document(path):
    """True for a path the rule watches. fnmatch's * crosses '/', so depth is checked."""
    for pattern in PATTERNS:
        if fnmatch.fnmatch(path, pattern) and path.count("/") == pattern.count("/"):
            return True
    return False


def read_file(app, path, ref=None):
    """The file's text at a ref, or in the working tree; None when absent."""
    if ref is None:
        full = os.path.join(app, path)
        if not os.path.isfile(full):
            return None
        with open(full, encoding="utf-8") as fh:
            return fh.read()
    r = _git(app, "show", "%s:%s" % (ref, path))
    if r.returncode != 0:
        return None
    return r.stdout


def list_documents(app, ref=None):
    """Every watched path, at a ref or in the working tree."""
    if ref is None:
        found = []
        for root, _dirs, files in os.walk(os.path.join(app, SETTINGS)):
            for name in files:
                rel = os.path.relpath(os.path.join(root, name), app).replace(os.sep, "/")
                if is_register_document(rel):
                    found.append(rel)
        return sorted(found)
    r = _git(app, "ls-tree", "-r", "--name-only", ref, "--", SETTINGS)
    if r.returncode != 0:
        raise RuntimeError("git ls-tree %s failed: %s" % (ref, r.stderr.strip()))
    return sorted(p for p in r.stdout.splitlines() if is_register_document(p))


def parse(text):
    """The document as a dict, {} when absent or not an object. Invalid JSON raises ValueError."""
    if text is None:
        return {}
    data = json.loads(text)
    return data if isinstance(data, dict) else {}


def is_mock(data):
    marker = data.get("x-openregister")
    return isinstance(marker, dict) and marker.get("type") == "mock"


def info_version(data):
    info = data.get("info")
    version = info.get("version") if isinstance(info, dict) else None
    return str(version) if version is not None else None


def register_versions(data):
    """slug -> declared version, for every register the document declares with one."""
    registers = data.get("components", {}).get("registers") if isinstance(data.get("components"), dict) else None
    if not isinstance(registers, dict):
        return {}
    found = {}
    for key, register in registers.items():
        if isinstance(register, dict) and register.get("version") is not None:
            slug = str(register.get("slug") or key).lower()
            found[slug] = str(register["version"])
    return found


def merge_order(paths):
    """Base documents first, then register.d, each sorted: the loaders' merge order."""
    base = sorted(p for p in paths if "/register.d/" not in p)
    fragments = sorted(p for p in paths if "/register.d/" in p)
    return base + fragments


def app_version(app, ref=None):
    text = read_file(app, INFO_XML, ref)
    if text is None:
        return None
    m = VERSION_RE.search(text)
    return m.group(1) if m else ""


def read_side(app, ref):
    """{path: parsed document} for every non-mock watched document on one side."""
    docs = {}
    for path in list_documents(app, ref):
        try:
            data = parse(read_file(app, path, ref))
        except ValueError as e:
            raise RuntimeError("%s is not valid JSON: %s" % (path, e))
        if not is_mock(data):
            docs[path] = data
    return docs


def effective_registers(docs):
    """slug -> (version, path that set it), merged in the loaders' order."""
    effective = {}
    for path in merge_order(list(docs)):
        for slug, version in register_versions(docs[path]).items():
            effective[slug] = (version, path)
    return effective


def changed_versions(app, base, ref=None):
    """(documents checked, [finding lines]) for every version that moved."""
    before = read_side(app, base)
    after = read_side(app, ref)
    changes = []

    for path in sorted(after):
        old = info_version(before.get(path, {}))
        new = info_version(after[path])
        if new is not None and old != new:
            changes.append("%s: info.version %s -> %s" % (path, old or "(none)", new))

    old_registers = effective_registers(before)
    for slug, (new, path) in sorted(effective_registers(after).items()):
        old = old_registers.get(slug, (None, None))[0]
        if old != new:
            changes.append("register %s: version %s -> %s (%s)" % (slug, old or "(none)", new, path))

    return sorted(set(before) | set(after)), changes


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("app")
    ap.add_argument("--base")
    ap.add_argument("--ref")
    args = ap.parse_args(argv)
    app = args.app

    if not args.base:
        print("%s: NOT APPLICABLE: no base ref, and this rule compares a change against its base." % TAG)
        return 4

    head_app = app_version(app, args.ref)
    if head_app is None:
        print("%s: NOT APPLICABLE: no %s, so this is not a Nextcloud app." % (TAG, INFO_XML))
        return 4

    try:
        base_app = app_version(app, args.base)
        paths, changes = changed_versions(app, args.base, args.ref)
    except RuntimeError as e:
        print("%s: could not read the change: %s" % (TAG, e))
        return 2

    print("%s: checked %d document(s), %d version change(s)" % (TAG, len(paths), len(changes)))
    for line in changes:
        print("  " + line)

    if not changes or base_app != head_app:
        if changes:
            print("  appinfo/info.xml <version> %s -> %s, so an upgrade imports it" % (base_app, head_app))
        return 0

    print("%s: FAIL: %d finding(s)" % (TAG, len(changes)))
    print("  appinfo/info.xml <version> stays %s. occ upgrade only runs the repair step that imports" % head_app)
    print("  the register when <version> changes, so no existing instance will import this register")
    print("  change. Raise <version> in appinfo/info.xml in this PR.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
