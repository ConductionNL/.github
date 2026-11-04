#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Resolve the controller names in appinfo/routes.php to the files that serve them.

Usage::

    python3 controller_resolver.py <app-root> <app-namespace> < route-controller-names

Reads one route controller name per line (the part before ``#``) and prints
``<name>\\t<path>`` per name, where ``<path>`` is the tracked PHP file under
``lib/`` that declares the class Nextcloud instantiates for it, or empty when
no such file exists. The last line is ``# resolved <n> of <m>``; a run without
it did not finish.

A name resolves the way Nextcloud resolves it: ``underScoreToCamelCase(ucfirst(name))
. 'Controller'``, looked up as given and under ``<app-namespace>\\Controller\\``.
Each candidate class is then followed through the app's class aliases
(``appinfo/class-aliases.json``, old name => new name) and mapped to a file
through the PSR-4 map in composer.json, with ``<app-namespace>\\`` => ``lib/`` as
the default. A class whose file does not sit at its PSR-4 path is still found
through the ``namespace`` and ``class`` declarations of the files under lib/.
"""
from __future__ import annotations

import json
import os
import re
import sys

NS_RE = re.compile(r"^\s*namespace\s+([A-Za-z0-9_\\]+)\s*;", re.M)
CLASS_RE = re.compile(r"^\s*(?:(?:final|abstract|readonly)\s+)*class\s+([A-Za-z0-9_]+)", re.M)


def psr4_map(root, app_ns):
    """[(prefix, dir)] longest prefix first."""
    pairs = []
    try:
        with open(os.path.join(root, "composer.json"), encoding="utf-8") as fh:
            autoload = json.load(fh).get("autoload", {}).get("psr-4", {})
        for prefix, dirs in autoload.items():
            for d in dirs if isinstance(dirs, list) else [dirs]:
                pairs.append((prefix.rstrip("\\") + "\\", d.rstrip("/") + "/"))
    except (OSError, ValueError, AttributeError):
        pass
    if app_ns and not any(p == app_ns + "\\" for p, _d in pairs):
        pairs.append((app_ns + "\\", "lib/"))
    return sorted(pairs, key=lambda p: len(p[0]), reverse=True)


def class_aliases(root):
    """{old fqcn: new fqcn} from appinfo/class-aliases.json, if the app has one."""
    try:
        with open(os.path.join(root, "appinfo", "class-aliases.json"), encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    entries = data.get("aliases", data) if isinstance(data, dict) else {}
    out = {}
    for old, new in entries.items() if isinstance(entries, dict) else []:
        target = new.get("class") if isinstance(new, dict) else new
        if isinstance(target, str):
            out[old.lstrip("\\")] = target.lstrip("\\")
    return out


def declared_classes(root, files):
    """{fqcn: path} from the namespace and class declarations of `files`."""
    out = {}
    for rel in files:
        try:
            with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        ns = NS_RE.search(text)
        for m in CLASS_RE.finditer(text):
            fqcn = (ns.group(1) + "\\" if ns else "") + m.group(1)
            out.setdefault(fqcn, rel)
    return out


def lib_php_files(root):
    out = []
    for base, dirs, files in os.walk(os.path.join(root, "lib")):
        dirs[:] = [d for d in dirs if d not in ("vendor", "node_modules")]
        out.extend(os.path.relpath(os.path.join(base, f), root) for f in files if f.endswith(".php"))
    return sorted(out)


def controller_class(name):
    """Nextcloud's RouteParser::buildControllerName()."""
    parts = name.split("_")
    camel = parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:])
    return camel[:1].upper() + camel[1:] + "Controller"


class Resolver:
    def __init__(self, root, app_ns):
        self.root = root
        self.app_ns = app_ns.strip("\\")
        self.psr4 = psr4_map(root, self.app_ns)
        self.aliases = class_aliases(root)
        self._declared = None

    def psr4_path(self, fqcn):
        for prefix, d in self.psr4:
            if fqcn.startswith(prefix):
                rel = d + fqcn[len(prefix):].replace("\\", "/") + ".php"
                if os.path.isfile(os.path.join(self.root, rel)):
                    return rel
        return None

    def declared(self, fqcn):
        if self._declared is None:
            self._declared = declared_classes(self.root, lib_php_files(self.root))
        return self._declared.get(fqcn)

    def file_of(self, fqcn):
        seen = set()
        while fqcn and fqcn not in seen:
            seen.add(fqcn)
            path = self.psr4_path(fqcn) or self.declared(fqcn)
            if path:
                return path
            fqcn = self.aliases.get(fqcn)
        return None

    def candidates(self, name):
        cls = controller_class(name)
        out = []
        if self.app_ns and not cls.startswith(self.app_ns + "\\"):
            out.append(f"{self.app_ns}\\Controller\\{cls}")
            if "\\" in cls:
                out.append(f"{self.app_ns}\\{cls}")
        out.append(cls)
        return out

    def resolve(self, name):
        for fqcn in self.candidates(name):
            path = self.file_of(fqcn)
            if path:
                return path
        return None


def app_namespace(root):
    """`OCA\\<App>` from lib/AppInfo/Application.php, else appinfo/info.xml, else ''."""
    try:
        with open(os.path.join(root, "lib", "AppInfo", "Application.php"), encoding="utf-8", errors="replace") as fh:
            m = re.search(r"^\s*namespace\s+(OCA\\[A-Za-z0-9_]+)", fh.read(), re.M)
        if m:
            return m.group(1)
    except OSError:
        pass
    try:
        with open(os.path.join(root, "appinfo", "info.xml"), encoding="utf-8", errors="replace") as fh:
            m = re.search(r"<namespace>\s*([A-Za-z0-9_]+)\s*</namespace>", fh.read())
        if m:
            return "OCA\\" + m.group(1)
    except OSError:
        pass
    return ""


def route_names_by_file(root, names):
    """{file: {route controller name, ...}} for the names that resolve."""
    resolver = Resolver(root, app_namespace(root))
    out = {}
    for name in set(names):
        path = resolver.resolve(name)
        if path:
            out.setdefault(os.path.normpath(path), set()).add(name)
    return out


def main(argv):
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    resolver = Resolver(argv[1], argv[2])
    names = [n.strip() for n in sys.stdin if n.strip()]
    found = 0
    for name in names:
        path = resolver.resolve(name) or ""
        found += bool(path)
        print(f"{name}\t{path}")
    print(f"# resolved {found} of {len(names)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
