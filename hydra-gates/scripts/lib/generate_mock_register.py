#!/usr/bin/env python3
"""Generate a `type: mock` register descriptor from an app's real ones.

WHY THIS IS GENERATED AND NOT WRITTEN

The fleet declares 578 schemas. 562 of them have no mock data. At the three
objects per schema the mock-data rule asks for, that is ~1,686 objects, across
payroll, archival, procurement, education and case management — domains whose
vocabulary an author outside them does not have.

Hand-writing them produces objects that LOOK right and are not: a `bsn` with a
failing 11-proef, a `status` outside the schema's own enum, a required field
quietly omitted. Demo data that does not satisfy its own schema is worse than
none, because the first thing it breaks is the demo.

🔴 SO NOTHING HERE IS INVENTED. Every value is derived from the schema that will
validate it — `enum` picks from the enum, `format` drives the shape, `minimum`
and `maxLength` are honoured, `required` is always populated. The output is
conformant BY CONSTRUCTION, and `--check` re-validates it against the same
schema so a drifted schema shows up as a failure rather than as a demo that
half-loads.

WHAT IT DELIBERATELY DOES NOT DO

It does not try to be plausible prose. `Voorbeeld Achternaam 2` is obviously
sample data, and that is the point: a demo dataset that reads like real records
invites somebody to treat it as real. Apps that want curated, domain-true data
for a headline schema override it — see `--keep`.

USAGE
  generate-mock-register.py <app-dir> [--objects N] [--out FILE] [--check]

  --objects N   objects per schema (default 3: enough for a list to look like a
                list, for an empty state to be distinguishable from a populated
                one, and for a detail page to have siblings to page between)
  --check       validate an existing mock descriptor instead of writing one;
                exits non-zero when a schema and its mock have drifted apart
  --keep        preserve objects already present for a schema, and top up only
                the schemas that are short. Curated data survives regeneration.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from typing import Any

# Deterministic on purpose: a generator seeded by the clock produces a fresh
# diff on every run, and a mock descriptor that churns is one no reviewer reads.
# Values are derived from (schema, property, index) instead.
LOREM = ["Alfa", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel"]


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-") or "item"


def _from_format(fmt: str, index: int) -> Any:
    """A value whose SHAPE the declared format demands."""
    day = f"{((index % 28) + 1):02d}"
    table = {
        "date": f"2026-03-{day}",
        "date-time": f"2026-03-{day}T09:00:00+00:00",
        "time": f"09:{((index % 60)):02d}:00",
        "email": f"voorbeeld{index}@example.invalid",
        "uri": f"https://example.invalid/resource/{index}",
        "url": f"https://example.invalid/resource/{index}",
        "hostname": "example.invalid",
        "ipv4": f"192.0.2.{(index % 254) + 1}",
        "uuid": f"00000000-0000-4000-8000-{index:012d}",
        "duration": "PT1H",
        # A placeholder that marks itself. See the module docstring: sample data
        # that reads as real is sample data somebody acts on.
        "bsn": f"BSN-PLACEHOLDER-{index:04d}",
        "password": "CHANGE_ME",
    }
    return table.get(fmt, f"Voorbeeld {fmt or 'waarde'} {index}")


# Anchored concatenations of character classes with fixed lengths — which is
# what almost every real `pattern` in the fleet's schemas is: a hex colour, a
# postcode, a reference number. Anything more exotic falls through to the
# candidate search in _satisfy_pattern(), and if THAT fails the value is left
# alone so the validator reports it rather than the generator hiding it.
def _expand_class(body: str) -> str:
    """Expand a character-class body into the characters it admits.

    🔴 PARSED, NOT LOOKED UP. The first version matched class bodies against a
    hardcoded table (`"0-9"`, `"A-Za-z"`, …), which meant every compound class
    the fleet actually uses — `[a-z0-9-]`, `[a-zA-Z0-9-_]`, `[/a-zA-Z0-9/_-]` —
    fell straight through and produced a value failing its own pattern. A table
    of the classes I happened to think of is not a parser.
    """
    if body.startswith("^"):
        # A negated class: anything outside it. Lowercase letters are the safest
        # generic answer and are excluded by the negations seen in practice.
        return "abcdefghijklmnopqrstuvwxyz"

    out: list[str] = []
    i = 0
    while i < len(body):
        if body[i] == "\\" and i + 1 < len(body):
            out.extend({"d": "0123456789", "w": "abcdefghijklmnopqrstuvwxyz0123456789_",
                        "s": " "}.get(body[i + 1], body[i + 1]))
            i += 2
            continue
        # A range only counts when the '-' sits BETWEEN two characters; a
        # trailing or leading '-' is a literal hyphen, which is exactly how
        # `[a-z0-9-]` is written.
        if i + 2 < len(body) and body[i + 1] == "-" and body[i + 2] != "]":
            start, end = ord(body[i]), ord(body[i + 2])
            if start <= end:
                out.extend(chr(c) for c in range(start, end + 1))
                i += 3
                continue
        out.append(body[i])
        i += 1

    return "".join(dict.fromkeys(out)) or "abcdefghijklmnopqrstuvwxyz"


def _synthesise(pattern: str, index: int, min_len: int = 0) -> str | None:
    """Build a string for an anchored class-and-quantifier pattern, or None."""
    body = pattern
    # Lookarounds constrain but do not generate. Dropping them lets the class
    # walk below build a candidate; _satisfy_pattern then verifies against the
    # FULL pattern, so a candidate the lookaround rejects is still caught.
    body = re.sub(r"\(\?[=!<][^)]*\)", "", body)
    if body.startswith("^"):
        body = body[1:]
    if body.endswith("$"):
        body = body[:-1]

    # A GROUPED ALTERNATION resolves to its first branch. `^([01]\\d|2[0-3]):[0-5]\\d$`
    # — a clock time — is the shape this appears in throughout the fleet, and
    # the walk below cannot step over `(` or `|`. Taking the first branch turns
    # it back into a plain class-and-quantifier run; _satisfy_pattern still
    # verifies the result against the FULL pattern, so a wrong branch is caught
    # rather than shipped.
    # An OPTIONAL group contributes nothing to the shortest matching string, so
    # drop it. `^\\d+\\.\\d+\\.\\d+(?:[-+][\\w.-]+)?$` — semver with an optional
    # pre-release — could not be walked at all with the group present, so the
    # value fell through unchanged and failed its own pattern.
    body = re.sub(r"\((?:\?:)?[^()]*\)[?*]", "", body)

    while True:
        group = re.search(r"\((?:\?:)?([^()]*\|[^()]*)\)", body)
        if group is None:
            break
        body = body[:group.start()] + group.group(1).split("|")[0] + body[group.end():]

    # A remaining non-capturing group is just its contents.
    body = re.sub(r"\(\?:([^()]*)\)", r"\1", body)

    out = []
    pos = 0
    while pos < len(body):
        # NO optional leading backslash: it swallowed the one `\d` needs, so
        # `^CVE-\d{4}-\d{4,}$` tokenised as a literal and produced a string
        # failing its own pattern. The escape branch consumes its own backslash.
        # `\\(?P<esc>[dws])` alone left `\\.` matching NEITHER branch, so the walk
        # abandoned every semver pattern — `^[0-9]+\\.[0-9]+\\.[0-9]+$` produced a
        # value failing it. An escaped anything-else is a literal of itself.
        token = re.match(r"(\[(?P<cls>[^\]]+)\]|\\(?P<esc>[dws])|\\(?P<elit>.)|(?P<lit>[^\[\\{}()|+*?]))"
                         r"(?:\{(?P<n>\d+)(?:,(?P<m>\d*))?\}|(?P<one>[+*?]))?", body[pos:])
        if token is None:
            return None
        pos += token.end()

        literal = token.group("lit")
        if literal is None:
            literal = token.group("elit")
        if literal is not None:
            alphabet = literal
            fixed = True
        else:
            cls = token.group("cls")
            if cls is None:
                cls = {"d": "0-9", "w": "A-Za-z0-9", "s": " "}[token.group("esc")]
            alphabet = _expand_class(cls)
            fixed = False

        count = 1
        if token.group("n"):
            # `\d*` after the comma, not `\d+`: an OPEN upper bound writes
            # `{4,}` with nothing after it. Requiring a digit there left the
            # quantifier unconsumed, the walk stuck, and the whole pattern
            # abandoned — so `^CVE-\d{4}-\d{4,}$` produced a value failing it.
            # `{4,}` and `{4,8}` both satisfy at their MINIMUM — the smallest
            # string the pattern admits is the one least likely to trip a
            # maxLength somewhere else on the same property.
            count = int(token.group("n"))
        elif token.group("one") in {"+", "*"}:
            # 🔴 AN OPEN QUANTIFIER MUST REACH minLength. `+` expanded to a flat
            # three characters, so `minLength: 20` with
            # `pattern: ^[A-Za-z0-9+/=]+$` produced "ABC" — a value satisfying
            # its pattern and violating its length, which is the same defect as
            # one satisfying its length and violating its pattern.
            count = max(3, min_len) if token.group("one") == "+" else min_len

        if fixed:
            out.append(alphabet * max(count, 1) if token.group("n") else alphabet)
        else:
            out.append("".join(alphabet[(index + i) % len(alphabet)] for i in range(count)))

    return "".join(out) or None


def _satisfy_pattern(value: Any, pattern: str, index: int, min_len: int = 0) -> Any:
    """Return a value matching `pattern`, or the original when none can be built."""
    try:
        compiled = re.compile(pattern)
    except re.error:
        return value

    # The length check belongs HERE, not after. An early return on "the pattern
    # matches" handed back "ABC" for `minLength: 20` — pattern-valid and
    # length-invalid, because only one of the two constraints was consulted.
    if (
        isinstance(value, str)
        and compiled.search(value)
        and len(value) >= min_len
    ):
        return value

    built = _synthesise(pattern, index, min_len)
    if built is not None and compiled.search(built):
        return built

    # 🔴 LEFT ALONE ON PURPOSE when nothing can be built. Emitting a value that
    # silently fails its own pattern is what `--check` exists to catch; quietly
    # substituting a wrong-but-different value would hide it instead.
    return value


# 🔴 READ FROM THE GATE'S OWN FILE, NEVER COPIED. gate-60 (icon-vocabulary)
# validates icons against `schemas/semantic-icons.json`; an icon outside it
# "renders blank wherever it is not aliased locally". The generator emitted
# `Voorbeeld Icon 1` for a property called `icon`, and gate-60 correctly failed
# the very PR that added the demo data.
#
# Carrying a copy of the vocabulary here is how the producer and the judge drift
# apart — the defect this package already had once today. Same file, one truth.
_ICON_CACHE: list[str] | None = None


def _vocabulary_icons() -> list[str]:
    """Icon names gate-60 accepts, read from its own vocabulary file."""
    global _ICON_CACHE  # noqa: PLW0603
    if _ICON_CACHE is not None:
        return _ICON_CACHE

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "schemas", "semantic-icons.json")
    names: list[str] = []
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        # 🔴 THE VALUES, NOT THE KEYS. This file maps a SEMANTIC key to the MDI
        # component name — `"documentation": "BookOpenVariantOutline"` — and
        # gate-60 accepts the MDI name. Emitting the key produced `documentation`,
        # which the gate rejects in the same breath as the invented name it
        # replaced: "a kebab-case or lowercase spelling of an MDI name resolves
        # to nothing". Half-reading a vocabulary is not reading it.
        for tier in ("tierA", "tierB"):
            block = data.get(tier)
            if isinstance(block, dict):
                names.extend(
                    v for k, v in block.items()
                    if not k.startswith("_") and isinstance(v, str) and v
                )
    except (OSError, ValueError):
        names = []

    # An EMPTY list is not a silent fallback to invented names: with no
    # vocabulary readable the caller leaves the value alone and gate-60 reports
    # it, which is the honest outcome.
    _ICON_CACHE = names
    return _ICON_CACHE


def _default_is_usable(default: Any, spec: dict) -> bool:
    """Whether a declared `default` actually satisfies its own property schema.

    Authors write defaults as documentation of intent, and nothing validates
    them: shillinq's `JournalEntry.lawfulness` defaults to an object whose
    `summary_opinion` is null while the nested schema admits only four
    non-null strings. Emitting that default produced a demo object that failed
    the very schema the default is written into.

    🔴 UNAVAILABLE VALIDATION IS NOT A CLEAN BILL OF HEALTH — but here the safe
    direction is to KEEP the author's default, because rejecting every default
    when `jsonschema` is missing would discard good ones wholesale and change
    output based on what happens to be installed. `--check` performs the real
    validation either way, so a bad default that slips through is reported
    rather than shipped silently.
    """
    try:
        import jsonschema  # noqa: PLC0415
    except ImportError:
        return True

    checkable = {
        k: v for k, v in spec.items()
        if k in {"type", "properties", "required", "enum", "items", "pattern",
                 "minLength", "maxLength", "minimum", "maximum", "multipleOf"}
    }
    if not checkable:
        return True

    try:
        jsonschema.validate(instance=default, schema=_drop_refs(checkable))
    except jsonschema.ValidationError:
        return False
    except Exception:  # noqa: BLE001
        # A schema too broken to validate against says nothing about the
        # default. Leave it to `--check`, which reports invalid schemas by name.
        return True
    return True


def _value(name: str, spec: dict, index: int, depth: int = 0) -> Any:
    """One value for one property, derived from that property's own rules."""
    if not isinstance(spec, dict):
        return f"Voorbeeld {index}"

    # 🔴 ENUM FIRST, ALWAYS. A value outside a declared enum is the single most
    # common way generated demo data fails validation, and it fails at save
    # time — long after the descriptor was reviewed and merged.
    enum = spec.get("enum")
    if isinstance(enum, list) and enum:
        return enum[index % len(enum)]

    const = spec.get("const")
    if const is not None:
        return const

    # A `default: null` on a typed property is not a usable value — it is the
    # absence of one, and handing it back produced `None is not of type 'string'`
    # on real fleet schemas. Fall through and derive a value instead.
    #
    # 🔴 AND A NON-NULL DEFAULT IS NOT AUTOMATICALLY A VALID ONE. shillinq's
    # `JournalEntry.lawfulness` declares a default OBJECT that carries
    # `summary_opinion: null` while its own nested schema restricts that
    # property to four non-null strings. Returning the default wholesale
    # emitted a demo object that failed the schema the default belongs to. A
    # default is an author's convenience, not a validated value.
    if "default" in spec and spec["default"] is not None:
        if _default_is_usable(spec["default"], spec):
            return spec["default"]

    kind = spec.get("type")
    if isinstance(kind, list):
        kind = next((k for k in kind if k != "null"), "string")

    if kind == "integer" or kind == "number":
        low = spec.get("minimum", spec.get("exclusiveMinimum", 1))
        try:
            # float(), not int(): `minimum: 0.01` truncated to 0 produced a value
            # BELOW its own minimum — the generator breaking the rule it was
            # reading. Integers are re-narrowed on return.
            low = float(low)
        except (TypeError, ValueError):
            low = 1.0
        if "exclusiveMinimum" in spec:
            low += 1
        value = low + index
        high = spec.get("maximum")
        if high is not None:
            try:
                value = min(value, int(high))
            except (TypeError, ValueError):
                pass
        # 🔴 `multipleOf` IS A CONSTRAINT, AND FLOATS DO NOT SATISFY IT BY LUCK.
        # shillinq declares `amount` with `multipleOf: 0.01`; the natural value
        # 2.01 is rejected, because a validator computes 2.01 / 0.01 and gets
        # 200.99999999999997. Snapping through Decimal produces a value that is
        # an exact multiple in the arithmetic the validator actually uses.
        step = spec.get("multipleOf")
        if isinstance(step, (int, float)) and not isinstance(step, bool) and step > 0:
            import math  # noqa: PLC0415

            # 🔴 SNAP IN THE VALIDATOR'S ARITHMETIC, NOT IN EXACT ARITHMETIC.
            # A Decimal snap produces a mathematically perfect multiple and
            # still fails: jsonschema tests `instance / multipleOf` in FLOAT,
            # and 2.01 / 0.01 is 200.99999999999997. `amount` came out as
            # 0.01, 1.01, 2.01 — the first two passed and the third did not,
            # which is exactly the kind of near-miss that looks like a fluke
            # and is really a units bug.
            #
            # So walk multiples until one divides cleanly the way the checker
            # divides. The cap keeps a pathological step from spinning; the
            # value is returned unsnapped in that case and `--check` reports it
            # rather than the generator claiming success.
            start = max(int(math.ceil(value / step)), 1)
            for k in range(start, start + 1000):
                candidate = step * k
                high_bound = spec.get("maximum")
                if isinstance(high_bound, (int, float)) and not isinstance(high_bound, bool):
                    if candidate > high_bound:
                        break
                quotient = candidate / step
                if int(quotient) == quotient:
                    return int(candidate) if kind == "integer" else float(candidate)

        if kind == "integer":
            import math  # noqa: PLC0415
            return int(math.ceil(value))
        return float(value)

    if kind == "boolean":
        return index % 2 == 0

    if kind == "array":
        if depth >= 3:
            return []
        items = spec.get("items") if isinstance(spec.get("items"), dict) else {}
        count = max(int(spec.get("minItems", 1) or 1), 1)
        return [_value(name, items, index + i, depth + 1) for i in range(count)]

    if kind == "object":
        if depth >= 3:
            # 🔴 REQUIRED SURVIVES THE DEPTH CAP. Returning a bare {} here
            # produced `sections.N.items.N: 'x' is a required property` — the
            # recursion guard, not the schema, deciding an object could be
            # empty. Emit the required keys flat and stop recursing.
            deep_req = spec.get("required")
            deep_req = deep_req if isinstance(deep_req, list) else []
            deep_props = spec.get("properties")
            deep_props = deep_props if isinstance(deep_props, dict) else {}
            return {
                key: f"Voorbeeld {key} {index + 1}"
                if not isinstance(deep_props.get(key), dict)
                else _value(key, {k: v for k, v in deep_props[key].items()
                                  if k not in {"properties", "items"}}, index, depth)
                for key in deep_req[:8]
            }
        props = spec.get("properties")
        if not isinstance(props, dict):
            return {}
        nested_required = spec.get("required")
        nested_required = nested_required if isinstance(nested_required, list) else []
        # Required first here too — the cap below must never be what drops a
        # property the nested schema demands.
        ordered = [k for k in nested_required if k in props]
        ordered += [k for k in props if k not in ordered]
        return {
            key: _value(key, props.get(key, {}), index, depth + 1)
            for key in ordered[:8]
        }

    # 🔴 A `pattern` OUTRANKS A `format`. Both may be declared on one property,
    # and the format placeholder does not have to satisfy the pattern: procest's
    # `citizenServiceNumber` is `format: bsn` with `pattern: ^[0-9]{9}$`, and the
    # BSN placeholder is `BSN-PLACEHOLDER-0000` — letters and hyphens against a
    # nine-digit-only pattern. shillinq's `sourceDocumentUri` is the same shape:
    # a `uri` format under `^docudesk://attachments/[a-f0-9-]{36}/.+$`.
    #
    # Returning the format value directly skipped the pattern entirely. The
    # format still chooses the SHAPE; the pattern gets the last word.
    fmt = spec.get("format")
    if fmt:
        formatted = _from_format(str(fmt), index)
        fmt_pattern = spec.get("pattern")
        if isinstance(formatted, str) and isinstance(fmt_pattern, str) and fmt_pattern:
            return _satisfy_pattern(
                formatted,
                fmt_pattern,
                index,
                spec.get("minLength") if isinstance(spec.get("minLength"), int) else 0,
            )
        return formatted

    # A property NAMED for an icon must carry one. Everything else about the
    # value is generic on purpose; this one is checked by another gate.
    if kind in (None, "string") and re.fullmatch(r"(?i)icon|.*icon", name or ""):
        icons = _vocabulary_icons()
        if icons:
            return icons[index % len(icons)]

    text = f"Voorbeeld {name.replace('_', ' ').strip().title()} {index + 1}"

    # A generated value that violates the schema's OWN length bound is the same
    # defect as one violating its enum, just later in the file.
    max_len = spec.get("maxLength")
    if isinstance(max_len, int) and max_len > 0:
        text = text[:max_len]
    min_len = spec.get("minLength")
    if isinstance(min_len, int) and len(text) < min_len:
        text = (text + " " + LOREM[index % len(LOREM)] * min_len)[:min_len]

    # A declared `pattern` is as binding as a declared enum, and was the first
    # thing `--check` caught: `Voorbeeld Color 1` against `^#[0-9A-Fa-f]{6}$`.
    pattern = spec.get("pattern")
    if isinstance(pattern, str) and pattern:
        text = _satisfy_pattern(
            text, pattern, index, min_len if isinstance(min_len, int) else 0
        )

    return text


