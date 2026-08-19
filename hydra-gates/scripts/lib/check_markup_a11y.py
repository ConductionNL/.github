#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Gate-31 (img-alt) and gate-32 (semantic-controls), over MARKUP only.

WHY THIS MOVED OUT OF THE BASH GATES
------------------------------------
Both gates read a file like this::

    _flat=$(tr '\\n' ' ' < "${vue}")
    echo "${_flat}" | grep -oE '<img\\b[^>]*>'

Two defects in three lines, and both were measured live:

1. THE WHOLE FILE IS FLATTENED, so `<script>` and comments are scanned as
   markup. On openbuild ALL THREE gate-31 findings were JSDoc prose —
   ``* @param {Event} e - The `<img>` `error` event`` (#235). On launchpad the
   single finding was a docblock in `<script>` explaining that
   `CnDashboardIcon` resolves a URL to an `<img>` (#220). The finding text was
   the tell: a real tag prints with its attributes, these printed as the bare
   four characters `<img>`.

   gate-32 has the same hole with the opposite sign. On softwarecatalog the
   comment written ABOVE a repaired element — "role/tabindex/keydown rather
   than a bare `<div @click>`" — was itself scored as the bad element, and
   REWORDING THE COMMENT cleared the gate with the markup byte-identical
   (#236). A gate a comment can clear is a gate a comment can also defeat.

2. `[^>]*` ENDS THE ELEMENT AT THE FIRST `>`, which in Vue is very often the
   arrow of `:reduce="option => option.value"` — gate-12's #236 defect, and
   the same shape as gate-9's `[^)]*` in #198. It is fixed here for all three
   gates at once by extracting through `source_scope.iter_open_tags`.

WHAT DOES NOT CHANGE
--------------------
The RULES are untouched — the accepted alt spellings, the required
role/tabindex/key-handler trio, the `<a href>` and `@click.stop` exemptions
are all carried over verbatim from the bash blocks. This changes WHERE the
gate looks, not what it asks, so before/after counts stay comparable and a
drop in findings is attributable to prose leaving the scope.

GATE-35 AND GATE-36 JOINED THEM (2026-08-12)
--------------------------------------------
They were the last two raw greps in the 31–36 family and each failed in one
direction, measured on a purpose-built fixture through the real wrapper.

gate-35 (img-alt-empty-only) was BLIND. Its noun list was `\\b`-anchored::

    grep -qiE '\\b(avatar|photo|thumbnail|picture|...)\\b'

`\\b` is a WORD-character boundary, and `U` is a word character, so
`avatarUrl`, `thumbnailUrl`, `photoUrl` and `pictureUrl` — the four commonest
spellings in a Vue codebase — could not match. A seven-image probe in which
every image was a violation reported **3**. Underscore is a word character
too, so `avatar_url` was invisible for the same reason. The fix TOKENISES the
src expression on camelCase / `_` / `-` / `.` / `/` boundaries and asks for
token EQUALITY. Equality, not substring: `photograph` and `pictures` stay out,
so recall is not bought with noise — which is what an over-broad `<noun>Url`
substring match would have done to code that is fine.

gate-36 (tabindex-positive) was NOISY. `grep -rnE` over raw bytes reported

    <!-- never write tabindex="5" here; positive values break focus order -->

as a positive tabindex. That is the gate-32 shape exactly (#236): a comment
documenting the defect scored AS the defect, so the better a team documents
its focus-order rule the redder its repo gets. The fix masks COMMENTS ONLY —
not the markup scope — because a positive tabindex is a property of the
rendered DOM wherever it is emitted from, including `<script>` and PHP code.
Blanking those regions would have narrowed the gate while removing the noise,
which is not a repair.

⚠️ Live fleet exposure of BOTH was zero on 2026-08-12, positive-controlled
across all 18 apps: zero positive tabindex values, and 17 `<img` occurrences
in total (14 real tags; the other 3 are JSDoc prose in openbuild), exactly one
of which carries `alt=""` — docudesk's `uploadIcon`, correctly silent under
both the old rule and the new one. So neither fix closes a live defect. Both
exist because a gate that cries wolf gets its silences believed, and gate-7
spent months reporting 0 IDORs across 18 apps for precisely that reason.

Usage::

    check_markup_a11y.py --rule img-alt|semantic-controls|img-alt-empty-only|tabindex-positive <file> [<file>...]

Prints one finding per line in the shape the bash gates emitted, so the
runner still counts lines. Exits 0 always; the count is the answer and the
exit status is a status (#209 — gate-19 returned its finding count as an exit
byte and 266 was reported as 10).
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from source_scope import (  # noqa: E402
    _OPEN_TAG,
    html_markup_mask,
    iter_open_tags,
    js_comment_mask,
    markup_mask,
    read_text,
)

# --- gate-31 ---------------------------------------------------------------
# `alt=`, `:alt=`, `v-bind:alt=`, `alt-text=` (some Conduction components
# proxy the prop under that name). Carried over unchanged from the bash gate.
ALT_ATTR = re.compile(r'(^|[\s])(:?alt|v-bind:alt|alt-text)=')

# --- gate-32 ---------------------------------------------------------------
NON_SEMANTIC = {
    "div", "span", "a", "p", "li", "article", "section",
    "header", "footer", "aside", "main", "nav",
}
CLICK = re.compile(r'@click|v-on:click')
HREF = re.compile(r'(^|\s)(:?href|v-bind:href)=')
ROLE = re.compile(r'(^|[\s])(:?role|v-bind:role)=')
TABINDEX = re.compile(r'(^|[\s])(:?tabindex|v-bind:tabindex)=')
KEYHANDLER = re.compile(r'@keydown|@keyup|@keypress|v-on:keydown|v-on:keyup|v-on:keypress')
# `@click.stop` with no handler (or an empty one) is event management, not a
# user interaction. opencatalogi's PublicationCard wrappers are the fleet
# example; the bash gate already exempted them.
CLICK_WITH_HANDLER = re.compile(r'@click(\.[a-z]+)*\s*=\s*"[^"]+"|v-on:click(\.[a-z]+)*\s*=\s*"[^"]+"')
CLICK_STOP_BARE = re.compile(r'@click\.stop(\s|/|>|$|=\s*("\s*"|\'\s*\'))')


def _img_alt(path: str, masked: str) -> list[str]:
    out = []
    for tag in iter_open_tags(masked, {"img"}):
        if ALT_ATTR.search(tag.attrs):
            continue
        out.append(f"{path}:{tag.line}: {tag.flat}")
    return out


def _semantic_controls(path: str, masked: str) -> list[str]:
    out = []
    for tag in iter_open_tags(masked, NON_SEMANTIC):
        if not CLICK.search(tag.attrs):
            continue
        if tag.name == "a" and HREF.search(tag.attrs):
            continue
        if CLICK_STOP_BARE.search(tag.attrs) and not CLICK_WITH_HANDLER.search(tag.attrs):
            continue
        missing = []
        if not ROLE.search(tag.attrs):
            missing.append("role=")
        if not TABINDEX.search(tag.attrs):
            missing.append("tabindex=")
        if not KEYHANDLER.search(tag.attrs):
            missing.append("@keydown")
        if missing:
            out.append(f"{path}:{tag.line}: {tag.flat} rule=missing[{','.join(missing)}]")
    return out


# --- gate-35 ---------------------------------------------------------------
# A LITERAL empty alt. A BOUND `:alt="x"` is out of scope on purpose (carried
# over from the bash gate): the developer there went through a prop pipeline
# and the value is a reviewer judgement, not a lie told to gate-31.
EMPTY_ALT = re.compile(r'(^|\s)alt\s*=\s*(""|\'\')')
# `:src` / `v-bind:src` carry the noun in a Vue expression; a plain `src`
# carries it in a literal attribute value (`src="/img/avatar.png"`, or a PHP
# template's `src="<?php p($avatarUrl) ?>"`). Both mean the same thing.
SRC_ATTR = re.compile(r'(^|\s)(:src|v-bind:src|src)\s*=\s*("([^"]*)"|\'([^\']*)\')')
# Content nouns. An image the author NAMED after a person or a picture and then
# declared decorative with alt="" is the "I made gate-31 green by lying" shape.
SEMANTIC_NOUNS = frozenset(
    {"avatar", "photo", "thumbnail", "picture", "headshot", "portrait"}
)
# camelCase / PascalCase / SCREAMING_CASE splitting, then every non-alphanumeric
# run is a separator. `avatarUrl` -> {avatar, url}; `AVATAR_URL` -> {avatar,
# url}; `/img/avatar.png` -> {img, avatar, png}; `profilePicture` -> {profile,
# picture}. The `\b`-anchored predicate this replaces could see NONE of the
# camelCase forms and none of the underscore ones either.
_CAMEL_1 = re.compile(r"([a-z0-9])([A-Z])")
_CAMEL_2 = re.compile(r"([A-Z]+)([A-Z][a-z])")
_NON_ALNUM = re.compile(r"[^A-Za-z0-9]+")


def _tokens(text: str) -> set[str]:
    """Lowercased identifier tokens of *text*, split on case and punctuation."""
    spaced = _CAMEL_2.sub(r"\1 \2", _CAMEL_1.sub(r"\1 \2", text))
    return {t for t in _NON_ALNUM.sub(" ", spaced).lower().split() if t}


# NAMED BY CONTEXT. `alt=""` is a lie only when the image is the ONLY thing
# carrying the meaning. Inside an element that takes its accessible name from
# its own text content, an empty alt is the CORRECT answer and the one WCAG
# asks for (H67): the name announced is the sibling text, and giving the image
# its own alt makes assistive technology say the same thing twice.
#
#     <a href="…">
#       <img :src="item.thumbnailUrl" alt="">   <-- decorative, correctly
#       <h4>{{ item.title }}</h4>               <-- THIS names the link
#     </a>
#
# So the noun test still decides WHICH images are suspicious; this decides
# whether the suspicion survives the markup around it. Deliberately narrow:
# only these four elements, and only when the ancestor actually carries text
# besides the image. An `<a>` wrapping nothing but the image is still a
# finding, because then the image IS the link's only possible name.
_NAME_GIVING = frozenset({"a", "button", "label", "figure"})
# DECLARED DECORATIVE, IN THE PLATFORM'S OWN VOCABULARY.
#
# `alt=""` alone is ambiguous — it is what an honest author writes for a
# decorative image AND what a careless one writes to silence gate-31. These
# three are not ambiguous: `role="presentation"` and `role="none"` remove the
# element's semantics, and `aria-hidden="true"` removes it from the
# accessibility tree entirely. An author who writes one of them has made an
# explicit, reviewable accessibility decision, and every assistive technology
# honours it.
#
# This is deliberately NOT a gate-specific opt-out tag. A token invented for a
# linter can be pasted to silence it and means nothing to a browser; these mean
# something to the browser first and to this gate only as a consequence. If the
# author is wrong, the markup is wrong in a way a screen-reader user can
# actually observe — which is the right place for that to be wrong.
_DECORATIVE_DECLARED = re.compile(
    r'(^|\s)(?:role\s*=\s*["\'](?:presentation|none)["\']'
    r'|aria-hidden\s*=\s*["\']true["\'])'
)
# Void elements never nest, so they must not be pushed onto the tag stack.
_VOID_ELEMENTS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})
_TAG_STRIP = re.compile(r"<[^>]*>", re.DOTALL)


def _name_giving_spans(masked: str) -> list[tuple[int, int]]:
    """Content spans of every `_NAME_GIVING` element, innermost last.

    A single forward pass with an explicit stack. Unbalanced markup simply
    never yields a span for the unclosed element, which is the safe direction:
    no span means no exemption means the finding stands.
    """
    stack: list[tuple[str, int]] = []
    spans: list[tuple[int, int]] = []
    for m in _OPEN_TAG.finditer(masked):
        name = m.group(2).lower()
        if m.group(1):                                  # closing tag
            for i in range(len(stack) - 1, -1, -1):
                if stack[i][0] == name:
                    if name in _NAME_GIVING:
                        spans.append((stack[i][1], m.start()))
                    del stack[i:]
                    break
            continue
        if m.group(4) or name in _VOID_ELEMENTS:        # self-closing / void
            continue
        stack.append((name, m.end()))
    return spans


def _named_by_context(masked: str, spans: list[tuple[int, int]],
                      img_start: int, img_end: int) -> bool:
    """True when some name-giving ancestor of the image also carries text."""
    for start, end in spans:
        if not (start <= img_start and img_end <= end):
            continue
        # Everything the ancestor contains EXCEPT this image's own tag. Vue
        # interpolation counts: `{{ item.title }}` renders as the text that
        # names the link.
        inner = masked[start:img_start] + masked[img_end:end]
        if _TAG_STRIP.sub("", inner).strip():
            return True
    return False


def _img_alt_empty_only(path: str, masked: str) -> list[str]:
    out = []
    spans = _name_giving_spans(masked)
    for tag in iter_open_tags(masked, {"img"}):
        if not EMPTY_ALT.search(tag.attrs):
            continue
        m = SRC_ATTR.search(tag.attrs)
        if m is None:
            continue
        value = m.group(4) if m.group(4) is not None else (m.group(5) or "")
        if not (_tokens(value) & SEMANTIC_NOUNS):
            continue
        if _DECORATIVE_DECLARED.search(tag.attrs):
            continue
        if _named_by_context(masked, spans, tag.start, tag.end):
            continue
        out.append(f"{path}:{tag.line}: {tag.flat} rule=empty-alt-on-semantic-bound-src")
    return out


# --- gate-36 ---------------------------------------------------------------
# A QUOTED positive integer. A bound `:tabindex="n"` is reviewer judgement and
# stays out, exactly as the bash gate had it.
TABINDEX_POSITIVE = re.compile(r'(^|[\s>"\'])tabindex\s*=\s*["\']\s*[1-9][0-9]*\s*["\']')
_JS_EXTS = (".js", ".ts", ".mjs", ".cjs", ".jsx", ".tsx")


def _comment_mask(src: str, path: str) -> str:
    """Comments blanked, EVERYTHING ELSE KEPT — offsets preserved.

    Deliberately NOT `markup_mask`. That returns the markup scope, which blanks
    `<script>`, `<style>` and PHP code wholesale; a positive tabindex emitted
    from a render function or from `echo '<div tabindex="5">'` would stop being
    a finding. Removing the false positive must not cost a true one, so only
    comments go: HTML `<!-- -->` plus JS comments inside `<script>` bodies for
    markup files, and JS comments for `.js`/`.ts`. String CONTENTS are kept,
    because for this gate the string IS the evidence (gate-34's lesson).
    """
    if os.path.splitext(path)[1].lower() in _JS_EXTS:
        return js_comment_mask(src)
    return html_markup_mask(src)


def _tabindex_positive(path: str, masked: str) -> list[str]:
    out = []
    for n, line in enumerate(masked.splitlines(), start=1):
        if TABINDEX_POSITIVE.search(line):
            out.append(f"{path}:{n}:{line.rstrip()[:200]}")
    return out


RULES = {
    "img-alt": _img_alt,
    "semantic-controls": _semantic_controls,
    "img-alt-empty-only": _img_alt_empty_only,
    "tabindex-positive": _tabindex_positive,
}

# Rules whose mask is "comments only", not "the markup scope". See _comment_mask.
_COMMENT_SCOPE_RULES = {"tabindex-positive"}


def scan_source(rule: str, path: str, src: str) -> list[str]:
    if rule in _COMMENT_SCOPE_RULES:
        return RULES[rule](path, _comment_mask(src, path))
    return RULES[rule](path, markup_mask(src, path))


def main(argv: list[str]) -> int:
    if len(argv) < 4 or argv[1] != "--rule" or argv[2] not in RULES:
        print(
            "usage: check_markup_a11y.py --rule "
            + "|".join(sorted(RULES))
            + " <file>...",
            file=sys.stderr,
        )
        return 2
    rule = argv[2]
    for path in argv[3:]:
        try:
            src = read_text(path)
        except OSError:
            continue
        for line in scan_source(rule, path, src):
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
