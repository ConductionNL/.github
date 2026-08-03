#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""
detect-redundant-controllers.py — flag controller/service methods whose body is
a pure pass-through to OpenRegister's ObjectService.

Per ADR-022 (`apps-consume-or-abstractions`), apps consume OpenRegister CRUD
directly via `useObjectStore` from `@conduction/nextcloud-vue` →
`/apps/openregister/api/objects?register=<app>&schema=<type>`. Wrapping the
generic CRUD in a per-schema controller (`MeetingController::index/create/show/
update/destroy`) plus a per-schema service method (`MeetingService::create/
read/update/delete`) duplicates capability the platform already provides and
ships dead code — observed on decidesk#60 (2026-04-19): 260 lines of
MeetingController + MeetingService CRUD with zero callers from the frontend.

Detection rules (all must hold for a method to be flagged):

  1. The method lives in `lib/Controller/*.php` or `lib/Service/*.php`.
  2. The method's effective body (comments, blank lines, try/catch wrappers,
     log calls, and JSONResponse construction stripped) reduces to ONE call:
     `$this->[a-z]+Service->find|createFromArray|updateFromArray|
     deleteFromId|findObjects` — the canonical ObjectService methods.
  3. The method has no authorization branch (no `requireAdmin`,
     `requireChairOrSecretary`, role check, or per-object ACL beyond what
     OpenRegister enforces by default), no schema-specific validation, and
     no side effects (notifications, transitions, queue jobs).

When (1)+(2)+(3) hold, the route should be deleted; the frontend should hit
OpenRegister directly. Domain methods that LOOK similar but really do
state-machine work (lifecycle transitions, publication, approval flows,
LLM/orchestration) escape the filter because their bodies contain extra
calls that aren't on the allow-list.

Output (one line per redundant method, lib-relative path):

    lib/Controller/MeetingController.php:90 method=index rule=pass-through-to-ObjectService

Exit 0 if no redundant methods. Exit 1 if any. The number of findings is
written as the last line, prefixed with `# count=`, for easy parsing.

Optional `--changed-files=<newline-separated-paths>` filters the scan to
those paths only — used in PR-scoped runs (Phase G).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable

# Methods on OpenRegister's ObjectService that are pure CRUD pass-throughs.
# A method body that calls ONE of these and nothing else of substance is
# a redundant wrapper.
OBJECT_SERVICE_CRUD = (
    "find",
    "findObjects",
    "createFromArray",
    "updateFromArray",
    "deleteFromId",
    "saveObject",  # legacy alias
)

# Calls / constructs that are considered "wrapper noise" — present in any
# controller body but do not constitute domain logic.
WRAPPER_NOISE_PATTERNS = (
    re.compile(r"^\s*$"),                                             # blank lines
    re.compile(r"^\s*//"),                                            # // comments
    re.compile(r"^\s*\*"),                                            # /* … */ continuation
    re.compile(r"^\s*/\*"),                                           # /* opener
    re.compile(r"^\s*\*/"),                                           # */ closer
    re.compile(r"^\s*\{"),                                            # bare {
    re.compile(r"^\s*\}"),                                            # bare }
    re.compile(r"^\s*try\s*\{?"),                                     # try [{]
    re.compile(r"^\s*\}\s*catch\b"),                                  # } catch
    re.compile(r"^\s*throw\s+\$e"),                                   # rethrow
    re.compile(r"^\s*return\s*$"),                                    # bare return
    re.compile(r"\$this->logger->(info|debug|notice|warning|error)"),  # log line
    re.compile(r"^\s*return\s+new\s+JSONResponse"),                   # response wrapping
    re.compile(r"^\s*return\s+\$\w+->jsonSerialize"),                 # entity → array
    re.compile(r"^\s*return\s+\$\w+\s*;"),                            # plain return $var;
    re.compile(r"^\s*return\s+null\s*;"),                             # null on miss
    re.compile(r"^\s*return\s+true\s*;"),                             # true on success
    re.compile(r"^\s*return\s+false\s*;"),                            # false on failure
    re.compile(r"^\s*if\s*\([^)]*===\s*null[^)]*\)\s*\{?\s*$"),        # if (...=== null) {
    re.compile(r"^\s*if\s*\([^)]*===\s*false[^)]*\)\s*\{?\s*$"),       # if (...=== false) {
    # `$objectService = $this->container->get('OCA\OpenRegister\…')`
    # — the canonical "fetch ObjectService from DI container" pattern.
    # It is plumbing, not domain logic.
    re.compile(r"\$\w+\s*=\s*\$this->container->get\(\s*['\"][^'\"]*OpenRegister[^'\"]*['\"]"),
)

