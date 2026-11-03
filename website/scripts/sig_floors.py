# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Collect the floors, baselines and ratchets each app keeps on `development`.

A source is either a directory of local clones (`<dir>/<app>/...`, read as they
are checked out) or the GitHub API (`gh api`, branch `development`). Only the
repository root, `.github/`, `l10n/` and `tests/` are searched, one level deep.
"""
import base64
import json
import os
import re
import subprocess

ORG = "ConductionNL"
SEARCHED_DIRS = ("", ".github", "l10n", "tests")
NAME = re.compile(r"baseline|floor|ratchet|eslint-suppressions", re.I)
SCRIPT = re.compile(r"\.(sh|js|mjs|cjs|ts|php|py)$")


class GitHubSource:
    """Files of one app's `development` branch through the GitHub API."""

    def __init__(self, app):
        self.app = app
        self.ref = self._api("commits/development")["sha"]
        tree = self._api(f"git/trees/{self.ref}?recursive=1")
        self.paths = sorted(e["path"] for e in tree["tree"] if e["type"] == "blob")

    def _api(self, path):
        out = subprocess.run(["gh", "api", f"repos/{ORG}/{self.app}/{path}"],
                             check=True, capture_output=True, text=True).stdout
        return json.loads(out)

    def read(self, path):
        blob = self._api(f"contents/{path}?ref={self.ref}")
        return base64.b64decode(blob["content"]).decode("utf-8", "replace")


class CloneSource:
    """Files of one app's local clone, at whatever it has checked out."""

    def __init__(self, root, app):
        self.root = os.path.join(root, app)
        self.ref = subprocess.run(["git", "-C", self.root, "rev-parse", "HEAD"],
                                  check=True, capture_output=True, text=True).stdout.strip()
        self.paths = []
        for sub in SEARCHED_DIRS:
            base = os.path.join(self.root, sub)
            if os.path.isdir(base):
                self.paths += [os.path.join(sub, f) if sub else f for f in sorted(os.listdir(base))
                               if os.path.isfile(os.path.join(base, f))]

    def read(self, path):
        with open(os.path.join(self.root, path), encoding="utf-8", errors="replace") as fh:
            return fh.read()


def candidates(paths):
    """Floor-like data files in the searched directories; the scripts that read them are skipped."""
    return [p for p in paths if os.path.dirname(p) in SEARCHED_DIRS and NAME.search(os.path.basename(p))
            and not SCRIPT.search(p)]