def _object_for(register: str, schema_name: str, schema: dict, index: int) -> dict:
    props = schema.get("properties")
    props = props if isinstance(props, dict) else {}
    required = schema.get("required")
    required = required if isinstance(required, list) else []

    body: dict[str, Any] = {}
    # REQUIRED FIRST, so a schema with many optional properties cannot push a
    # required one past the cap below and produce an object that fails to save.
    for key in required:
        # 🔴 EMITTED EVEN WITH NO SPEC. A schema may list a property in
        # `required` that its `properties` map does not describe. Skipping it
        # produced objects failing their own `required` — the generator omitting
        # the one field the schema insists on. An untyped required key gets a
        # plain string, which is what an undescribed property most often is.
        body[key] = _value(key, props.get(key, {}), index)

    for key, spec in props.items():
        if key in body:
            continue
        if len(body) >= 24:
            break
        body[key] = _value(key, spec, index)

    label = body.get("name") or body.get("title") or f"{schema_name}-{index + 1}"

    return {
        "@self": {
            "register": register,
            "schema": schema_name,
            "slug": _slugify(f"{schema_name}-{label}-{index + 1}"),
        },
        **body,
    }


def _as_dict(value: object) -> dict:
    """`value` when it is a mapping, otherwise an empty one.

    Descriptor `components` blocks are not uniformly shaped: some ship
    `registers` as a LIST of register objects rather than a slug-keyed map.
    Anything reading `.keys()` off them without checking crashes on those.
    """
    return value if isinstance(value, dict) else {}