# Patterns that, if present in a method body, RESCUE the method from being
# flagged. These signal genuine domain logic (state machines, RBAC beyond
# per-object ACLs, side effects). Conservative — better to under-flag than
# false-positive on a real domain action.
RESCUE_PATTERNS = (
    re.compile(r"requireAdmin\b"),
    re.compile(r"requireChairOrSecretary\b"),
    re.compile(r"isAdmin\s*\("),
    re.compile(r"->\s*transition\s*\("),
    re.compile(r"->\s*publish\s*\("),
    re.compile(r"->\s*approve\s*\("),
    re.compile(r"->\s*forward\s*\("),
    re.compile(r"->\s*generate(Draft|ALV|Report)"),
    re.compile(r"->\s*extractActionItems\b"),
    re.compile(r"->\s*notify\w*\s*\("),
    re.compile(r"->\s*sendMail\s*\("),
    re.compile(r"BackgroundJob\s*\("),
    re.compile(r"\$this->\w+Service->\w+\("),  # any non-objectService call → escape
    re.compile(r"validateAgainst|validateData|validateInput"),
)

# A method whose visible body — minus the wrapper noise above — is exactly
# ONE line matching this pattern is a pass-through. Two shapes:
#   1) `$this->objectService->createFromArray(...)` — service injected via DI.
#   2) `$objectService->createFromArray(...)` — common local-variable name
#      after `$objectService = $this->container->get('OCA\OpenRegister\…')`.
# The `$objectService|$registerService|...` whitelist constrains the
# bare-variable form so we don't catch every random `$x->find()` chain.
OBJECT_SERVICE_CALL_RE = re.compile(
    r"(\$this->[a-zA-Z_]*[Ss]ervice|\$objectService|\$registerService|\$schemaService|\$openRegister)->\b("
    + "|".join(OBJECT_SERVICE_CRUD)
    + r")\s*\("
)

# Method header — captures the method name. Must match `public function NAME(`
# with optional return type after the closing paren.
METHOD_HEADER_RE = re.compile(
    r"^\s*public\s+function\s+(?P<name>\w+)\s*\(",
    flags=re.MULTILINE,
)

# Method names that look like generic CRUD entry points. Only methods
# whose name fits this shape are eligible to be flagged. A method named
# `reviseAgenda` or `publishMinutes` or `submitForApproval` is plainly
# domain logic — even if its body is one ObjectService call with a
# hardcoded state field, the name signals intent. We err on the side of
# not flagging when the name doesn't look CRUD.
CRUD_METHOD_NAMES = {
    "index", "list", "all", "fetchAll", "findAll", "search",
    "show", "get", "read", "fetch", "fetchOne", "find", "findOne", "show$",
    "create", "store", "post", "save", "saveOne",
    "update", "patch", "put", "edit", "modify",
    "delete", "destroy", "remove",
}
CRUD_NAME_RE = re.compile(
    r"^(" + "|".join(re.escape(n) for n in CRUD_METHOD_NAMES) + r")$"
)

