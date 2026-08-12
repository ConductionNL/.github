#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Gate-16 spec-coverage — diff-scoped @spec traceability enforcer.

Every public/protected backend method and every non-trivial frontend method
ADDED or MODIFIED in a PR must carry an ``@spec openspec/...`` reference in its
docblock (PHP) or JSDoc (JS/TS/Vue). This makes the code → docblock → spec
chain mandatory going forward (ADR-003) without bouncing PRs on the mountain of
pre-existing untagged legacy methods (ADR-020 — gates scope to the PR diff).

Diff scope
==========

The set of "changed methods" is derived from ``git diff -U0`` against
``$HYDRA_GATE_BASE_REF`` (default ``origin/development``). For each in-scope
file we collect the set of *added* line numbers (the right-hand side of the
diff) and only flag a method whose declaration line OR body overlaps one of
those added lines. A method that exists in the diff's context but was not
itself touched is never flagged — so untouched legacy methods stay green even
when a neighbouring method changes.

That added-line set is then narrowed to the lines whose CONTENT changed, not
merely their layout (``.github#395``): brace style, indentation, intra-line
spacing and a PHP trailing comma are normalised away on both sides before a
line counts as added. Only a line the normalisation still shows as different
puts a method in scope — and the narrowing is an intersection with git's own
answer, so it can never widen the scope.

This runs against the CURRENT working directory's git repo (the script is
repo-agnostic — it lives in hydra but operates on whatever app is checked out
at cwd).

Scope rules
===========

Backend (``*.php``):
  In-scope dirs:   lib/Controller, lib/Service, lib/BackgroundJob,
                   lib/Command, lib/Cron, lib/Listener, lib/Repair.
  In-scope methods: ``public`` + ``protected`` functions.
  Exempt:          __construct, magic methods (__call/__get/__set/...),
                   simple accessors (get*/set*/is*/has* with a body of <=2
                   non-blank lines), and anything under lib/Db or
                   lib/Migration.

Frontend (``*.js`` / ``*.ts`` / ``*.vue``):
  In-scope: Vue SFC ``methods:`` / ``computed:`` functions, ``setup()`` bodies,
            composable exports under src/composables/, Pinia/Vuex actions under
            src/store*/, and exported functions under src/services, src/utils,
            src/lib, src/entities.
  Exempt:   trivial state-passthrough getters + lifecycle hooks (created/
            mounted/...) with empty or <=2-line bodies, src/main.js,
            src/bootstrap.js, *.spec.* / *.test.* / __tests__.

The rule
========

The docblock / JSDoc immediately above an in-scope, changed method must contain
a string matching ``@spec\\s+openspec/``. Missing → one finding::

    <path>::<method> — missing @spec

Exit code is the number of findings (0 == clean), mirroring the other
python-backed gates.

Usage::

    python3 scripts/lib/check_spec_coverage.py [app-dir]
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exclusion_reason import exclude_pattern, is_reason_bearing  # noqa: E402

SPEC_RE = re.compile(r"@spec\s+openspec/")
# `@spec exclude <reason>` — intentional, reason-required non-coverage marker.
# A bare `@spec exclude` (no reason) is NOT compliant — it would let a method
# silently hide a gap, so it is flagged like a missing @spec.
#
# NEITHER IS `@spec exclude .` (.github#400). The marker used to be graded by
# `if reason:` — plain truthiness — so any non-empty string counted, and a
# single full stop was the whole difference between a blocked PR and a green
# one. The rule now lives in exclusion_reason.is_reason_bearing(), shared with
# gates 19, 25 and 26, which had the identical defect.
SPEC_EXCLUDE_RE = re.compile(exclude_pattern("spec"))

# ---- backend ---------------------------------------------------------------

BACKEND_DIRS = (
    "lib/Controller",
    "lib/Service",
    "lib/BackgroundJob",
    "lib/Command",
    "lib/Cron",
    "lib/Listener",
    "lib/Repair",
)
BACKEND_EXEMPT_DIRS = ("lib/Db", "lib/Migration")

