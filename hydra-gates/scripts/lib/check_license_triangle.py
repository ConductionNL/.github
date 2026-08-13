#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Gate-28 license-triangle — every licence a file declares must agree with
the licence the package declares, and with the OTHER declarations in the
same file.

WHY THIS WAS REWRITTEN (ConductionNL/.github#171)
-------------------------------------------------
The shell implementation this replaces did:

    grep -oE '^[[:space:]]*\\*[[:space:]]*@license[[:space:]]+[^[:space:]*]+' \\
        "${_php}" | head -1 | awk '{print $3}'

Two defects, both of which made a GREEN gate-28 mean nothing.

1. **It read only the FIRST `@license` tag and never looked at
   `SPDX-License-Identifier:` at all.** A fleet sweep found **174 files
   declaring BOTH `EUPL-1.2` and an AGPL licence in the same file** —
   launchpad 123, openregister 47, openconnector 4 — and most of them were
   PASSING, because the EUPL tag came first and the SPDX line was invisible.
   Disagreement *within* one file is the stronger signal of the two: it
   means someone edited one declaration and not the other.

2. **A single NUL byte turned a real PASS into a false RED.**
   `shillinq/lib/Service/InventoryValuationReportService.php` carried a raw
   0x00 inside a PHPDoc describing a `sku\\0warehouse` composite key. `file`
   then reported the PHP source as `data`, `grep` switched to binary mode
   and printed `Binary file … matches` instead of the line, and `awk
   '{print $3}'` over THAT read **the file path** as the licence value. The
   header was correct all along. The same idiom is live in
   `doriath/src/import/model.js:117` and
   `openbuild/src/services/manifestValidation/documentAttachments.js:136`,
   so it would have recurred.

   Reading the bytes in Python with `errors='replace'` removes the class:
   there is no binary-mode switch to trip. The `_looks_like_a_path` guard
   below stays anyway, because a "licence value" that is a path is a
   parser malfunction and must be reported as one rather than as a licence
   finding — a wrong answer that names itself is recoverable, a wrong
   answer wearing the right shape is not.

WHAT IS *NOT* A DECLARATION
---------------------------
A licence identifier inside a string literal is test data, not a claim.
nldesign's `MarianneFontTest.php` and `ClaimAccuracyTest.php` assert on
non-EUPL identifiers; "fixing" them breaks the tests. A declaration is
therefore only counted when nothing but comment syntax and whitespace
precedes it on its line — which is true of every real header and false of
every assertion string.

Usage:
    check_license_triangle.py <composer-license-set> <file>...

`<composer-license-set>` is pipe-joined (`EUPL-1.2` or `EUPL-1.2|MIT`),
matching what the runner already computes from composer.json.
"""
from __future__ import annotations

import re
import sys

# A declaration line: only comment syntax and whitespace may precede the tag.
# `* @license EUPL-1.2`, `// SPDX-License-Identifier: EUPL-1.2`,
# `# SPDX-License-Identifier: EUPL-1.2`, `/** @license EUPL-1.2` all count.
# `$this->assertSame('SPDX-License-Identifier: MIT', $x)` does not: a quote
# precedes the tag.
DECL = re.compile(
    r'^[\s]*(?:/\*+|\*+/?|//+|#+|<!--)?[\s]*'
    r'(?:@license|SPDX-License-Identifier:)[\s]+'
    r'([^\s*\'"`;,)\]]+)'
    r'(?P<rest>[^\n]*)',
    re.MULTILINE,
)

# A SENTENCE THAT BEGINS WITH THE TAG IS NOT A SECOND DECLARATION (#415/#423).
#
# The anchor above was already right about position — a quote before the tag
# means test data, not a claim — but it said nothing about what FOLLOWS the
# identifier. So a docblock line explaining a licence the file does NOT use:
#
#     * @license EUPL-1.2
#     * @license MIT was never used here — see the note above.
#
# read as a file declaring two licences, and produced BOTH
# `license-internal-conflict` and `license-triangle-drift`. The note about
# the licence that was ruled out scored as the licence.
#
# THE REMAINDER MAY NOT BE EMPTY, because the fleet's own header is not.
# Measured over every tracked `lib/**/*.php` in openregister, opencatalogi,
# procest, docudesk, larpingapp and softwarecatalog — 2,394 files, every
# distinct declaration form:
#
#     2724  @license EUPL-1.2 https://joinup.ec.europa.eu/…/eupl-text-eupl-12
#     2095  @license EUPL-1.2   (and `SPDX-License-Identifier: EUPL-1.2`)
#       11  @license https://www.gnu.org/licenses/agpl-3.0.html GNU AGPL v3 or later
#        8  @license AGPL-3.0-or-later https://www.gnu.org/licenses/agpl-3.0.en.html
#
# A rule of "nothing may follow the identifier" would have deleted the FIRST
# and most common form — 2,724 real declarations, in the fleet's own house
# style — and the gate would have gone quiet on exactly the files it exists
# to compare. So the remainder is allowed to be a URL, a comment terminator
# or trailing punctuation, and nothing else: those are what a header carries
# and prose is what it does not.
#
# The URL-FIRST form (11 files) is deliberately left alone: its identifier is
# a URL, `_looks_like_a_path` already reports it as a parser malfunction, and
# that diagnostic is not this change's to silence. The rule below therefore
# only applies to a value that is not itself path-shaped.
_DECL_TAIL_OK = re.compile(
    r'^(?:\s|https?://\S+|\*/|--!?>|[.,;:)\]]|\(\s*\)|\s*\Z)*$'
)
# `/` is deliberately ALLOWED in the captured value. Excluding it (to stop
# `@license EUPL-1.2*/` capturing the comment terminator) also truncated a
# path-shaped value to its first segment, so `lib/Service/Thing.php` arrived
# as `lib` and the path guard below never fired — the malfunction would have
# been reported as an ordinary licence drift, sending someone to edit a
# header that was already correct. The terminator is stripped instead.
#
# `--!>` as well as `-->`: HTML5 treats both as a comment terminator, and a
# pattern that knows only one of them is `py/bad-tag-filter`. Nothing here
# sanitises markup — this only trims a terminator off a licence identifier —
# but a half-known comment syntax is a half-known comment syntax, and the
# narrower pattern would silently leave `EUPL-1.2--!` as the "licence".
_TRAILING_COMMENT = re.compile(r'(?:\*/|--!?>)+$')


def _looks_like_a_path(value: str) -> bool:
    """A licence value that is a path is a parse failure, not a licence."""
    return ('/' in value
            or value.endswith(('.php', '.js', '.ts', '.vue', '.json'))
            or value.startswith('.'))


def declarations(src: str) -> list[str]:
    """Every licence identifier this source DECLARES, in order, deduplicated
    while preserving first-seen order."""
    seen: list[str] = []
    for m in DECL.finditer(src):
        v = _TRAILING_COMMENT.sub('', m.group(1).strip()).strip().rstrip('.,;')
        if not v or v in seen:
            continue
        # See _DECL_TAIL_OK: a header carries an identifier and at most a URL;
        # prose after the identifier means the line is a SENTENCE about a
        # licence, not a declaration of one. Path-shaped values keep their
        # existing "parser malfunction" report regardless of what follows.
        if not _looks_like_a_path(v) and not _DECL_TAIL_OK.match(m.group('rest')):
            continue
        seen.append(v)
    return seen


def read_text(path: str) -> str | None:
    """Read a source file as text, immune to embedded NUL bytes.

    Binary mode + `errors='replace'` is the whole fix for defect 2: there is
    no heuristic here that a 0x00 can flip.
    """
    try:
        with open(path, 'rb') as f:
            return f.read().decode('utf-8', errors='replace')
    except OSError:
        return None


def scan_file(path: str, allowed: set[str]) -> list[str]:
    src = read_text(path)
    if src is None:
        return []
    decls = declarations(src)
    if not decls:
        return []

    findings: list[str] = []
    bogus = [d for d in decls if _looks_like_a_path(d)]
    for d in bogus:
        findings.append(
            f"{path} file_license={d} rule=license-value-is-a-path "
            f"(parser malfunction, not a licence claim — report, do not 'fix' the header)")
    real = [d for d in decls if not _looks_like_a_path(d)]

    # The stronger signal first: the file disagrees with ITSELF.
    if len(set(real)) > 1:
        findings.append(
            f"{path} file_licenses={','.join(real)} rule=license-internal-conflict "
            f"(one file declares more than one licence — a green gate here was never evidence)")

    for d in real:
        if d not in allowed:
            findings.append(
                f"{path} file_license={d} composer_license={'|'.join(sorted(allowed))} "
                f"rule=license-triangle-drift")
    return findings


def scan_files(files: list[str], composer_license: str) -> list[str]:
    allowed = {p.strip() for p in composer_license.split('|') if p.strip()}
    if not allowed:
        return []
    out: list[str] = []
    for path in files:
        out.extend(scan_file(path, allowed))
    return out


def declared_file_count(files: list[str]) -> int:
    """How many of *files* actually carried a licence declaration.

    The runner needs this to keep #172's distinction intact: PASS only when
    at least one file was really compared, `structural` when lib/ and a
    composer licence both exist but nothing in scope declared anything. A
    gate that reports PASS having opened zero files is the falsely-GREEN
    shape the coverage block exists to make impossible, and moving the read
    into a helper must not quietly re-create it.
    """
    n = 0
    for path in files:
        src = read_text(path)
        if src is not None and declarations(src):
            n += 1
    return n


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: check_license_triangle.py <composer-license-set> <file>...",
              file=sys.stderr)
        return 2
    files = argv[2:]
    for line in scan_files(files, argv[1]):
        print(line)
    # Findings on stdout, the compared-file count on stderr, so the caller can
    # capture one without parsing it out of the other.
    print(f"declared_files={declared_file_count(files)}", file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
