#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""ADR-083 — OpenRegister is a constructor-injected, runtime-guarded dependency.

Three checks, each able to fail on its own:

  lookup   a ``$this->container->get('OCA\\OpenRegister\\…')`` anywhere under
           ``lib/``. The dependency is real; announcing it as a string hides it
           from the constructor, from the type system, and from tooling.
           Measured 2026-08-14: gate-7 reported 50 findings against pipelinq,
           every one a correctly-delegated endpoint, because the delegation was
           only ever a string literal.

  header   an ``OCA\\OpenRegister\\…`` reference in a class header
           (``extends`` / ``implements``). This is FATAL AT AUTOLOAD, not
           lazily degradable — it takes down every route including the one that
           would have told the admin what is wrong. Constructor injection is
           the safe form precisely because it is resolved on construction.

  frontpage
           the app's default route transitively constructing an
           OpenRegister-dependent class. This is the check that protects the
           promise: an instance without OpenRegister must still reach a start
           screen that explains itself. Measured 2026-08-14, NO app satisfied
           this — including hermiq, whose DashboardController publishes
           ``opencatalogi_available`` and also injects
           ``OCA\\OpenRegister\\Db\\OrganisationMapper``.

Exit codes follow the suite convention:

    0   pass
    1   findings (count them from the ``FAIL`` lines)
    3   empty scope — nothing to inspect, which is a SKIP and not a pass
    4   the app declares no OpenRegister dependency at all