# `public function foo(` / `protected function foo(` — capture visibility+name.
PHP_METHOD_RE = re.compile(
    r"^\s*(?:final\s+|abstract\s+|static\s+)*"
    r"(?P<vis>public|protected)\s+"
    r"(?:static\s+)?function\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(",
)
PHP_MAGIC_RE = re.compile(r"^__")
PHP_ACCESSOR_RE = re.compile(r"^(get|set|is|has)[A-Z0-9_]")

# ---- frontend --------------------------------------------------------------

FRONTEND_EXPORT_DIRS = (
    "src/composables",
    "src/services",
    "src/utils",
    "src/lib",
    "src/entities",
)
FRONTEND_STORE_RE = re.compile(r"(^|/)src/stores?(/|$)")
FRONTEND_EXEMPT_FILES = ("src/main.js", "src/main.ts", "src/bootstrap.js", "src/bootstrap.ts")
LIFECYCLE_HOOKS = {
    "beforeCreate", "created", "beforeMount", "mounted",
    "beforeUpdate", "updated", "beforeUnmount", "unmounted",
    "beforeDestroy", "destroyed", "activated", "deactivated",
}
# Vue framework state/render options — never business logic, always exempt
# regardless of body size (`data()` returns the component's state object,
# `render()` is a compile target). `setup()` stays IN scope (it holds real
# composable wiring per the gate spec).
VUE_FRAMEWORK_OPTIONS = {"data", "render"}
# An exported function declaration in a JS/TS module.
JS_EXPORT_FN_RE = re.compile(
    r"^\s*export\s+(?:default\s+)?(?:async\s+)?function\s*\*?\s*"
    r"(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)?\s*\(",
)
JS_EXPORT_CONST_FN_RE = re.compile(
    r"^\s*export\s+(?:default\s+)?const\s+(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)\s*="
    r"\s*(?:async\s+)?(?:\([^)]*\)|[A-Za-z_$][A-Za-z0-9_$]*)\s*=>",
)
# A method-shorthand or named function inside a Vue methods:/computed:/actions:
# block or setup(). e.g. `  fetchThings () {` or `  async save (id) {`.
VUE_METHOD_RE = re.compile(
    r"^(?P<indent>\s+)(?:async\s+)?(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)\s*"
    r"\([^)]*\)\s*\{",
)

# ---- cosmetic-reformat normalisation (.github#395) --------------------------
#
# A line whose only difference from its base version is LAYOUT is not a changed
# method. `git diff -w` cannot express that: the brace of Nextcloud's K&R style
# is a TOKEN THAT MOVED LINES, not whitespace that changed width, so
# `public function foo()` and `public function foo() {` differ under `-w` and
# every method in a reformatted app reads as modified.
#
# Each rule below is narrow enough that the two forms it equates are the same
# program. Nothing here is a heuristic about intent.

# `foo() {` -> `foo()`. The brace still has to be SOMEWHERE — Allman puts it on
# its own line, which normalises to the empty string and is dropped — so no
# information is lost, only its position.
_NORM_TRAILING_BRACE_RE = re.compile(r"\s*\{$")
_NORM_WS_RE = re.compile(r"\s+")
# A complete single- or double-quoted literal, escapes included. Whitespace
# INSIDE one is content and is left exactly as it is: `'a b'` -> `'ab'` is a
# change to what a user sees and must stay visible to this gate.
_NORM_STRING_RE = re.compile(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"")


