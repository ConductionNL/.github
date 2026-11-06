# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""gate-123 helper library: the five-star file floor.

An app may list files that must stay at SIG's 5-star unit bounds in
`.sig/five-star-files.txt`: repo-relative paths, one per line, blank lines and
`#` comments allowed. Every unit in a listed file must keep

    NLOC <= 15, McCabe <= 5 and at most 2 parameters

and the file must hold no duplicated block of 6 or more code lines (SIG's
6-line windows, compared without whitespace, against every measured file of
the same language and against the file itself). The units are gate 122's
(lizard at its pinned version, through UnitReader), the windows are gate
122's dup_windows().

Lines every file shares are left out of the clone windows: `use`,
`namespace` and import statements (also a multi-line import block), and
comment-only lines such as the `}//end methodName()` marker. In Vue, JS and
TS files also the SFC block tags (`<template>`, `<script setup>`, `</style>`
and the like) and the `export default {` line with its closing `}`.
Everything else counts: a bare `}`, component lists, lifecycle bodies and
template markup included.

Three kinds of unit are exempt from the parameter rule only, detected from the
source and never listed by hand. Size, complexity and clones still apply.
  * A constructor that only wires its dependencies: every parameter is
    promoted (PHP 8, TypeScript), assigned to a property (as is, or one of
    its properties when a services object is unpacked), or passed on to the
    parent constructor, and the body does nothing else.
  * A PHP method that implements a method of an interface in its class's
    `implements` chain, through parent and abstract parent classes and the
    interfaces those extend. Interfaces are read from the repository and from
    the files vendor/composer's autoload maps point at. When a type in the
    chain cannot be read, a method marked `@inheritDoc` or `#[\\Override]`
    counts as implementing it.
  * A public controller method that a `name` entry in appinfo/routes.php
    targets, when every parameter is a path parameter of that one route. A
    parameter that comes from the query, the body or the route's `defaults`
    is not fixed by the path, so the method stays under the rule. `resources`
    entries name no method and do not count.

A listed path that does not exist, is not a measured source file, or that
lizard cannot read fails, so the list stays honest. Removing a path from the
list fails too while the file still exists.

lizard up to 1.25.0 reads Vue, JavaScript and TypeScript unreliably
(terryyin/lizard#549). While the pinned version is one of those, findings in
.vue, .js and .ts files are reported as warnings and never fail.
"""
import os
import re

import check_sig_maintainability as sig

LIST_PATH = ".sig/five-star-files.txt"
BOUNDS = {"nloc": 15, "ccn": 5, "params": 2}
LABEL = {"nloc": "NLOC {v} > 15", "ccn": "McCabe {v} > 5", "params": "{v} parameters > 2"}
JS_LANGS = ("vue", "javascript", "typescript")
LIZARD_JS_UNRELIABLE_THROUGH = (1, 25, 0)
LIZARD_JS_ISSUE = "terryyin/lizard#549"
CONSTRUCTORS = ("__construct", "constructor", "__init__")


# --------------------------------------------------------------------------
# the list
# --------------------------------------------------------------------------

def parse_list(text):
    """The paths of a five-star list, in order, without duplicates."""
    out = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip() if not raw.lstrip().startswith("#") else ""
        if line.startswith("./"):
            line = line[2:]
        if line and line not in out:
            out.append(line)
    return out


def list_at(app, ref):
    """The list committed at `ref`, or None when it has none."""
    rc, out = sig.git(app, "show", f"{ref}:{LIST_PATH}")
    return parse_list(out) if rc == 0 else None


def list_at_head(app):
    path = os.path.join(app, LIST_PATH)
    return parse_list(sig.read_text(path)) if os.path.isfile(path) else None


def list_present(app, base_ref):
    if os.path.isfile(os.path.join(app, LIST_PATH)):
        return True
    return bool(base_ref) and sig.git(app, "cat-file", "-e", f"{base_ref}:{LIST_PATH}")[0] == 0


def js_reliable(version=None):
    """Whether lizard `version` (the pinned one by default) reads Vue, JS and TS reliably."""
    parts = tuple(int(x) for x in re.findall(r"\d+", version or sig.LIZARD_VERSION)[:3])
    return parts > LIZARD_JS_UNRELIABLE_THROUGH


# --------------------------------------------------------------------------
# the constructor exemption
# --------------------------------------------------------------------------

PHP_STRING_OR_COMMENT = re.compile(
    r"""'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*"|/\*.*?\*/|//[^\n]*|#(?!\[)[^\n]*""", re.S)


def _strip_comments(src, lang):
    if lang == "php":
        return PHP_STRING_OR_COMMENT.sub(lambda m: m.group(0) if m.group(0)[0] in "'\"" else " ", src)
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"//[^\n]*", "", src)
    if lang == "python":
        src = re.sub(r"#[^\n]*", "", src)
    return src


