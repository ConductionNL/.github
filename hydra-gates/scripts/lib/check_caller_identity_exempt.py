#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""check_caller_identity_exempt.py — is a gate-3 caller-identity finding closable?

WHY THIS EXISTS (.github#339)
-----------------------------
gate-3's ``caller-identity-ignored`` rule reports any public method under
``lib/Service`` / ``lib/Controller`` that declares ``$uid`` / ``$callerUid`` /
``$userId`` / ``$caller`` and never references it in its body.  That is
decidesk#45's shape: a builder-generated ``authorize*()`` stub that accepts the
caller and then forgets to check it.

It is ALSO the shape of a correct strategy implementation.  Measured on procest
(``development`` @ ``792fe1f4b``), all three findings the gate produced were of
the second kind::

    lib/Service/Transitions/ChecklistGuard.php:64        method=evaluate param=$userId
    lib/Service/Transitions/RequiredDocumentGuard.php:49 method=evaluate param=$userId
    lib/Service/Transitions/RequiredFieldGuard.php:47    method=evaluate param=$userId

All three implement ``GuardEvaluatorInterface::evaluate(array, array, string
$userId)``.  Two of the five implementors (``RoleGuard``, ``MandaatGuard``) use
the parameter — it is the whole point of those classes.  A guard that asks "is
this required field filled in?" has no business consulting the caller, so the
only edits that silence the gate are deleting the parameter (breaking the
interface and every call site in ``GuardRegistry::evaluateAll()``) or
referencing it pointlessly to get the grep count to 2.  Both make the code
worse; the finding had no closing action.

WHAT MAKES A FINDING EXEMPT
---------------------------
Two conditions, and BOTH must hold.  Either alone is insufficient, and that is
deliberate:

1. **The signature is imposed from outside.**  The declaring class names a
   supertype (``implements`` / ``extends``, transitively) that is resolvable in
   this repository and declares the same method with the same parameter.  This
   is fully mechanical: nothing the author asserts, only what the type graph
   says.  It is what makes the exemption un-sprinklable — a fixer agent cannot
   escape the rule by adding a docblock line, because an invented service
   method has no supertype and there is no legitimate reason to keep an unused
   parameter on one.  You would simply delete it.

2. **The author marked THAT parameter unused.**  The method docblock's
   ``@param`` line for the flagged parameter carries an explicit
   unused / ignored marker, e.g.::

       @param string $userId Current user UID (unused)

   Condition 1 alone would exempt a genuinely gutted implementation: if
   ``RoleGuard`` stopped consulting ``$userId`` tomorrow that is a real defect,
   and it is contract-imposed too.  The marker is what separates "deliberate"
   from "forgot", and it is per-parameter, which
   ``@SuppressWarnings(PHPMD.UnusedFormalParameter)`` is not — that annotation
   is method-wide and cannot name which parameter it excuses.  #339 offered
   both and preferred the PHPMD tag; the per-``@param`` marker is the stricter
   of the two, and procest already carries it on all three findings while
   ``MandaatGuard`` — which carries the PHPMD tag for a DIFFERENT parameter —
   does not.  Keying on the PHPMD tag would have exempted MandaatGuard's
   ``$userId`` for a reason that was never about ``$userId``.

FAIL-CLOSED
-----------
Anything unresolvable is NOT an exemption: a supertype that lives outside this
repository (an OCP interface, a vendored contract) cannot be inspected, so the
finding stands.  Every error path exits non-zero.  A gate helper that cannot
read its input must not answer "exempt".

Usage:
    check_caller_identity_exempt.py --root DIR --file F --line N \\
        --method NAME --param '$userId'

Exit codes:
    0 — EXEMPT: contract-imposed AND explicitly marked unused
    1 — not exempt (report the finding)
    2 — could not decide (report the finding)
"""

import argparse
import os
import re
import sys

# `final class X`, `abstract class X`, `readonly final class X`, `interface X`,
# `trait X` — capture the kind and the name.
TYPE_DECL = re.compile(
    r'^\s*(?:(?:final|abstract|readonly)\s+)*(class|interface|trait)\s+(\w+)\b'
)
UNUSED_MARKER = re.compile(r'\b(?:unused|ignored|not\s+used|no[t]?\s+consulted)\b', re.I)

MAX_DEPTH = 6  # supertype BFS bound; a cycle guard already prevents loops.


def read_lines(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as fh:
        return fh.read().split('\n')


def docblock_above(lines, idx):
    """Return the docblock lines immediately preceding 0-based line `idx`.

    Skips blank lines and PHP 8 attribute lines (`#[NoAdminRequired]`), which
    legitimately sit between a docblock and its signature. Returns [] when the
    preceding non-skippable line is not a docblock terminator.
    """
    i = idx - 1
    while i >= 0 and (lines[i].strip() == '' or lines[i].strip().startswith('#[')):
        i -= 1
    if i < 0 or not lines[i].strip().endswith('*/'):
        return []
    end = i
    while i >= 0 and '/**' not in lines[i]:
        i -= 1
    if i < 0:
        return []
    return lines[i:end + 1]


def param_marked_unused(doc, param):
    """True when the @param line for `param` carries an explicit unused marker."""
    # `@param string $userId ...`, `@param $userId ...`, `@param string|null $userId ...`
    pat = re.compile(r'@param\b[^$]*' + re.escape(param) + r'\b(.*)$')
    for line in doc:
        m = pat.search(line)
        if m and UNUSED_MARKER.search(m.group(1)):
            return True
    return False


def enclosing_type(lines, idx):
    """Nearest type declaration at or above 0-based `idx`.

    Returns (name, supertypes) or (None, []).
    """
    for i in range(idx, -1, -1):
        m = TYPE_DECL.match(lines[i])
        if not m:
            continue
        # The header may wrap across lines; read on until `{` or a blank line.
        header = []
        j = i
        while j < len(lines) and j < i + 12:
            header.append(lines[j])
            if '{' in lines[j]:
                break
            j += 1
        return m.group(2), parse_supertypes(' '.join(header))
    return None, []


def parse_supertypes(header):
    """Short names from `extends A` / `implements B, C` in a type header."""
    names = []
    for kw in ('extends', 'implements'):
        m = re.search(kw + r'\s+([\w\\\s,]+?)(?:\s*\{|\s+implements\b|$)', header)
        if not m:
            continue
        for raw in m.group(1).split(','):
            short = raw.strip().split('\\')[-1].strip()
            if short and short not in names:
                names.append(short)
    return names


def index_types(root):
    """Map short type name -> [file paths] for every PHP type declared under lib/."""
    index = {}
    lib = os.path.join(root, 'lib')
    if not os.path.isdir(lib):
        return index
    for dirpath, _dirnames, filenames in os.walk(lib):
        for fn in filenames:
            if not fn.endswith('.php'):
                continue
            path = os.path.join(dirpath, fn)
            try:
                lines = read_lines(path)
            except OSError:
                continue
            for line in lines:
                m = TYPE_DECL.match(line)
                if m:
                    index.setdefault(m.group(2), []).append(path)
    return index


def declares(path, method, param):
    """True when `path` declares `method` with `param` in its signature.

    Reads the signature region — from `function <method>(` to the first `;` or
    `{` — which is the only place a parameter can appear. `;` = an interface or
    abstract declaration, `{` = a body; both count as declaring the contract.
    """
    try:
        lines = read_lines(path)
    except OSError:
        return False
    start = re.compile(r'\bfunction\s+' + re.escape(method) + r'\s*\(')
    for i, line in enumerate(lines):
        if not start.search(line):
            continue
        sig = []
        for j in range(i, min(i + 20, len(lines))):
            sig.append(lines[j])
            if ';' in lines[j] or '{' in lines[j]:
                break
        if re.search(re.escape(param) + r'\b', ' '.join(sig)):
            return True
    return False


def contract_imposed(root, lines, idx, method, param):
    """True when a resolvable supertype declares `method` with `param`."""
    _name, supers = enclosing_type(lines, idx)
    if not supers:
        return False
    index = index_types(root)
    seen = set()
    frontier = [(s, 0) for s in supers]
    while frontier:
        name, depth = frontier.pop(0)
        if name in seen or depth > MAX_DEPTH:
            continue
        seen.add(name)
        for path in index.get(name, []):
            if declares(path, method, param):
                return True
            # Not here — follow this type's own parents.
            try:
                plines = read_lines(path)
            except OSError:
                continue
            for i, line in enumerate(plines):
                m = TYPE_DECL.match(line)
                if m and m.group(2) == name:
                    header = ' '.join(plines[i:i + 12])
                    for s in parse_supertypes(header):
                        frontier.append((s, depth + 1))
                    break
    return False


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--root', required=True)
    ap.add_argument('--file', required=True)
    ap.add_argument('--line', required=True, type=int, help='1-based signature line')
    ap.add_argument('--method', required=True)
    ap.add_argument('--param', required=True, help='e.g. $userId')
    args = ap.parse_args()

    path = args.file if os.path.isabs(args.file) else os.path.join(args.root, args.file)
    try:
        lines = read_lines(path)
    except OSError as exc:
        print(f'check_caller_identity_exempt: cannot read {path}: {exc}', file=sys.stderr)
        return 2
    idx = args.line - 1
    if idx < 0 or idx >= len(lines):
        print(f'check_caller_identity_exempt: line {args.line} out of range in {path}',
              file=sys.stderr)
        return 2

    if not param_marked_unused(docblock_above(lines, idx), args.param):
        return 1
    if not contract_imposed(args.root, lines, idx, args.method, args.param):
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