def _unify_quote_style(literal: str) -> str:
    """``"abc"`` -> ``'abc'`` when the two forms denote the SAME string.

    Only a double-quoted literal is rewritten, and only when its body has no
    ``$`` or ``{`` (interpolation, in both simple and complex syntax), no ``'``
    (which would need escaping on the other side), and no backslash other than
    the ones spelling ``\\"``. Those exclusions are the whole safety argument:
    they are exactly what makes a double-quoted string mean something a
    single-quoted one does not. ``"\\n"`` is a newline and ``'\\n'`` is two
    characters, so a literal carrying any other escape is left alone; ``"a\\"b"``
    and ``'a"b'`` are the same three characters in PHP and in JS alike, so that
    one is unescaped and equated. This equates two spellings of one value, never
    two values.
    """
    if not literal.startswith('"'):
        return literal
    body = literal[1:-1]
    if any(c in body for c in ("$", "{", "'")):
        return literal
    if "\\" in body.replace('\\"', ""):
        return literal
    return "'" + body.replace('\\"', '"') + "'"


def _normalise_code_line(line: str) -> str | None:
    """A layout-independent key for ``line``, or ``None`` if the line carries no
    code identity at all (blank, or a bare docblock ``*``, or a lone brace).

    Applied to BOTH sides of the comparison, so the only question it answers is
    "are these two lines the same program". What it deliberately equates:

    * brace placement — K&R vs Allman (``.github#395``, and gate-14's ``#391``);
    * indentation and intra-line spacing, including operator and cast spacing
      (``(array) $x`` / ``(array)$x``) and docblock column alignment;
    * quote style, under the narrow rule in ``_unify_quote_style``.

    What it deliberately does NOT equate: anything INSIDE a string literal.
    ``'a b'`` -> ``'ab'`` changes what a user reads and stays visible to this
    gate, which is why literals are lifted out before whitespace is touched.

    Whitespace outside a literal is REMOVED rather than collapsed because
    php-cs-fixer both adds it (``'a'.$b`` -> ``'a' . $b``) and removes it
    (``(array) $x`` -> ``(array)$x``); collapsing to a single space leaves the
    second form differing, and was measured on procest#819 to recover 71 of the
    185 false findings against 183 for removal. Removal can in principle weld
    two tokens together (``else if`` -> ``elseif``, which procest's diff
    actually contains), but each pair it can weld is either the same program —
    that one is — or one half of it does not parse, so it cannot equate two
    different WORKING programs.
    """
    s = line.strip()
    if s == "" or s == "*":
        return None
    s = _NORM_TRAILING_BRACE_RE.sub("", s)
    if s == "":
        return None
    out: list[str] = []
    pos = 0
    for m in _NORM_STRING_RE.finditer(s):
        out.append(_NORM_WS_RE.sub("", s[pos:m.start()]))
        out.append(_unify_quote_style(m.group(0)))
        pos = m.end()
    out.append(_NORM_WS_RE.sub("", s[pos:]))
    return "".join(out)


def _comparison_keys(text: str, is_php: bool) -> tuple[list[int], list[str], list[str]]:
    """``(line_numbers, keys, keys_with_trailing_comma_kept)`` for ``text``.

    Two variants of the same key, index-aligned, because the two comparisons
    below want different things from a trailing comma. Line-vs-line, a PHP
    trailing comma is a no-op and must be ignored — php-cs-fixer adds one to
    every multi-line parameter list, which is 2 of procest's 185 findings on its
    own. Region-vs-region (the re-wrap rule) has to keep it, because there the
    commas are load-bearing punctuation of the joined statement.
    """
    numbers: list[int] = []
    keys: list[str] = []
    keys_full: list[str] = []
    for i, raw in enumerate(text.splitlines()):
        k = _normalise_code_line(raw)
        if k is None:
            continue
        numbers.append(i + 1)
        keys_full.append(k)
        keys.append(k[:-1] if is_php and k.endswith(",") else k)
    return numbers, keys, keys_full