def _close(src, i, opening="(", closing=")"):
    """Index of the bracket that closes the one at `i`, or -1."""
    depth = 0
    for j in range(i, len(src)):
        if src[j] == opening:
            depth += 1
        elif src[j] == closing:
            depth -= 1
            if depth == 0:
                return j
    return -1


def _split_top(text, seps):
    """`text` split at any char of `seps` outside brackets."""
    out, depth, cur = [], 0, []
    for ch in text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if depth == 0 and ch in seps:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur))
    return [s.strip() for s in out if s.strip()]


def _params(ptext, lang):
    """[(name, promoted)] of a parameter list."""
    out = []
    for piece in _split_top(ptext, ","):
        piece = re.sub(r"#\[.*?\]", "", piece, flags=re.S).strip()
        promoted = bool(re.match(r"(public|protected|private|readonly)\b", piece))
        if lang == "php":
            m = re.search(r"\$(\w+)", piece)
        else:
            piece = re.sub(r"^((public|protected|private|readonly)\s+)+", "", piece)
            m = re.match(r"[*\s]*(\w+)", piece)
        if m and not (lang == "python" and m.group(1) in ("self", "cls")):
            out.append((m.group(1), promoted))
    return out


ASSIGN = re.compile(r"^(?:\$this->|this\.|self\.)(\w+)\s*=\s*\$?(\w+)(?:(?:->|\??\.)\w+)*$")
FORWARD = re.compile(r"^(?:parent::__construct|super\(\)\.__init__|super)\s*\((.*)\)$", re.S)


def is_wiring_constructor(unit, source, lang):
    """Whether `unit` is a constructor that only wires dependencies: every
    parameter is promoted, assigned to a property (as is, or one of its
    properties when a services object is unpacked), or passed on to the parent
    constructor (named arguments too), and the body holds nothing else."""
    if re.split(r"::|\.", unit["name"])[-1] not in CONSTRUCTORS:
        return False
    lines = source.splitlines()
    src = _strip_comments("\n".join(lines[unit["start"] - 1:unit["end"]]), lang)
    name = re.search(r"\b(__construct|constructor|__init__)\s*\(", src)
    if not name:
        return False
    open_at = name.end() - 1
    close_at = _close(src, open_at)
    if close_at < 0:
        return False
    params = _params(src[open_at + 1:close_at], lang)
    rest = src[close_at + 1:]
    if lang == "python":
        colon = rest.find(":")
        body, seps = (rest[colon + 1:] if colon >= 0 else None), ";\n"
    else:
        brace = rest.find("{")
        end = _close(rest, brace, "{", "}") if brace >= 0 else -1
        body, seps = (rest[brace + 1:end] if end > 0 else None), (";" if lang == "php" else ";\n")
    if body is None:
        return False
    names = {n for n, _p in params}
    wired = {n for n, promoted in params if promoted}
    for stmt in _split_top(body, seps):
        stmt = " ".join(stmt.split())
        m = ASSIGN.match(stmt)
        if m and m.group(2) in names:
            wired.add(m.group(2))
            continue
        f = FORWARD.match(stmt)
        args = [re.sub(r"^\w+\s*:\s*", "", a).lstrip(".").lstrip("$")
                for a in _split_top(f.group(1), ",")] if f else None
        if f and all(a in names for a in args):
            wired.update(args)
            continue
        return False
    return wired == names


# --------------------------------------------------------------------------
# the interface exemption (PHP)
# --------------------------------------------------------------------------

