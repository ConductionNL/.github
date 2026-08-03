#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Gate 31 helper — relation-dialect (ADR-062 rules 6/7/10).

Enforces the ONE canonical OpenRegister relation dialect across changed
register files (``lib/Settings/*register*.json`` + ``lib/Settings/register.d/
*.json``). A relation is a schema PROPERTY carrying ``type: string`` (or array
``items``), ``format: uuid`` and ``$ref: <schemaKey>`` (same register set);
``x-relation-filter`` rides on the same property. Bespoke per-schema dialects
are banned. Observed 2026-07-08 across the fleet detail-page redesign:
decidesk shipped per-schema ``x-openregister-relations`` blocks nothing
consumed (retired 2026-07-08), scholiq used bare-string FKs-by-convention
(85 converted), and procest's ``case.status`` proved the rule-10 lifecycle
carve-out (an FK-scoped editable picker, NOT a frozen ``readOnly`` field).

Checks (each offending location prints one finding to stdout; WARN-prefixed
lines are advisory and never fail the gate):
  a. BANNED DIALECT   — any ``x-openregister-relations`` key anywhere in a
                        changed register file.
  b. RELATION SHAPE   — a property (or its items) ADDED/MODIFIED in the diff
                        with ``format: uuid`` + a relation-shaped description
                        but NO ``$ref`` (conservative: format:uuid alone is
                        NOT enough — NC-user-id fields legitimately lack $ref).
  c. FILTER PLACEMENT — ``x-relation-filter`` anywhere except directly on a
                        property; or on a property that is not a relation
                        (filter on non-relation is inert).
  d. FILTER TOKENS    — every ``@``-prefixed filter value must be ``@objectId``
                        or ``@object.<existingPropertyOfSameSchema>``; unknown
                        tokens, nonexistent fields and two-hop ``@object.a.b``
                        all fail.
  e. FROZEN LIFECYCLE — a ``$ref`` + ``readOnly:true`` property on a schema
                        whose ``x-openregister-lifecycle`` has no ``transitions``
                        block and whose lifecycle ``field`` equals that property
                        (rule 10: readOnly with no expressible transitions =
                        permanently frozen).
  f. $REF TARGETS     — a string ``$ref`` must resolve to a schema key in the
                        same register file set (case-exact). A numeric ``$ref``
                        is allowed (live-schema form) but WARNs.

Diff-scoping (ADR-020): only the changed register files passed on argv are
inspected, so legacy debt in an untouched register never blocks an unrelated
PR. Check (b) is refined further to the PROPERTY level — when
``HYDRA_GATE_BASE_REF`` is set it only flags properties whose declaration line
is ADDED or MODIFIED vs the base ref (going-forward enforcement, exactly like
gate 28). Checks a/c/d/e/f apply to the whole changed file per the gate
contract (a banned dialect or a dangling $ref anywhere in a file the PR
touched is a structural defect).

Usage:
    check_relation_dialect.py <log-path> <register.json> [<register.json> ...]
"""

import glob
import json
import os
import re
import subprocess
import sys


# --------------------------------------------------------------------------
# Position-tracking JSON parse (shared shape with check_schema_property_meta.py)
# — each object dict remembers the source line of its direct keys so findings
# can be mapped back to the diff for property-level scoping.
# --------------------------------------------------------------------------
class _LineDict(dict):
    __slots__ = ("key_lines",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.key_lines = {}


_TOKEN_RE = re.compile(
    r"""
      (?P<ws>[ \t\r\n]+)
    | (?P<str>"(?:[^"\\]|\\.)*")
    | (?P<punct>[{}\[\]:,])
    | (?P<lit>true|false|null)
    | (?P<num>-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)
    """,
    re.VERBOSE,
)


def _tokenize(text):
    line = 1
    pos = 0
    length = len(text)
    while pos < length:
        m = _TOKEN_RE.match(text, pos)
        if not m:
            raise ValueError(f"Unexpected character at offset {pos}: {text[pos]!r}")
        kind = m.lastgroup
        value = m.group()
        tok_line = line
        line += value.count("\n")
        pos = m.end()
        if kind == "ws":
            continue
        yield kind, value, tok_line


class _Parser:
    def __init__(self, text):
        self._tokens = list(_tokenize(text))
        self._i = 0

    def _peek(self):
        return self._tokens[self._i] if self._i < len(self._tokens) else (None, None, None)

    def _next(self):
        tok = self._tokens[self._i]
        self._i += 1
        return tok

    def parse(self):
        return self._parse_value()

    def _parse_value(self):
        kind, value, line = self._peek()
        if kind == "punct" and value == "{":
            return self._parse_object()
        if kind == "punct" and value == "[":
            return self._parse_array()
        if kind == "str":
            self._next()
            return json.loads(value)
        if kind == "num":
            self._next()
            return json.loads(value)
        if kind == "lit":
            self._next()
            return {"true": True, "false": False, "null": None}[value]
        raise ValueError(f"Unexpected token {value!r} at line {line}")

    def _parse_object(self):
        obj = _LineDict()
        self._next()
        kind, value, _ = self._peek()
        if kind == "punct" and value == "}":
            self._next()
            return obj
        while True:
            kkind, kval, kline = self._next()
            if kkind != "str":
                raise ValueError(f"Expected object key, got {kval!r} at line {kline}")
            key = json.loads(kval)
            ckind, cval, cline = self._next()
            if not (ckind == "punct" and cval == ":"):
                raise ValueError(f"Expected ':' at line {cline}")
            obj[key] = self._parse_value()
            obj.key_lines[key] = kline
            nkind, nval, nline = self._next()
            if nkind == "punct" and nval == ",":
                continue
            if nkind == "punct" and nval == "}":
                break
            raise ValueError(f"Expected ',' or '}}' at line {nline}")
        return obj

    def _parse_array(self):
        arr = []
        self._next()
        kind, value, _ = self._peek()
        if kind == "punct" and value == "]":
            self._next()
            return arr
        while True:
            arr.append(self._parse_value())
            nkind, nval, nline = self._next()
            if nkind == "punct" and nval == ",":
                continue
            if nkind == "punct" and nval == "]":
                break
            raise ValueError(f"Expected ',' or ']' at line {nline}")
        return arr


# --------------------------------------------------------------------------
# Diff-scope helpers (shared shape with check_schema_property_meta.py).
# --------------------------------------------------------------------------
def _changed_lines(file_path, base_ref):
    try:
        proc = subprocess.run(
            ["git", "diff", "-U0", "--no-color", base_ref, "--", file_path],
            capture_output=True, text=True, check=False,
        )
    except (OSError, ValueError):
        return None
    if proc.returncode != 0:
        return None
    changed = set()
    saw_hunk = False
    for line in proc.stdout.splitlines():
        if not line.startswith("@@"):
            continue
        saw_hunk = True
        m = re.search(r"\+(\d+)(?:,(\d+))?", line)
        if not m:
            continue
        start = int(m.group(1))
        count = int(m.group(2)) if m.group(2) is not None else 1
        for ln in range(start, start + count):
            changed.add(ln)
    if not saw_hunk:
        if _is_tracked_at(file_path, base_ref):
            return set()
        return None
    return changed


def _is_tracked_at(file_path, base_ref):
    try:
        proc = subprocess.run(
            ["git", "cat-file", "-e", f"{base_ref}:{file_path}"],
            capture_output=True, text=True, check=False,
        )
        return proc.returncode == 0
    except (OSError, ValueError):
        return False


# --------------------------------------------------------------------------
# Register-set discovery — the global schema-key set is needed so a string
# $ref in a changed file resolves against EVERY register (base + fragments),
# not only the changed file.
# --------------------------------------------------------------------------
def _settings_dir(path):
    marker = os.path.join("lib", "Settings")
    norm = os.path.normpath(path)
    idx = norm.find(marker)
    if idx == -1:
        return None
    return norm[: idx + len(marker)]


def _schemas_of(doc):
    if not isinstance(doc, dict):
        return {}
    schemas = (doc.get("components") or {}).get("schemas")
    if isinstance(schemas, dict) and schemas:
        return schemas
    # Root-level single-schema fragment.
    if isinstance(doc.get("properties"), dict):
        name = doc.get("title") or doc.get("slug") or "root"
        return {name: doc}
    return {}


def _global_schema_keys(paths):
    """Every name a `$ref` may legitimately point at.

    This is the JSON object key AND each schema's declared ``slug``, because the
    slug is what OpenRegister actually stores and serves — a `$ref` is resolved
    against the slug, not against the key the schema happens to sit under in the
    register document.

    Collecting only the keys produced false positives fleet-wide (hermiq
    2026-08-02: 26 findings, every one of them a correct reference). The two are
    NOT merely a casing difference and cannot be normalised into each other:

        "Skill":    { "slug": "agentskill", ... }   ->  $ref: "agentskill"

    Demanding the key there would have required `$ref: "Skill"`, which resolves
    to nothing at runtime — so "fixing" the findings would have broken every
    relation the gate was written to protect.
    """
    keys = set()
    seen = set()
    for p in paths:
        sd = _settings_dir(p)
        if not sd or sd in seen:
            continue
        seen.add(sd)
        candidates = glob.glob(os.path.join(sd, "*register*.json"))
        candidates += glob.glob(os.path.join(sd, "register.d", "*.json"))
        for c in candidates:
            try:
                with open(c, encoding="utf-8") as fh:
                    doc = json.load(fh)
            except (OSError, ValueError):
                continue
            for name, schema in _schemas_of(doc).items():
                keys.add(name)
                if isinstance(schema, dict):
                    slug = schema.get("slug")
                    if isinstance(slug, str) and slug != "":
                        keys.add(slug)
    return keys


# --------------------------------------------------------------------------
# Relation helpers.
# --------------------------------------------------------------------------
_RELATION_DESC_RE = re.compile(r"\b(reference to|verwijzing naar|uuid of the|fk to)\b", re.I)


def _ref_of(prop):
    """Return (raw_ref_value, is_array) for a relation property, or (None,_).

    An EMPTY-STRING $ref is treated as "no ref": OpenRegister's schema editor
    writes `"$ref": ""` boilerplate on every property regardless of type
    (observed fleet-wide on softwarecatalog 2026-07-08) — flagging those as
    dangling produced 61 false positives on plain scalar/enum fields.
    """
    if not isinstance(prop, dict):
        return None, False
    if "$ref" in prop and prop["$ref"] not in ("", None):
        return prop["$ref"], False
    items = prop.get("items")
    if isinstance(items, dict) and items.get("$ref") not in ("", None) and "$ref" in items:
        return items["$ref"], True
    return None, False


def _is_relation_prop(prop):
    if not isinstance(prop, dict):
        return False
    if "$ref" in prop:
        return True
    if "x-openregister-relation" in prop:
        return True
    items = prop.get("items")
    if isinstance(items, dict) and "$ref" in items:
        return True
    return False


def _has_uuid_format(prop):
    if prop.get("format") == "uuid":
        return True
    items = prop.get("items")
    if isinstance(items, dict) and items.get("format") == "uuid":
        return True
    return False


def _resolve_ref(ref, keys):
    """Return ('ok'|'warn'|'fail', normalized). Numeric → warn (live-schema
    form). Hash form resolves to its last path segment."""
    if isinstance(ref, (int, float)):
        return "warn", str(ref)
    if not isinstance(ref, str):
        return "fail", repr(ref)
    r = ref.strip()
    if r.lstrip("-").isdigit():
        return "warn", r
    if r.startswith("#"):
        r = r.rstrip("/").rsplit("/", 1)[-1]
    return ("ok", r) if r in keys else ("fail", r)


# --------------------------------------------------------------------------
# Per-file checks.
# --------------------------------------------------------------------------
def check_file(path, keys, findings, base_ref):
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        doc = _Parser(text).parse()
    except (OSError, ValueError) as exc:
        findings.append((path, f"{path}: PARSE ERROR — {exc}"))
        return

    changed = _changed_lines(path, base_ref) if base_ref else None
    schemas = _schemas_of(doc)

    # Set of property dicts (by identity) that are legitimate direct schema
    # properties — used to detect misplaced x-relation-filter (check c).
    property_ids = set()

    for sname, schema in schemas.items():
        if not isinstance(schema, dict):
            continue
        props = schema.get("properties")
        if not isinstance(props, dict):
            continue
        lc = schema.get("x-openregister-lifecycle")
        lc_field = lc.get("field") if isinstance(lc, dict) else None
        lc_has_transitions = isinstance(lc, dict) and bool(lc.get("transitions"))
        plines = getattr(props, "key_lines", {})

        for pname, prop in props.items():
            if not isinstance(prop, dict) or pname.startswith("@"):
                continue
            property_ids.add(id(prop))
            pline = plines.get(pname, 0)
            in_diff = changed is None or pline in changed

            # (b) relation-shape heuristic — property-level diff scoped.
            if in_diff and _has_uuid_format(prop) and not _is_relation_prop(prop):
                desc = prop.get("description") or ""
                items = prop.get("items")
                if isinstance(items, dict):
                    desc = f"{desc} {items.get('description') or ''}"
                if _RELATION_DESC_RE.search(desc):
                    findings.append((path, (
                        f"{path}: {sname}.{pname} — relation-shaped property "
                        f"(format:uuid + relation description) lacks canonical "
                        f"$ref (ADR-062 rule 7)"
                    )))

            # (d) filter tokens — validate every @-prefixed value.
            filt = prop.get("x-relation-filter")
            if isinstance(filt, dict):
                for fk, token in filt.items():
                    if not isinstance(token, str) or not token.startswith("@"):
                        continue
                    if token == "@objectId":
                        continue
                    if token.startswith("@object."):
                        field = token[len("@object."):]
                        if "." in field:
                            findings.append((path, (
                                f"{path}: {sname}.{pname} x-relation-filter "
                                f"[{fk}]={token} — two-hop tokens unsupported "
                                f"(ADR-062 rule 6)"
                            )))
                        elif field not in props:
                            findings.append((path, (
                                f"{path}: {sname}.{pname} x-relation-filter "
                                f"[{fk}]={token} — references nonexistent field "
                                f"'{field}' on schema {sname}"
                            )))
                    else:
                        findings.append((path, (
                            f"{path}: {sname}.{pname} x-relation-filter "
                            f"[{fk}]={token} — unknown token (expected @objectId "
                            f"or @object.<field>)"
                        )))

            # (e) frozen lifecycle — rule 10.
            if (
                "$ref" in prop
                and prop.get("readOnly") is True
                and lc_field == pname
                and isinstance(lc, dict)
                and not lc_has_transitions
            ):
                findings.append((path, (
                    f"{path}: {sname}.{pname} — readOnly status property with no "
                    f"expressible transitions (x-openregister-lifecycle has no "
                    f"'transitions' block) = permanently frozen (ADR-062 rule 10) "
                    f"— drop readOnly and scope an editable picker with "
                    f"x-relation-filter instead"
                )))

            # (f) $ref target resolution.
            ref, _is_arr = _ref_of(prop)
            if ref is not None:
                verdict, norm = _resolve_ref(ref, keys)
                if verdict == "fail":
                    findings.append((path, (
                        f"{path}: {sname}.{pname} — $ref '{ref}' does not resolve "
                        f"to a schema key in the register set (case-exact)"
                    )))
                elif verdict == "warn":
                    findings.append((path, "WARN:" + (
                        f"{path}: {sname}.{pname} — numeric $ref '{ref}' "
                        f"(live-schema id form); registers should author the "
                        f"schema slug"
                    )))

    # (a) banned dialect + (c) misplaced/inert x-relation-filter — raw walk.
    _raw_walk(doc, path, property_ids, findings)


def _raw_walk(node, path, property_ids, findings):
    if isinstance(node, dict):
        if "x-openregister-relations" in node:
            findings.append((path, (
                f"{path}: banned dialect — 'x-openregister-relations' block "
                f"(canonical dialect is a property-level $ref; the bespoke "
                f"per-schema block was retired 2026-07-08, ADR-062 rule 7)"
            )))
        if "x-relation-filter" in node:
            if id(node) not in property_ids:
                findings.append((path, (
                    f"{path}: x-relation-filter is placed off a property (inside "
                    f"items / an x-* block / non-property node) — it rides only on "
                    f"the relation property itself (ADR-062 rule 6)"
                )))
            elif not (
                ("$ref" in node)
                or ("x-openregister-relation" in node)
                # Array relation form (ADR-062 rule 7): the $ref sits on
                # items while the filter rides the property — both valid.
                or (isinstance(node.get("items"), dict) and (
                    "$ref" in node["items"]
                    or "x-openregister-relation" in node["items"]
                ))
            ):
                findings.append((path, (
                    f"{path}: x-relation-filter on a property with no $ref — "
                    f"filter on a non-relation is inert (ADR-062 rule 6)"
                )))
        for v in node.values():
            _raw_walk(v, path, property_ids, findings)
    elif isinstance(node, list):
        for v in node:
            _raw_walk(v, path, property_ids, findings)


def main(argv):
    if len(argv) < 3:
        return 0
    log_path = argv[1]
    paths = argv[2:]
    base_ref = os.environ.get("HYDRA_GATE_BASE_REF", "").strip()
    keys = _global_schema_keys(paths)
    findings = []
    for p in paths:
        check_file(p, keys, findings, base_ref)
    with open(log_path, "a", encoding="utf-8") as g:
        for _p, msg in findings:
            g.write(msg + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