def _is_pure_rewrap(base_region: list[str], head_region: list[str], is_php: bool) -> bool:
    """True if the two regions are the SAME CHARACTERS, distributed differently
    across lines — a line-length reflow such as ``'a '.`` + ``'b'`` becoming
    ``'a '`` + ``.'b'``, or a long call broken after an argument.

    PHP ONLY, and never across a line comment. Both restrictions are about the
    one thing a line break can do besides layout: END something. JavaScript has
    automatic semicolon insertion, so joining ``return`` and ``x`` changes what
    the function returns; PHP has no ASI. And in either language a ``//`` runs
    to the end of the line, so inserting a break after one UNCOMMENTS whatever
    followed — the same characters, a different program. Refusing the rule
    whenever the region contains a comment introducer costs only precision.
    """
    if not is_php or not base_region or not head_region:
        return False
    joined_base = "".join(base_region)
    if joined_base != "".join(head_region):
        return False
    return "//" not in joined_base and "#" not in joined_base


def _substantively_changed_lines(base_text: str, head_text: str, is_php: bool) -> set[int]:
    """1-based line numbers in ``head_text`` that are not present, unchanged, in
    ``base_text`` once both sides are normalised by ``_normalise_code_line``."""
    _, base_keys, base_full = _comparison_keys(base_text, is_php)
    head_numbers, head_keys, head_full = _comparison_keys(head_text, is_php)
    matcher = SequenceMatcher(None, base_keys, head_keys, autojunk=False)
    changed: set[int] = set()
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag not in ("replace", "insert"):
            continue
        if _is_pure_rewrap(base_full[i1:i2], head_full[j1:j2], is_php):
            continue
        for j in range(j1, j2):
            changed.add(head_numbers[j])
    return changed


def _is_in_gate_scope(rel: str) -> bool:
    """True if this path is one gate-16 would evaluate at all."""
    if rel.endswith(".php"):
        return rel.startswith(BACKEND_DIRS) and not rel.startswith(BACKEND_EXEMPT_DIRS)
    return _is_frontend_in_scope(rel)


def _drop_cosmetic_only(
    changed: dict[str, set[int]], base_commit: str, cwd: Path,
) -> dict[str, set[int]]:
    """Narrow each file's added-line set to the lines that are not pure layout.

    INTERSECTS with git's own set — it can only ever REMOVE lines, never add
    one. A file that is new at HEAD (no base blob) or that cannot be read keeps
    git's answer untouched, so the failure mode of every lookup here is the
    PRE-EXISTING behaviour, not silence.
    """
    out: dict[str, set[int]] = {}
    for rel, added in changed.items():
        if not added or not _is_in_gate_scope(rel):
            out[rel] = added
            continue
        base_text = _git(["show", f"{base_commit}:{rel}"], cwd)
        if not base_text:
            # Added by this branch, or unreadable at the base: every line of it
            # is genuinely new.
            out[rel] = added
            continue
        try:
            head_text = (cwd / rel).read_text(encoding="utf-8")
        except OSError:
            out[rel] = added
            continue
        out[rel] = added & _substantively_changed_lines(base_text, head_text, rel.endswith(".php"))
    return out


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
    """Return {relative_path: {added_line_numbers}} from ``git diff -U0``.

    Falls back from ``BASE...HEAD`` to ``BASE`` (working-tree diff) so the
    gate works both on a PR branch and on an uncommitted local checkout.

    A LINE THAT ONLY MOVED IS NOT A CHANGED METHOD (.github#395). git's answer
    is then narrowed by ``_drop_cosmetic_only``: each in-scope file is compared
    against its own base version with layout normalised away, and any added line
    that survives normalisation as identical is dropped from the scope. Measured
    on ConductionNL/procest#819, a `conduction/coding-standard` adoption PR of
    921 PHP files: 185 findings before, 0 after, and PHP's own tokeniser agrees
    — the 54 files those findings named are token-identical to their base once
    whitespace, comments, trailing commas and quote style are set aside.
    """
    diff = _git(["diff", "-U0", "--diff-filter=ACMR", f"{base_ref}...HEAD"], cwd)
    three_dot = True
    if not diff.strip():
        diff = _git(["diff", "-U0", "--diff-filter=ACMR", base_ref], cwd)
        three_dot = False
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
    # `A...B` diffs against the MERGE BASE, so that — not `base_ref` itself — is
    # the version each file has to be compared with. Getting this wrong would
    # compare against a commit the branch never saw and silently stop
    # suppressing anything, which is why it is resolved rather than assumed.
    base_commit = base_ref
    if three_dot:
        base_commit = _git(["merge-base", base_ref, "HEAD"], cwd).strip() or base_ref
    return _drop_cosmetic_only(result, base_commit, cwd)