def _app_id(app_dir: str) -> str:
    """The app's id — `<id>` in appinfo/info.xml, never the directory name.

    🔴 `x-openregister.app` IS LOAD-BEARING. The descriptor inventory resolves
    a register to an app by that field, so writing the wrong value attributes
    the register to an app that does not exist — and the `--app=` command this
    generator prints into its own description then resolves nothing.

    Directory names lag the fleet rename: humaniq's checkout is still `hrmq`
    while its shipped `<id>` is already `humaniq`, and the same split will
    reach every app whose id moves. The id is the authority (CLAUDE.md), so
    read it rather than infer it from where the checkout happens to sit.

    Falls back to the directory basename when info.xml has no `<id>`, which is
    what a non-app directory looks like. abspath first: `basename(".")` is
    `"."`, a nonsense id (and filename) the gate would otherwise produce every
    time, since it always passes a relative dot.
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


def _merge_definition(existing: dict | None, incoming: dict) -> dict:
    """Combine two files' definitions of the SAME schema name.

    An extending file carries the properties the base does not, so the schema
    the demo data must satisfy is the union. Property maps and `required` lists
    are unioned; every other key keeps the first file's value, because a later
    file that merely extends has no business restating a `title` or a `slug`.

    The base is not privileged over the overlay for individual properties: a
    name defined in both keeps the FIRST seen, matching the previous behaviour
    for the only case where the two genuinely disagree.
    """
    if not isinstance(existing, dict):
        return incoming

    merged = dict(existing)

    old_props = existing.get("properties")
    new_props = incoming.get("properties")
    if isinstance(new_props, dict):
        props = dict(old_props) if isinstance(old_props, dict) else {}
        for prop_name, prop_spec in new_props.items():
            props.setdefault(prop_name, prop_spec)
        merged["properties"] = props

    old_req = existing.get("required")
    new_req = incoming.get("required")
    if isinstance(new_req, list):
        seen = list(old_req) if isinstance(old_req, list) else []
        for item in new_req:
            if item not in seen:
                seen.append(item)
        merged["required"] = seen

    for key, value in incoming.items():
        if key not in ("properties", "required"):
            merged.setdefault(key, value)

    return merged


def _component_files(app_dir: str) -> list[tuple[str, dict]]:
    """Every non-mock file an app ships that carries a `components` block.

    🔴 WIDER THAN `_descriptors`, DELIBERATELY. A schema definition does not
    have to live in the file that declares its register. hrmq declares the
    `humaniq` register with a list of 54 schema NAMES in one file and DEFINES
    all 54 across thirty others that declare no register at all.

    Sweeping definitions only from register-declaring files left every one of
    those names undefined; the resolver then dropped them as unresolvable and
    the generator announced "hrmq: declares no schemas — nothing to generate"
    and exited 0. Three apps — hrmq, doriath, hermiq — were written off as
    having no schemas on the strength of that sentence.

    The predicate that finds the files must be as wide as the thing being
    collected. Registers still come from the narrow set below.
    """
    found = []
    for path in sorted(glob.glob(os.path.join(app_dir, "lib", "**", "*.json"), recursive=True)):
        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        components = data.get("components")
        if not isinstance(components, dict):
            continue
        registers = components.get("registers")
        schemas = components.get("schemas")
        has_registers = isinstance(registers, dict) and bool(registers)
        has_schemas = isinstance(schemas, dict) and bool(schemas)
        if not has_registers and not has_schemas:
            continue
        marker = data.get("x-openregister")
        marker = marker if isinstance(marker, dict) else {}
        if marker.get("type") == "mock":
            continue
        found.append((path, data))
    return found


def _descriptors(app_dir: str) -> list[tuple[str, dict]]:
    """The subset that DECLARES a register — the authority on register->schema.

    Kept narrow on purpose: the `fallback` rule below ("a register that names
    no list carries the schemas defined beside it") is only meaningful in a
    file where the register is actually declared. Widening this set would
    restore the cross-product the map exists to prevent.
    """
    return [
        (path, data)
        for path, data in _component_files(app_dir)
        if isinstance(data["components"].get("registers"), dict)
        and bool(data["components"]["registers"])
    ]


def _owns_register(data: dict, app_id: str | None) -> bool:
    """Whether THIS app owns the register a descriptor declares.

    🔴 A DESCRIPTOR IN AN APP'S TREE IS NOT NECESSARILY THAT APP'S REGISTER.
    openregister ships `n8n_workflows.openregister.json`, which declares
    `x-openregister.app: n8n` — the n8n app's register, carried here so it
    installs alongside. Generating demo data for it put five foreign schemas
    into openregister's descriptor, under a register openregister does not
    own, and openregister's own `validate-register` rejected them for missing
    `slug` (a field n8n's schemas do not declare).

    This is the same rule the descriptor INVENTORY already applies — attribute
    by the DECLARING app, not by which tree the file sits in. The generator
    disagreed with the inventory, so the two tools described different fleets.

    A descriptor with no `app` marker is this app's own, which is the ordinary
    single-app case.
    """
    if app_id is None:
        return True
    marker = data.get("x-openregister")
    marker = marker if isinstance(marker, dict) else {}
    declared = marker.get("app")
    if not isinstance(declared, str) or not declared:
        return True
    return declared == app_id


def _register_schema_map(
    app_dir: str, app_id: str | None = None
) -> tuple[dict[str, dict], dict[str, list[str]], dict[str, dict]]:
    """Resolve which schemas each register actually carries.

    🔴 THE REGISTER'S OWN `schemas` LIST IS THE AUTHORITY, and honouring it is
    not optional. Fleet descriptors are MODULAR: pipelinq declares one register
    across twenty files, each contributing a few schemas, and one file may
    declare several registers at once. Pairing every register in a file with
    every schema in that file is a cross-product — it generated six objects for
    `client` instead of three, attributed schemas to registers that do not carry
    them, and validated objects against a same-named schema defined in a
    different file.

    Falls back to "every schema in this file" only for a register that declares
    no list, which is what a single-register descriptor looks like.

    @return (registers, register->schema names, schema name->definition)
    """
    registers: dict[str, dict] = {}
    owns: dict[str, set[str]] = {}
    definitions: dict[str, dict] = {}
    fallback: dict[str, set[str]] = {}

    # Definitions are swept from EVERY component file, register-declaring or
    # not — see _component_files. The register pairing below stays narrow.
    #
    # 🔴 MERGED, NOT first-wins. A fleet app may define one schema across more
    # than one file: pipelinq ships a base `ticket` and a separate CTI overlay
    # that adds `telephony_platform` and friends, with its own comment saying
    # "the overlay must land here or OpenRegister's magic-table columns for
    # these fields never exist". `setdefault` kept whichever file sorted first
    # and silently discarded the other — so which half of `ticket` the demo
    # data was generated against depended on a filename. Neither outcome is
    # wrong-looking: both produce a valid object against a real schema.
    for _path, data in _component_files(app_dir):
        decl_schemas = data["components"].get("schemas")
        if isinstance(decl_schemas, dict):
            for name, spec in decl_schemas.items():
                if isinstance(spec, dict):
                    definitions[name] = _merge_definition(definitions.get(name), spec)

    for _path, data in _descriptors(app_dir):
        # A register another app declares is not this app's to seed — see
        # _owns_register.
        if not _owns_register(data, app_id):
            continue

        components = data["components"]
        decl_registers = components.get("registers") or {}
        decl_schemas = components.get("schemas") or {}

        for slug, reg in (decl_registers or {}).items():
            if not isinstance(reg, dict):
                continue
            if slug not in registers or len(reg) > len(registers[slug]):
                registers[slug] = reg
            # 🔴 UNION, NOT else. A modular register declares its `schemas` list
            # in SOME files and not others — pipelinq names it in one file and
            # omits it in twenty more that each define a few schemas. Treating
            # the list as authoritative wherever it appeared, and ignoring the
            # rest, dropped scholiq from 118 schemas to 1 and launchpad to 0.
            #
            # A register carries the union of every list it declares AND the
            # schemas defined alongside it in files where it declares none.
            listed = reg.get("schemas")
            if isinstance(listed, list) and listed:
                owns.setdefault(slug, set()).update(str(x) for x in listed)
            if isinstance(decl_schemas, dict) and decl_schemas:
                fallback.setdefault(slug, set()).update(decl_schemas.keys())

    resolved: dict[str, list[str]] = {}
    for slug in registers:
        names = set(owns.get(slug, set())) | set(fallback.get(slug, set()))
        # Only schemas that are actually DEFINED somewhere: a register may list
        # a name whose definition ships in a file this app does not have.
        resolved[slug] = sorted(n for n in names if n in definitions)

    return registers, resolved, definitions


def build(app_dir: str, app_id: str, per_schema: int, existing: dict | None) -> dict:
    keep: dict[tuple[str, str], list] = {}
    if existing:
        for obj in existing.get("components", {}).get("objects", []) or []:
            ref = obj.get("@self", {}) if isinstance(obj, dict) else {}
            keep.setdefault((ref.get("register", ""), ref.get("schema", "")), []).append(obj)

    decl_registers, owns, definitions = _register_schema_map(app_dir, app_id)

    registers: dict[str, Any] = {}
    schemas: dict[str, Any] = {}
    objects: list[dict] = []

    for reg_slug, reg in decl_registers.items():
        carried_names = owns.get(reg_slug) or []
        if not carried_names:
            continue

        registers[reg_slug] = {
            "slug": reg.get("slug", reg_slug),
            "title": f"{reg.get('title', reg_slug)} (demo)",
            "version": reg.get("version", "1.0.0"),
            "description": "Demo data for "
                           f"{reg.get('title', reg_slug)}. Generated from the register's own "
                           "schemas — see hydra-gates/scripts/lib/generate_mock_register.py.",
        }

        for sch_name in carried_names:
            sch = definitions[sch_name]
            schemas.setdefault(sch_name, sch)
            carried = keep.get((reg_slug, sch_name), [])
            objects.extend(carried)
            for index in range(len(carried), per_schema):
                objects.append(_object_for(reg_slug, sch_name, sch, index))

    return {
        "openapi": "3.0.0",
        "info": {
            "title": f"{app_id} demo data",
            "version": "1.0.0",
            "description": (
                "Demo data covering every schema this app supplies, offered as the first "
                "step of the app's setup walkthrough. Generated from the schemas "
                "themselves, so every object satisfies the schema that will validate it."
            ),
        },
        "x-openregister": {
            "type": "mock",
            "app": app_id,
            "description": (
                f"Demo data for {app_id}. NOT installed automatically — a mock register is "
                "imported on demand, from the setup walkthrough or "
                f"`occ openregister:descriptors:list --app={app_id} --import=<slug>`."
            ),
        },
        "paths": {},
        "components": {"registers": registers, "schemas": schemas, "objects": objects},
    }


# The seven types JSON Schema itself defines. OpenRegister's vocabulary is a
# superset; anything outside this set is its own and jsonschema cannot judge it.
_JSON_SCHEMA_TYPES = {
    "string", "number", "integer", "boolean", "array", "object", "null",
}


def _drop_refs(node: Any) -> Any:
    """Normalise an OpenAPI-flavoured schema into something jsonschema can judge.

    Two dialect differences, both of which produced FALSE FINDINGS:

    `$ref` in OpenRegister names a schema SLUG, not a URL — `{"$ref": "project"}`
    raises `RefResolutionError: unknown url type: 'project'`. Dropped, because
    this validator's question is "does the object satisfy the shape declared
    HERE"; a cross-schema reference is a relation OpenRegister owns.

    🔴 `nullable: true` IS OPENAPI, NOT JSON SCHEMA. Every descriptor in the
    fleet declares `"openapi": "3.0.0"` and uses it. jsonschema does not know
    the keyword, so a property declared nullable — and given `null` by the
    schema's OWN declared `default` — was reported as
    `None is not of type 'string'`. The data was right and the validator was
    wrong, which is the more dangerous direction: it would have had an author
    "fix" conformant demo data.

    Translated to `type: [T, "null"]`, which is what the keyword means.
    """
    if isinstance(node, dict):
        out = {k: _drop_refs(v) for k, v in node.items() if k != "$ref"}

        # 🔴 `required: true` ON A PROPERTY IS OPENAPI 2.0, NOT JSON SCHEMA,
        # where `required` is an ARRAY on the parent object. jsonschema reports
        # it as `True is not of type 'array'` — 62 such "errors" across two
        # apps, none of them a defect in the data.
        #
        # Measured before deciding: 38 of the 42 properties carrying the flag
        # are ALSO named in their parent's `required` array, so the flag is
        # redundant and consistent. Dropping it here judges the object against
        # what the parent actually declares.
        #
        # (The four that are NOT mirrored are a real finding — a field its
        # author marked required that nothing enforces — but that is a defect in
        # those schemas, and silently promoting them to required would change
        # what saves.)
        if out.get("required") is True or out.get("required") is False:
            out.pop("required", None)

        # An EMPTY `required` is "too short" to jsonschema. OpenRegister's own
        # validator unsets it — `if required is not null and empty: unset` — so
        # matching that is reading the same rule, not relaxing it.
        if isinstance(out.get("required"), list) and not out["required"]:
            out.pop("required", None)

        # 🔴 BUILDER PLACEHOLDERS ARE "UNSET", NOT A CONSTRAINT. These schemas are
        # emitted by a form builder that writes EVERY keyword, using `null` or
        # `[]` for the ones that do not apply:
        #
        #     "minLength": null, "maximum": null, "oneOf": []
        #
        # `oneOf: []` means "validate against exactly one of NOTHING", which no
        # value can satisfy — 144 properties in one app carried it. Read as
        # written they are unsatisfiable; read as intended they are absent.
        # Absent is what the author meant and what OpenRegister does.
        for key in ("oneOf", "anyOf", "allOf", "enum"):
            if key in out and (out[key] is None or out[key] == []):
                out.pop(key)
        # 🔴 ANY keyword holding null, not a list I maintain. The first version
        # enumerated minLength/maxLength/minimum/maximum/minItems/maxItems/
        # pattern/format — and still left twenty failures, because the builder
        # also writes `multipleOf: null`, `exclusiveMinimum: null` and others.
        # An enumeration of the keywords I happened to think of is the same
        # mistake as the icon table it replaced, one file apart.
        #
        # `default` and `const` are exempt: null is a legitimate VALUE for both,
        # and dropping them would discard what the schema actually declares.
        for key in [k for k, v in out.items()
                    if v is None and k not in ("default", "const")]:
            out.pop(key)

        # 🔴 OpenRegister's TYPE VOCABULARY IS WIDER THAN JSON SCHEMA'S.
        # `PropertyValidatorHandler::$validTypes` accepts `file`, `geo`, `color`,
        # `recurrence`, `NcFile`, `NcMail`, `NcContact`, `NcNote`, `NcTodo` —
        # `type: "file"` with `format: "base64"` is a first-class property type
        # here, handled at PropertyValidatorHandler:244. jsonschema knows none of
        # them, so it called twelve legitimate declarations invalid.
        #
        # Dropped rather than mapped: what these carry is app-specific and this
        # validator's question is only whether the demo VALUE is well-formed for
        # the shape declared. A `type` that is a dict is builder noise and goes
        # the same way.
        kind = out.get("type")
        if isinstance(kind, str) and kind not in _JSON_SCHEMA_TYPES:
            out.pop("type")
        elif not isinstance(kind, (str, list)) and kind is not None:
            out.pop("type")

        if out.pop("nullable", None) is True:
            kind = out.get("type")
            if isinstance(kind, str):
                out["type"] = [kind, "null"]
            elif isinstance(kind, list) and "null" not in kind:
                out["type"] = [*kind, "null"]
        return out
    if isinstance(node, list):
        return [_drop_refs(v) for v in node]
    return node


def _validate(obj: dict, schema: dict) -> str | None:
    """Validate one object against its schema. Returns the first error, or None.

    🔴 REAL VALIDATION, NOT A COUNT. An earlier draft of this file claimed in its
    docstring that `--check` "re-validates against the same schema" while the
    code only counted objects. A generator that asserts conformance it never
    checks is the same defect as demo data that does not load: both look right
    until somebody depends on them.

    Falls back to a targeted check when `jsonschema` is unavailable, rather than
    silently reporting success — an unavailable validator is not a clean bill of
    health.
    """
    body = {k: v for k, v in obj.items() if k != "@self"}
    try:
        import jsonschema  # noqa: PLC0415

        stripped = {
            k: v for k, v in schema.items()
            if k in {"type", "properties", "required", "enum", "items",
                     "additionalProperties", "nullable"}
        }
        stripped.setdefault("type", "object")

        # 🔴 OpenRegister's `$ref` IS NOT A URL. A property may carry
        # `"$ref": "project"` — a reference to another schema BY SLUG, resolved
        # by OpenRegister at save time, not by a JSON Schema resolver. Handed to
        # jsonschema it raises RefResolutionError: unknown url type: 'project'.
        #
        # Dropped rather than followed: this validator's job is "does the object
        # satisfy the shape declared HERE", and a cross-schema reference is a
        # relation OpenRegister owns. Left in, every app with a relation would
        # crash the checker — and a crash reported as a finding is as wrong as a
        # crash reported as a pass.
        stripped = _drop_refs(stripped)

        try:
            jsonschema.validate(instance=body, schema=stripped)
        except jsonschema.ValidationError as err:
            return f"{'.'.join(str(p) for p in err.absolute_path) or '<root>'}: {err.message}"
        except jsonschema.SchemaError as err:
            return f"the SCHEMA itself is invalid: {err.message}"
        except Exception as err:  # noqa: BLE001 - see below
            # An UNEXPECTED validator error is not a clean bill of health. Say
            # what happened and let the caller treat it as a failure, rather than
            # returning None and calling unvalidated data validated.
            return f"the validator could not judge this object: {type(err).__name__}: {err}"
        return None
    except ImportError:
        pass

    for key in (schema.get("required") or []):
        if key not in body:
            return f"required property '{key}' is missing"
    props = schema.get("properties") or {}
    for key, value in body.items():
        spec = props.get(key)
        if not isinstance(spec, dict):
            continue
        enum = spec.get("enum")
        if isinstance(enum, list) and enum and value not in enum:
            return f"'{key}' = {value!r} is outside its enum"
    return None


def check(app_dir: str, app_id: str, per_schema: int, only: set[str] | None = None) -> int:
    """Report schemas whose mock coverage is missing, short, or INVALID.

    `only` limits the judgement to descriptors the caller named — the gate
    passes the PR's changed files, so a fleet that predates ADR-111 is not
    reddened for schemas nobody touched. Absent, every descriptor is judged
    (what a human running this by hand wants).
    """
    # 🔴 EVERY MOCK DESCRIPTOR, NOT ONE FILENAME. This read a single
    # `{app_id}_mock_register.json`, which was wrong twice over:
    #
    #   1. `app_id` comes from `basename(app_dir)`, and the gate passes `.` —
    #      so the target became `./lib/Settings/._mock_register.json` and every
    #      app reported zero demo objects, including apps that have them.
    #   2. The convention is not universal anyway. OpenRegister's five mocks are
    #      `bag_register.json`, `brp_register.json`, `dso_register.json` … — a
    #      checker keyed on a filename would have called all five missing.
    #
    # The marker is `x-openregister.type: mock`, the same thing the inventory
    # keys on. Read what the app declares, not what it was expected to name.
    have: dict[tuple[str, str], int] = {}
    objects_by_key: dict[tuple[str, str], list] = {}
    for path in sorted(glob.glob(os.path.join(app_dir, "lib", "**", "*.json"), recursive=True)):
        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        marker = data.get("x-openregister")
        if not isinstance(marker, dict) or marker.get("type") != "mock":
            continue
        for obj in (data.get("components", {}) or {}).get("objects", []) or []:
            ref = obj.get("@self", {}) if isinstance(obj, dict) else {}
            key = (ref.get("register", ""), ref.get("schema", ""))
            have[key] = have.get(key, 0) + 1
            objects_by_key.setdefault(key, []).append(obj)

    _regs, owns, definitions = _register_schema_map(app_dir, app_id)

    # Which (register, schema) pairs the caller's scope actually covers. Built
    # from the same authority the generator uses, so the producer and the judge
    # cannot disagree about which pairs exist.
    in_scope_pairs: list[tuple[str, str]] = []
    # 🔴 `_component_files`, NOT `_descriptors`. In a modular app a PR that adds
    # a schema touches a file declaring no register, so keying the delta scope
    # on register-declaring files would put that new schema out of scope — the
    # gate would pass a PR that shipped a schema with no demo data at all.
    for _path, decl in _component_files(app_dir):
        if only is not None and os.path.relpath(_path, app_dir) not in only:
            continue
        # 🔴 BOTH KEYS GUARDED. `components.registers` is not always a mapping:
        # openregister's `avg-bundle.json` and `report-bundle.json` use a LIST
        # of register objects. `_descriptors` required a dict, so widening
        # discovery to schema-only files let those through and this line died
        # with `'list' object has no attribute 'keys'` — a crashed checker, not
        # a finding. Their schemas still count; they contribute no slug here.
        touched = set(_as_dict(decl["components"].get("schemas")).keys())
        touched |= set(_as_dict(decl["components"].get("registers")).keys())
        for reg_slug, names in owns.items():
            for sch_name in names:
                if sch_name in touched or reg_slug in touched:
                    pair = (reg_slug, sch_name)
                    if pair not in in_scope_pairs:
                        in_scope_pairs.append(pair)

    checked = failures = 0
    for reg_slug, sch_name in in_scope_pairs:
        sch = definitions.get(sch_name)
        checked += 1
        key = (reg_slug, sch_name)
        count = have.get(key, 0)
        if count < per_schema:
            failures += 1
            print(
                f"FAIL {app_id}: register '{reg_slug}' schema '{sch_name}' has "
                f"{count} demo object(s), needs {per_schema} (ADR-111 rule 1). Regenerate "
                f"with `python3 vendor/conduction/hydra-gates/scripts/lib/generate_mock_register.py .`"
            )
            continue

        # 🔴 AND THE OBJECTS MUST SATISFY THE SCHEMA. Counting them only
        # proves somebody wrote something. Demo data that fails its own
        # schema fails at import, in front of whoever asked for a demo.
        if not isinstance(sch, dict):
            continue
        for obj in objects_by_key.get(key, []):
            error = _validate(obj, sch)
            if error is not None:
                failures += 1
                print(
                    f"FAIL {app_id}: register '{reg_slug}' schema '{sch_name}' has a "
                    f"demo object that does not satisfy its own schema — {error}"
                )
                break

    print(f"checked {checked} schema(s)")

    return 1 if failures else 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app_dir")
    parser.add_argument("--objects", type=int, default=3)
    parser.add_argument("--out")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--keep", action="store_true")
    parser.add_argument(
        "--only-changed",
        action="store_true",
        help="read changed files on stdin and judge only the descriptors among them",
    )
    args = parser.parse_args(argv[1:])

    app_dir = args.app_dir.rstrip("/") or "."
    app_id = _app_id(app_dir)

    if args.check:
        only = None
        if args.only_changed:
            changed = {
                line.strip() for line in sys.stdin.read().splitlines() if line.strip()
            }
            only = {c for c in changed if c.endswith(".json") and c.startswith("lib/")}
            if not only:
                # 🔴 A COUNT, PRINTED EVEN WHEN ZERO — the caller distinguishes
                # "ran and found nothing in scope" from "never ran" by this line.
                print("checked 0 schema(s)")
                return 4
        return check(app_dir, app_id, args.objects, only)

    out = args.out or os.path.join(app_dir, "lib", "Settings", f"{app_id}_mock_register.json")
    existing = None
    if args.keep and os.path.isfile(out):
        try:
            with open(out, encoding="utf-8") as handle:
                existing = json.load(handle)
        except (OSError, ValueError):
            existing = None

    built = build(app_dir, app_id, args.objects, existing)
    schemas = len(built["components"]["schemas"])
    objects = len(built["components"]["objects"])
    if schemas == 0:
        print(f"{app_id}: declares no schemas — nothing to generate.")
        return 0

    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(built, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(f"{app_id}: wrote {objects} demo object(s) across {schemas} schema(s) -> {out}")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
