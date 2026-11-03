#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""php_attributes: step over PHP 8 attributes when walking up to a docblock.

Several gates walk upward from a method declaration to the docblock above it,
and PHP attributes sit between the two. A line-prefix test (`#[`, `]`, `)]`)
only recognises a one-line attribute. A multi-line one

    /** @spec openspec/... */
    #[McpTool(
        name: 'createTask',
    )] // registered by the scanner
    public function createTask(...)

has argument lines and a closing line that the prefix test does not know, so
the walk stopped on it and an existing docblock read as missing.

``attribute_block_start(lines, end)`` answers structurally instead: it finds
the nearest line at or above ``end`` that opens an attribute (`#[`) and accepts
the span only when, scanned as PHP, it is one or more complete attributes
(brackets balanced outside strings and comments) followed by nothing but
whitespace or a comment, and the last attribute closes on ``lines[end]``. Anything else is not an
attribute and the caller's walk stops as before.
"""

from __future__ import annotations

# The longest attribute span the scan looks back over. Attributes longer than
# this are not recognised and the walk stops there, as it did before.
ATTRIBUTE_LOOKBACK = 200

_OPEN = "([{"
_CLOSE = ")]}"


def _skip_string(text: str, pos: int) -> int:
    """Index just past the quoted string starting at ``text[pos]``."""
    quote = text[pos]
    j = pos + 1
    while j < len(text):
        c = text[j]
        if c == "\\":
            j += 2
            continue
        if c == quote:
            return j + 1
        j += 1
    return len(text)


def _skip_comment(text: str, pos: int) -> int | None:
    """Index just past the comment starting at ``text[pos]``, or None when no
    comment starts there. ``#[`` opens an attribute, not a comment."""
    if text.startswith("/*", pos):
        close = text.find("*/", pos + 2)
        return len(text) if close < 0 else close + 2
    if text.startswith("//", pos) or (text[pos] == "#" and not text.startswith("#[", pos)):
        newline = text.find("\n", pos)
        return len(text) if newline < 0 else newline
    return None


def _match_attribute(text: str, pos: int) -> int | None:
    """``text[pos:]`` starts with ``#[``. Return the index just past the ``]``
    that closes it, or None when it does not close inside ``text``."""
    depth = 0
    j = pos + 1
    while j < len(text):
        c = text[j]
        if c in "'\"":
            j = _skip_string(text, j)
            continue
        skipped = _skip_comment(text, j)
        if skipped is not None:
            j = skipped
            continue
        if c in _OPEN:
            depth += 1
        elif c in _CLOSE:
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    return None


def last_attribute_end(text: str) -> int | None:
    """When ``text`` is one or more complete PHP attributes, optionally
    separated and followed by whitespace and comments, and nothing else,
    return the index just past the last attribute's ``]``. Otherwise None."""
    pos = 0
    last = None
    while pos < len(text):
        c = text[pos]
        if c.isspace():
            pos += 1
            continue
        skipped = _skip_comment(text, pos)
        if skipped is not None:
            pos = skipped
            continue
        if not text.startswith("#[", pos):
            return None
        last = _match_attribute(text, pos)
        if last is None:
            return None
        pos = last
    return last


def attribute_block_start(lines: list[str], end: int) -> int | None:
    """Index of the line opening the attribute(s) that end on ``lines[end]``,
    or None when ``lines[end]`` does not end an attribute.

    ``end`` may itself be the opening line (a one-line attribute). Stacked
    attributes are returned one block at a time: the caller continues its walk
    from the returned index minus one and meets the next block there.
    """
    if end < 0 or "]" not in lines[end]:
        return None
    for k in range(end, max(-1, end - ATTRIBUTE_LOOKBACK), -1):
        if not lines[k].lstrip().startswith("#["):
            continue
        text = "\n".join(lines[k:end + 1])
        last = last_attribute_end(text)
        # The last attribute must close ON lines[end]: a comment line below an
        # attribute (a one-line docblock) is not part of it.
        if last is not None and last > len(text) - len(lines[end]):
            return k
        return None
    return None