def spec_tags_removed(base_ref: str, cwd: Path) -> set[str]:
    """Return the files whose diff DELETES an ``@spec`` line.

    WHY THIS EXISTS (.github#271)
    -----------------------------
    ``_overlaps`` walks FORWARD from the declaration line through the method
    body. The docblock sits ABOVE the declaration, so it is outside the scope
    window entirely — and the docblock is the only place ``@spec`` can live.

    The consequence is that the one edit which REMOVES coverage is the one edit
    this gate cannot see. Measured 2026-08-08 on a two-file fixture: delete the
    ``@spec openspec/...`` line from a tagged method, leave the body
    byte-identical, and the helper prints ``# count=0`` and exits 0. Every
    ``@spec`` tag in a repository can be stripped and gate-16 stays green.

    Worse, ``run_gate`` skips a file whose ``added`` set is empty, and a pure
    deletion produces exactly that — so the file was never even opened.

    Same family as the ``filter_preexisting_methods.py`` defect that lets an
    auth-attribute removal be filed as pre-existing (gates 5/9/30): a
    body-shaped scope cannot see a change that is not in the body. Gate-16 does
    not route through that helper — its four call sites are gates 6, 7, 8 and
    30 — it arrives at the same blind spot by its own path.

    DELIBERATELY NARROW. This does NOT put every docblock edit in scope: fixing
    a typo in a legacy untagged method's docblock must not surface that method
    as a finding, because ADR-020 exists to stop inherited debt blocking
    unrelated work. It fires only when the diff actually TOOK A TAG AWAY, which
    is never inherited debt and is always the author's own doing.
    """
    removed: set[str] = set()
    for form in ([f"{base_ref}...HEAD"], [base_ref]):
        diff = _git(["diff", "-U0", "--diff-filter=ACMRD", *form], cwd)
        if not diff.strip():
            continue
        current: str | None = None
        for line in diff.splitlines():
            if line.startswith("--- a/"):
                current = line[6:]
            elif line.startswith("+++ b/"):
                # Prefer the new path for renames; fall back to the old one.
                current = line[6:]
            elif line.startswith("-") and not line.startswith("---"):
                if current and (SPEC_RE.search(line) or SPEC_EXCLUDE_RE.search(line)):
                    removed.add(current)
        if removed:
            break
    return removed


def _docblock_spec_status(lines: list[str], decl_idx: int) -> tuple[str, str | None]:
    """Classify the docblock immediately above ``decl_idx`` into one of:
      - ``("covered", None)``        — has ``@spec openspec/...``
      - ``("excluded", reason)``     — has ``@spec exclude <reason>`` (reason-bearing)
      - ``("exclude_noreason", None)`` — has ``@spec exclude`` with no usable reason
      - ``("none", None)``           — neither (an uncovered gap)
    """
    block = _docblock_block(lines, decl_idx)
    if any(SPEC_RE.search(b) for b in block):
        return ("covered", None)
    for b in block:
        m = SPEC_EXCLUDE_RE.search(b)
        if m:
            reason = m.group("reason").strip().rstrip("*/").strip()
            # `if reason:` here was .github#400 — "." is a non-empty string, so
            # it was truthy, so it was a reason. The normalisation above stays
            # local (PHP docblocks close with `*/`); only the VERDICT is shared.
            if is_reason_bearing(reason):
                return ("excluded", reason)
            return ("exclude_noreason", None)
    return ("none", None)