# Opt-out marker — a method whose docblock declares `@spec exclude <reason>` is
# intentional facade/adapter plumbing with no standalone contract (the same
# escape hatch gate-16 spec-coverage honours). The receiver regex above matches
# ANY `$this->*Service->` call (incl. legitimate domain services like
# `applicationService`, and the deliberate ObjectServiceMapperAdapter facade),
# so this annotation is how authors declare a flagged pass-through is by design.
SPEC_EXCLUDE_RE = re.compile(r"@spec\s+exclude\b")


def _split_methods(php_source: str):
    """
    Yield (method_name, line_number, body) for every `public function ...`
    method in a PHP file. Body is the raw text between the method's opening
    `{` and matching closing `}` (using brace-depth counting; tolerates
    nested control flow). Line number is the line of the `public function`
    declaration.
    """
    lines = php_source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    for header_match in METHOD_HEADER_RE.finditer(php_source):
        # Locate the line of the header.
        header_pos = header_match.start()
        line_no = next(
            (i for i, off in enumerate(offsets) if off > header_pos),
            len(offsets),
        )

        # Skip past the header to the first `{` that opens the body.
        cursor = header_match.end()
        while cursor < len(php_source) and php_source[cursor] != "{":
            cursor += 1
        if cursor >= len(php_source):
            continue
        body_start = cursor + 1

        # Walk forward, tracking brace depth, until we close the body.
        depth = 1
        cursor = body_start
        in_string: str | None = None  # tracks ' or " when inside a string
        in_line_comment = False
        in_block_comment = False
        while cursor < len(php_source) and depth > 0:
            ch = php_source[cursor]
            nxt = php_source[cursor + 1] if cursor + 1 < len(php_source) else ""
            if in_line_comment:
                if ch == "\n":
                    in_line_comment = False
            elif in_block_comment:
                if ch == "*" and nxt == "/":
                    in_block_comment = False
                    cursor += 1
            elif in_string is not None:
                if ch == "\\":
                    cursor += 1  # skip escaped char
                elif ch == in_string:
                    in_string = None
            else:
                if ch == "/" and nxt == "/":
                    in_line_comment = True
                elif ch == "/" and nxt == "*":
                    in_block_comment = True
                    cursor += 1
                elif ch in ("'", '"'):
                    in_string = ch
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        body_end = cursor
                        yield header_match["name"], line_no, php_source[body_start:body_end]
                        break
            cursor += 1


def _collapse_to_statements(body: str) -> list[str]:
    """
    Collapse a PHP method body to a list of logical statements — one
    per element. Joins continuation lines that span open parentheses or
    brackets (PHP's named-arg formatting routinely splits a single call
    across 4+ lines, which would otherwise inflate the significant-line
    count and mask pass-through bodies).
    """
    statements: list[str] = []
    buf: list[str] = []
    paren_depth = 0
    bracket_depth = 0
    for raw_line in body.splitlines():
        line = raw_line
        # Track paren/bracket depth, ignoring those inside strings.
        in_string: str | None = None
        for i, ch in enumerate(line):
            if in_string is not None:
                if ch == "\\":
                    continue  # actual char check skipped, handled by next iter
                if ch == in_string:
                    in_string = None
                continue
            if ch in ("'", '"'):
                in_string = ch
            elif ch == "(":
                paren_depth += 1
            elif ch == ")":
                paren_depth = max(0, paren_depth - 1)
            elif ch == "[":
                bracket_depth += 1
            elif ch == "]":
                bracket_depth = max(0, bracket_depth - 1)
        buf.append(line)
        # A statement ends when we hit a newline at depth 0. PHP statements
        # also end at `;` — but flushing on every `;` would split inside
        # an open call. Buffer until we close back to depth 0.
        if paren_depth == 0 and bracket_depth == 0:
            statements.append("\n".join(buf).strip())
            buf = []
    if buf:
        statements.append("\n".join(buf).strip())
    return [s for s in statements if s]


