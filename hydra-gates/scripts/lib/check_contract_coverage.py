#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Gate-25 contract-coverage — diff-scoped new-public-endpoint contract-test enforcer.

A controller method ADDED in the PR diff that is **registered as a route** in
``appinfo/routes.php`` AND is publicly reachable (``#[PublicPage]`` /
``#[NoAdminRequired]`` / ``@PublicPage`` / ``@NoAdminRequired``) is a new
network-facing endpoint. It MUST be covered by an automated contract test —
either a Newman/Postman collection assertion under
``tests/integration/*.postman_collection.json`` that hits its route, OR a
PHPUnit controller test under ``tests/**`` that exercises the controller method
— OR carry a reason-bearing ``@contract exclude <reason>`` in its docblock.

This is the API-layer companion to gate-19 (e2e-coverage, UI layer) and gate-16
(spec-coverage, code↔spec). Together they close the loop so a newly-exposed
endpoint can never merge without an automated proof that its wire contract holds.

Diff scope
==========

The set of ADDED methods is derived from ``git diff -U0`` against
``$HYDRA_GATE_BASE_REF`` (default ``origin/development``): only a controller
method whose **declaration line** falls on an added line is considered new.
Pre-existing endpoints (untouched legacy debt) are never flagged — ADR-020.

What counts as coverage
=======================

A new endpoint ``<controller>#<method>`` (route slug) is considered covered when:

1. A ``*.postman_collection.json`` file under ``tests/integration/`` references
   the endpoint's URL path. We resolve the path from the matching route entry's
   ``'url'`` and look for the literal path segment (minus ``{placeholders}``) in
   any collection request ``raw`` URL. A looser fallback also matches the method
   name appearing in a request ``name``.
2. OR a PHPUnit test file under ``tests/`` (``*Test.php``) references the
   controller method — either ``->method(`` (calling it) or naming the
   controller class plus the method anywhere in the file.
3. OR the method's docblock carries ``@contract <ref>`` (an explicit pointer to
   a Newman collection / test) or a reason-bearing ``@contract exclude <reason>``.

A bare ``@contract exclude`` (no reason) is non-compliant — flagged like a
missing test, mirroring gate-16/gate-19's exclude rules.

Usage::

    HYDRA_GATE_BASE_REF=origin/development python3 scripts/lib/check_contract_coverage.py [app-dir]
    python3 scripts/lib/check_contract_coverage.py [app-dir] --mode report
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exclusion_reason import exclude_pattern, is_reason_bearing  # noqa: E402
from source_scope import php_mask  # noqa: E402

GATE_NUM = 25

# ---------------------------------------------------------------------------
# AN EXIT CODE IS A STATUS. THE COUNT GOES ON STDOUT.
# ---------------------------------------------------------------------------
# Same convention gate-19 settled on after returning its finding count as an
# exit status (.github#209): a byte cannot carry a count, and a count cannot
# carry a status. It carries a status; the number is printed.
#
# EMPTY_SCOPE exists because PASS and "I inspected nothing" used to be the same
# 0, which is why --require-full-coverage — whose whole job is to notice gates
# that did not run — could not see this one. (.github#242)
EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_ERROR = 2
EXIT_EMPTY_SCOPE = 3      # scope resolved, selected nothing -> runner _skip `na` (.github#268)
EXIT_NOT_APPLICABLE = 4   # subject matter absent entirely   -> runner _skip na

# A routed name: 'controller#method' (snake_case controller, camelCase method,
# Settings\Foo namespaced controllers allowed).
_ROUTE_NAME_RE = re.compile(
    r"'name'\s*=>\s*'([A-Za-z][A-Za-z0-9_\\]*#[A-Za-z0-9_]+)'"
)
# The route entry's own `'url'` key. The ENTRY is no longer matched by a
# regex — see `_entry_span` / `parse_routes`: a bracket-pair pattern that
# forbids nested brackets cannot read `'requirements' => [...]`, and every
# route that declares one lost its url.
_ROUTE_URL_RE = re.compile(r"'url'\s*=>\s*'([^']+)'")

# public function foo( — capture name. Only public methods can be endpoints.
_PHP_PUBLIC_METHOD_RE = re.compile(
    r"^\s*(?:final\s+|abstract\s+|static\s+)*public\s+(?:static\s+)?function\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(",
)

_PUBLIC_AUTH_RE = re.compile(
    r"#\[(?:PublicPage|NoAdminRequired)\b|@(?:PublicPage|NoAdminRequired)\b"
)

_CONTRACT_REF_RE = re.compile(r"@contract\s+(?!exclude\b)(?P<ref>\S+)")
# What counts as a <reason> is decided by exclusion_reason.is_reason_bearing(),
# shared with gates 16, 19 and 26 — all four graded it with plain truthiness, so
# `@contract exclude .` was a reason (.github#400).
_CONTRACT_EXCLUDE_RE = re.compile(exclude_pattern("contract"))


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "-c", "safe.directory=*", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
        return out.stdout
    except OSError:
        return ""


def changed_lines(base_ref: str, cwd: Path) -> dict[str, set[int]]:
    """Return {relative_path: {added_line_numbers}} from ``git diff -U0``."""
    diff = _git(["diff", "-U0", "--diff-filter=ACMR", f"{base_ref}...HEAD"], cwd)
    if not diff.strip():
        diff = _git(["diff", "-U0", "--diff-filter=ACMR", base_ref], cwd)
    result: dict[str, set[int]] = {}
    current: str | None = None
    hunk_re = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            result.setdefault(current, set())
        elif line.startswith("+++ /dev/null"):
            current = None
        elif line.startswith("@@") and current is not None:
            m = hunk_re.match(line)
            if m:
                start = int(m.group(1))
                count = int(m.group(2)) if m.group(2) is not None else 1
                for n in range(start, start + count):
                    result[current].add(n)
    return result


# ---------------------------------------------------------------------------
# Route table parsing
# ---------------------------------------------------------------------------


def _slug_for_controller(rel_path: str) -> str:
    """Derive a route-slug controller name from a controller file path.

    lib/Controller/FooController.php          -> foo
    lib/Controller/Settings/BarController.php -> Settings\\bar
    """
    short = rel_path
    short = re.sub(r"^lib/Controller/", "", short)
    short = re.sub(r"Controller\.php$", "", short)
    if "/" in short:
        ns, last = short.rsplit("/", 1)
        last = last[:1].lower() + last[1:]
        return f"{ns}\\{last}"
    return short[:1].lower() + short[1:]


def _entry_span(struct: str, at: int) -> tuple[int, int] | None:
    """The innermost balanced ``[ … ]`` containing offset *at* in *struct*.

    *struct* must be PHP with string CONTENTS blanked and offsets preserved
    (``php_mask(..., blank_strings=True)``), because a route file is full of
    brackets that are data rather than structure —
    ``'requirements' => ['uuid' => '[A-Za-z0-9\\-]+']`` has two of them inside
    one string literal, and a walk over raw text counts those.

    Returns ``(open, close)`` offsets, or None when the walk cannot balance —
    in which case the caller keeps the old, url-less answer rather than
    guessing a span.
    """
    depth = 0
    open_at = -1
    i = at - 1
    while i >= 0:
        c = struct[i]
        if c == "]":
            depth += 1
        elif c == "[":
            if depth == 0:
                open_at = i
                break
            depth -= 1
        i -= 1
    if open_at == -1:
        return None
    depth = 0
    j = open_at
    n = len(struct)
    while j < n:
        c = struct[j]
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return (open_at, j)
        j += 1
    return None


def _top_level_only(text: str, struct: str, start: int, end: int) -> str:
    """``text[start:end]`` with every NESTED ``[ … ]`` blanked out.

    So ``'url'`` is read from the entry's own keys and never from a nested
    array — ``'requirements' => ['url' => '.+']`` is a parameter constraint on
    a route whose path is ``/{url}``, not the route's path.
    """
    out = []
    depth = 0
    for i in range(start, min(end, len(text), len(struct))):
        c = struct[i]
        if c == "[":
            depth += 1
            out.append(" ")
            continue
        if c == "]":
            depth = max(0, depth - 1)
            out.append(" ")
            continue
        out.append(text[i] if depth == 0 else " ")
    return "".join(out)


def parse_route_urls(routes_path: Path) -> dict[str, list[str]]:
    """Return {route-name: [every url it is registered under]}.

    route-name is the ``'controller#method'`` slug; the list is empty for a
    resource/implicit route that declares no ``'url'``.

    ONE METHOD, SEVERAL PATHS — AND ANY OF THEM IS THE ENDPOINT (#430).
    -------------------------------------------------------------------
    This returned ONE url per name and the last entry overwrote the earlier
    ones, which is not a property of the route table: registering a method
    under several paths is ordinary Nextcloud, and a `'postfix'` entry exists
    precisely so it can be done under the same name. Measured across the
    eighteen core apps, **six of them** do it with differing urls — 13 names
    in zaakafhandelapp, 9 in opencatalogi, 4 in docudesk, 2 each in
    openregister and softwarecatalog, 1 in openconnector::

        ['name' => 'resultaten#pages', 'url' => '/resultaten', 'verb' => 'GET'],
        ['name' => 'resultaten#pages', 'postfix' => 'details',
         'url' => '/resultaten/{id}', 'verb' => 'GET'],

    Keeping one of the two makes the coverage question depend on which entry
    the parser happened to keep, and a contract test for the other path
    answers nothing. `is_covered` now asks about all of them; `ep["url"]` —
    what the finding line prints — stays the first, so the message is stable.

    A NESTED ARRAY IS NOT A MISSING URL (#430).
    -------------------------------------------
    ``_ROUTE_ENTRY_RE`` matched a route entry as ``\\[[^\\[\\]]*?\\]`` — a
    bracket pair with NO brackets inside it. Every route that declares
    ``'requirements' => [...]`` therefore failed the entry match and fell
    through to the name-only sweep below, which records the route with an
    EMPTY url. The url was in the file, on the line above, in plain sight.

    Measured 2026-08-13 across the eighteen core apps: **9 endpoints** reached
    ``is_covered`` with ``url=""``. An empty url makes the url arm
    unsatisfiable by construction, so those nine could only ever be covered by
    the request-name arm or by PHPUnit — and when the request-name arm broke
    (see ``is_covered``) they became findings that no correct Postman request
    could close. That is the unclosable shape gate-59 forbids, and it was
    created by a regex that could not read a two-key array. Examples, all from
    launchpad ``appinfo/routes.php``::

        ['name' => 'page#deepLink', 'url' => '/{deepLink}', 'verb' => 'GET',
         'requirements' => ['deepLink' => '(?!api(?:/|$)).+']],

    The entry is now recovered by BALANCING brackets from the name's own
    offset, over a string-masked copy so that bracket characters inside a
    requirement regex are not counted as structure. The name-only sweep is
    kept as the fallback it always was: an entry whose brackets do not balance
    still yields ``""`` rather than a guess.
    """
    try:
        text = routes_path.read_text(encoding="utf-8")
    except OSError:
        return {}
    routes: dict[str, list[str]] = {}
    try:
        struct = php_mask(text, blank_strings=True)
    except Exception:                                # pragma: no cover - wiring
        struct = text
    if len(struct) != len(text):                     # pragma: no cover - wiring
        struct = text
    for m in _ROUTE_NAME_RE.finditer(text):
        name = m.group(1)
        span = _entry_span(struct, m.start())
        url = ""
        if span is not None:
            url_m = _ROUTE_URL_RE.search(
                _top_level_only(text, struct, span[0] + 1, span[1]))
            if url_m is not None:
                url = url_m.group(1)
        routes.setdefault(name, [])
        if url and url not in routes[name]:
            routes[name].append(url)
    return routes


def parse_routes(routes_path: Path) -> dict[str, str]:
    """{route-name: first registered url} — see ``parse_route_urls``."""
    return {k: (v[0] if v else "")
            for k, v in parse_route_urls(routes_path).items()}


# ---------------------------------------------------------------------------
# Controller method scanning
# ---------------------------------------------------------------------------


def _decl_preamble(lines: list[str], decl_idx: int) -> list[str]:
    """The lines PHP itself binds to the declaration at ``decl_idx``.

    Walks upward from the declaration and accepts only what belongs to that
    declaration's own preamble — its attribute list, its ONE docblock, `//`
    notes and blank lines — stopping at the first line that belongs to
    something else (a closing brace, a statement, another declaration).

    WHY THIS IS NOT A LINE WINDOW (.github#363)
    -------------------------------------------
    This used to be ``lines[decl_idx - 20 : decl_idx + 1]``. A distance in
    LINES is not the relationship being tested, and it was wrong in both
    directions at once — confirmed live in ONE file, ONE run, 2026-08-12:

        listThings      #[PublicPage] on its own line above it   correct
        adminOnlyPurge  NO auth attribute of its own             FLAGGED —
                        the window reached back over the previous method's
                        closing brace and read ITS #[PublicPage]
        farAttribute    #[PublicPage] 21 lines up, separated only
                        by its own (long) docblock               MISSED —
                        its own attribute fell outside the window

    So the gate reported an administrator-only endpoint as a newly-exposed
    public one, and stayed SILENT about a genuinely public, genuinely
    untested one. The silent half is the dangerous one: detecting a
    newly-exposed endpoint is the entire purpose of this gate, and
    attributes-before-a-long-docblock is simply what a house style with long
    descriptions produces.

    Structure decides, not distance. ``_docblock_block`` below already walked
    upward this way for the @contract tag; the auth question now asks it the
    same way.
    """
    out: list[str] = []
    i = decl_idx - 1
    seen_doc = False
    while i >= 0:
        raw = lines[i]
        s = raw.strip()
        # Blank lines, PHP attributes (`#[...]`, incl. the `]` / `)]` tail of a
        # multi-line one) and `//` notes are all part of the preamble.
        if s == "" or s.startswith("#[") or s.startswith("]") or s.startswith(")]") \
                or s.startswith("//"):
            out.append(raw)
            i -= 1
            continue
        # The declaration's own docblock — exactly one, and only when it ENDS
        # on this line. Consume it whole, then keep walking: an attribute
        # written ABOVE the docblock still belongs to this declaration.
        if not seen_doc and s.endswith("*/"):
            j = i
            while j >= 0 and "/*" not in lines[j]:
                j -= 1
            if j < 0:
                break
            out.extend(lines[j : i + 1])
            i = j - 1
            seen_doc = True
            continue
        break
    return out


def _method_is_public_endpoint(lines: list[str], decl_idx: int) -> bool:
    """True if the method at ``decl_idx`` carries a PublicPage / NoAdminRequired
    attribute or docblock tag IN ITS OWN declaration preamble.

    Never in a neighbour's — see ``_decl_preamble``.
    """
    head = "\n".join(_decl_preamble(lines, decl_idx) + [lines[decl_idx]])
    return bool(_PUBLIC_AUTH_RE.search(head))


def _docblock_block(lines: list[str], decl_idx: int) -> list[str]:
    """Return the /** ... */ block immediately above ``decl_idx`` (skipping PHP
    attributes, line comments + blanks), or [] when absent.

    ``//`` IS PART OF THE GAP (.github, doriath 2026-08-16)
    ------------------------------------------------------
    This walk skipped blanks and ``#[...]`` attributes but stopped dead on a
    ``//`` line. Attributes very often carry an explanatory comment beside
    them, and doriath spells it exactly that way::

         */
        #[PublicPage]
        #[NoCSRFRequired]
        // The public shell — one of only four rendered public pages ...
        #[AnonRateLimit(limit: 120, period: 60)]
        public function page(): TemplateResponse {

    The walk halted on the comment, found no ``*/`` there, and returned [] —
    so the docblock was INVISIBLE and every tag read out of it (``@contract``,
    ``@contract exclude``) silently stopped working. The endpoint was reported
    as having no contract test while carrying a reason-bearing exclusion three
    lines above, and the only way to satisfy the gate was to move a comment.

    A gate that can be switched off by where a comment sits is not measuring
    the thing it names.
    """
    i = decl_idx - 1
    while i >= 0:
        stripped = lines[i].strip()
        if (stripped == "" or stripped.startswith("#[")
                or stripped.startswith("]") or stripped.startswith("//")):
            i -= 1
            continue
        break
    if i < 0 or "*/" not in lines[i]:
        return []
    block: list[str] = []
    while i >= 0:
        block.append(lines[i])
        if "/**" in lines[i] or "/*" in lines[i]:
            break
        i -= 1
    return block


def _contract_status(lines: list[str], decl_idx: int) -> tuple[str, str | None]:
    """Classify the docblock above ``decl_idx``:
      ("ref", None)            — has @contract <ref> (explicit pointer)
      ("excluded", reason)     — has @contract exclude <reason> (reason set)
      ("exclude_noreason", None) — bare @contract exclude
      ("none", None)           — neither
    """
    block = _docblock_block(lines, decl_idx)
    for b in block:
        if _CONTRACT_REF_RE.search(b):
            return ("ref", None)
    for b in block:
        m = _CONTRACT_EXCLUDE_RE.search(b)
        if m:
            reason = m.group("reason").strip().rstrip("*/").strip()
            # `if reason:` here was .github#400.
            if is_reason_bearing(reason):
                return ("excluded", reason)
            return ("exclude_noreason", None)
    return ("none", None)


def scan_new_endpoints(
    app_dir: Path, changed: dict[str, set[int]], routes: dict[str, list[str]]
) -> list[dict]:
    """Return new public endpoints ADDED in the diff that are registered routes.

    Each dict: {ref, controller_path, method, url, contract_status, reason}.
    """
    out: list[dict] = []
    for rel, added in changed.items():
        if not rel.startswith("lib/Controller/") or not rel.endswith("Controller.php"):
            continue
        cfile = app_dir / rel
        if not cfile.is_file():
            continue
        try:
            lines = cfile.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        slug = _slug_for_controller(rel)
        for idx, line in enumerate(lines):
            m = _PHP_PUBLIC_METHOD_RE.match(line)
            if not m:
                continue
            decl_line_no = idx + 1  # 1-based
            if decl_line_no not in added:
                continue  # method declaration not added in this PR
            method = m.group("name")
            ref = f"{slug}#{method}"
            if ref not in routes:
                continue  # not a registered route → not a public endpoint
            if not _method_is_public_endpoint(lines, idx):
                continue  # admin-only / no public attribute → out of scope
            status, reason = _contract_status(lines, idx)
            out.append(
                {
                    "ref": ref,
                    "controller_path": rel,
                    "method": method,
                    "url": (routes.get(ref) or [""])[0],
                    "urls": list(routes.get(ref) or []),
                    "contract_status": status,
                    "reason": reason,
                }
            )
    return out


# ---------------------------------------------------------------------------
# Coverage scanning (Newman + PHPUnit)
# ---------------------------------------------------------------------------


# The fields of a Postman collection that DECLARE A REQUEST, as opposed to the
# fields that describe one in prose. `description` is deliberately absent, and
# it is the whole point of this list — see `_newman_paths`.
_NEWMAN_EVIDENCE_KEYS = ("raw", "path", "host", "name", "url", "method")

# Of those, the ones that can carry a request's PATH. `name` is deliberately
# absent: a request called "delete /api/things" is evidence that someone
# NAMED a request, and the name arm below judges that separately, by the
# controller method it claims to exercise. Folding it in here would let a
# request name assert a url it does not send to.
_NEWMAN_URL_FIELDS = ("raw", "path", "host", "url", "item")


def _tag(field: str, value: str) -> str:
    """One evidence line: ``<field>:<value>``, newlines flattened.

    THE FIELD TRAVELS WITH THE VALUE (#430). ``_newman_paths`` returns a
    newline-joined list of extracted VALUES, and the caller then has to ask
    "which kind of string was this?". Before this tag it could not: the
    request-name arm in ``is_covered`` was still matching the JSON key syntax
    ``"name"\\s*:\\s*"`` that the extraction had just removed, so it matched
    nothing the collection declared. See the long note in ``is_covered``.

    Newlines are flattened because the tag prefixes only the FIRST line of a
    value, and a multi-line value (a `body.raw` JSON payload) would otherwise
    contribute untagged lines that a ``^name:`` anchor could land on by
    accident. One value, one line, one field.
    """
    return field + ":" + " ".join(value.split())


def _newman_evidence(node, out: list[str], field: str = "item") -> None:
    """Collect request-declaring strings from a parsed Postman collection.

    Walks the whole tree (folders nest arbitrarily) and keeps only values that
    hang off a declaring key, each TAGGED with the key it hung off. A `url`
    may be a bare string or an object with `raw` / `host` / `path`; both
    shapes are handled by recursing rather than by knowing the schema version.

    A `path` list is emitted BOTH as its segments and as the joined path. The
    join is what makes a v2.1 collection that writes no `raw` still answer a
    path question — its url exists only as `["api", "things", "7"]`, and no
    per-segment line can match a multi-segment route.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            if key in _NEWMAN_EVIDENCE_KEYS:
                if isinstance(value, str):
                    out.append(_tag(key, value))
                elif (key == "path" and isinstance(value, list)
                        and all(isinstance(x, str) for x in value)):
                    out.append(_tag("path", "/" + "/".join(value)))
                    for seg in value:
                        out.append(_tag("path", seg))
                else:
                    _newman_evidence(value, out, key)
            elif isinstance(value, (dict, list)):
                _newman_evidence(value, out, "item")
    elif isinstance(node, list):
        for item in node:
            if isinstance(item, str):
                out.append(_tag(field, item))
            else:
                _newman_evidence(item, out, field)


def _newman_paths(app_dir: Path) -> str:
    """The request-declaring strings of every Postman collection under tests/integration.

    A COLLECTION'S PROSE IS NOT A REQUEST — THE JSON DIALECT OF #415.
    ------------------------------------------------------------------
    This used to be the raw text of the collection FILE, and `is_covered` then
    asked whether the endpoint's path appears anywhere in it. A Postman
    `description` is prose stored in a JSON string, which is a comment wearing
    a different syntax — so it answered too. Measured on this checker, one
    fixture, one variable:

        no collection at all              FAIL — 1 new public endpoint
        + a collection with ZERO items    PASS — 1 endpoint, all covered
          whose description reads
          "NOTE: we do NOT yet cover
           /api/things — the DELETE
           endpoint is untested."

    A collection that contains no requests at all, and SAYS SO, reported the
    endpoint covered. Same shape as the PHPUnit TODO above and as gate 19's
    original defect: the sentence admitting the debt is the sentence that
    discharges it.

    So the haystack is now built from the fields that DECLARE a request
    (`raw` / `path` / `host` / `url` / `name` / `method`) rather than from the
    file's bytes. Unlike the PHP side this cannot use a comment mask — JSON
    has no comments and the evidence genuinely IS a string. The discriminator
    here is WHICH string, not whether it is one.

    AND THE ANSWER TO "WHICH" HAS TO SURVIVE THE EXTRACTION (#430). Each line
    is ``<field>:<value>`` — see ``_tag``. The extraction above removed the
    JSON, and ``is_covered``'s request-name arm was still written against JSON
    key syntax, so the discriminator this docstring claims was not being
    applied: the name arm matched nothing at all. The tag is what lets that
    arm ask its question of names and the url arm ask its question of urls.

    ⚠️ A collection that does not parse falls back to the raw bytes rather
    than to "not covered". Silently converting a malformed fixture into
    findings would be this change inventing failures in repos it was never
    measured against; the honest failure mode for an unreadable input is the
    behaviour that was there before it.
    """
    buf: list[str] = []
    root = app_dir / "tests" / "integration"
    if not root.is_dir():
        return ""
    for p in root.rglob("*.postman_collection.json"):
        try:
            raw = p.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            parsed = json.loads(raw)
        except (ValueError, RecursionError):
            # The pre-extraction behaviour, tagged so the url arm can still
            # read it. An untagged blob would be invisible to BOTH arms, which
            # would turn "unreadable fixture" into findings — the opposite of
            # what this fallback is for.
            buf.extend(_tag("raw", line) for line in raw.splitlines())
            continue
        found: list[str] = []
        _newman_evidence(parsed, found)
        buf.extend(found)
    return "\n".join(buf)


def _phpunit_text(app_dir: Path) -> str:
    """Concatenated CODE of every *Test.php under tests/ — comments blanked.

    A COMMENT SAYING YOU STILL OWE THE TEST MUST NOT BE THE TEST (#415).
    -------------------------------------------------------------------
    This used to be the raw text of every test file, and ``is_covered`` then
    asked whether ``->destroy(`` appears anywhere in it. Prose is made of the
    same bytes as code, so it did not have to be a call. Measured on this
    checker directly, one fixture, one variable:

        no tests at all                       FAIL — 1 new public endpoint
        + a test file whose ONLY mention of   PASS — 1 endpoint, all covered
          the method is
          "// TODO: we still owe a contract
           test that calls
           $this->controller->destroy($id)
           ... Not written yet."

    **That is gate 19's defect, verbatim, in the gate written as gate 19's
    API-layer companion.** A comment stating the debt satisfied the gate that
    exists to collect it, and the sentence that switched the gate off is the
    sentence a diligent author writes. The more honest the TODO, the more
    coverage it fabricates.

    STRING CONTENTS GO TOO. ``->destroy(`` is a call; it is never legitimately
    spelled inside a string literal, so an error message or a fixture payload
    that quotes one is not evidence either. The delimiters survive, so nothing
    that depends on "is this a string" is disturbed.

    The Newman side is deliberately NOT masked here — it is JSON, where the
    evidence genuinely IS a string (a request ``name``/``raw`` url). Its own
    prose problem is real and separate; see the note on ``_newman_paths``.
    """
    buf: list[str] = []
    root = app_dir / "tests"
    if not root.is_dir():
        return ""
    for p in root.rglob("*Test.php"):
        try:
            buf.append(php_mask(p.read_text(encoding="utf-8"), blank_strings=True))
        except OSError:
            continue
    return "\n".join(buf)


# One url path segment as a collection can spell it: a literal, Postman's
# `{{var}}`, an Express-style `:id`, or a concrete fixture value. It may not
# contain a `/`, a quote or whitespace — those end the segment.
_URL_SEGMENT = r"[^/\"'\s]+"
# A Nextcloud route placeholder: `{id}`, `{register}`, … Matched non-greedily
# so `_{type}` yields the literal `_` and one wildcard, not one wildcard.
_PLACEHOLDER_RE = re.compile(r"\{[^{}/]*\}")


_APP_ID_RE = re.compile(r"<id>\s*([A-Za-z0-9_-]+)\s*</id>")
# `scheme://authority` — never part of a path, and stripping it is what lets
# an absolute url anchor at the start of its own path.
_AUTHORITY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://[^/\s\"']*")


def _app_id(app_dir: Path) -> str:
    """The app's own id from appinfo/info.xml — the segment a collection url
    puts after ``/apps/``. Empty when it cannot be read; see
    ``_route_url_pattern`` for what that costs (one of four left anchors)."""
    try:
        m = _APP_ID_RE.search(
            (app_dir / "appinfo" / "info.xml").read_text(encoding="utf-8"))
    except OSError:
        return ""
    return m.group(1) if m else ""


def _route_url_pattern(url: str, app_id: str = ""):
    """A regex matching this route's path in a collection url — or None.

    A PLACEHOLDER IS A WILDCARD, NOT A DELETION (#430).
    ---------------------------------------------------
    This was ``_url_signature``: drop every segment containing a ``{`` and
    join the survivors::

        /api/pos-transactions/{id}/confirm  ->  "api/pos-transactions/confirm"

    That string is not a path. It cannot occur in any correctly-written
    collection url for that route, because a correct url has an id between
    those two segments — so ``sig in newman`` was unsatisfiable for every
    route with a MEDIAL placeholder. Measured 2026-08-13 across the eighteen
    core apps: **16 endpoints reported "missing a contract test" while the
    app's own collection contained a request for exactly that route**, e.g.
    docudesk ``api/templates/{id}/versions`` against
    ``{{baseUrl}}/index.php/apps/docudesk/api/templates/{{templateId}}/versions``.
    No correct app change could close them — the only moves were a duplicate
    PHPUnit test or a false ``@contract exclude`` on an endpoint that IS
    tested, which is the unclosable shape gate-59 forbids.

    The concatenation also silently paired routes that share their literal
    segments: ``/api/things/{id}`` and ``/api/{kind}/things`` both reduce to
    ``api/things``.

    WHY A REGEX AND NOT "TRUNCATE AT THE FIRST PLACEHOLDER".
    Truncating ``/api/pos-transactions/{id}/confirm`` to
    ``/api/pos-transactions`` would match, but it would ALSO match
    ``…/{id}/cancel``, ``…/{id}/park`` and ``…/{id}/settle`` — five distinct
    endpoints covered by one request to any of them, in a gate whose entire
    subject is per-endpoint coverage. Keeping every literal segment and
    wildcarding only the placeholders is what separates them; verified by the
    ``sibling_operation`` arms in test_check_contract_coverage.py, where a
    request to ``…/{id}/confirm`` covers ``confirm`` and leaves ``cancel``
    reported.

    ``{{var}}``, ``:id`` and a literal fixture value all satisfy a wildcard
    segment, so this reads every dialect a Postman collection writes.

    EVERY PLACEHOLDER IS REQUIRED, INCLUDING A TRAILING ONE — AND THAT IS A
    TIGHTENING, MEASURED BEFORE IT WAS KEPT.
    ``_url_signature`` dropped trailing placeholders too, so a request to
    ``/api/things`` used to count as evidence for ``/api/things/{id}``. The
    first draft of this repair preserved that leniency, and it was measured to
    be unshippable ALONGSIDE the `parse_routes` repair below: eight
    openregister endpoints whose url had never been parsed (`ui#objectDetail`,
    `linkedEntity#addObjectLink`, …) acquired one, and the lenient pattern
    then let `/registers/{id}` be answered by a request to `/api/registers`.
    A parser repair that CONVERTS FINDINGS INTO SILENCE is the wrong trade
    whichever way the count moves, so the leniency goes with it.

    A ROUTE ENDS WHERE THE URL ENDS. The right edge is end-of-value, a quote,
    whitespace or a `?`. It is deliberately NOT "any segment boundary": with
    `/` allowed there, `/registers/{id}` is satisfied by
    `…/api/registers/{{id}}/import`, i.e. by a request to a DIFFERENT
    endpoint that merely has this route as a prefix.

    THE LEFT EDGE IS ANCHORED ON THE APP BASE, AND IT HAS TO BE.
    A route path starts at the app root, so ``/registers/{id}`` is a
    DIFFERENT endpoint from ``/api/registers/{id}`` — but with the left edge
    free, the second contains the first and answers for it. That is not
    hypothetical: it is the exact cost of the `parse_routes` repair below.
    Measured, one variable, on openregister — four SPA page routes
    (`ui#objectDetail`, `ui#registersDetails`, `ui#schemasDetails`,
    `ui#applicationDetails`) acquired a parsed url for the first time and
    were immediately answered by API requests to `…/api/objects/…`,
    `…/api/registers/…`. Four real findings would have been converted into
    silence by a repair whose whole subject is findings that could not be
    closed.

    So the match must begin where the app's own path begins. Every spelling
    the fleet's collections actually use is accepted, and each was read off
    the collections rather than imagined:

        {{base_url}}/index.php/apps/openregister/api/…   after `/apps/<id>`
        {{baseUrl}}/{{app}}/api/drc/…                    after a `}`
        "/api/things/7"                                  after a quote
        /api/things/7                                    at the value start

    ``<id>`` is the app id from ``appinfo/info.xml``. When it cannot be read
    the app-base branch is simply absent — the other three still apply, and
    the pattern is then no looser than the ones this repair replaces.

    A PLACEHOLDER IS A PART OF A SEGMENT, NOT ALWAYS THE WHOLE OF IT.
    OpenRegister writes `/api/objects/{uuid}/_{type}`, where the literal `_`
    is what distinguishes a link sub-resource from an object's schema id.
    Wildcarding the whole segment lets `/api/objects/{{reg}}/{{schema}}`
    answer it, which is a different endpoint. Only the braces become wild.
    """
    if not url:
        return None
    segs = [s for s in url.split("?")[0].split("/") if s]
    if not segs:
        return None
    if all(_PLACEHOLDER_RE.sub("", s) == "" for s in segs):
        # A route that is nothing but placeholders (`/{deepLink}`) has no
        # literal to match on. Any url would satisfy it, which is not
        # evidence about this endpoint — leave it to the name / PHPUnit arms
        # rather than accept the first url in the collection.
        return None

    def _seg(seg: str) -> str:
        out, last = [], 0
        for m in _PLACEHOLDER_RE.finditer(seg):
            out.append(re.escape(seg[last:m.start()]))
            out.append(_URL_SEGMENT)
            last = m.end()
        out.append(re.escape(seg[last:]))
        return "".join(out)

    # Led by `/` so `/api/things` cannot be satisfied by `/xapi/things`, and
    # by the app base so `/registers/{id}` cannot be satisfied by
    # `/api/registers/7`.
    left = r"(?:^|(?<=[}\"'\s])"
    if app_id:
        left += r"|(?<=/apps/" + re.escape(app_id) + r")"
    left += r")"
    body = "/" + "/".join(_seg(s) for s in segs)
    return re.compile(left + body + r"(?=[\"'\s?]|$)")


def is_covered(ep: dict, newman: str, phpunit: str, app_id: str = "") -> bool:
    """True if the endpoint is covered by Newman OR PHPUnit OR a @contract ref.

    THE NAME ARM WAS MATCHING A SYNTAX THAT NO LONGER EXISTS (#430).
    ----------------------------------------------------------------
    It read::

        re.search(rf'"name"\\s*:\\s*"[^"]*\\b{method}\\b', newman)

    i.e. JSON key syntax — against a haystack that ``_newman_paths`` had just
    rebuilt out of extracted VALUES, with the JSON removed. The arm therefore
    matched nothing a collection declares; where it still fired at all it was
    on incidental JSON inside a captured request BODY.

    That is not a small arm. Measured 2026-08-13 across the eighteen core
    apps, at package ``fa555a2`` vs ``a316aa5`` on identical trees: **36 of
    the 41 endpoints that newly became findings had been covered by this arm
    and by nothing else.** Nine apps went from PASS to FAIL on it.

    Both arms now ask their question of the field that answers it: the url arm
    of the url-bearing fields, the name arm of ``name:`` lines only. A request
    NAMED after the controller method is the collection's own claim to
    exercise it — which is what the arm always meant, and what it stopped
    being able to see.
    """
    if ep["contract_status"] in ("ref", "excluded"):
        return True
    method = ep["method"]
    if newman:
        # EVERY url the method is registered under, not just the first: a
        # `'postfix'` entry registers the same name under a second path, and a
        # contract test for either is a contract test for the endpoint.
        patterns = [p for p in (_route_url_pattern(u, app_id)
                                for u in (ep.get("urls") or [ep["url"]]))
                    if p is not None]
        if patterns:
            for line in newman.splitlines():
                field, _, value = line.partition(":")
                if field not in _NEWMAN_URL_FIELDS:
                    continue
                # `https://host` is not part of the path, and dropping it is
                # what lets a v2.0 absolute url (`https://x/api/things/7`)
                # anchor at the start of its own path rather than after a
                # host that looks like a path segment.
                value = _AUTHORITY_RE.sub("", value)
                if any(p.search(value) for p in patterns):
                    return True
        # A request NAMED after the controller method. Anchored to `name:` so
        # a url or a payload that happens to contain the word cannot answer a
        # question about what somebody called a request.
        # Case-SENSITIVE, exactly as the arm was before it broke. Folding case
        # here would widen coverage — i.e. remove findings — and this change
        # is a repair of an arm that stopped firing, not a relaxation of what
        # it accepts.
        if re.search(rf"^name:.*\b{re.escape(method)}\b", newman, re.MULTILINE):
            return True
    # PHPUnit: method call or a clear textual reference to the controller method.
    if phpunit:
        if re.search(rf"->\s*{re.escape(method)}\s*\(", phpunit):
            return True
    return False


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------


def _collect(app_dir: Path, base_ref: str) -> list[dict]:
    routes_path = app_dir / "appinfo" / "routes.php"
    if not routes_path.is_file():
        return []
    routes = parse_route_urls(routes_path)
    changed = changed_lines(base_ref, app_dir)
    return scan_new_endpoints(app_dir, changed, routes)


def _collect_from(app_dir: Path, changed: dict[str, set[int]]) -> list[dict]:
    """``_collect`` with the line map supplied rather than derived from a diff.

    Lets run_gate decide the scope — diff or whole tree — instead of the scope
    being hardcoded to "diff" inside the collector, which is what hid 32
    uncovered endpoints on openconnector behind a PASS (.github#242).
    """
    routes_path = app_dir / "appinfo" / "routes.php"
    if not routes_path.is_file():
        return []
    return scan_new_endpoints(app_dir, changed, parse_route_urls(routes_path))


def _all_controller_lines(app_dir: Path) -> dict[str, set[int]]:
    """Every line of every controller — the full-tree equivalent of a diff.

    ``scan_new_endpoints`` asks "was this method's declaration line ADDED?".
    A full-tree audit answers yes for every line, which makes every registered
    public endpoint a candidate exactly as it would be on the commit that first
    introduced it.
    """
    out: dict[str, set[int]] = {}
    cdir = app_dir / "lib" / "Controller"
    if not cdir.is_dir():
        return out
    for cfile in cdir.rglob("*Controller.php"):
        try:
            n = len(cfile.read_text(encoding="utf-8").splitlines())
        except OSError:
            continue
        out[str(cfile.relative_to(app_dir))] = set(range(1, n + 1))
    return out


def run_gate(app_dir: Path) -> int:
    """Audit wire-contract coverage. Returns a status; the COUNT is printed.

    SCOPE IS THE CALLER'S DECISION, AND IT IS NOT DEFAULTED (.github#242)
    --------------------------------------------------------------------
    This used to diff against ``HYDRA_GATE_BASE_REF`` UNCONDITIONALLY, with the
    ref defaulted to ``origin/development`` even when the caller had asked for
    no scoping at all. On a full-tree run the diff came back empty and the gate
    printed ``PASS — no new public endpoints in diff`` having opened nothing.

    Because the narrowing happened HERE — inside the helper, below the runner's
    base resolution — the runner could not tell a full-tree request had been
    reduced to nothing, and because the verdict was PASS rather than a skip,
    ``--require-full-coverage`` could not see it either.

    Measured on openconnector 2026-08-08: **PASS** as the runner invoked it,
    **32** public endpoints with no contract test against the root commit.
    """
    base_ref = os.environ.get("HYDRA_GATE_BASE_REF")

    if not (app_dir / "appinfo" / "routes.php").is_file():
        print(
            f"[gate-{GATE_NUM}] contract-coverage: NOT APPLICABLE — no "
            f"appinfo/routes.php, so this app exposes no routed endpoint whose "
            f"wire contract could be tested."
        )
        return EXIT_NOT_APPLICABLE

    if base_ref:
        changed = changed_lines(base_ref, app_dir)
        # The scope that matters is CONTROLLER files, not "any file". A diff of
        # a hundred docs commits still opens no controller, and reporting PASS
        # for it claims a wire contract was checked when none was read.
        changed = {
            rel: lines for rel, lines in changed.items()
            if rel.startswith("lib/Controller/") and rel.endswith("Controller.php")
        }
        if not changed:
            print(
                f"[gate-{GATE_NUM}] contract-coverage: EMPTY SCOPE — "
                f"diff-scoped against '{base_ref}' and NO controller file was "
                f"touched, so no endpoint was inspected. Wire-contract coverage "
                f"is UNVERIFIED by this run. This is not a pass. Audit the whole "
                f"tree by running without HYDRA_GATE_BASE_REF, or with "
                f"--scope-to-diff --base <root-commit>."
            )
            return EXIT_EMPTY_SCOPE
        endpoints = _collect_from(app_dir, changed)
    else:
        all_lines = _all_controller_lines(app_dir)
        if not all_lines:
            print(
                f"[gate-{GATE_NUM}] contract-coverage: NOT APPLICABLE — "
                f"appinfo/routes.php exists but there is no "
                f"lib/Controller/*Controller.php for a route to reach."
            )
            return EXIT_NOT_APPLICABLE
        endpoints = _collect_from(app_dir, all_lines)

    if not endpoints:
        scope_desc = (
            f"the diff against '{base_ref}'" if base_ref else "the whole tree"
        )
        print(
            f"[gate-{GATE_NUM}] contract-coverage: PASS — "
            f"{scope_desc} contains no new public endpoint"
        )
        return EXIT_PASS
    newman = _newman_paths(app_dir)
    phpunit = _phpunit_text(app_dir)
    app_id = _app_id(app_dir)
    findings: list[str] = []
    for ep in endpoints:
        if ep["contract_status"] == "exclude_noreason":
            findings.append(f"{ep['ref']} — @contract exclude without reason (reason required)")
            continue
        if not is_covered(ep, newman, phpunit, app_id):
            findings.append(
                f"{ep['ref']} — new public endpoint (url={ep['url'] or '?'}) "
                f"missing Newman/PHPUnit contract test or @contract exclude"
            )
    for line in sorted(set(findings)):
        print(line)
    count = len(set(findings))
    if count == 0:
        print(
            f"[gate-{GATE_NUM}] contract-coverage: PASS — "
            f"{len(endpoints)} new endpoint(s), all covered"
        )
        return EXIT_PASS
    print(
        f"[gate-{GATE_NUM}] contract-coverage: FAIL — "
        f"{count} new public endpoint(s) without a contract test"
    )
    # A STATUS, not the count. Returning the count meant 256 findings exited 0
    # and read as PASS — the same byte-width bug gate-19 shipped (.github#209).
    # The honest number is the one printed above, and the runner reads it there.
    return EXIT_FAIL


def run_report(app_dir: Path) -> int:
    base_ref = os.environ.get("HYDRA_GATE_BASE_REF", "origin/development")
    endpoints = _collect(app_dir, base_ref)
    newman = _newman_paths(app_dir)
    phpunit = _phpunit_text(app_dir)
    app_id = _app_id(app_dir)
    covered = uncovered = excluded = 0
    rows = []
    for ep in endpoints:
        if ep["contract_status"] in ("ref", "excluded"):
            excluded += 1
            state = "excluded"
        elif is_covered(ep, newman, phpunit, app_id):
            covered += 1
            state = "covered"
        else:
            uncovered += 1
            state = "uncovered"
        rows.append({"ref": ep["ref"], "url": ep["url"], "state": state})
    out = {
        "mode": "report",
        "gate": GATE_NUM,
        "app": app_dir.name,
        "totals": {
            "new_endpoints": len(endpoints),
            "covered": covered,
            "excluded": excluded,
            "uncovered": uncovered,
        },
        "endpoints": rows,
    }
    print(json.dumps(out, indent=2))
    return 0


def main(argv: list[str]) -> int:
    mode = "gate"
    app = "."
    rest = argv[1:]
    i = 0
    while i < len(rest):
        if rest[i] == "--mode" and i + 1 < len(rest):
            mode = rest[i + 1]
            i += 2
            continue
        app = rest[i]
        i += 1
    app_dir = Path(app).resolve()
    if mode == "report":
        return run_report(app_dir)
    return run_gate(app_dir)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
