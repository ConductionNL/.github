#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Every property in a shipped object must be DECLARED by its schema.

WHY THIS EXISTS
---------------
OpenRegister does not reject an undeclared property. It drops it, and answers
200. `MagicMapper::writeMagicRow()` iterates the SCHEMA's declared property
names and asks the data for each one:

    $schemaProperties = $schema->getProperties();
    foreach (array_keys($schemaProperties) as $propertyName) {
        if (array_key_exists($propertyName, $data) === true) {

A key in `$data` with no matching declared property is never visited, so it is
never written to a column, because it has no column. The save succeeds. The
value is gone. And the mismatch is silent in the OTHER direction too:
`MagicSearchHandler::applyObjectFilters()` compiles a filter on an undeclared
key to a literal `1 = 0`, so a query on it matches zero rows forever.

Nothing in the fleet's toolchain could see this before. gate-101 validates
demo objects with `jsonschema`, and JSON Schema is OPEN-WORLD by default: an
undeclared property is valid unless the schema says `additionalProperties:
false`, and — measured across ~1,930 fleet schemas — **not one schema anywhere
in the fleet declares it**. So every gate-101 run over every one of these
defects printed PASS, correctly, against the rule it was asked to enforce.

WHAT IT HAS ALREADY COST, in two days
-------------------------------------
  dossiq#1782  ten demo keys no schema declares, across ten shipped objects —
               a `catalog` key carrying a zero uuid on three each of the
               generated `caseType`, `decisionType` and `documentType`
               objects, plus `zaaksysteemMapping.openstaandeWijzigingen`.
  dossiq#1779  eight StUF field names that drifted from their schemas during a
               vocabulary pass (`bronEntiteit` vs `sourceEntity`,
               `berichtSoort` vs `messageKind`, `duurMs` vs `durationMs`, …).
               Every async confirmation was dropped.
  and earlier  `publications`/`publishedAt` — every publication record
               stripped; the opschorting pause fields; `taskUuid`.

Each was found by a human reading JSON. That is the part this file replaces.

Run:
    check_shipped_object_properties.py <app-dir> [--only-changed]

`--only-changed` reads changed file paths (repo-relative, one per line) from
stdin and narrows the judgement — see `_in_scope` for what "changed" means and
why it is deliberately wider than "the object's own file".

Exit: 0 clean · 1 findings · 2 fatal (could not run) · 4 nothing in scope
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from typing import Any

# ---------------------------------------------------------------------------
# THE ENVELOPE. Keys that are NOT schema properties and must never be reported.
#
# 🔴 THIS LIST IS COPIED FROM OPENREGISTER, NOT INVENTED HERE. Guessing it is
# how a gate like this produces hundreds of false findings and gets switched
# off in a week. `ImportService::importObjects()` already had to answer exactly
# this question — which dropped keys are a LOSS and which are envelope — and
# answered it in code:
#
#     if ($rawName === '' || $rawName === 'id' || $rawName === 'uuid'
#         || $rawName[0] === '@' || $rawName[0] === '_'
#     ) { continue; }
#     // `@`/`_`/`id` are envelope and metadata, never user data, so they are
#     // not losses.
#
# `@self` is covered by the `@` rule; `SaveObject::extractUuidAndSelfData()`
# unsets exactly `@self` and `id` before the body is written.
# ---------------------------------------------------------------------------
_ENVELOPE_EXACT = {"", "id", "uuid"}
_ENVELOPE_PREFIXES = ("@", "_")

# ---------------------------------------------------------------------------
# THE SECOND EXEMPTION, AND IT IS A DELIBERATE BLIND SPOT.
#
# `MetadataHydrationHandler::hydrateObjectMetadata()` reads the body for a
# display name, description and summary and copies whichever it finds into the
# object's `_name` / `_description` / `_summary` METADATA columns, via
# `tryCommonFields()`. It never unsets them. So when the schema does not
# declare one of these, the body copy is still dropped — but the VALUE is not
# lost: it is in a metadata column, and every list and detail view reads it
# from there.
#
# They are therefore not the defect this gate is about, and reporting them
# would drown it: measured across the fleet's ~5,800 shipped objects,
# `description` appears 1,431 times, `name` 1,333, `title` 507, `slug` 494,
# `summary` 59 — an order of magnitude more than every real finding combined.
#
# STATED AS A LIMIT, NOT HIDDEN: an object that carries `title` against a
# schema that declares `title` as a real business field with its own semantics
# is not judged by this gate. That is a narrower gate than the ideal one and a
# much more useful one than the ideal one nobody runs.
#
# The spellings are `tryCommonFields()`'s own, Dutch included.
# ---------------------------------------------------------------------------
_METADATA_BEARING = {
    "slug", "image",
    "name", "title", "label", "naam", "titel",
    "description", "beschrijving", "omschrijving", "beschrijvingLang",
    "summary", "samenvatting", "shortDescription", "beschrijvingKort",
}


def _is_property_key(key: object) -> bool:
    """Whether a top-level key of a shipped object is a schema property at all."""
    if not isinstance(key, str):
        return False
    if key in _ENVELOPE_EXACT or key in _METADATA_BEARING:
        return False
    return not key.startswith(_ENVELOPE_PREFIXES)


def _app_id(app_dir: str) -> str:
    """The app's id — `<id>` in appinfo/info.xml, never the directory name.

    Directory names lag the fleet rename (humaniq's checkout is still `hrmq`),
    and `apps-extra` is full of worktree duplicates that all carry the same
    `<id>`. The id is the authority; `basename(".")` is `"."`.
    """
    info = os.path.join(app_dir, "appinfo", "info.xml")
    try:
        with open(info, encoding="utf-8") as handle:
            match = re.search(r"<id>\s*([^<\s]+)\s*</id>", handle.read())
        if match:
            return match.group(1)
    except OSError:
        pass
    return os.path.basename(os.path.abspath(app_dir))


def _json_files(app_dir: str) -> list[tuple[str, Any, str | None]]:
    """Every `lib/**/*.json` in the app, decoded.

    Returns (relative path, decoded document, parse error). A file that does
    not parse is carried with its error rather than skipped: if it is IN SCOPE
    it becomes a finding, because a gate that cannot read the file it was asked
    to judge has not judged it.
    """
    out: list[tuple[str, Any, str | None]] = []
    pattern = os.path.join(app_dir, "lib", "**", "*.json")
    for path in sorted(glob.glob(pattern, recursive=True)):
        rel = os.path.relpath(path, app_dir)
        try:
            with open(path, encoding="utf-8") as handle:
                out.append((rel, json.load(handle), None))
        except OSError as err:
            out.append((rel, None, f"could not be opened: {err}"))
        except ValueError as err:
            out.append((rel, None, f"is not valid JSON: {err}"))
    return out


def _schema_declarations(docs: list[tuple[str, Any, str | None]]) -> tuple[dict, dict, dict]:
    """Union every schema definition the app ships.

    @return (definition key -> declared property names,
             definition key -> the files that declared it,
             slug -> definition key)

    🔴 THE UNION, ACROSS EVERY FILE, INCLUDING MOCKS. Three separate reasons,
    each already a measured fleet bug:

      * A schema definition does not live in the file that declares its
        register. humaniq declares its register with a list of 54 schema NAMES
        in one file and DEFINES all 54 across thirty others (the docstring of
        `generate_mock_register._component_files` records this).
      * A schema is EXTENDED by later `register.d` fragments, which the loader
        deep-merges in sorted filename order. shillinq defines `ARInvoice`
        across seventeen fragments. Reading one file's definition and calling
        it the schema would report every property the other sixteen added.
      * A mock descriptor declares its own `components.schemas`, and the
        importer imports them. gate-106 excludes mocks when asking who OWNS a
        slug, which is a different question — for "is this property declared",
        a mock's declaration counts.

    Erring toward MORE declarations is the safe direction: it can only lose a
    finding, never invent one, and a gate that invents findings gets switched
    off.
    """
    declared: dict[str, set[str]] = {}
    sources: dict[str, set[str]] = {}
    slugs: dict[str, str] = {}

    for rel, data, _err in docs:
        if not isinstance(data, dict):
            continue
        components = data.get("components")
        if not isinstance(components, dict):
            continue
        schemas = components.get("schemas")
        if not isinstance(schemas, dict):
            continue
        for name, spec in schemas.items():
            if not isinstance(spec, dict):
                continue
            declared.setdefault(name, set())
            sources.setdefault(name, set()).add(rel)
            props = spec.get("properties")
            if isinstance(props, dict):
                declared[name].update(str(k) for k in props)
            slug = spec.get("slug")
            if isinstance(slug, str) and slug:
                slugs.setdefault(slug, name)

    return declared, sources, slugs


def _objects(rel: str, data: Any) -> list[dict]:
    """Every shipped object in one document, in every container shape it uses.

    🔴 FOUR SHAPES, ALL LIVE, ALL COUNTED. A checker keyed on one of them is
    the gate-101 blind spot with a different number on it:

      1. `components.objects` as a LIST      — 151 files fleet-wide
      2. `objects` at the TOP LEVEL, a LIST  —  56 files (all shillinq)
      3. `components.objects` as a DICT keyed by slug — 3 files (shillinq)
      4. `x-openregister.seedData.objects`, a MAP of schema slug -> list —
         9 files (decidiq's four profiles, stackiq, openregister's DSAR pack),
         read by `ImportHandler::importSeedData()`
    """
    found: list[dict] = []
    if not isinstance(data, dict):
        return found

    components = data.get("components")
    containers = [data.get("objects")]
    if isinstance(components, dict):
        containers.append(components.get("objects"))

    for container in containers:
        if isinstance(container, list):
            found.extend(o for o in container if isinstance(o, dict))
        elif isinstance(container, dict):
            found.extend(o for o in container.values() if isinstance(o, dict))

    marker = data.get("x-openregister")
    if isinstance(marker, dict):
        seed = marker.get("seedData")
        if isinstance(seed, dict) and isinstance(seed.get("objects"), dict):
            for bucket in seed["objects"].values():
                if isinstance(bucket, list):
                    found.extend(o for o in bucket if isinstance(o, dict))
    return found


def _in_scope(rel: str, schema_key: str | None, changed: set[str] | None,
              sources: dict[str, set[str]]) -> bool:
    """Whether this object is judged by this run.

    🔴 WIDER THAN "THE OBJECT'S OWN FILE CHANGED", AND THE INCIDENT SAYS WHY.
    dossiq#1782 was created by two PRs a minute apart: #1779 REMOVED a property
    from a schema, and #1780 added the only seed object carrying it. Neither PR
    touched both files. A gate scoped to the object's own file passes #1779
    (it changed no object) and passes #1780 (against the schema as it read
    before #1779 landed, if it read the base at all).

    So an object is in scope when its own file changed OR when any file that
    DECLARES its schema changed. Removing a property is then judged against
    every object that was relying on it, which is the direction the incident
    actually travelled.
    """
    if changed is None:
        return True
    if rel in changed:
        return True
    if schema_key is None:
        return False
    return bool(sources.get(schema_key, set()) & changed)


def run(app_dir: str, changed: set[str] | None) -> int:
    app_id = _app_id(app_dir)
    docs = _json_files(app_dir)
    if not docs:
        print(f"{app_id}: no JSON under lib/ — nothing ships objects here.")
        print("checked 0 object(s)")
        return 4

    declared, sources, slugs = _schema_declarations(docs)

    findings = 0
    checked = 0
    unjudged: list[str] = []

    for rel, data, err in docs:
        if err is not None:
            # Only a finding when the unreadable file is one this run was asked
            # to judge. Fail closed: an unreadable descriptor in scope is not a
            # pass, and JSON validity is not this gate's subject elsewhere.
            if changed is not None and rel not in changed:
                continue
            findings += 1
            print(f"FAIL {app_id}: {rel} {err} — this run was asked to judge it and could not.")
            continue

        for obj in _objects(rel, data):
            ref = obj.get("@self", {})
            ref = ref.get("schema") if isinstance(ref, dict) else None

            key: str | None = None
            if isinstance(ref, str) and ref:
                # 🔴 THE SLUG FIRST, THEN THE DEFINITION KEY. The importer
                # resolves `@self.schema` as a SLUG, and most apps' keys happen
                # to BE their slugs — which is why keying on one alone survives
                # nearly everywhere and then misses entirely on hermiq (30 of
                # 30 keys differ from their slugs) and buildiq (15 of 16).
                if ref in slugs:
                    key = slugs[ref]
                elif ref in declared:
                    key = ref

            if not _in_scope(rel, key, changed, sources):
                continue

            if key is None:
                # UNJUDGED, NOT CLEAN. The object names a schema this app does
                # not define — a cross-app reference, or a schema that ships
                # elsewhere. Every one of its properties would read as
                # undeclared, so reporting it would be a guess. Counted and
                # named in the summary so the number is never mistaken for a
                # judgement.
                unjudged.append(f"{rel}: @self.schema '{ref}' is not defined in this app")
                continue

            checked += 1
            allowed = declared[key]
            orphans = [k for k in obj if _is_property_key(k) and k not in allowed]
            if not orphans:
                continue

            findings += 1
            where = ", ".join(sorted(sources.get(key, {"?"})))
            slug = obj.get("@self", {}).get("slug") if isinstance(obj.get("@self"), dict) else None
            print(
                f"FAIL {app_id}: {rel} — object '{slug or '<no slug>'}' carries "
                f"{len(orphans)} propert{'y' if len(orphans) == 1 else 'ies'} schema "
                f"'{key}' does not declare: {', '.join(sorted(orphans))}. "
                f"OpenRegister stores none of them and answers 200; a filter on one "
                f"compiles to `1 = 0`. Declare the propert"
                f"{'y' if len(orphans) == 1 else 'ies'} in {where}, or remove "
                f"{'it' if len(orphans) == 1 else 'them'} from the object."
            )

    if unjudged:
        print(f"NOTE {app_id}: {len(unjudged)} object(s) were NOT judged — their schema is not "
              f"defined in this app, so every property would read as undeclared:")
        for line in sorted(set(unjudged))[:20]:
            print(f"  NOTE   {line}")

    # The terminal summary the runner greps for. A run that crashed before this
    # line has measured nothing, and the runner says so rather than passing.
    print(f"checked {checked} object(s)")
    return 1 if findings else 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app_dir")
    parser.add_argument("--only-changed", action="store_true")
    args = parser.parse_args(argv)

    changed: set[str] | None = None
    if args.only_changed:
        changed = {line.strip() for line in sys.stdin.read().splitlines() if line.strip()}
        if not changed:
            print("no changed files were supplied on stdin, so nothing is in scope.")
            print("checked 0 object(s)")
            return 4
        # Nothing this gate can judge changed. NOT APPLICABLE, not a pass.
        if not any(c.startswith("lib/") and c.endswith(".json") for c in changed):
            print("this diff touches no JSON under lib/, so no shipped object is in scope.")
            print("checked 0 object(s)")
            return 4

    return run(args.app_dir, changed)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