PHP_NAMESPACE = re.compile(r"^\s*namespace\s+([\w\\]+)\s*;", re.M)
PHP_USE = re.compile(r"^\s*use\s+\\?([\w\\]+)(?:\s+as\s+(\w+))?\s*;", re.M)
PHP_GROUP_USE = re.compile(r"^\s*use\s+\\?([\w\\]+)\\\{([^}]*)\}\s*;", re.M)
PHP_TYPE = re.compile(r"\b(?:(?:abstract|final|readonly)\s+)*(class|interface)\s+(\w+)\s*"
                      r"(?:extends\s+([\w\\,\s]+?))?\s*(?:implements\s+([\w\\,\s]+?))?\s*\{", re.S)
PHP_FUNCTION = re.compile(r"\bfunction\s+&?\s*(\w+)\s*\(")
PSR4_ENTRY = re.compile(r"'((?:[^'\\]|\\.)*)'\s*=>\s*array\((.*?)\),")
CLASSMAP_ENTRY = re.compile(r"'((?:[^'\\]|\\.)*)'\s*=>\s*\$(vendorDir|baseDir)\s*\.\s*'([^']*)'")
DIR_ENTRY = re.compile(r"\$(vendorDir|baseDir)\s*\.\s*'([^']*)'")
INHERITS_MARK = re.compile(r"@inheritdoc|#\[\\?Override\]", re.I)


def php_types_of(text):
    """{fully qualified name: {"kind", "extends", "implements", "methods"}} of
    the classes and interfaces one PHP file declares, names resolved through
    its namespace and `use` imports."""
    code = _strip_comments(text, "php")
    m = PHP_NAMESPACE.search(code)
    ns = m.group(1) if m else ""
    alias = {}
    for g in PHP_GROUP_USE.finditer(code):
        for part in g.group(2).split(","):
            bits = part.split()
            if bits:
                alias[bits[-1].split("\\")[-1]] = g.group(1) + "\\" + bits[0]
    for u in PHP_USE.finditer(code):
        alias[u.group(2) or u.group(1).split("\\")[-1]] = u.group(1)

    def resolve(name):
        name = name.strip()
        if name.startswith("\\"):
            return name[1:]
        head, _, tail = name.partition("\\")
        if head in alias:
            return alias[head] + ("\\" + tail if tail else "")
        return f"{ns}\\{name}" if ns else name

    def names(group):
        return [resolve(n) for n in (group or "").split(",") if n.strip()]

    out = {}
    for t in PHP_TYPE.finditer(code):
        brace = t.end() - 1
        end = _close(code, brace, "{", "}")
        body = code[brace + 1:end] if end > 0 else ""
        kind = t.group(1)
        out[resolve(t.group(2))] = {
            "kind": kind,
            "extends": names(t.group(3)),
            "implements": names(t.group(4)),
            "methods": set(PHP_FUNCTION.findall(body)) if kind == "interface" else set(),
        }
    return out


class PhpTypes:
    """The PHP classes and interfaces of the repository, plus those composer's
    autoload files (vendor/composer) can locate on disk. Read lazily."""

    def __init__(self, app):
        self.app = app
        self.types = None
        self.psr4, self.classmap = [], {}

    def _load(self):
        self.types = {}
        for rel in sig.tracked_files(self.app):
            if rel.lower().endswith(".php") and os.path.isfile(os.path.join(self.app, rel)):
                self.types.update(php_types_of(sig.read_text(os.path.join(self.app, rel))))
        composer = os.path.join(self.app, "vendor", "composer")
        dirs = {"vendorDir": os.path.join(self.app, "vendor"), "baseDir": self.app}
        psr4 = os.path.join(composer, "autoload_psr4.php")
        if os.path.isfile(psr4):
            for m in PSR4_ENTRY.finditer(sig.read_text(psr4)):
                prefix = m.group(1).replace("\\\\", "\\")
                for d in DIR_ENTRY.finditer(m.group(2)):
                    self.psr4.append((prefix, dirs[d.group(1)] + d.group(2)))
        classmap = os.path.join(composer, "autoload_classmap.php")
        if os.path.isfile(classmap):
            for m in CLASSMAP_ENTRY.finditer(sig.read_text(classmap)):
                self.classmap[m.group(1).replace("\\\\", "\\")] = dirs[m.group(2)] + m.group(3)

    def get(self, fqcn):
        if self.types is None:
            self._load()
        if fqcn not in self.types:
            paths = [self.classmap[fqcn]] if fqcn in self.classmap else []
            paths += [os.path.join(d, fqcn[len(p):].replace("\\", "/") + ".php")
                      for p, d in self.psr4 if fqcn.startswith(p)]
            for path in paths:
                if os.path.isfile(path):
                    self.types.update(php_types_of(sig.read_text(path)))
                    break
        return self.types.get(fqcn)

    def interface_methods(self, fqcn):
        """(method names of every interface `fqcn` implements, through its
        parents and the interfaces those extend; whether a type in the chain
        could not be read)."""
        methods, unresolved, seen = set(), False, set()
        stack = [(fqcn, False)]
        while stack:
            name, is_iface = stack.pop()
            if name in seen:
                continue
            seen.add(name)
            t = self.get(name)
            if t is None:
                unresolved = unresolved or name != fqcn
                continue
            if t["kind"] == "interface":
                methods |= t["methods"]
                stack += [(n, True) for n in t["extends"]]
            else:
                stack += [(n, False) for n in t["extends"]] + [(n, True) for n in t["implements"]]
        return methods, unresolved


