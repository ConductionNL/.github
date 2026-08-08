#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Does a Nextcloud PHP template OWN THE DOCUMENT, or is it a fragment?

WHY THIS EXISTS
---------------
Nextcloud's `OCP\\Template` renderer SUBSTITUTES an app template into core's
own page. A template that emits no `<html>` / `<body>` is a fragment inside a
document core already built — core emitted that page's landmarks, its `lang`
attribute and its skip link long before the template's first byte.

gate-38 was asking every `templates/settings/*.php` in the fleet for a skip
link. Measured: NOT ONE of the 30 app templates in this fleet owns a document
— the typical body is literally `<div id="procest-settings"></div>`, a Vue
mount point — so the finding was universal and its only remedy was to inject
a SECOND "skip to content" anchor ahead of core's real one. A WCAG 2.4.1
regression demanded by a WCAG 2.4.1 gate (#214, #216, #227).

WHY A HELPER AND NOT A GREP
---------------------------
The first cut of this check was `grep -iE '<(html|body)\\b'`, and the very
first fixture it ran against defeated it: the fixture's own explanatory
comment contained the words `<html>`, so a bare mount point was classified as
a page root. That is the gate-64 defect verbatim — a checker that greps a
string literal misses every constant and matches every comment, failing both
ways at once — so the classification is done on EMITTED MARKUP only:

  * `<?php … ?>` regions are removed. Anything inside them is code, a
    docblock or a `//` comment; none of it is markup the browser receives.
  * `<!-- … -->` HTML comments are removed. Commented-out markup ships
    nothing.

Usage:
    php_template_scope.py --owns-document <file>   # exit 0 = owns, 1 = fragment
    php_template_scope.py --classify <file>...     # "<path>: page-root|fragment"
"""
from __future__ import annotations

import re
import sys

# `<?php … ?>` and the short echo form `<?= … ?>`. An unterminated opener runs
# to end of file, which is the language's own rule and the common shape of a
# template whose PHP header is followed by nothing but more PHP.
PHP_BLOCK = re.compile(r'<\?(?:php\b|=)?.*?(?:\?>|\Z)', re.DOTALL | re.IGNORECASE)
HTML_COMMENT = re.compile(r'<!--.*?-->', re.DOTALL)

DOCUMENT_TAG = re.compile(r'<(?:html|body)\b', re.IGNORECASE)


def emitted_markup(src: str) -> str:
    """The template's output shape: PHP regions and HTML comments removed.

    Order matters. Comments are stripped AFTER php blocks, because a `?>`
    inside an HTML comment really does close the block in PHP, and pretending
    otherwise would swallow markup that does ship.
    """
    return HTML_COMMENT.sub(' ', PHP_BLOCK.sub(' ', src))


def owns_document(src: str) -> bool:
    """True when the template emits `<html>` or `<body>` itself.

    Only such a template is rendered outside core's shell, and only such a
    template can carry a bypass mechanism (SC 2.4.1) or a `lang` attribute
    (SC 3.1.1) of its own.
    """
    return bool(DOCUMENT_TAG.search(emitted_markup(src)))


def _read(path: str) -> str:
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def main(argv: list[str]) -> int:
    if len(argv) >= 3 and argv[1] == '--owns-document':
        try:
            return 0 if owns_document(_read(argv[2])) else 1
        except OSError:
            # Unreadable is NOT "fragment". Refuse rather than answer.
            print(f'php_template_scope: cannot read {argv[2]}', file=sys.stderr)
            return 2
    if len(argv) >= 3 and argv[1] == '--classify':
        for path in argv[2:]:
            try:
                kind = 'page-root' if owns_document(_read(path)) else 'fragment'
            except OSError:
                kind = 'unreadable'
            print(f'{path}: {kind}')
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
