#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Gate 83 — contract-surface-shift.

A method on a PUBLISHED CONTRACT can be served two ways: DECLARED
(`public function getSchema(): ?string`) or MAGIC (an `@method` docblock tag
routed through `__call()`). Moving a method between those two surfaces is a
BREAKING CHANGE FOR EVERY CONSUMER, and it breaks them with no commit in their
repositories.

The reason is PHPUnit, which picks its mock builder on exactly that
distinction:

    addMethods()   throws CannotUseAddMethodsException  if the method EXISTS
    onlyMethods()  throws CannotUseOnlyMethodsException if it does NOT

So every consumer that doubles the class has hard-coded an assumption about
which surface each method sits on. Declaring a previously-magic method
invalidates every `addMethods()` double of it; deleting a declaration
invalidates every `onlyMethods()` one.

MEASURED, not hypothetical. On 2026-08-15 OpenRegister published its
ObjectService/ObjectEntity interfaces, which forced `getUuid()`,
`getRegister()` and `getSchema()` to be declared. Fallout in repositories that
had not changed a line: opencatalogi 42 errors across all 6 PHPUnit matrix
cells, decidesk 1. Both `development` branches went red on commits that had
passed hours earlier, and the failures surfaced on unrelated dependency PRs,
where they read as those PRs' fault.

WHY THIS GATE LIVES ON THE PRODUCER SIDE. It cannot be written in the consuming
repository. The hydra-gates job checks out exactly two things — the app and the
gates package — so a consumer-side checker has no access to the real class and
would resolve every external double as "unknown". It would report ZERO findings
for the one change that matters, which reads as a pass. The authority for what
is declared lives here, in the repo that owns the class, so the check lives
here too.

FAILS when a method moves between the magic and declared surfaces of a
published-contract class, or is added to / removed from a contract interface,
unless the change carries a reason-bearing annotation:

    @contract-shift <category> — <reason>

Categories are CLOSED: `announced` (consumers told, e.g. an issue or ADR names
them), `internal-only` (the method is not doubled anywhere in the fleet, and
the reason says how that was established), `new-contract` (a brand-new
interface nobody implements or doubles yet).

ALWAYS diff-scoped: this gate is about the MOMENT of the shift. A full-tree
sweep would report every declared method on every contract class forever, which
is a description of the codebase, not a finding.

Exit codes follow the package convention: 0 clean, 1 findings, 3 scope resolved
but selected nothing, 4 not applicable to this repo.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

EXIT_EMPTY_SCOPE = 3      # scope resolved, selected nothing -> runner _skip na
EXIT_NOT_APPLICABLE = 4   # repo publishes no contract -> runner _skip na

VALID_CATEGORIES = {'announced', 'internal-only', 'new-contract'}

# `@method [static] [return-type] name(...)`. The name is the last identifier
# before the opening paren, which is what makes this tolerant of return types
# that carry namespaces, unions or nullable markers.
METHOD_TAG = re.compile(
    r'^\s*\*\s*@method\s+(?:static\s+)?(?:[^\s(]+\s+)?([A-Za-z_]\w*)\s*\(',
    re.MULTILINE)

# A really-declared method. Visibility is required: this gate is about the
# PUBLIC surface a consumer can double, so private/protected are irrelevant and
# `function` inside a closure must not match.
DECLARED = re.compile(
    r'^\s*(?:final\s+|abstract\s+)?public\s+(?:static\s+)?function\s+([A-Za-z_]\w*)\s*\(',
    re.MULTILINE)

# An interface method has no body and no visibility keyword requirement, but
# PSR-12 and this fleet write them public. Matched separately because the
# declaration ends in `;` rather than `{`.
INTERFACE_METHOD = re.compile(
    r'^\s*(?:public\s+)?(?:static\s+)?function\s+([A-Za-z_]\w*)\s*\([^;{]*\)\s*(?::[^;{]+)?;',
    re.MULTILINE)

# `[^\S\n]` — horizontal whitespace ONLY, deliberately not `\s`.
#
# `\s*` matches newlines, so a bare `@contract-shift announced` on its own line
# let the match run past the line end and capture the docblock's closing `*/`
# as the reason. That is a non-empty string, so the no-reason branch never
# fired and the escape hatch was silently open: any bare tag passed. Caught by
# the bare-annotation control, which is the only reason it was ever noticed.
SHIFT_TAG = re.compile(
    r'@contract-shift[^\S\n]+([A-Za-z-]+)[^\S\n]*(?:—|--|-)?[^\S\n]*([^\n]*)')