def implements_interface_method(unit, source, types):
    """Whether PHP `unit` (named Class::method) implements a method of an
    interface in its class's `implements` chain. When a type of the chain
    cannot be read, a method marked `@inheritDoc` or `#[\\Override]` counts."""
    if "::" not in unit["name"]:
        return False
    cls, method = unit["name"].rsplit("::", 1)
    fqcn = next((n for n in php_types_of(source) if n.split("\\")[-1] == cls.split("\\")[-1]), None)
    if fqcn is None:
        return False
    methods, unresolved = types.interface_methods(fqcn)
    if method in methods:
        return True
    if not unresolved:
        return False
    lines = source.splitlines()
    head = []
    for n in range(unit["start"] - 2, max(unit["start"] - 40, -1), -1):
        s = lines[n].strip()
        if s and not s.startswith(("*", "/*", "#[")):
            break
        head.append(s)
    return bool(INHERITS_MARK.search("\n".join(head) + "\n" + lines[unit["start"] - 1]))


# --------------------------------------------------------------------------
# the route exemption (PHP)
# --------------------------------------------------------------------------

ROUTES_PATH = "appinfo/routes.php"
PHP_STRING_VALUE = re.compile(r"""['"](\w+)['"]\s*=>\s*(?:'([^']*)'|"([^"]*)")""")
ROUTE_TARGET = re.compile(r"^((?:\w+\\+)*)(\w+)#(\w+)$")
PATH_PARAMETER = re.compile(r"\{(\w+)\}")
HIDDEN_METHOD = re.compile(r"\b(private|protected)\b")


def _php_arrays(code):
    """The text of every PHP array in `code`, nested arrays cut out, so a key
    found in one belongs to that array. Brackets inside strings do not count."""
    mask = re.sub(r"""'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*\"""",
                  lambda m: " " * len(m.group(0)), code, flags=re.S)
    frames = [[]]
    for i, ch in enumerate(mask):
        if ch in "[(":
            frames.append([])
        elif ch in "])":
            if len(frames) > 1:
                yield "".join(frames.pop())
        else:
            frames[-1].append(code[i])


def _camel(name, first_upper):
    """A route name segment as Nextcloud's router maps it: `foo_bar` to
    FooBar or fooBar; a name without underscores keeps its case."""
    parts = name.split("_")
    head = parts[0][:1].upper() + parts[0][1:] if first_upper else parts[0][:1].lower() + parts[0][1:]
    return head + "".join(p[:1].upper() + p[1:] for p in parts[1:])


def routes_of(text):
    """{(controller class, method): [set of path parameters per route]} of the
    `name` and `url` entries of a routes.php. The class is relative to the
    app's Controller namespace: `Settings\\Foo#bar` is in its Settings folder."""
    out = {}
    for entry in _php_arrays(_strip_comments(text, "php")):
        values = {m.group(1): m.group(2) if m.group(2) is not None else m.group(3)
                  for m in PHP_STRING_VALUE.finditer(entry)}
        target = ROUTE_TARGET.match(values.get("name", ""))
        if target and "url" in values:
            folder = re.sub(r"\\+", r"\\", target.group(1))
            key = (folder + _camel(target.group(2), True) + "Controller", _camel(target.group(3), False))
            out.setdefault(key, []).append(set(PATH_PARAMETER.findall(values["url"])))
    return out