def phpstan_count(text):
    """Ignored errors in a phpstan baseline: each entry counts its `count`, or 1."""
    total, entry, indent = 0, 0, None
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == "ignoreErrors:"), len(lines))
    for line in lines[start + 1:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        depth = len(line) - len(line.lstrip())
        if stripped.startswith("-") and indent in (None, depth):
            indent = depth
            total += entry
            entry = 1
        found = re.match(r"count:\s*(\d+)", stripped)
        if found and entry:
            entry = int(found.group(1))
    return total + entry


def eslint_count(text):
    return sum(rule["count"] for rules in json.loads(text).values() for rule in rules.values())


def coverage_pct(text):
    return f"{float(text.strip()):.2f}%"


def frontend_coverage(text):
    data = json.loads(text)
    if all(data.get(k) is None for k in ("phpunit", "vitest")):
        return "not recorded yet"
    return " / ".join(f"{k} {data[k]:.2f}%" for k in ("phpunit", "vitest") if data.get(k) is not None)


def debt_total(text):
    data = json.loads(text)
    return sum(v for v in data.values() if isinstance(v, int)), ", ".join(f"{k} {v}" for k, v in data.items())


# (row id, label, what it holds, matcher, reader returning value or (value, detail)).
KNOWN = [
    ("sig_floor", "SIG floor (gate 123)", "4-star checks the app must keep",
     lambda p: p == ".github/sig-floor.json", lambda t: len(json.loads(t)["checks"])),
    ("procedure_code", "procedure code (gate 119)", "procedure-named classes allowed",
     lambda p: p == ".procedure-code-baseline.json", lambda t: json.loads(t)["count"]),
    ("php_coverage", "PHP coverage (coverage-guard)", "line coverage the PHP suite may not drop below",
     lambda p: p == ".coverage-baseline", coverage_pct),
    ("test_coverage", "test coverage ratchet", "suite coverage per runner, raised on every gain",
     lambda p: p == "tests/.coverage-baseline.json", frontend_coverage),
    ("debt_ratchet", "debt ratchet", "suppressions and ignores counted by check:debt-ratchet",
     lambda p: p == ".debt-baseline.json", debt_total),
    ("eslint", "eslint suppressions", "suppressed eslint violations",
     lambda p: p == "eslint-suppressions.json", eslint_count),
    ("phpstan", "phpstan baseline", "ignored phpstan errors, all baseline files",
     lambda p: re.fullmatch(r"phpstan-baseline[\w.-]*\.neon", p), phpstan_count),
    ("psalm", "psalm baseline", "baselined psalm issues",
     lambda p: p == "psalm-baseline.xml", lambda t: len(re.findall(r"<code>", t))),
    ("phpmd", "phpmd baseline", "baselined phpmd violations",
     lambda p: p == "phpmd.baseline.xml", lambda t: len(re.findall(r"<violation\b", t))),
    ("schema_l10n", "schema l10n baseline", "untranslated schema strings allowed",
     lambda p: p == "l10n/.schema-l10n-baseline.json", lambda t: json.loads(t)["uncovered"]),
]
LABEL = {row_id: (label, what) for row_id, label, what, _, _ in KNOWN}


def collect_app(source):
    """{row id: {"value", "detail", "files"}} for one app, plus the SIG floor."""
    cells, floor = {}, None
    for path in candidates(source.paths):
        text = source.read(path)
        row = next(((rid, read) for rid, _, _, match, read in KNOWN if match(path)), None)
        if row is None:
            cells[f"other:{path}"] = {"value": "present", "detail": path, "files": [path]}
            continue
        rid, read = row
        value = read(text)
        value, detail = value if isinstance(value, tuple) else (value, path)
        cell = cells.get(rid)
        if cell:
            cell["value"] += value
            cell["files"].append(path)
            cell["detail"] = ", ".join(cell["files"])
        else:
            cells[rid] = {"value": value, "detail": detail, "files": [path]}
        if rid == "sig_floor":
            data = json.loads(text)
            floor = {"measured_at": data.get("measured_at"), "profile": data.get("profile"),
                     "checks": [floor_row_id(c) for c in data["checks"]]}
    return cells, floor


def floor_row_id(check):
    """`javascript unit_size >30` → `javascript.unit_size.30`, the matrix row id."""
    lang, rest = check.split(" ", 1)
    return f"{lang}.{rest.replace(' >', '.')}"


def collect(apps, clones=None):
    """Floor rows over all apps, each app's floor, and the ref each was read at."""
    per_app, floors, refs = {}, {}, {}
    for app in apps:
        source = CloneSource(clones, app) if clones else GitHubSource(app)
        per_app[app], floors[app] = collect_app(source)
        refs[app] = source.ref
    row_ids = [rid for rid, *_ in KNOWN] + sorted({r for c in per_app.values() for r in c if r.startswith("other:")})
    rows = []
    for rid in row_ids:
        cells = {app: {"value": c[rid]["value"], "detail": c[rid]["detail"]} for app, c in per_app.items() if rid in c}
        if not cells:
            continue
        label, what = LABEL[rid] if rid in LABEL else (rid.split(":", 1)[1], "other floor-like file")
        rows.append({"id": rid, "label": label, "what": what, "cells": cells})
    return {"rows": rows, "refs": refs}, floors