def _docblock_block(lines: list[str], decl_idx: int) -> list[str]:
    """Return the lines of the ``/** ... */`` block immediately preceding the
    declaration on ``decl_idx`` (skipping PHP attributes + blank lines), or
    ``[]`` if there is no docblock directly above."""
    i = decl_idx - 1
    # Skip PHP attributes, blank lines, and intervening single-line comments
    # (e.g. `/* istanbul ignore next */`, `// eslint-disable-next-line`) that
    # commonly sit between a docblock and the declaration it documents. Without
    # this, a `/* istanbul ignore next */` line — which contains `*/` — is
    # mistaken for the docblock close and the real `@spec` docblock above is
    # never read (observed on openregister store `refreshXList` actions).
    while i >= 0:
        stripped = lines[i].strip()
        if stripped == "" or stripped.startswith("#[") or stripped.startswith("]"):
            i -= 1
            continue
        if stripped.startswith("//"):
            i -= 1
            continue
        # A single-line block comment that is NOT a docblock opener — including a
        # trailing line comment after it, e.g. `/* istanbul ignore next */ // note`.
        if stripped.startswith("/*") and not stripped.startswith("/**") and "*/" in stripped:
            after = stripped.split("*/", 1)[1].strip()
            if after == "" or after.startswith("//"):
                i -= 1
                continue
        break
    if i < 0:
        return []
    # The line just above should be the close of a block comment.
    if "*/" not in lines[i]:
        return []
    block: list[str] = []
    while i >= 0:
        block.append(lines[i])
        if "/**" in lines[i] or "/*" in lines[i]:
            break
        i -= 1
    return block


def _docblock_has_spec(lines: list[str], decl_idx: int) -> bool:
    """True if the docblock above ``decl_idx`` carries ``@spec openspec/`` OR a
    reason-bearing ``@spec exclude <reason>`` — i.e. the method is compliant
    (covered or intentionally excluded). A bare ``@spec exclude`` is NOT
    compliant."""
    status, _ = _docblock_spec_status(lines, decl_idx)
    return status in ("covered", "excluded")


def _body_line_count(lines: list[str], decl_idx: int) -> int:
    """Count non-blank lines in the brace-delimited body following the
    declaration on ``decl_idx``. Used to identify trivial accessors / hooks.
    Returns a large number if no brace is found (treat as non-trivial)."""
    depth = 0
    started = False
    count = 0
    n = len(lines)
    i = decl_idx
    while i < n:
        line = lines[i]
        opens = line.count("{")
        closes = line.count("}")
        if not started and opens > 0:
            started = True
        if started:
            # Count body lines (exclude the decl line itself and the closing).
            if i > decl_idx:
                stripped = line.strip()
                if stripped and stripped not in ("{", "}"):
                    count += 1
            depth += opens - closes
            if depth <= 0 and (opens or closes):
                break
        i += 1
        if i - decl_idx > 400:
            break
    return count


def _overlaps(decl_idx: int, lines: list[str], added: set[int]) -> bool:
    """True if the method's declaration or body (1-based lines) intersects the
    set of added line numbers."""
    # decl_idx is 0-based; convert to 1-based and walk the body span.
    depth = 0
    started = False
    i = decl_idx
    n = len(lines)
    while i < n:
        if (i + 1) in added:
            return True
        opens = lines[i].count("{")
        closes = lines[i].count("}")
        if not started and opens > 0:
            started = True
        if started:
            depth += opens - closes
            if depth <= 0 and (opens or closes):
                break
        i += 1
        if i - decl_idx > 400:
            break
    return False


def check_php_file(rel: str, text: str, added: set[int], findings: list[str]) -> None:
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        m = PHP_METHOD_RE.match(line)
        if not m:
            continue
        name = m.group("name")
        if PHP_MAGIC_RE.match(name):
            continue
        if PHP_ACCESSOR_RE.match(name) and _body_line_count(lines, idx) <= 2:
            continue
        if not _overlaps(idx, lines, added):
            continue
        if _docblock_has_spec(lines, idx):
            continue
        findings.append(f"{rel}::{name} — missing @spec")