class Routes:
    """The routes of the app's appinfo/routes.php. Read lazily."""

    def __init__(self, app):
        self.app = app
        self.table = None

    def paths_of(self, cls, method):
        if self.table is None:
            path = os.path.join(self.app, ROUTES_PATH)
            self.table = routes_of(sig.read_text(path)) if os.path.isfile(path) else {}
        return self.table.get((cls, method), [])


def route_fixes_signature(unit, source, routes):
    """Whether PHP `unit` is a public controller method that a route names as
    its target, with every parameter a path parameter of that one route."""
    if "::" not in unit["name"]:
        return False
    cls, method = unit["name"].rsplit("::", 1)
    short = cls.split("\\")[-1]
    fqcn = next((n for n in php_types_of(source) if n.split("\\")[-1] == short), "")
    paths = routes.paths_of(fqcn.partition("\\Controller\\")[2], method)
    if not paths:
        return False
    lines = source.splitlines()
    src = _strip_comments("\n".join(lines[unit["start"] - 1:unit["end"]]), "php")
    name = re.search(r"\bfunction\s+&?\s*\w+\s*\(", src)
    if not name or HIDDEN_METHOD.search(src[:name.start()]):
        return False
    close_at = _close(src, name.end() - 1)
    params = {n for n, _p in _params(src[name.end():close_at], "php")} if close_at > 0 else set()
    return bool(params) and any(params <= path for path in paths)


# --------------------------------------------------------------------------
# duplication
# --------------------------------------------------------------------------

IMPORT_LINE = {
    "php": re.compile(r"^(use|namespace)\s"),
    "python": re.compile(r"^(import|from)\s"),
}
JS_IMPORT_LINE = re.compile(r"^(import\b|export\s+(\*|\{[^}]*\}?)\s*(from\b|$))")
END_MARKER = re.compile(r"^[\s{}()\[\];,]*(//|#(?!\[)).*$")


SFC_TAG = re.compile(r"^</?(template|script|style)\b[^>]*>$", re.I)
EXPORT_DEFAULT = re.compile(r"^export\s+default\s*\{$")
OBJECT_CLOSE = re.compile(r"^\}\s*;?$")


def _export_default_close(lines, start):
    """Line number of the `}` that closes the `export default {` object opened
    on line `start` (1-based), or None."""
    depth = 0
    for n in range(start, len(lines) + 1):
        s = lines[n - 1]
        depth += s.count("{") - s.count("}")
        if depth == 0:
            return n if OBJECT_CLOSE.match(s.strip()) else None
    return None


def floor_code_lines(text, lang):
    """gate 122's code lines minus the lines that are the same in every file:
    `use`, `namespace` and import statements (also when they span lines), and
    a bracket followed only by a comment, such as `}//end methodName()`. In
    Vue, JS and TS also the SFC block tags (`<template>`, `<script setup>`,
    `</style>` ...) and the `export default {` line with its closing `}`."""
    code = sig.code_lines(text, lang)
    lines = text.splitlines()
    pattern = IMPORT_LINE.get(lang, JS_IMPORT_LINE)
    js = lang in JS_LANGS
    out, depth, skip = set(), 0, set()
    for n in sorted(code):
        s = lines[n - 1].strip()
        opens = s.count("(") + s.count("{") + s.count("[") - s.count(")") - s.count("}") - s.count("]")
        if depth > 0:
            depth += opens
            continue
        if pattern.match(s):
            depth = max(opens, 0)
            continue
        if END_MARKER.match(s) or n in skip:
            continue
        if js and SFC_TAG.match(s):
            continue
        if js and EXPORT_DEFAULT.match(s):
            close = _export_default_close(lines, n)
            if close:
                skip.add(close)
            continue
        out.add(n)
    return out