Every run ends with a ``checked N file(s)`` line. A run that stops before it is
a crash, not a clean tree — the runner distinguishes the two on that line.
"""

from __future__ import annotations

import argparse
import os
import re
import sys

# ---------------------------------------------------------------------------
# Source handling
# ---------------------------------------------------------------------------

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
# `(?m)` ONCE, at the start. Repeating it inside the alternation is a
# DeprecationWarning today and a hard error in a later Python — and a checker
# that writes to stderr gets its warning quoted back as a finding by whatever
# captures the log.
_LINE_COMMENT = re.compile(r"(?m)(?<!:)//[^\n]*$|^[ \t]*#[^\n]*$")


def _strip_comments(src: str) -> str:
    """Blank comments, PRESERVING line count and string literals.

    Both properties matter. Line count, because findings name real lines. String
    literals, because the container form IS a string literal — stripping those
    is how the first cut of gate-7's Pattern 2b matched nothing at all.

    Comments must go for the opposite reason: read raw source and a class merely
    NAMED in a docblock qualifies the file, which is a gate switched off by
    prose.
    """
    def _blank(m: re.Match) -> str:
        return re.sub(r"[^\n]", " ", m.group(0))

    return _LINE_COMMENT.sub(_blank, _BLOCK_COMMENT.sub(_blank, src))


_OR_CLASS = r"OCA\\{1,2}OpenRegister\\{1,2}[A-Za-z0-9_\\]+"

# `$this->container->get('OCA\OpenRegister\…')`, and the `\OCA\…::class` form.
_LOOKUP_RE = re.compile(
    r"->\s*get\s*\(\s*['\"]\\?" + _OR_CLASS + r"['\"]"
    r"|->\s*get\s*\(\s*\\?" + _OR_CLASS + r"\s*::\s*class"
)

# A class header naming an OpenRegister type. Matches the declaration line only,
# so a constructor-injected OR type (which is what this ADR ASKS for) is not
# caught here.
_HEADER_RE = re.compile(
    r"(?m)^\s*(?:final\s+|abstract\s+|readonly\s+)*class\s+[A-Za-z0-9_]+"
    r"[^\{]*?\b(?:extends|implements)\b[^\{]*?"
    r"(?P<or>(?:\\?" + _OR_CLASS + r"))"
)

# A file "depends on OpenRegister" when it names the vendor namespace in code —
# an import, a container lookup, or a type reference.
_OR_MENTION_RE = re.compile(r"\\?" + _OR_CLASS)

# `namespace OCA\OpenRegister…` — the file DECLARES itself part of OpenRegister
# rather than depending on it. Used to recognise the OpenRegister app itself,
# where every _OR_MENTION_RE hit is a self-reference and means nothing.
_OR_NAMESPACE_RE = re.compile(r"(?m)^\s*namespace\s+OCA\\OpenRegister\b")

# Constructor-promoted and declared typed properties: `private readonly Foo $bar`
_PROP_TYPE_RE = re.compile(
    r"(?:private|protected|public)\s+(?:readonly\s+)?"
    r"\\?(?P<type>[A-Za-z_][A-Za-z0-9_\\]*)\s+\$[A-Za-z_][A-Za-z0-9_]*"
)


def _php_files(root: str, sub: str = "lib") -> list[str]:
    base = os.path.join(root, sub)
    out: list[str] = []
    for dirpath, _dirs, files in os.walk(base):
        for name in files:
            if name.endswith(".php"):
                out.append(os.path.join(dirpath, name))
    return sorted(out)


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def _line_of(src: str, pos: int) -> int:
    return src.count("\n", 0, pos) + 1


def _rel(root: str, path: str) -> str:
    return os.path.relpath(path, root)


# ---------------------------------------------------------------------------
# Check: lookup
# ---------------------------------------------------------------------------

def _check_lookup(root: str, files: list[str]) -> list[str]:
    findings = []
    for path in files:
        src = _strip_comments(_read(path))
        for m in _LOOKUP_RE.finditer(src):
            findings.append(
                "FAIL %s:%d container lookup of OpenRegister — inject the "
                "dependency as a typed constructor property instead (ADR-083 "
                "rule 1). The class it needs is declared nowhere a reader or a "
                "gate can see it." % (_rel(root, path), _line_of(src, m.start()))
            )
    return findings


# ---------------------------------------------------------------------------
# Check: header
# ---------------------------------------------------------------------------

def _check_header(root: str, files: list[str]) -> list[str]:
    findings = []
    for path in files:
        src = _strip_comments(_read(path))
        for m in _HEADER_RE.finditer(src):
            findings.append(
                "FAIL %s:%d class header references %s — extends/implements "
                "against OpenRegister is FATAL AT AUTOLOAD when the app is "
                "absent, so it takes down the start screen that would explain "
                "the problem. Compose instead (ADR-083 rule 2)."
                % (_rel(root, path), _line_of(src, m.start()), m.group("or"))
            )
    return findings


# ---------------------------------------------------------------------------
# Check: frontpage reachability
# ---------------------------------------------------------------------------

def _class_index(root: str, files: list[str]) -> dict:
    """Map short class name -> file, for types declared under lib/."""
    index: dict = {}
    decl = re.compile(r"(?m)^\s*(?:final\s+|abstract\s+|readonly\s+)*class\s+([A-Za-z0-9_]+)")
    for path in files:
        for m in decl.finditer(_strip_comments(_read(path))):
            index.setdefault(m.group(1), path)
    return index


def _frontpage_controllers(root: str) -> list[str]:
    """Controller short names serving the app's default route.

    Reads appinfo/routes.php for a route whose url is '/' and for the
    #[FrontpageRoute] attribute. Returns [] when neither is present — the caller
    treats that as an empty scope rather than inventing a target.
    """
    names: set = set()
    routes = os.path.join(root, "appinfo", "routes.php")
    src = _strip_comments(_read(routes))
    if src:
        for m in re.finditer(
            r"['\"]name['\"]\s*=>\s*['\"](?P<ctl>[A-Za-z0-9_]+)#[A-Za-z0-9_]+['\"]"
            r"[^\]]*?['\"]url['\"]\s*=>\s*['\"]/['\"]",
            src,
            re.DOTALL,
        ):
            names.add(m.group("ctl"))
        for m in re.finditer(
            r"['\"]url['\"]\s*=>\s*['\"]/['\"][^\]]*?"
            r"['\"]name['\"]\s*=>\s*['\"](?P<ctl>[A-Za-z0-9_]+)#",
            src,
            re.DOTALL,
        ):
            names.add(m.group("ctl"))
    # Attribute routing: #[FrontpageRoute] on a controller method.
    for path in _php_files(root, os.path.join("lib", "Controller")):
        if "FrontpageRoute" in _strip_comments(_read(path)):
            names.add(os.path.basename(path)[: -len(".php")])
    return sorted(
        n if n.endswith("Controller") else n[:1].upper() + n[1:] + "Controller"
        for n in names
    )


def _check_frontpage(root: str, files: list[str]) -> tuple[list[str], int]:
    index = _class_index(root, files)
    targets = _frontpage_controllers(root)
    if not targets:
        return [], 0

    findings = []
    for target in targets:
        start = index.get(target)
        if start is None:
            continue
        # Walk constructor-injected types to a fixpoint, staying inside lib/.
        seen: set = set()
        queue = [start]
        chain: dict = {start: [target]}
        while queue:
            path = queue.pop()
            if path in seen:
                continue
            seen.add(path)
            src = _strip_comments(_read(path))
            if path != start and _OR_MENTION_RE.search(src):
                findings.append(
                    "FAIL %s the default route reaches %s, which depends on "
                    "OpenRegister — via %s. Without OpenRegister the controller "
                    "cannot be constructed, so the start screen 500s instead of "
                    "telling the admin to install it (ADR-083 rule 3)."
                    % (
                        _rel(root, start),
                        _rel(root, path),
                        " -> ".join(chain.get(path, [])),
                    )
                )
                continue
            for m in _PROP_TYPE_RE.finditer(src):
                short = m.group("type").rsplit("\\", 1)[-1]
                nxt = index.get(short)
                if nxt and nxt not in seen:
                    chain[nxt] = chain.get(path, []) + [short]
                    queue.append(nxt)
        # The start file itself naming OpenRegister is the direct case.
        src = _strip_comments(_read(start))
        if _OR_MENTION_RE.search(src):
            findings.append(
                "FAIL %s the default route's own controller references "
                "OpenRegister directly, so it cannot be constructed without it "
                "(ADR-083 rule 3)." % _rel(root, start)
            )
    return findings, len(targets)


# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument(
        "--check",
        choices=["all", "lookup", "header", "frontpage"],
        default="all",
    )
    args = ap.parse_args(argv[1:])
    root = os.path.abspath(args.root)

    if not os.path.isdir(os.path.join(root, "lib")):
        print("no lib/ — this repo has no PHP app tree, so nothing was inspected.")
        print("checked 0 file(s)")
        return 3

    files = _php_files(root)
    if not files:
        print("lib/ contains no PHP files, so nothing was inspected.")
        print("checked 0 file(s)")
        return 3

    # ADR-083 governs how an app depends on OpenRegister. OpenRegister is not
    # such an app, and inside it EVERY file is in the OCA\OpenRegister
    # namespace — so "references OpenRegister" is true of the whole tree and
    # says nothing. Measured 2026-08-14 before this guard: rule 3 reported
    # openregister's own DashboardController twice, purely for naming its own
    # namespace, while the finding text talked about an app that cannot boot
    # without a dependency it *is*.
    #
    # Same boundary gate-7 draws between its Pattern 2 and Pattern 2b, and it
    # is a SKIP rather than a pass: nothing here was judged.
    if any(_OR_NAMESPACE_RE.search(_strip_comments(_read(f))) for f in files):
        print("this IS the OpenRegister app (files declare namespace "
              "OCA\\OpenRegister), so ADR-083 — which governs how OTHER apps "
              "depend on it — has no subject matter here.")
        print("checked %d file(s)" % len(files))
        return 4

    # An app that never mentions OpenRegister has no dependency to shape.
    # Reported as its own code so it can never read as a pass.
    if not any(_OR_MENTION_RE.search(_strip_comments(_read(f))) for f in files):
        print("this app references OpenRegister nowhere under lib/, so ADR-083 "
              "has no subject matter here.")
        print("checked %d file(s)" % len(files))
        return 4

    findings: list[str] = []
    if args.check in ("all", "lookup"):
        findings += _check_lookup(root, files)
    if args.check in ("all", "header"):
        findings += _check_header(root, files)
    frontpage_targets = 0
    if args.check in ("all", "frontpage"):
        fp, frontpage_targets = _check_frontpage(root, files)
        findings += fp

    for line in findings:
        print(line)
    if args.check in ("all", "frontpage") and frontpage_targets == 0:
        print("NOTE: no default route found in appinfo/routes.php and no "
              "#[FrontpageRoute] attribute, so rule 3 inspected nothing.")
    print("checked %d file(s)" % len(files))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