def _is_frontend_in_scope(rel: str) -> bool:
    if rel in FRONTEND_EXEMPT_FILES:
        return False
    if ".spec." in rel or ".test." in rel or "__tests__" in rel:
        return False
    if rel.endswith(".vue"):
        return rel.startswith("src/")
    if rel.endswith((".js", ".ts")):
        if rel.startswith(FRONTEND_EXPORT_DIRS):
            return True
        if FRONTEND_STORE_RE.search(rel):
            return True
    return False


def check_frontend_file(rel: str, text: str, added: set[int], findings: list[str]) -> None:
    lines = text.splitlines()
    is_vue = rel.endswith(".vue")
    is_module = rel.endswith((".js", ".ts"))
    in_store = bool(FRONTEND_STORE_RE.search(rel))
    in_export_dir = rel.startswith(FRONTEND_EXPORT_DIRS)

    for idx, line in enumerate(lines):
        name: str | None = None

        # Exported function / arrow-const in a JS/TS module.
        if is_module and (in_export_dir or in_store):
            jm = JS_EXPORT_FN_RE.match(line) or JS_EXPORT_CONST_FN_RE.match(line)
            if jm:
                name = jm.groupdict().get("name") or "default"

        # Vue method-shorthand (also covers composable/setup/store-action
        # functions written as method shorthand inside an object literal).
        if name is None:
            vm = VUE_METHOD_RE.match(line)
            if vm:
                cand = vm.group("name")
                # Skip control-flow keywords that look like a call.
                if cand in ("if", "for", "while", "switch", "catch", "function", "return"):
                    continue
                # Vue framework state/render options are never business logic.
                if cand in VUE_FRAMEWORK_OPTIONS:
                    continue
                # Lifecycle hooks with trivial bodies are exempt.
                if cand in LIFECYCLE_HOOKS and _body_line_count(lines, idx) <= 2:
                    continue
                # In a plain Vue SFC we only care about method-ish blocks; this
                # heuristic accepts any object-method shorthand and relies on
                # the diff-scope + trivial-getter exemption to stay quiet.
                if is_vue or in_store or in_export_dir:
                    # Trivial state-passthrough getter: `getFoo () { return ... }`
                    if _body_line_count(lines, idx) <= 2 and PHP_ACCESSOR_RE.match(cand):
                        continue
                    name = cand

        if name is None:
            continue
        if not _overlaps(idx, lines, added):
            continue
        if _docblock_has_spec(lines, idx):
            continue
        findings.append(f"{rel}::{name} — missing @spec")


def _iter_in_scope_files(app_dir: Path) -> list[str]:
    """All in-scope backend + frontend files in the repo (full-repo, no diff)."""
    rels: list[str] = []
    for d in BACKEND_DIRS:
        base = app_dir / d
        if base.is_dir():
            rels += [str(p.relative_to(app_dir)) for p in base.rglob("*.php")]
    src = app_dir / "src"
    if src.is_dir():
        for p in src.rglob("*"):
            if p.is_file():
                rel = str(p.relative_to(app_dir))
                if _is_frontend_in_scope(rel):
                    rels.append(rel)
    return sorted(set(rels))


def run_report(app_dir: Path) -> int:
    """Full-repo coverage report (NOT diff-scoped). Lists every uncovered
    in-scope method as JSON so AI tooling can act on the gaps directly —
    the mechanical replacement for the coverage-scan enumeration pass.
    Always exits 0 (a report is informational, never a build failure)."""
    uncovered: list[str] = []
    for rel in _iter_in_scope_files(app_dir):
        path = app_dir / rel
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        # added = every line, so the diff-scope `_overlaps` check always passes
        # → every in-scope method is evaluated; @spec / @spec-exclude still skip.
        all_lines = set(range(1, len(text.splitlines()) + 2))
        if rel.endswith(".php"):
            if rel.startswith(BACKEND_EXEMPT_DIRS) or not rel.startswith(BACKEND_DIRS):
                continue
            check_php_file(rel, text, all_lines, uncovered)
        elif _is_frontend_in_scope(rel):
            check_frontend_file(rel, text, all_lines, uncovered)
    uncovered = sorted(set(uncovered))
    out = {
        "mode": "report",
        "uncovered_count": len(uncovered),
        "uncovered": [
            {"ref": u, "layer": "backend" if u.split("::", 1)[0].endswith(".php") else "frontend"}
            for u in uncovered
        ],
    }
    print(json.dumps(out, indent=2))
    return 0


