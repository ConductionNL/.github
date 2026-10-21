#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""gate-121 helper: register schemas use the authorization dialect OpenRegister reads.

OpenRegister reads a schema's access rules from `authorization` and its
administered checks from `x-openregister-validations`. Three other keys look
like they do the same job and do nothing:

  * `x-openregister-rbac`        never read; the schema is as open as one without it
  * `x-rbac-role`                never read, wherever it sits (a lifecycle
                                 transition included)
  * `x-openregister-validation`  the singular; only the plural is read

A schema that relies on them reads as protected in review and is not. Measured
2026-10-21: shillinq carried them on hundreds of schemas, every one of them
open to any user who could reach the register.

WHAT IS READ
------------
Every register document under lib/Settings: `*register*.json` at the top
level (mocks included), `register.d/*.json`, and every JSON file under
`packages/`. Only documents with a `components.schemas` object carry schemas;
the others are counted and skipped.

THE RULE
--------
  * a dead key anywhere inside a schema body      -> FAIL, one finding per key,
                                                     naming file, schema and path
  * a schema with no non-empty `authorization`    -> REPORT-ONLY census, unless
                                                     --require-authorization
  * no register document with schemas             -> NOT APPLICABLE (exit 4)

The census merges the documents the way OpenRegister's RegisterDocumentLoader
does: non-mock top-level documents, then register.d in sorted order, deep
merged, so an `authorization` block a fragment adds to a base schema counts.
Package documents are counted on their own. Mocks are sample data and are not
in the census, but a dead key in one is still a finding.

A key that is a direct child of a `properties` map is a property NAME, not an
annotation, and is not judged.

Usage:
    check_register_auth_dialect.py <app-dir> [--documents-from FILE]
                                   [--judge-from FILE] [--require-authorization]

  --documents-from  the watched documents, one path per line, relative to the
                    app (the runner passes the tracked files); default: walk
                    lib/Settings.
  --judge-from      judge dead keys only in these files (a narrowed run); the
                    census always reads every document.

Output always ends in one of
    [gate-121] register-auth-dialect: checked N document(s), S schema(s), 0 finding(s)
    [gate-121] register-auth-dialect: FAIL: K finding(s) in D schema(s)