def _is_redundant_body(body: str) -> bool:
    """
    Return True if the method body's effective content is one ObjectService
    CRUD call and nothing else.
    """
    object_service_hits = 0
    significant = 0
    for stmt in _collapse_to_statements(body):
        # Wrapper noise patterns are designed for single lines, but the
        # statements come back multi-line when they span paren depth.
        # Test against the FIRST line of each statement (where the noise
        # marker usually lives) AND against the joined form for
        # multi-line statements that begin with e.g. `return new`.
        first_line = stmt.splitlines()[0] if stmt else ""
        if any(p.search(first_line) for p in WRAPPER_NOISE_PATTERNS):
            continue
        if any(p.search(stmt) for p in WRAPPER_NOISE_PATTERNS):
            # `\$this->logger->info(...)` may sit on the second line.
            continue
        if OBJECT_SERVICE_CALL_RE.search(stmt):
            object_service_hits += 1
            significant += 1
            continue
        if any(p.search(stmt) for p in RESCUE_PATTERNS):
            # Real domain logic — escape.
            return False
        # Anything else that survives is significant code.
        significant += 1
    return object_service_hits == 1 and significant == 1


def _method_docblock(src_lines: list[str], header_line_no: int) -> str:
    """
    Return the docblock text immediately preceding a method header (1-based
    ``header_line_no``). Skips PHP 8 attribute lines (``#[...]``) and blank
    lines between the docblock and the header. Returns "" when there is no
    docblock directly above the method.
    """
    i = header_line_no - 2  # 0-based index of the line just above the header
    while i >= 0:
        stripped = src_lines[i].strip()
        if stripped == "" or stripped.startswith("#["):
            i -= 1
            continue
        break
    if i < 0 or not src_lines[i].strip().endswith("*/"):
        return ""
    block: list[str] = []
    while i >= 0:
        block.append(src_lines[i])
        if src_lines[i].lstrip().startswith("/*"):
            break
        i -= 1
    return "\n".join(reversed(block))


def scan_files(
    paths: Iterable[tuple[Path, Path]],
    scope_filter: set[str] | None = None,
) -> list[str]:
    """
    Scan each file pair (absolute_path, display_path) and return one
    finding line per redundant method. The display path is what we print
    (lib-relative); the absolute path is what we open.
    """
    findings: list[str] = []
    for abs_path, display_path in paths:
        if scope_filter is not None and str(display_path) not in scope_filter:
            continue
        try:
            source = abs_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        src_lines = source.splitlines()
        for method_name, line_no, body in _split_methods(source):
            # Only check methods whose name fits a CRUD shape — methods
            # named after a domain action (publishX, transitionY,
            # generateZ) are presumed to be domain logic regardless of
            # body shape, and must not be flagged.
            if not CRUD_NAME_RE.match(method_name):
                continue
            # Honour an explicit `@spec exclude` docblock — intentional
            # facade/adapter plumbing the author has declared out of scope.
            if SPEC_EXCLUDE_RE.search(_method_docblock(src_lines, line_no)):
                continue
            if _is_redundant_body(body):
                findings.append(
                    f"{display_path}:{line_no} method={method_name} "
                    f"rule=pass-through-to-ObjectService"
                )
    return findings


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--changed-files",
        default="",
        help="Newline-separated list of paths in scope (empty = scan all).",
    )
    parser.add_argument(
        "app_dir",
        nargs="?",
        default=".",
        help="App root (defaults to cwd).",
    )
    args = parser.parse_args(argv)

    root = Path(args.app_dir).resolve()
    candidates = list(
        (root / "lib" / sub).glob("*.php")
        for sub in ("Controller", "Service")
    )
    flat_paths = [p for group in candidates for p in group]

    scope_filter: set[str] | None = None
    if args.changed_files.strip():
        scope_filter = {
            line.strip()
            for line in args.changed_files.splitlines()
            if line.strip()
        }

    paired = [(p, p.relative_to(root)) for p in flat_paths]
    findings = scan_files(paired, scope_filter)

    for finding in findings:
        print(finding)
    print(f"# count={len(findings)}")
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