def _git_show(base_ref: str, rel: str, cwd: Path) -> str:
    """The file as it was at ``base_ref``; empty string when it did not exist."""
    return _git(["show", f"{base_ref}:{rel}"], cwd)


def _uncovered_in_text(rel: str, text: str) -> set[str]:
    """Every in-scope method in ``text`` that carries no @spec, ignoring diff
    scope. Used to diff a file against its own base version so only the methods
    whose coverage CHANGED are reported (.github#271)."""
    if not text:
        return set()
    out: list[str] = []
    all_lines = set(range(1, len(text.splitlines()) + 2))
    if rel.endswith(".php"):
        if rel.startswith(BACKEND_EXEMPT_DIRS) or not rel.startswith(BACKEND_DIRS):
            return set()
        check_php_file(rel, text, all_lines, out)
    elif _is_frontend_in_scope(rel):
        check_frontend_file(rel, text, all_lines, out)
    return set(out)


def run_gate(app_dir: Path) -> int:
    base_ref = os.environ.get("HYDRA_GATE_BASE_REF", "origin/development")
    changed = changed_lines(base_ref, app_dir)
    # Files this diff STRIPPED an @spec tag from (.github#271). A pure deletion
    # produces an empty `added` set, which the loop below used to skip outright,
    # so the file was not even opened.
    stripped = spec_tags_removed(base_ref, app_dir)
    findings: list[str] = []

    for rel in sorted(set(changed) | stripped):
        added = changed.get(rel, set())
        path = app_dir / rel
        if not path.is_file():
            continue
        if rel in stripped:
            # WHAT THIS PR TOOK AWAY, AND ONLY THAT.
            #
            # Evaluating the whole file here would name every untagged method in
            # it, which on a legacy file is inherited debt the author did not
            # touch — the thing ADR-020 exists to keep out of a PR. So the file
            # is evaluated TWICE, once as it is and once as it was at the base,
            # with the same walkers and therefore the same exemptions, and the
            # findings are the DIFFERENCE. A file that lost one tag reports one
            # finding; a file that lost none reports none, however much
            # pre-existing debt it carries.
            before = _uncovered_in_text(rel, _git_show(base_ref, rel, app_dir))
            now = _uncovered_in_text(rel, path.read_text(encoding="utf-8"))
            findings.extend(sorted(now - before))
            if not added:
                continue
        elif not added:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue

        if rel.endswith(".php"):
            if rel.startswith(BACKEND_EXEMPT_DIRS):
                continue
            if not rel.startswith(BACKEND_DIRS):
                continue
            check_php_file(rel, text, added, findings)
        elif _is_frontend_in_scope(rel):
            check_frontend_file(rel, text, added, findings)

    for line in sorted(set(findings)):
        print(line)
    # TERMINAL MARKER (.github#271) — see the note in
    # check_dashboard_antipattern.py. gate-16 decided its verdict with `wc -l`
    # over this helper's stdout after `2>/dev/null || true`, so a helper that
    # crashed produced an empty log and the gate reported PASS. Verified
    # 2026-08-08 by running the suite with a python3 stub that always exits 1:
    # gate-16 said PASS while nothing had been inspected.
    #
    # The exit code is now a STATUS (0 clean / 1 findings), not the count. It
    # used to be `len(set(findings))` — a count in one byte, which is #209:
    # openregister's own root-scoped sweep is well past 255.
    _count = len(set(findings))
    print(f"# count={_count}")
    return 1 if _count else 0


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