def git_show(repo: Path, ref: str, path: str) -> str | None:
    """Read a path at a ref. None means the path did not exist there."""
    proc = subprocess.run(
        ['git', '-C', str(repo), 'show', f'{ref}:{path}'],
        capture_output=True, text=True)
    if proc.returncode != 0:
        return None
    return proc.stdout


def changed_php(repo: Path, base: str) -> list[str] | None:
    """PHP files under lib/ changed against base. None means base unresolvable."""
    probe = subprocess.run(
        ['git', '-C', str(repo), 'rev-parse', '--verify', f'{base}^{{commit}}'],
        capture_output=True, text=True)
    if probe.returncode != 0:
        return None
    proc = subprocess.run(
        ['git', '-C', str(repo), 'diff', '--name-only', f'{base}...HEAD'],
        capture_output=True, text=True)
    if proc.returncode != 0:
        return None
    return [p for p in proc.stdout.splitlines()
            if p.startswith('lib/') and p.endswith('.php')]


def contract_interfaces(repo: Path) -> set[str]:
    """Interface short-names published under lib/Contract/."""
    d = repo / 'lib' / 'Contract'
    if not d.is_dir():
        return set()
    return {p.stem for p in d.glob('*Interface.php')}


def is_contract_file(repo: Path, path: str, ifaces: set[str], text: str) -> bool:
    """A contract interface itself, or a class implementing one."""
    if path.startswith('lib/Contract/') and path.endswith('Interface.php'):
        return True
    for name in ifaces:
        if re.search(r'\bimplements\b[^{]*\b' + re.escape(name) + r'\b', text):
            return True
    return False


def surfaces(text: str, is_interface: bool) -> tuple[set[str], set[str]]:
    """(magic, declared) method names for one file's text."""
    magic = set(METHOD_TAG.findall(text))
    if is_interface:
        declared = set(INTERFACE_METHOD.findall(text))
    else:
        declared = set(DECLARED.findall(text))
    # A name on both surfaces is DECLARED: the real method wins at runtime and
    # `__call()` is never reached for it. Treating it as magic would let a
    # declaration hide behind a leftover docblock tag, which is precisely the
    # shape this gate exists to catch.
    return (magic - declared), declared


def _clean_reason(raw: str) -> str:
    """Strip docblock furniture so `*/` alone never counts as a reason."""
    return re.sub(r'(\*/|\*)\s*$', '', raw).strip()


def annotation_for(text: str, method: str) -> tuple[str | None, str]:
    """The @contract-shift category and reason governing `method`, if any.

    Accepted on the method's own docblock or, for a whole-interface change, at
    class level. Searched within the 40 lines preceding the declaration so a
    tag cannot be borrowed from an unrelated member far above.
    """
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if re.search(r'\bfunction\s+' + re.escape(method) + r'\s*\(', line) \
                or re.search(r'@method\b.*\b' + re.escape(method) + r'\s*\(', line):
            window = '\n'.join(lines[max(0, idx - 40):idx + 1])
            m = SHIFT_TAG.search(window)
            if m:
                return m.group(1).strip(), _clean_reason(m.group(2))
    # Class-level tag: governs every shift in the file.
    head = '\n'.join(lines[:60])
    m = SHIFT_TAG.search(head)
    if m:
        return m.group(1).strip(), _clean_reason(m.group(2))
    return None, ''