def duplicated_blocks(app, targets, corpus):
    """{target: [(first line, last line, "other:line")]} of the 6+ line blocks
    in each target that also occur elsewhere: in the target itself or in a file
    of `corpus` ({rel: lang}) of the same language."""
    lines_of, windows = {}, {}
    for rel, lang in corpus.items():
        text = sig.read_text(os.path.join(app, rel))
        lines_of[rel] = text.splitlines()
        windows[rel] = list(sig.dup_windows(lines_of[rel], floor_code_lines(text, lang)))
    where = {}
    for rel in sorted(corpus):
        for _i, key, nums in windows[rel]:
            where.setdefault((corpus[rel], key), []).append((rel, nums[0]))
    out = {}
    for rel in targets:
        blocks = []
        for _i, key, nums in windows.get(rel, []):
            copies = [c for c in where[(corpus[rel], key)] if c != (rel, nums[0])]
            if not copies:
                continue
            if blocks and nums[0] <= blocks[-1][1]:
                blocks[-1][1] = max(blocks[-1][1], nums[-1])
            else:
                blocks.append([nums[0], nums[-1], f"{copies[0][0]}:{copies[0][1]}"])
        out[rel] = [tuple(b) for b in blocks]
    return out


# --------------------------------------------------------------------------
# the verdict
# --------------------------------------------------------------------------

def judge(app, paths, reader, scope=None):
    """(failures, warnings) for the listed `paths`, as lists of message strings.
    Findings in Vue, JS and TS files are warnings while lizard reads them
    unreliably."""
    scope = scope or sig.Scope(app)
    failures, warnings = [], []
    lenient = not js_reliable()
    types = PhpTypes(app)
    routes = Routes(app)
    measured = {}
    for rel in paths:
        full = os.path.normpath(os.path.join(app, rel))
        if os.path.isabs(rel) or not full.startswith(os.path.abspath(app) + os.sep):
            failures.append(f"{rel}: listed in {LIST_PATH} but not a path inside the repository")
        elif not os.path.isfile(full):
            failures.append(f"{rel}: listed in {LIST_PATH} but does not exist; remove it from the list")
        elif not sig.LANG_OF_EXT.get(os.path.splitext(rel)[1].lower()):
            failures.append(f"{rel}: listed in {LIST_PATH} but not a measured source file (php, js, ts, vue, py)")
        else:
            measured[rel] = sig.LANG_OF_EXT[os.path.splitext(rel)[1].lower()]
    if not measured:
        return failures, warnings
    corpus = {f: lg for f, lg in sig.production_files(app, scope).items() if lg in set(measured.values())}
    corpus.update(measured)
    dups = duplicated_blocks(app, sorted(measured), corpus)
    for rel, lang in sorted(measured.items()):
        sink = warnings if lenient and lang in JS_LANGS else failures
        source = sig.read_text(os.path.join(app, rel))
        before = len(reader.skipped)
        units = reader.units(rel, lang, source)
        if len(reader.skipped) > before:
            sink.append(f"{rel}: lizard could not read it, so it cannot be held at 5 stars: "
                        f"{reader.skipped[-1]['reason']}")
            continue
        for u in units:
            for key, bound in BOUNDS.items():
                if u[key] <= bound:
                    continue
                if key == "params" and (is_wiring_constructor(u, source, lang) or (
                        lang == "php" and (implements_interface_method(u, source, types)
                                           or route_fixes_signature(u, source, routes)))):
                    continue
                sink.append(f"{rel}:{u['start']} {u['name']}: {LABEL[key].format(v=u[key])}")
        for first, last, other in dups[rel]:
            sink.append(f"{rel}:{first}-{last}: duplicated block of {sig.DUP_MIN_LINES}+ code lines, "
                        f"same as {other}")
    return failures, warnings


def selected(app, mb, head_list, base_list):
    """The listed paths to judge: all of them without a merge base (full mode);
    with one (diff mode) the listed paths the change touches or adds to the
    list, and every listed path that no longer exists."""
    if not mb:
        return list(head_list)
    touched = set(sig.changed_paths(app, mb))
    added = set(head_list) - set(base_list or [])
    return [p for p in head_list
            if p in touched or p in added or not os.path.isfile(os.path.join(app, p))]


def lowered(app, head_list, base_list):
    """Paths the change removes from the list while the file still exists."""
    return [p for p in (base_list or []) if p not in head_list and os.path.isfile(os.path.join(app, p))]