and the exit status is 0 clean, 1 findings, 4 not applicable, 2 the checker
could not run. A traceback is exit 1 with no summary line, which the runner
reports as WIRING, never as a finding.
"""

import argparse
import json
import os
import re
import sys

TAG = "[gate-121] register-auth-dialect"
SETTINGS = "lib/Settings"
WATCHED = re.compile(
    r"^lib/Settings/(?:[^/]*register[^/]*\.json|register\.d/[^/]+\.json|packages/.+\.json)$"
)
DEAD_KEYS = {
    "x-openregister-rbac": "OpenRegister never reads it. Declare the rules in the schema's `authorization` block.",
    "x-rbac-role": "OpenRegister never reads it. Declare the role in the schema's `authorization` block, or guard the transition with `requires`.",
    "x-openregister-validation": "OpenRegister reads only the plural. Rename it to `x-openregister-validations`.",
}


def is_watched(path):
    return bool(WATCHED.match(path))


def is_fragment(path):
    return "/register.d/" in path


def is_package(path):
    return path.startswith(SETTINGS + "/packages/")


def walk_documents(app):
    found = []
    for root, dirs, files in os.walk(os.path.join(app, SETTINGS)):
        dirs[:] = [d for d in dirs if d not in ("node_modules", "vendor")]
        for name in files:
            rel = os.path.relpath(os.path.join(root, name), app).replace(os.sep, "/")
            if is_watched(rel):
                found.append(rel)
    return sorted(found)


def read_list(path):
    with open(path, encoding="utf-8") as fh:
        return sorted({line.strip() for line in fh if line.strip()})


def load(app, path):
    """The parsed document. Invalid JSON raises ValueError naming the file."""
    with open(os.path.join(app, path), encoding="utf-8") as fh:
        try:
            return json.load(fh)
        except ValueError as e:
            raise ValueError("%s is not valid JSON: %s" % (path, e))


def schemas_of(doc):
    if not isinstance(doc, dict):
        return None
    components = doc.get("components")
    if not isinstance(components, dict):
        return None
    schemas = components.get("schemas")
    return schemas if isinstance(schemas, dict) else None


def is_mock(doc):
    marker = doc.get("x-openregister") if isinstance(doc, dict) else None
    return isinstance(marker, dict) and marker.get("type") == "mock"


def dead_keys(node, path, in_properties=False):
    """(json path, key) for every dead key inside a schema body."""
    found = []
    if isinstance(node, dict):
        for key, value in node.items():
            if not in_properties and key in DEAD_KEYS:
                found.append(("%s.%s" % (path, key), key))
            found.extend(dead_keys(value, "%s.%s" % (path, key), key == "properties" and not in_properties))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            found.extend(dead_keys(value, "%s[%d]" % (path, i)))
    return found


def deep_merge(base, overlay):
    """RegisterDocumentLoader::deepMergeConfig: maps merge, lists concatenate, scalars win."""
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = deep_merge(base[key], value)
        elif isinstance(value, list) and isinstance(base.get(key), list):
            base[key] = base[key] + value
        else:
            base[key] = value
    return base


def has_authorization(schema):
    auth = schema.get("authorization") if isinstance(schema, dict) else None
    return isinstance(auth, dict) and len(auth) > 0


def census(docs):
    """[(schema label, covered)] over the merged register and each package."""
    merged = {}
    order = sorted(p for p in docs if not is_fragment(p) and not is_package(p))
    order += sorted(p for p in docs if is_fragment(p))
    for path in order:
        doc = docs[path]
        if isinstance(doc, dict) and not is_mock(doc):
            merged = deep_merge(merged, json.loads(json.dumps(doc)))
    rows = [(key, has_authorization(schema)) for key, schema in sorted((schemas_of(merged) or {}).items())]
    for path in sorted(p for p in docs if is_package(p)):
        doc = docs[path]
        if isinstance(doc, dict) and not is_mock(doc):
            for key, schema in sorted((schemas_of(doc) or {}).items()):
                rows.append(("%s (%s)" % (key, path), has_authorization(schema)))
    return rows


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("app")
    ap.add_argument("--documents-from")
    ap.add_argument("--judge-from")
    ap.add_argument("--require-authorization", action="store_true")
    args = ap.parse_args(argv)
    app = args.app

    try:
        paths = read_list(args.documents_from) if args.documents_from else walk_documents(app)
        paths = [p for p in paths if is_watched(p)]
        judged = set(read_list(args.judge_from)) if args.judge_from else set(paths)
        docs = {p: load(app, p) for p in paths}
    except (OSError, ValueError) as e:
        print("%s: could not read the register documents: %s" % (TAG, e))
        return 2

    with_schemas = [p for p in paths if schemas_of(docs[p])]
    if not with_schemas:
        print("%s: NOT APPLICABLE: %d register document(s) under %s and none declares components.schemas." % (TAG, len(paths), SETTINGS))
        return 4

    findings = []
    for path in sorted(p for p in with_schemas if p in judged):
        for key, schema in sorted(schemas_of(docs[path]).items()):
            for where, dead in dead_keys(schema, "components.schemas.%s" % key):
                findings.append((path, key, where, dead))

    rows = census(docs)
    covered = sum(1 for _, ok in rows if ok)
    uncovered = [label for label, ok in rows if not ok]
    by_key = {k: sum(1 for f in findings if f[3] == k) for k in DEAD_KEYS}

    print("%s: dead keys: %s" % (TAG, ", ".join("%s=%d" % (k, by_key[k]) for k in sorted(by_key))))
    print("%s: authorization coverage: %d of %d schema(s) declare an authorization block, %d do not%s"
          % (TAG, covered, len(rows), len(uncovered), "" if args.require_authorization else " (report-only)"))
    for label in uncovered:
        print("    no authorization: %s" % label)

    failing_uncovered = uncovered if args.require_authorization else []
    total = len(findings) + len(failing_uncovered)
    print("%s: checked %d document(s), %d schema(s), %d finding(s)" % (TAG, len(paths), len(rows), total))
    if total == 0:
        return 0

    schemas_hit = {(f[0], f[1]) for f in findings} | set(failing_uncovered)
    print("%s: FAIL: %d finding(s) in %d schema(s)" % (TAG, total, len(schemas_hit)))
    for path, _key, where, dead in findings:
        print("  %s: %s: %s" % (path, where, DEAD_KEYS[dead]))
    for label in failing_uncovered:
        print("  %s: no authorization block, and HYDRA_GATE_REGISTER_AUTHORIZATION_BLOCKING is on." % label)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