def main() -> int:
    parser = argparse.ArgumentParser(description='Gate 83 — contract-surface-shift')
    parser.add_argument('repo', nargs='?', default='.')
    parser.add_argument('--base', default=os.environ.get('HYDRA_GATE_BASE_REF', ''))
    parser.add_argument('--all', action='store_true',
                        help='accepted for runner symmetry; this gate is always '
                             'diff-scoped and --all only reports applicability')
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    ifaces = contract_interfaces(repo)
    if not ifaces:
        print('checked 0 contract method(s) — no lib/Contract/*Interface.php, '
              'this repo publishes no contract.')
        return EXIT_NOT_APPLICABLE

    if args.all or not args.base:
        # WIRING, NOT A VERDICT. The runner invokes this to learn whether the
        # checker can run at all; a surface shift is only visible against a
        # base, so there is nothing to judge here and saying so is the honest
        # answer. Printing the terminal summary is what proves it ran.
        print(f'checked 0 contract method(s) [no diff base], '
              f'{len(ifaces)} published interface(s): 0 failure(s)')
        return EXIT_EMPTY_SCOPE

    changed = changed_php(repo, args.base)
    if changed is None:
        # FAIL CLOSED. An unresolvable base is not an empty diff, and reporting
        # it as one would turn a broken scope into a green gate.
        print(f'FAIL  the diff base {args.base!r} does not resolve, so no '
              f'contract surface could be compared. Nothing was gated.')
        print('\nchecked 0 contract method(s) [unresolvable base], '
              '0 published interface(s) compared: 1 failure(s)')
        return 1

    fails: list[str] = []
    checked = 0
    considered = 0

    for path in changed:
        head_text = git_show(repo, 'HEAD', path)
        if head_text is None:
            continue  # deleted in HEAD; a removed file is a different gate's business
        if not is_contract_file(repo, path, ifaces, head_text):
            continue
        considered += 1
        base_text = git_show(repo, args.base, path)
        if base_text is None:
            continue  # brand-new file: nobody can have doubled it yet

        is_iface = path.startswith('lib/Contract/')
        base_magic, base_declared = surfaces(base_text, is_iface)
        head_magic, head_declared = surfaces(head_text, is_iface)

        moved_to_declared = sorted((base_magic & head_declared) - base_declared)
        moved_to_magic = sorted((base_declared & head_magic) - head_declared)
        added_to_iface = sorted(head_declared - base_declared) if is_iface else []
        removed_from_iface = sorted(base_declared - head_declared) if is_iface else []

        events: list[tuple[str, str]] = []
        for m in moved_to_declared:
            events.append((m, f'`{m}()` moved from the MAGIC surface (@method) to a '
                              f'DECLARED method. Every consumer doubling it with '
                              f'addMethods() now throws CannotUseAddMethodsException'))
        for m in moved_to_magic:
            events.append((m, f'`{m}()` moved from a DECLARED method to the MAGIC '
                              f'surface (@method). Every consumer doubling it with '
                              f'onlyMethods() now throws CannotUseOnlyMethodsException'))
        for m in added_to_iface:
            if m in moved_to_declared:
                continue
            events.append((m, f'`{m}()` was ADDED to published interface {Path(path).stem}. '
                              f'Every implementing class must now declare it, so every '
                              f'addMethods() double of it breaks'))
        for m in removed_from_iface:
            events.append((m, f'`{m}()` was REMOVED from published interface '
                              f'{Path(path).stem}, which retracts a method consumers '
                              f'may call and may double with onlyMethods()'))

        for method, detail in events:
            checked += 1
            category, reason = annotation_for(head_text, method)
            if category is None:
                fails.append(
                    f'{path}: {detail}, and the change carries no '
                    f'`@contract-shift <category> — <reason>`. This breaks consumers '
                    f'with no commit in their repositories, so it is declared or it '
                    f'is not made.')
            elif category not in VALID_CATEGORIES:
                fails.append(
                    f'{path}: `@contract-shift {category}` is not one of the closed '
                    f'categories {sorted(VALID_CATEGORIES)}. A fourth needs an ADR '
                    f'amendment, not a new string in a docblock.')
            elif not reason:
                fails.append(
                    f'{path}: `@contract-shift {category}` on `{method}()` carries no '
                    f'reason. The escape hatch is auditable, not silent.')

    for f in fails:
        print(f'FAIL  {f}')

    print(f'\nchecked {checked} contract surface shift(s) [diff vs {args.base}], '
          f'{considered} contract file(s) in scope: {len(fails)} failure(s)')

    if fails:
        return 1
    # A PASS asserted about a surface nothing inspected is not a pass. When the
    # diff touched no contract file at all, say so as NOT APPLICABLE rather than
    # letting the runner print PASS for a gate that judged nothing.
    if considered == 0:
        return EXIT_EMPTY_SCOPE
    return 0


if __name__ == '__main__':
    sys.exit(main())
