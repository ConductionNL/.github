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
merely their layout (``.github#395``, ``.github#435``): brace style,
indentation, intra-line spacing, a trailing comma, quote style, a statement
re-wrapped across lines and — in JS/TS/Vue — a parenthesis prettier re-printed
from its own precedence table are normalised away on both sides before a line
counts as added. Only a line the normalisation still shows as different puts a
method in scope — and the narrowing is an intersection with git's own answer, so
it can never widen the scope.

Every rule is paired with a control proving a real change still travels through
it (``NormalisationTest`` and ``JsNormalisationTest``), because a normalisation
loose enough to swallow ``+`` -> ``-`` would pass every "reports nothing" arm
and quietly retire the gate.

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

# `@spec openspec/…` AT TAG POSITION, NOT ANYWHERE ON THE LINE (#422).
#
# This was an unanchored substring, so a docblock line that MENTIONED the tag
# carried it. Measured on this checker, one fixture, one line:
#
#     an untagged public method                        -> uncovered (a finding)
#     + a docblock reading
#       "* TODO: nobody has written @spec
#        openspec/specs/thing/spec.md for this yet"    -> covered   <- the defect
#
# This one is borderline and the borderline is worth stating: `@spec` is a
# docblock marker, so unlike every other gate in #422 the evidence legitimately
# LIVES in a comment and a comment mask would delete it. What was missing is
# not comment-awareness, it is POSITION — the same anchoring gates 47 and 48
# were given, and that gate 46 still lacks. The tag has to OPEN its line's
# content; a sentence that quotes it does not.
#
# THE LEAD CLASS IS MEASURED, NOT GUESSED. It must pass every spelling the
# fleet actually uses, and `[ \t>*#-]` — the `standalone` lead
# `exclusion_reason.exclude_pattern` uses for markdown — is NOT enough here,
# because PHP and JS docblocks are opened with slashes:
#
#     ` * @spec openspec/…`      3,726 in procest      (covered by the md lead)
#     `/** @spec openspec/…`       626 in procest,
#                                  638 in opencatalogi (needs `/`)
#
# So `/` is in the class, for the SINGLE-LINE DOCBLOCK form. The fleet also
# carries 109 `// @spec openspec/…` lines (openregister 56, procest 43,
# softwarecatalog 10) and those are unaffected either way: `_docblock_block`
# skips `//` lines when looking for the block above a declaration, so a
# line-comment tag has never satisfied this gate. Measured, not assumed — the
# expectation going in was the opposite, and arm 5 of the suite records it.
#
# Swept over lib/ + src/ of procest, opencatalogi,
# openregister, softwarecatalog, docudesk and larpingapp — 15,972 occurrences —
# exactly TWO stop counting, and both are prose about a tag rather than a tag:
#
#     `// Per @spec openspec/specs/tenant-isolation-audit/spec.md ("the system MUST…`
#     `NOTE: this used to read ``@spec openspec/changes/dso-…/tasks.md#T07``.`
#
# The second is this defect in the wild: a note about a tag that was REMOVED,
# reading as the tag.
#
# ⚠️ AND THE START ANCHOR ALONE WAS NOT THE ANSWER — MEASURING SAID SO.
# The first cut of this was `^[ \t>*#/-]*@spec\s+openspec/` and nothing else.
# Swept exhaustively over every in-scope method in the six repos (46,187
# judgements, diff scope bypassed so every line counts as changed) it produced
# FIVE new findings, all in decidesk's VotingRoundPanel.vue, all of this shape:
#
#     /** Rule enum option lists for the open-round dialog. @spec openspec/specs/voting-system/spec.md */
#     voteThresholdOptions() {
#
# That is a REAL, deliberate tag in the ordinary PHPDoc order — description
# first, tag after — and the only way to close the finding would have been to
# reflow correct documentation. A gate that reddens documented code teaches
# authors to stop documenting it, which is the FALSE-POSITIVE half of this same
# class and the half the survey calls the corrosive one. So the second
# alternative admits a tag that FOLLOWS A COMPLETED SENTENCE, which is what
# the real form is and what none of the prose forms are:
#
#     ` * TODO: nobody has written @spec openspec/…`     rejected (no terminator)
#     ` * NOTE: this used to read @spec openspec/…`      rejected (no terminator)
#     ` * TODO: still owed: @spec openspec/…`            rejected (`:` is not one)
#     `/** … open-round dialog. @spec openspec/…  */`    accepted
#
# Measured again with this pattern: ZERO new findings in all six repos.
#
# The residual hole is stated rather than hidden: a debt sentence that ENDS in
# a full stop immediately before the tag — "not written yet. @spec openspec/x"
# — still counts. Closing that needs the tag's OWNERSHIP of the line, which is
# the same question gate-46 has open, and it is not worth 5 false positives
# here.
SPEC_RE = re.compile(
    r"(?:^[ \t>*#/-]*@spec\s+openspec/)"
    r"|(?:[.!?)]\s+@spec\s+openspec/)"
)
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

# ---- cosmetic-reformat normalisation (.github#395, .github#435) -------------
#
# A line whose only difference from its base version is LAYOUT is not a changed
# method. `git diff -w` cannot express that: the brace of Nextcloud's K&R style
# is a TOKEN THAT MOVED LINES, not whitespace that changed width, so
# `public function foo()` and `public function foo() {` differ under `-w` and
# every method in a reformatted app reads as modified.
#
# Each rule below is narrow enough that the two forms it equates are the same
# program. Nothing here is a heuristic about intent.

# `foo() {` -> `foo()`. PHP ONLY. The brace still has to be SOMEWHERE — Allman
# puts it on its own line, which normalises to the empty string and is dropped —
# so no information is lost, only its position, and php-cs-fixer moves it.
#
# JS/TS/Vue deliberately KEEP the brace (.github#435). prettier never moves an
# opening brace off its line, so the rule buys nothing there, and dropping the
# character actively CORRUPTS the re-wrap comparison below: a mustache split as
# `<span>{{` + `x` + `}}</span>` loses one `{` and stops matching its own
# single-line base; a multi-line `import {` loses the brace that opens the
# specifier list. A `}`-only line was already kept on both languages, so keeping
# `{` makes the two halves of a brace pair symmetric rather than adding a rule.
_NORM_TRAILING_BRACE_RE = re.compile(r"\s*\{$")
_NORM_WS_RE = re.compile(r"\s+")
# A complete single- or double-quoted literal, escapes included. Whitespace
# INSIDE one is content and is left exactly as it is: `'a b'` -> `'ab'` is a
# change to what a user sees and must stay visible to this gate.
_NORM_STRING_RE = re.compile(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"")
# A comma sitting immediately before its own closer — `[a,]`, `f(a,)`, `{k:v,}`.
# In both PHP (7.3+/8.0) and JS (ES2017+) that comma is punctuation, not an
# element, and prettier's `trailingComma: "all"` adds one to every construct it
# breaks over lines. It is dropped ONLY when the character before it is neither
# `[` nor `,` — `[,]` is a one-element array with a HOLE and `[a,,]` is a
# two-element one, and erasing either comma would change the value.
_TRAILING_COMMA_BEFORE_CLOSER_RE = re.compile(r"(?<![\[,]),(?=[)\]}])")
# An ELISION — the only two spellings a hole can have once whitespace is gone.
# `[a, , b]` is a three-element array; `[, a]` is two. A region containing
# either is never treated as a re-wrap, and a line containing either never has
# its trailing comma normalised away.
_ELISION_MARKERS = (",,", "[,")
# ASI: the restricted productions. A line terminator after one of these ENDS the
# statement, so `return` + `x` is not `return x`.
_JS_RESTRICTED_TAIL_RE = re.compile(
    r"(?:^|[^A-Za-z0-9_$.])(?:return|throw|break|continue|yield|async)$"
)
# …and the tokens that may not be preceded by a line terminator. `x` + `++y` is
# `x; ++y`, never `x++y`; `x` + `=>y` is not an arrow function at all.
_JS_NO_PRECEDING_BREAK_RE = re.compile(r"^(?:\+\+|--|=>)")

# ---- redundant parentheses (.github#435) ------------------------------------
#
# prettier does not edit the source text, it RE-PRINTS the syntax tree, so every
# parenthesis in its output is one its own precedence table says is needed and
# every parenthesis the author wrote that is not needed is gone. Both directions
# show up in one adoption diff:
#
#     return a || b                ->  return (\n a\n || b\n )   (added: ASI)
#     map[s] || (s || '-')         ->  map[s] || s || '-'        (removed)
#     x = (a && b) ? c : d         ->  x = a && b ? c : d        (removed)
#     x = await f() || {}          ->  x = (await f()) || {}     (added)
#
# Equating those needs PRECEDENCE, which is the one thing #395 refused to reason
# about. It is reasoned about here, conservatively and in one place: a paren pair
# is dropped only when the expression inside it binds STRICTLY TIGHTER than both
# of its neighbours. Strictly, so associativity never enters the argument —
# `a - (b - c)` and `(a - b) - c` are both refused rather than one of them being
# proved. Every construct the table does not recognise is refused too.
#
# The residual risk of a wrong entry is bounded by the caller: the two sides must
# already be character-identical apart from parentheses before this runs, so the
# only edit it could hide is one that changes NOTHING BUT a parenthesis. That is
# a real bug class (a precedence bug), which is why the controls in
# `RedundantParenTest` are all of that exact shape.
_JS_IDENT_CHAR = re.compile(r"[A-Za-z0-9_$]")
# Binding power, higher binds tighter. Longest spelling first — the scanner is
# greedy, so `===` must be tried before `==` and `**` before `*`.
_JS_OPERATORS: tuple[tuple[str, int], ...] = (
    (">>>=", 2), ("**=", 2), ("<<=", 2), (">>=", 2), ("&&=", 2), ("||=", 2),
    ("??=", 2), ("===", 9), ("!==", 9), (">>>", 11),
    ("**", 14), ("==", 9), ("!=", 9), ("<=", 10), (">=", 10), ("&&", 5),
    ("||", 4), ("??", 4), ("<<", 11), (">>", 11), ("+=", 2), ("-=", 2),
    ("*=", 2), ("/=", 2), ("%=", 2), ("&=", 2), ("|=", 2), ("^=", 2),
    ("=>", 2), ("=", 2), ("?", 3), (":", 3), ("|", 6), ("^", 7), ("&", 8),
    ("<", 10), (">", 10), ("+", 12), ("-", 12), ("*", 13), ("/", 13),
    ("%", 13), (",", 1), ("!", 14), ("~", 14),
)
# Word-spelled operators. They are only recognisable while the whitespace is
# still there, which is why the re-wrap comparison runs on a SPACE-COLLAPSED
# variant of each line rather than the space-STRIPPED one used to match lines:
# `'value' in ctx` collapses to `'value' in ctx` but strips to `'value'inctx`,
# where `in` is indistinguishable from the tail of an identifier and its binding
# power of 10 would silently read as a primary's 21.
_JS_WORD_BINARY = {"in": 10, "instanceof": 10}
_JS_WORD_UNARY = {"typeof": 14, "void": 14, "delete": 14, "await": 14}
# A word before `(` that is an OPERATOR rather than a callee, with the binding
# power the parenthesised expression must beat to lose its parentheses.
_JS_PREFIX_WORD_CONTEXT = {
    "return": 0, "case": 0,          # a full Expression, comma operator included
    "of": 2, "else": 2, "do": 2,     # an AssignmentExpression
    "in": 10, "instanceof": 10,
    **_JS_WORD_UNARY,
}
# …and the words that make the parentheses load-bearing outright.
_JS_PREFIX_WORD_REFUSE = {"new", "yield", "function", "class"}
# Nothing may be squeezed against a `)` we are about to delete: `(a || b).c`,
# `(f || g)(x)`, `(a || b)[0]`, `(x)?.y` and `(a)++` all read differently once
# the parentheses are gone. `/` is NOT in this list, though it IS refused on the
# LEFT: a `/` before `(` may open a regular expression, whose parentheses are
# capture groups and not grouping at all, but a `/` after `)` can only be
# division — a regular expression may not follow an operand.
_JS_SUFFIX_REFUSE_CHARS = ".([`"
# TypeScript assertions bind looser than they look: `a || b as string` asserts
# only `b`, so `(a || b) as string` is a different expression and the
# parentheses stay.
_JS_TYPE_ASSERTION_WORDS = {"as", "satisfies"}
# The operators whose re-grouping provably preserves the value, so a pair of
# parentheses may go even at EQUAL binding power. `+` is deliberately absent:
# `1 + (2 + '3')` is `'123'` and `1 + 2 + '3'` is `'33'`.
_JS_ASSOCIATIVE_OPS = {"||", "&&", "??"}
# The binding power of an expression with no top-level operator at all — an
# identifier, a literal, a member/call chain. Nothing binds tighter, so a pair of
# parentheses around one is always removable.
_JS_PRIMARY_PREC = 21
_JS_MAX_PAREN_PASSES = 30
# How many opcodes either side of one the re-wrap comparison may reach for the
# rest of the construct, and the line ceiling that stops it becoming "compare the
# whole file" — see `_js_rewrap_in_context`.
_JS_CONTEXT_REACH = (0, 1, 2, 3, 4)
_JS_CONTEXT_MAX_LINES = 120


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


_JS_BRACKET_PAIR = {"(": ")", "[": "]", "{": "}"}


def _js_scan(text: str) -> tuple[list[bool], list[int]] | None:
    """``(is_literal_char, bracket_depth)`` per character, or ``None`` when the
    text does not scan cleanly — an unterminated quote or a bracket closed by the
    wrong kind. ``None`` means every caller refuses, which is the safe direction.

    A region of a diff is a FRAGMENT, not a program: it routinely opens a brace
    it never closes (``for (…) {`` is one whole opcode) or closes one it never
    opened. Those are tolerated — the depth simply runs on, negative if need be —
    because refusing them was measured to cost 30 of pipelinq#820's findings for
    no safety at all: an unmatched bracket has no pair, so no pair is analysed.

    A template literal is literal text EXCEPT inside ``${…}``, which is ordinary
    expression code and holds parentheses of its own. Both are modelled: the
    ``${`` pushes a brace whose matching ``}`` hands the scanner back to template
    text, so a nested template inside an interpolation nests correctly, and the
    ``in_template`` flag needs no stack of its own.
    """
    n = len(text)
    literal = [False] * n
    depth = [0] * n
    stack: list[str] = []
    level = 0
    in_template = False
    i = 0
    while i < n:
        c = text[i]
        depth[i] = level
        if in_template:
            literal[i] = True
            if c == "\\":
                if i + 1 < n:
                    literal[i + 1] = True
                    depth[i + 1] = level
                i += 2
                continue
            if c == "`":
                in_template = False
                i += 1
                continue
            if text[i:i + 2] == "${":
                # The `{` is pushed like any other bracket, so the
                # interpolation's own brackets nest and its `}` is what hands
                # the scanner back to template text.
                depth[i + 1] = level
                stack.append("${")
                level += 1
                in_template = False
                i += 2
                continue
            i += 1
            continue
        if c in "'\"":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            if j >= n:
                return None
            for k in range(i, j + 1):
                literal[k] = True
                depth[k] = level
            i = j + 1
            continue
        if c == "`":
            literal[i] = True
            in_template = True
            i += 1
            continue
        if c in "([{":
            stack.append(c)
            level += 1
        elif c in ")]}":
            if stack and stack[-1] == "${":
                if c != "}":
                    return None
                stack.pop()
                level -= 1
                depth[i] = level
                # NOT marked literal: it is the interpolation's delimiter, and a
                # `)` that ends right before it has to be able to see a closer on
                # its right rather than "a string follows, refuse".
                in_template = True
                i += 1
                continue
            if stack:
                if _JS_BRACKET_PAIR[stack[-1]] != c:
                    return None
                stack.pop()
            level -= 1
            depth[i] = level
        i += 1
    return (literal, depth) if not in_template else None


def _js_word_at(text: str, end: int) -> str:
    """The identifier ending at ``end`` (exclusive), or ``""``."""
    start = end
    while start > 0 and _JS_IDENT_CHAR.match(text[start - 1]):
        start -= 1
    return text[start:end]


def _js_operator_ending_at(text: str, end: int) -> int | None:
    """Binding power of the symbolic operator ending at ``end`` (exclusive)."""
    if text[end - 2:end] in ("++", "--"):
        return None
    for spelling, prec in _JS_OPERATORS:
        if text[:end].endswith(spelling):
            return prec
    return None


def _js_operator_starting_at(text: str, start: int) -> int | None:
    """Binding power of the symbolic operator starting at ``start``."""
    if text[start:start + 2] in ("++", "--"):
        return None
    for spelling, prec in _JS_OPERATORS:
        if text.startswith(spelling, start):
            return prec
    return None


def _js_inner_binding(inner: str, at_statement_start: bool) -> tuple[int, set[str]] | None:
    """``(lowest binding power holding ``inner`` together, its top-level operator
    spellings)``, or ``None`` when the expression is one this analysis refuses to
    reason about.

    Every top-level operator counts, prefix ones included — ``(-a) * b`` is read
    as bound by ``-`` at 12, so it loses to ``*`` at 13 and keeps its
    parentheses. Over-counting like that can only ever make the answer smaller,
    and a smaller answer only ever refuses.
    """
    scanned = _js_scan(inner)
    if scanned is None:
        return None
    literal, depth = scanned
    stripped = inner.strip()
    if not stripped:
        return None
    # An object literal, a function or a class expression AT THE HEAD OF A
    # STATEMENT: there the parentheses are what stop it being read as a block or
    # a declaration. In expression position — after `return`, after an operator —
    # `{ a: 1 }[k]` is already an object literal and the parentheses are only
    # grouping, so the refusal would be pure cost.
    if at_statement_start and (stripped[0] == "{" or re.match(r"^(?:function|class)\b", stripped)):
        return None
    # `a++ + b` and `a + ++b` are the same characters once the spaces go, so an
    # increment anywhere in the expression refuses it. Literal-aware, or a CSS
    # class called `badge--off` would refuse every expression mentioning it —
    # which is exactly what it did until pipelinq#820 named the method.
    code_only = "".join("\x00" if lit else ch for lit, ch in zip(literal, inner))
    if "++" in code_only or "--" in code_only:
        return None
    prec = _JS_PRIMARY_PREC
    ops: set[str] = set()
    i = 0
    n = len(inner)
    while i < n:
        if literal[i] or depth[i] > 0:
            i += 1
            continue
        c = inner[i]
        if _JS_IDENT_CHAR.match(c):
            j = i
            while j < n and _JS_IDENT_CHAR.match(inner[j]):
                j += 1
            word = inner[i:j]
            if word in _JS_WORD_BINARY:
                prec = min(prec, _JS_WORD_BINARY[word])
                ops.add(word)
            elif word in _JS_WORD_UNARY:
                prec = min(prec, _JS_WORD_UNARY[word])
                ops.add(word)
            elif word in _JS_TYPE_ASSERTION_WORDS:
                return None
            i = j
            continue
        if c in "'\" ":
            i += 1
            continue
        if c in "([{)]}":
            i += 1
            continue
        spelling = _js_operator_spelling_at(inner, i)
        if spelling is None:
            # `++`, `--`, `.`, `;`, `#`, or anything else unmodelled.
            if c in ".;#":
                i += 1
                continue
            return None
        prec = min(prec, dict(_JS_OPERATORS)[spelling])
        ops.add(spelling)
        i += len(spelling)
    return prec, ops


def _js_removable_paren(text: str, literal: list[bool], depth: list[int]) -> tuple[int, int] | None:
    """The first grouping-parenthesis pair in ``text`` that provably does not
    change the parse. ``None`` when there is none."""
    n = len(text)
    for i in range(n):
        if literal[i] or text[i] != "(":
            continue
        close = _js_matching_close(text, literal, depth, i)
        if close is None:
            continue
        context = _js_left_context(text, literal, i)
        if context is None:
            continue
        left, at_statement_start = context
        right = _js_right_context(text, literal, close)
        if right is None:
            continue
        binding = _js_inner_binding(text[i + 1:close], at_statement_start)
        if binding is None:
            continue
        inner, ops = binding
        if inner > max(left, right):
            return (i, close)
        # EQUAL binding power, but the operator is one whose two groupings are
        # the same value. `a || (b || c)` and `a || b || c` differ only in where
        # a short circuit is written down. Restricted to the three operators for
        # which that is true of ANY operands — `+` is not one of them
        # (`1 + (2 + '3')` is `'123'`, `1 + 2 + '3'` is `'33'`), and neither is
        # floating-point `*`.
        if inner == max(left, right) and ops and ops <= _JS_ASSOCIATIVE_OPS:
            if len(ops) == 1 and _js_neighbour_spellings(text, literal, i, close) <= ops:
                return (i, close)
    return None


def _js_neighbour_spellings(text: str, literal: list[bool], open_at: int, close_at: int) -> set[str]:
    """The symbolic operators immediately left of ``(`` and right of ``)``."""
    out: set[str] = set()
    i = open_at
    while i > 0 and text[i - 1] == " ":
        i -= 1
    for spelling, _ in _JS_OPERATORS:
        if i and not literal[i - 1] and text[:i].endswith(spelling):
            out.add(spelling)
            break
    j = close_at + 1
    while j < len(text) and text[j] == " ":
        j += 1
    if j < len(text) and not literal[j]:
        spelling = _js_operator_spelling_at(text, j)
        if spelling is not None:
            out.add(spelling)
    return out


def _js_operator_spelling_at(text: str, start: int) -> str | None:
    """The symbolic operator starting at ``start``, longest spelling first."""
    if text[start:start + 2] in ("++", "--"):
        return None
    for spelling, _ in _JS_OPERATORS:
        if text.startswith(spelling, start):
            return spelling
    return None


def _js_matching_close(text: str, literal: list[bool], depth: list[int], open_at: int) -> int | None:
    """The ``)`` that closes the ``(`` at ``open_at``, or ``None`` if the
    fragment does not contain it. Depth dipping BELOW the opener's level before a
    candidate is reached means the fragment is malformed there, so the search
    stops rather than pairing across the gap."""
    want = depth[open_at]
    for j in range(open_at + 1, len(text)):
        if literal[j]:
            continue
        if depth[j] < want:
            return None
        if text[j] == ")" and depth[j] == want:
            return j
    return None


def _js_left_context(
    text: str, literal: list[bool], open_at: int,
) -> tuple[int, bool] | None:
    """``(binding power the parenthesised expression must beat on its left, is it
    at the head of a statement)``, or ``None`` to refuse — a call, an unmodelled
    neighbour, or a keyword whose parentheses are part of the syntax rather than
    grouping."""
    i = open_at
    while i > 0 and text[i - 1] == " ":
        i -= 1
    if i == 0:
        # Start of the region: an AssignmentExpression may stand here, and it is
        # the head of a statement.
        return (2, True)
    prev = text[i - 1]
    if literal[i - 1]:
        return None  # a call on a string, or an unmodelled neighbour
    if _JS_IDENT_CHAR.match(prev):
        word = _js_word_at(text, i)
        # A MEMBER whose name happens to spell a keyword is a callee, not an
        # operator. `axios.delete(url)` is a call; reading its `delete` as the
        # unary operator hands the parentheses a binding power of 14 and deletes
        # them, welding `axios.deleteurl`. Found on pipelinq's forecastApi.js.
        if text[:i - len(word)].rstrip(" ").endswith("."):
            return None
        if word in _JS_PREFIX_WORD_REFUSE:
            return None
        if word in _JS_PREFIX_WORD_CONTEXT:
            return (_JS_PREFIX_WORD_CONTEXT[word], False)
        return None  # a callee, or `if` / `for` / `while` / `switch` / `catch`
    if prev in ")]}." and prev != "}":
        return None  # a call, an index, or a member access
    if prev == "}":
        return (2, True)  # the end of the previous block: a statement head
    if prev == "/":
        return None  # a regular expression's own parentheses are capture groups
    if prev == ";":
        return (2, True)
    if prev in "([{,:?":
        return (2, False)
    prec = _js_operator_ending_at(text, i)
    return None if prec is None else (prec, False)


def _js_right_context(text: str, literal: list[bool], close_at: int) -> int | None:
    """Binding power the parenthesised expression must beat on its right."""
    i = close_at + 1
    while i < len(text) and text[i] == " ":
        i += 1
    if i >= len(text):
        return 0
    nxt = text[i]
    if literal[i]:
        # A string cannot follow an operand, so this is the next statement —
        # but a template literal could be a TAGGED template, which is a call.
        return None
    if nxt in _JS_SUFFIX_REFUSE_CHARS or text[i:i + 2] in ("++", "--", "?."):
        return None
    if _JS_IDENT_CHAR.match(nxt):
        word = re.match(r"[A-Za-z0-9_$]+", text[i:]).group(0)
        if word in _JS_WORD_BINARY:
            return _JS_WORD_BINARY[word]
        if word in _JS_TYPE_ASSERTION_WORDS:
            return None
        # `(a) b` is not an expression in any dialect this gate reads, so the
        # word begins the NEXT statement — the region joined two of them. The
        # parenthesised expression therefore ends here, at statement level.
        return 2
    if nxt in ")]},;:":
        return 2
    return _js_operator_starting_at(text, i)


def _js_drop_redundant_parens(text: str) -> str | None:
    """``text`` with every provably-redundant grouping parenthesis removed, or
    ``None`` when it could not be scanned. Applied to BOTH sides, so it is a
    canonical form, not a rewrite of one of them."""
    for _ in range(_JS_MAX_PAREN_PASSES):
        scanned = _js_scan(text)
        if scanned is None:
            return None
        pair = _js_removable_paren(text, *scanned)
        if pair is None:
            return text
        i, j = pair
        text = text[:i] + text[i + 1:j] + text[j + 1:]
    return text


def _normalise_code_line(line: str, is_php: bool = True) -> str | None:
    """A layout-independent key for ``line``, or ``None`` if the line carries no
    code identity at all (blank, a bare docblock ``*``, or — in PHP — a lone
    opening brace).

    Applied to BOTH sides of the comparison, so the only question it answers is
    "are these two lines the same program". What it deliberately equates:

    * brace placement — K&R vs Allman (``.github#395``, and gate-14's ``#391``).
      PHP only; see ``_NORM_TRAILING_BRACE_RE`` for why JS keeps its brace;
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
    return _normalise_line(line, is_php, collapse_whitespace=False)


def _normalise_line(line: str, is_php: bool, collapse_whitespace: bool) -> str | None:
    """The shared body of the two key variants — see ``_normalise_code_line``
    (``collapse_whitespace=False``) and ``_spaced_code_line`` (``True``)."""
    s = line.strip()
    if s == "" or s == "*":
        return None
    if is_php:
        s = _NORM_TRAILING_BRACE_RE.sub("", s)
        if s == "":
            return None
    replacement = " " if collapse_whitespace else ""
    if not is_php and "`" in s:
        masked = _mask_literals_with_scanner(s, replacement)
        if masked is not None:
            return masked
    out: list[str] = []
    pos = 0
    for m in _NORM_STRING_RE.finditer(s):
        out.append(_NORM_WS_RE.sub(replacement, s[pos:m.start()]))
        out.append(_unify_quote_style(m.group(0)))
        pos = m.end()
    out.append(_NORM_WS_RE.sub(replacement, s[pos:]))
    return "".join(out)


def _mask_literals_with_scanner(s: str, replacement: str) -> str | None:
    """``_normalise_line``'s body for a line carrying a TEMPLATE LITERAL.

    ``_NORM_STRING_RE`` knows about ``'`` and ``"`` only, so a backtick's text
    was being whitespace-stripped like code and ``` `not installed. ` ``` read
    as ``` `not installed.` ```. The scanner marks quasi text as literal and
    ``${…}`` as the code it is, which is exactly the distinction wanted.

    ``None`` when the line does not scan (a fragment, e.g. a Vue attribute split
    across lines), which falls back to the regex — the pre-existing behaviour.
    """
    scanned = _js_scan(s)
    if scanned is None:
        return None
    literal, _ = scanned
    out: list[str] = []
    i = 0
    n = len(s)
    while i < n:
        if not literal[i]:
            j = i
            while j < n and not literal[j]:
                j += 1
            out.append(_NORM_WS_RE.sub(replacement, s[i:j]))
            i = j
            continue
        j = i
        while j < n and literal[j]:
            j += 1
        run = s[i:j]
        out.append(_unify_quote_style(run) if run[:1] in ("'", '"') else run)
        i = j
    return "".join(out)


def _spaced_code_line(line: str, is_php: bool) -> str | None:
    """``_normalise_code_line`` with runs of whitespace COLLAPSED to one space
    instead of removed. Same lines kept, same literals preserved, same brace
    rule — only the JS re-wrap comparison uses it, and only because a word-
    spelled operator (``in``, ``instanceof``, ``typeof``, ``await``) is
    unrecognisable once the spaces around it are gone."""
    return _normalise_line(line, is_php, collapse_whitespace=True)


def _comparison_keys(
    text: str, is_php: bool,
) -> tuple[list[int], list[str], list[str], list[str]]:
    """``(line_numbers, keys, keys_with_trailing_comma_kept, spaced_keys)``.

    Three variants of the same key, index-aligned, because the comparisons below
    want different things from the same line. Line-vs-line, a trailing comma is
    a no-op and must be ignored — php-cs-fixer adds one to every multi-line
    parameter list (2 of procest's 185 findings on its own) and prettier's
    ``trailingComma: "all"`` does the same to every JS construct it breaks.
    Region-vs-region (the re-wrap rule) has to keep it, because there the commas
    are load-bearing punctuation of the joined statement. The JS re-wrap rule
    additionally needs the spaces back, for the reason in ``_spaced_code_line``.

    The JS half of the comma rule (``.github#435``) is refused on any line
    carrying an ELISION marker, because there a comma is an ELEMENT: ``[a, , b]``
    has three entries and ``[a, b]`` has two. Only ONE trailing comma is ever
    dropped, so ``a,,`` can never be reduced to ``a``.
    """
    numbers: list[int] = []
    keys: list[str] = []
    keys_full: list[str] = []
    keys_spaced: list[str] = []
    for i, raw in enumerate(text.splitlines()):
        k = _normalise_code_line(raw, is_php)
        if k is None:
            continue
        numbers.append(i + 1)
        keys_full.append(k)
        keys.append(k[:-1] if k.endswith(",") and _may_drop_trailing_comma(k) else k)
        keys_spaced.append("" if is_php else (_spaced_code_line(raw, is_php) or ""))
    return numbers, keys, keys_full, keys_spaced


def _may_drop_trailing_comma(key: str) -> bool:
    """True if the final comma of ``key`` is punctuation rather than a hole."""
    return not any(marker in key for marker in _ELISION_MARKERS)


def _drop_punctuation_commas(joined: str) -> str:
    """Remove every comma that sits immediately before its own closer."""
    return _TRAILING_COMMA_BEFORE_CLOSER_RE.sub("", joined)


def _js_asi_hazard(region: list[str]) -> bool:
    """True if any line break INSIDE ``region`` is one that JavaScript's
    automatic semicolon insertion gives a meaning to.

    Two directions, and both are needed. A break AFTER a restricted production
    (``return`` / ``throw`` / ``break`` / ``continue`` / ``yield`` / ``async``)
    terminates the statement, so ``return`` + ``buildThing(a)`` returns
    ``undefined`` where the joined line returns the thing. A break BEFORE
    ``++`` / ``--`` / ``=>`` is equally load-bearing in the other direction:
    ``x`` + ``++y`` is two statements and ``x++y`` is not a program at all.
    """
    for i in range(len(region) - 1):
        if _JS_RESTRICTED_TAIL_RE.search(region[i]):
            return True
        if _JS_NO_PRECEDING_BREAK_RE.match(region[i + 1]):
            return True
    return False


def _is_pure_rewrap(base_region: list[str], head_region: list[str]) -> bool:
    """The PHP arm: true if the two regions are the SAME CHARACTERS, distributed
    differently across lines — a line-length reflow such as ``'a '.`` + ``'b'``
    becoming ``'a '`` + ``.'b'``, or a long call broken after an argument.

    Never across a line comment. That restriction is about the one thing a line
    break can do besides layout: END something. A ``//`` runs to the end of its
    line, so inserting a break after one UNCOMMENTS whatever followed and joining
    two lines COMMENTS OUT whatever follows the ``//`` — the same characters, a
    different program. Refusing the rule whenever the region contains a comment
    introducer costs only precision.

    ``.github#435`` gave JS its own arm (``_is_pure_js_rewrap``) rather than a
    branch in here, so that every byte of this function's behaviour — and so of
    the PHP half of #395 — is unchanged. Verified against the pre-#435 checker on
    3,054 real (base, head) PHP file pairs from openregister's history: no
    difference on any of them.
    """
    if not base_region or not head_region:
        return False
    joined_base = "".join(base_region)
    if joined_base != "".join(head_region):
        return False
    return "//" not in joined_base and "#" not in joined_base


def _is_pure_js_rewrap(base_region: list[str], head_region: list[str]) -> bool:
    """The JS/TS/Vue arm of the re-wrap rule (``.github#435``). Both regions are
    ``_spaced_code_line`` keys, NOT the space-stripped ones.

    prettier re-wraps everything it touches — an argument list, an object
    literal, a mustache, a CSS declaration block — adds a trailing comma
    wherever it breaks, and re-prints parentheses from its own precedence table.
    None of that is a changed method, but four JS-specific hazards make "same
    characters, different line breaks" an unsafe test on its own, and each is
    REFUSED rather than reasoned about:

    * a ``//`` anywhere in either region (see ``_is_pure_rewrap``) — including
      one inside a string, e.g. a URL. That is deliberately blunt: this
      normaliser has no parser, and the cost of the bluntness is precision
      while the cost of getting it wrong is a method that changed and was never
      reported;
    * a line break INSIDE a template literal, which is a CHARACTER of the
      resulting string. Detected by the backtick PARITY of each line: if every
      line on both sides carries an even number of backticks then no literal can
      span a break, and an odd count anywhere refuses the whole region. A
      backtick that stays on one line — which is every one prettier produces
      when it breaks an argument list around a URL — is no hazard at all, and
      refusing those outright cost 21 of pipelinq#820's findings;
    * an ELISION marker (``,,`` or ``[,``) anywhere in either region. There a
      comma is an element of an array and the trailing-comma rule must not touch
      it;
    * an ASI-sensitive break — see ``_js_asi_hazard``.

    What survives all four is compared in a canonical form: punctuation commas
    dropped, provably-redundant parentheses dropped, then whitespace removed. A
    region whose parentheses cannot be scanned safely falls back to the
    characters-identical test, which is the pre-#435 behaviour.
    """
    joined_base = " ".join(base_region)
    joined_head = " ".join(head_region)
    for region, joined in ((base_region, joined_base), (head_region, joined_head)):
        if "//" in joined:
            return False
        if any(line.count("`") % 2 for line in region):
            return False
        if any(marker in _NORM_WS_RE.sub("", joined) for marker in _ELISION_MARKERS):
            return False
    if _js_asi_hazard(base_region) or _js_asi_hazard(head_region):
        return False
    return _js_canonical(joined_base) == _js_canonical(joined_head)


def _js_rewrap_in_context(
    base_spaced: list[str], head_spaced: list[str],
    opcodes: list[tuple[str, int, int, int, int]], at: int,
) -> bool:
    """``_is_pure_js_rewrap`` on a window that grows OPCODE BY OPCODE until the
    re-flow fits inside it (``.github#435``).

    One opcode is often not the whole re-wrap. prettier turning::

        return a
            || b

    into::

        return (
            a
            || b
        )

    leaves the ``|| b`` line byte-identical, so ``SequenceMatcher`` calls it
    EQUAL and splits the reflow into two opcodes with an untouched line wedged
    between: a replace that opens a parenthesis it never closes, and a lone
    ``)`` insert. Neither half is analysable alone; together they are one reflow.

    The window therefore grows to whole neighbouring OPCODES, never to a raw line
    count. That is the difference between working and not: the two sides of this
    reflow have different line counts, so "two more lines each" lands the base at
    ``},`` and the head at ``)``, comparing different constructs forever. An
    opcode boundary is a point where base index and head index provably
    correspond, so every window this builds is aligned at both ends.

    Widening can only ever SUPPRESS, never report, and each rung demands full
    canonical equality of a LARGER pair of regions — a stronger claim than the
    last, not a weaker one. Only the head lines of THIS opcode are dropped from
    the scope; the neighbours are re-judged on their own turn.
    """
    for reach in _JS_CONTEXT_REACH:
        lo, hi = max(0, at - reach), min(len(opcodes) - 1, at + reach)
        _, i1, _, j1, _ = opcodes[lo]
        _, _, i2, _, j2 = opcodes[hi]
        if (i2 - i1) > _JS_CONTEXT_MAX_LINES or (j2 - j1) > _JS_CONTEXT_MAX_LINES:
            break
        if _is_pure_js_rewrap(base_spaced[i1:i2], head_spaced[j1:j2]):
            return True
    return False


def _js_canonical(joined: str) -> str:
    """The form two JS regions are compared in: redundant parentheses gone,
    whitespace OUTSIDE a string literal gone, punctuation commas gone. Applied to
    both sides.

    The whitespace is removed literal-by-literal rather than with one blanket
    ``sub`` because the region arrives SPACED — that is the whole point of
    ``_spaced_code_line`` — and a blanket strip would reach inside the literals
    too. ``'not installed. '`` -> ``'not installed.'`` is text a user reads, and
    #395's first rule is that this gate keeps seeing it.
    """
    stripped = _js_drop_redundant_parens(joined)
    if stripped is not None:
        joined = stripped
    scanned = _js_scan(joined)
    if scanned is None:
        # Unscannable — fall back to the regex, which is what the PHP side uses
        # and which cannot see a template literal.
        out: list[str] = []
        pos = 0
        for m in _NORM_STRING_RE.finditer(joined):
            out.append(_NORM_WS_RE.sub("", joined[pos:m.start()]))
            out.append(m.group(0))
            pos = m.end()
        out.append(_NORM_WS_RE.sub("", joined[pos:]))
        return _drop_punctuation_commas("".join(out))
    literal, _ = scanned
    kept = "".join(
        ch for lit, ch in zip(literal, joined) if lit or not ch.isspace()
    )
    return _drop_punctuation_commas(kept)


def _substantively_changed_lines(base_text: str, head_text: str, is_php: bool) -> set[int]:
    """1-based line numbers in ``head_text`` that are not present, unchanged, in
    ``base_text`` once both sides are normalised by ``_normalise_code_line``."""
    _, base_keys, base_full, base_spaced = _comparison_keys(base_text, is_php)
    head_numbers, head_keys, head_full, head_spaced = _comparison_keys(head_text, is_php)
    matcher = SequenceMatcher(None, base_keys, head_keys, autojunk=False)
    opcodes = matcher.get_opcodes()
    changed: set[int] = set()
    for at, (tag, i1, i2, j1, j2) in enumerate(opcodes):
        if tag not in ("replace", "insert"):
            continue
        if is_php:
            if _is_pure_rewrap(base_full[i1:i2], head_full[j1:j2]):
                continue
        elif _js_rewrap_in_context(base_spaced, head_spaced, opcodes, at):
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


def _merge_base(base_ref: str, cwd: Path) -> str:
    """The merge-base of ``base_ref`` and HEAD, or ``base_ref`` itself when it
    cannot be resolved.

    Unresolvable means: ``base_ref`` does not exist in this checkout (a
    shallow clone that never fetched it), or it exists but shares no history
    with HEAD (a shallow clone with ``fetch-depth: 1``, or genuinely unrelated
    histories). ``run-hydra-gates.sh`` is this fleet's actual fail-closed gate
    for that condition — it refuses the whole diff-scoped run (``exit 99``)
    or marks the five DELTA gates, 16 among them, NOT APPLICABLE and NOT
    counted as passing (full-scope mode), before this script is ever invoked.
    By contract ``base_ref`` already shares history with HEAD by the time
    ``run_gate`` runs it. This fallback only matters for a direct/standalone
    invocation that bypasses that guard (a local run, a test), and it is not
    a silent pass even then: falling back to ``base_ref`` itself means every
    caller below compares against THAT tree, and a tree with no shared
    history reads as every line of it deleted and every line of HEAD added —
    a checker built to flag deletions (``spec_tags_removed``) or additions
    (``changed_lines``) reports LOUDLY, not quietly, against a base this
    unrelated. Degrading here rather than raising is what lets a caller that
    does not need this specific comparison (most of ``run_gate``'s loop does
    not touch ``spec_tags_removed`` or ``_git_show`` at all) keep working.
    """
    return _git(["merge-base", base_ref, "HEAD"], cwd).strip() or base_ref


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

    The same is true of `@nextcloud/prettier-config` for JS/TS/Vue
    (`.github#435`). Measured on ConductionNL/pipelinq#820, 324 files: 468
    findings before, 11 after, with `development` at PASS on both sides.
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
        base_commit = _merge_base(base_ref, cwd)
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

    A BEHIND BRANCH MUST NOT INHERIT ANOTHER COMMIT'S REMOVAL. This used to try
    ``base_ref...HEAD`` (merge-base, correct) and, whenever THAT diff contained
    no removed ``@spec`` line, retry ``base_ref`` two-dot (the ref's live tip,
    working-tree diff) — triggered by "found nothing", not by "the first diff
    was unusable". On a branch sitting behind ``base_ref``, the merge-base diff
    is a perfectly good, non-empty answer that legitimately contains zero
    removed tags; the retry nonetheless fired, compared HEAD against
    ``base_ref``'s CURRENT tip, and read every tag a commit merged into
    ``base_ref`` AFTER the branch point as "removed by this PR" — because that
    tag exists at the live tip and not on the (stale) branch.
    Measured: shillinq#938, 28 commits behind `origin/development`, a diff
    touching only 2 `tests/e2e/` files (true scope zero) — 21 methods across
    six controllers, all tagged by an already-merged commit, reported REMOVED.
    Merging development into the branch (closing the gap) made the same run
    report zero.

    Fixed by making the SAME distinction ``changed_lines`` already makes: the
    two-dot form is for the genuinely-uncommitted-diff case (a local run with
    no HEAD commit yet), and it is used only when the correct, merge-base-
    relative diff produced no output at all — never merely because it found
    nothing worth flagging.
    """
    diff = _git(["diff", "-U0", "--diff-filter=ACMRD", f"{base_ref}...HEAD"], cwd)
    if not diff.strip():
        diff = _git(["diff", "-U0", "--diff-filter=ACMRD", base_ref], cwd)
    removed: set[str] = set()
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
    # The "before" snapshot for a stripped file has to be the MERGE BASE, not
    # `base_ref`'s live tip — same reasoning as `changed_lines`' own
    # `base_commit`. `base_ref` (typically `origin/development`) keeps moving
    # after a branch diverges; reading "before" off its current tip mixes in
    # whatever THAT ref did to the file independently of this PR (e.g. a
    # tagged method development added after the branch point reads as
    # "covered before, uncovered now" on a branch that never saw it — a
    # second, subtler face of the same base-drift defect `spec_tags_removed`
    # had).
    merge_base = _merge_base(base_ref, app_dir)
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
            before = _uncovered_in_text(rel, _git_show(merge_base, rel, app_dir))
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
