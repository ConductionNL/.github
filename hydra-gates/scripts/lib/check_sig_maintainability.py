#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""gate-122 helper: the SIG maintainability metrics, as a ratchet and as a report.

The Software Improvement Group (SIG, platform Sigrid) rates maintainability per
language from risk profiles: the share of code that sits in units (methods and
functions) above a size, complexity or parameter bound, plus duplication and a
few architecture properties. The 4-star limits come from the SIG/TUV NORD CERT
"Guidance for Producers" v17.0. hydra's phpmd runs at its own defaults with
baselines, so a green phpmd is not a green SIG profile.

TWO MODES
---------
ratchet   (the gate, on a delta base)
    For every unit the diff ADDS or CHANGES (a unit whose line range holds an
    added line), a finding when
        NLOC > 60, McCabe > 10, or 5 or more parameters
    and for every duplicated fragment of 6 or more lines the diff INTRODUCES
    (one occurrence of the clone has at least 6 added lines).

    A finding is NEW when the unit is new, or when the change pushed it over a
    bound or made an already-over unit worse. A changed unit that was already
    over the bound at the base and did not get worse is INHERITED, and so is
    every finding on a unit the diff did not touch. Only NEW findings count.

report    (nightly, or a full-scope run with no base)
    The whole risk profile of one app, per language, against the 4-star limits:
    unit size, unit complexity, unit interfacing, duplication, and for PHP and
    Python module coupling, component independence and an entanglement
    approximation. Written as JSON and as a short markdown table.

PROFILES (report mode)
----------------------
four-star   the default: the 4-star limits of the Guidance for Producers.
five-star   half of every 4-star limit (SIG does not publish 5-star limits,
            so half the share of code allowed in each risk band is the
            yardstick, rounded to one decimal where the half has two):
            duplication 2.8%, unit size 23.6/11.6/4.2%, complexity
            10.1/3.7/0.55%, parameters 7.5/1.65/0.45%, module coupling
            5.0/2.8/0.95%, component independence 96.9% (half the exposed
            share), entanglement 0.0385.
Chosen with --profile, or HYDRA_GATE_SIG_PROFILE when the flag is absent.
The profile changes only the limits a report is compared with; the ratchet's
unit bounds and the gate's advisory status do not change.

WHAT IS MEASURED
----------------
Tracked files with a source extension (php, js/mjs/cjs/jsx, ts/tsx, vue, py),
minus Sigrid's own default excludes (vendored at the bottom of this file, from
github.com/Software-Improvement-Group/sigridci resources/default-excludes.txt),
minus test code (SIG rates test code separately), minus the Nextcloud build
output directory js/ and l10n/. A `sigrid.yaml` (or .yml) at the repository
root adds its top-level `exclude:` patterns, so the gate scopes the code the
way SIG will once the repository carries a scope file.

TOOLS, PINNED
-------------
lizard 1.24.3 (units: NLOC, McCabe, parameters) and jscpd 4.0.5 (the
ratchet's clones). The report's duplication follows SIG's line definition
directly (windows of 6 code lines equal modulo whitespace) and shows jscpd's
figure next to it as a cross-check.
A different version produces different numbers, so the pinned version is
loaded or installed into the tool cache (HYDRA_GATE_TOOLS_DIR, default
~/.cache/hydra-gates/tools) and any other version is refused. Set
HYDRA_GATE_SIG_NO_INSTALL=1 to forbid the install.

Two lizard traps are handled here:
  * PHP parameter counts: lizard's PHP reader keeps only the last parameter in
    `parameters`. The count is the number of unique `$names` in `long_name`.
  * Crashes: lizard raises on some files (a Vue component in openconnector).
    Each file is analysed on its own with a time limit, and a file lizard
    cannot read is listed as skipped, never silently dropped.

Python methods do not count `self` or `cls` as a parameter.

Usage:
    check_sig_maintainability.py ratchet <app-dir> --base-ref REF
    check_sig_maintainability.py report  <app-dir> [--json FILE] [--md FILE]
                                         [--profile four-star|five-star]

Output ends in one of
    [gate-122] sig-maintainability: checked U changed unit(s) in F file(s), ...
    [gate-122] sig-maintainability: FAIL: N finding(s) ...
    [gate-122] sig-maintainability: report: ...
Exit status: 0 clean (or a report), 1 findings, 2 an unknown profile,
3 the base does not resolve, 4 nothing to judge, 5 a pinned tool is unavailable. A traceback is exit 1 with
no summary line, which the runner reports as WIRING, never as a finding.
"""
import argparse
import collections
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile

GATE = "[gate-122] sig-maintainability"
LIZARD_VERSION = "1.24.3"
JSCPD_VERSION = "4.0.5"

LANG_OF_EXT = {
    ".php": "php",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".vue": "vue",
    ".py": "python",
}

# Ratchet bounds: a changed unit is a finding ABOVE these.
RATCHET = {"nloc": 60, "ccn": 10, "params": 4}
RATCHET_LABEL = {"nloc": "NLOC > 60", "ccn": "McCabe > 10", "params": "5 or more parameters"}
DUP_MIN_LINES = 6

# 4-star limits, per language, as (bound, max share of unit LOC strictly above bound).
LIMITS = {
    "unit_size": [(15, .471), (30, .231), (60, .083)],
    "unit_complexity": [(5, .202), (10, .073), (25, .011)],
    "unit_interfacing": [(2, .150), (4, .033), (6, .009)],  # 3+, 5+, 7+ parameters
    "module_coupling": [(10, .100), (20, .056), (50, .019)],
}
DUPLICATION_LIMIT = .056
INDEPENDENCE_MIN = .937
ENTANGLEMENT_LIMIT = .077


PROFILES = {
    "four-star": {
        "stars": "4-star",
        "source": "SIG/TUV NORD CERT Guidance for Producers v17.0, 4 stars",
        "limits": LIMITS,
        "duplication": DUPLICATION_LIMIT,
        "independence_min": INDEPENDENCE_MIN,
        "entanglement": ENTANGLEMENT_LIMIT,
    },
    "five-star": {
        "stars": "5-star",
        "source": "half of each 4-star limit of the SIG/TUV NORD CERT Guidance for Producers v17.0 "
                  "(SIG publishes no 5-star limits)",
        "limits": {
            "unit_size": [(15, .236), (30, .116), (60, .042)],
            "unit_complexity": [(5, .101), (10, .037), (25, .0055)],
            "unit_interfacing": [(2, .075), (4, .0165), (6, .0045)],
            "module_coupling": [(10, .050), (20, .028), (50, .0095)],
        },
        "duplication": .028,
        "independence_min": .969,
        "entanglement": .0385,
    },
}
DEFAULT_PROFILE = "four-star"

TEST_PATTERNS = [
    r".*/tests?/.*", r".*/__tests__/.*", r".*/__mocks__/.*", r".*/e2e/.*",
    r".*[.](spec|test)[.](js|mjs|cjs|jsx|ts|tsx)",
    r".*/test_[^/]*[.]py", r".*/[^/]*_test[.]py", r".*/conftest[.]py",
]
NEXTCLOUD_EXCLUDES = [r"/js/.*", r"/l10n/.*"]

FILE_TIMEOUT = int(os.environ.get("HYDRA_GATE_SIG_FILE_TIMEOUT", "30"))


# --------------------------------------------------------------------------
# scope
# --------------------------------------------------------------------------

def sigrid_yaml_excludes(app):
    """Top-level `exclude:` regexes of sigrid.yaml / sigrid.yml, if present."""
    for name in ("sigrid.yaml", "sigrid.yml"):
        path = os.path.join(app, name)
        if not os.path.isfile(path):
            continue
        out, inside = [], False
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if re.match(r"^exclude:\s*$", line):
                    inside = True
                    continue
                if inside:
                    m = re.match(r"^\s+-\s+[\"']?(.+?)[\"']?\s*$", line)
                    if m:
                        out.append(m.group(1))
                    elif line.strip() and not line.startswith((" ", "\t", "#")):
                        inside = False
        return out
    return []


class Scope:
    def __init__(self, app):
        pats = SIGRID_DEFAULT_EXCLUDES + NEXTCLOUD_EXCLUDES + sigrid_yaml_excludes(app)
        self.exclude = [re.compile(p) for p in pats]
        self.tests = [re.compile(p) for p in TEST_PATTERNS]

    def language(self, rel):
        lang = LANG_OF_EXT.get(os.path.splitext(rel)[1].lower())
        if not lang:
            return None
        probe = "/" + rel
        if any(p.fullmatch(probe) for p in self.exclude):
            return None
        if any(p.fullmatch(probe) for p in self.tests):
            return None
        return lang


def tracked_files(app):
    rc, out = git(app, "ls-files", "-z")
    if rc == 0:
        return [p for p in out.split("\0") if p]
    found = []
    for root, dirs, files in os.walk(app):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "vendor")]
        for fn in files:
            found.append(os.path.relpath(os.path.join(root, fn), app))
    return found


def production_files(app, scope):
    """{rel path: language} for every measured file in the working tree."""
    out = {}
    for rel in tracked_files(app):
        lang = scope.language(rel)
        if lang and os.path.isfile(os.path.join(app, rel)):
            out[rel] = lang
    return out


def git(app, *args):
    p = subprocess.run(["git", "-c", "safe.directory=*", *args], cwd=app,
                       capture_output=True, text=True, errors="replace")
    return p.returncode, p.stdout


# --------------------------------------------------------------------------
# tools
# --------------------------------------------------------------------------

def tools_dir():
    base = os.environ.get("HYDRA_GATE_TOOLS_DIR") or os.path.join(
        os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache"),
        "hydra-gates", "tools")
    return base


def may_install():
    return os.environ.get("HYDRA_GATE_SIG_NO_INSTALL", "0") != "1"


def load_lizard():
    """Import lizard at the pinned version, installing it into the tool cache
    when allowed. Returns (module, None) or (None, reason)."""
    target = os.path.join(tools_dir(), f"lizard-{LIZARD_VERSION}")
    if os.path.isdir(target):
        sys.path.insert(0, target)
    try:
        import lizard  # noqa: F401
    except ImportError:
        lizard = None
    if lizard is not None and getattr(lizard, "version", "") == LIZARD_VERSION:
        return lizard, None
    if lizard is not None:
        found = getattr(lizard, "version", "?")
        for name in [m for m in sys.modules if m == "lizard" or m.startswith(("lizard_", "lizard."))]:
            del sys.modules[name]
        if target in sys.path:
            return None, f"lizard {found} is importable but {LIZARD_VERSION} is pinned; remove {target} and retry"
    if not may_install():
        return None, f"lizard {LIZARD_VERSION} is not installed and HYDRA_GATE_SIG_NO_INSTALL=1 forbids installing it"
    os.makedirs(target, exist_ok=True)
    p = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
                        "--no-input", "--target", target, f"lizard=={LIZARD_VERSION}"],
                       capture_output=True, text=True)
    if p.returncode != 0:
        shutil.rmtree(target, ignore_errors=True)
        return None, f"pip could not install lizard=={LIZARD_VERSION}: {(p.stderr or p.stdout).strip()[-300:]}"
    sys.path.insert(0, target)
    try:
        import lizard
    except ImportError as e:
        return None, f"lizard installed into {target} but does not import: {e}"
    if getattr(lizard, "version", "") != LIZARD_VERSION:
        return None, f"imported lizard {getattr(lizard, 'version', '?')} from {lizard.__file__}, not the pinned {LIZARD_VERSION}"
    return lizard, None


def find_jscpd():
    """Path to a jscpd binary at the pinned version, or (None, reason)."""
    env = os.environ.get("HYDRA_GATE_JSCPD")
    target = os.path.join(tools_dir(), f"jscpd-{JSCPD_VERSION}")
    exe = env or os.path.join(target, "node_modules", ".bin", "jscpd")
    if not os.path.isfile(exe):
        if env:
            return None, f"HYDRA_GATE_JSCPD={env} does not exist"
        if not shutil.which("npm"):
            return None, "npm is not on PATH, so jscpd cannot be installed"
        if not may_install():
            return None, f"jscpd {JSCPD_VERSION} is not installed and HYDRA_GATE_SIG_NO_INSTALL=1 forbids installing it"
        os.makedirs(target, exist_ok=True)
        p = subprocess.run(["npm", "install", "--silent", "--no-audit", "--no-fund", "--ignore-scripts",
                            "--prefix", target, f"jscpd@{JSCPD_VERSION}"], capture_output=True, text=True)
        if p.returncode != 0 or not os.path.isfile(exe):
            return None, f"npm could not install jscpd@{JSCPD_VERSION}: {(p.stderr or p.stdout).strip()[-300:]}"
    p = subprocess.run([exe, "--version"], capture_output=True, text=True)
    found = (p.stdout or "").strip().splitlines()[-1:] or ["?"]
    if found[0] != JSCPD_VERSION:
        return None, f"{exe} reports jscpd {found[0]}, not the pinned {JSCPD_VERSION}"
    return exe, None


# --------------------------------------------------------------------------
# units
# --------------------------------------------------------------------------

class _Timeout(Exception):
    pass


def _alarm(_sig, _frame):
    raise _Timeout()


def unit_params(lang, func):
    if lang == "php":
        # lizard's PHP reader keeps only the last parameter; long_name lists each $name twice.
        return len(set(re.findall(r"\$\w+", func.long_name)))
    params = list(func.parameters)
    if lang == "python" and params and params[0] in ("self", "cls"):
        params = params[1:]
    return len(params)


class UnitReader:
    def __init__(self, lizard):
        self.analyzer = lizard.FileAnalyzer(lizard.get_extensions([]))
        self.skipped = []

    def units(self, rel, lang, code):
        """Units of one file's source. A file lizard cannot read is recorded in
        self.skipped and yields no units."""
        use_alarm = hasattr(signal, "SIGALRM")
        if use_alarm:
            old = signal.signal(signal.SIGALRM, _alarm)
            signal.alarm(FILE_TIMEOUT)
        try:
            info = self.analyzer.analyze_source_code(rel, code)
        except _Timeout:
            self.skipped.append({"file": rel, "reason": f"lizard did not finish within {FILE_TIMEOUT}s"})
            return []
        except Exception as e:  # lizard raises on some inputs; one file must not sink the run
            self.skipped.append({"file": rel, "reason": f"lizard raised {type(e).__name__}: {str(e)[:160]}"})
            return []
        finally:
            if use_alarm:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old)
        out = []
        for f in info.function_list:
            out.append({
                "file": rel, "lang": lang, "name": f.name, "start": f.start_line, "end": f.end_line,
                "nloc": f.nloc, "ccn": f.cyclomatic_complexity, "params": unit_params(lang, f),
            })
        return out


def read_text(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


# --------------------------------------------------------------------------
# duplication
# --------------------------------------------------------------------------

def run_jscpd(app, exe, files):
    """Clone pairs among `files` (repo-relative), as a list of
    {"a": (file, start, end), "b": (file, start, end), "lines": n, "code": {file: set}}.

    jscpd matches tokens and skips comments, so a reported fragment can span a
    docblock, and its first and last line may match only in part. SIG counts
    code lines repeated literally modulo whitespace, so the code lines of both
    fragments are paired in order and only the pairs that are equal without
    whitespace count. A clone is kept when at least 6 lines do, and "code"
    holds those line numbers per fragment."""
    if not files:
        return []
    out_dir = tempfile.mkdtemp(prefix="sig-jscpd-")
    try:
        cmd = [exe, "--silent", "--reporters", "json", "--output", out_dir,
               "--min-lines", str(DUP_MIN_LINES), "--min-tokens", "30", "--mode", "weak", *files]
        p = subprocess.run(cmd, cwd=app, capture_output=True, text=True)
        report = os.path.join(out_dir, "jscpd-report.json")
        if not os.path.isfile(report):
            raise RuntimeError(f"jscpd exited {p.returncode} without a report: {(p.stderr or p.stdout).strip()[-300:]}")
        with open(report) as fh:
            data = json.load(fh)
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)
    code, text = {}, {}

    def code_in(occ):
        f, s, e = occ
        if f not in code:
            lang = LANG_OF_EXT.get(os.path.splitext(f)[1].lower(), "")
            text[f] = read_text(os.path.join(app, f)).splitlines()
            code[f] = code_lines("\n".join(text[f]), lang)
        return [n for n in range(s, e + 1) if n in code[f]]

    def literal_pairs(occ_a, occ_b):
        same_a, same_b = set(), set()
        for na, nb in zip(code_in(occ_a), code_in(occ_b)):
            if "".join(text[occ_a[0]][na - 1].split()) == "".join(text[occ_b[0]][nb - 1].split()):
                same_a.add(na)
                same_b.add(nb)
        return same_a, same_b

    clones = []
    for d in data.get("duplicates", []):
        a, b = d["firstFile"], d["secondFile"]
        occ_a = (os.path.relpath(os.path.join(app, a["name"]), app), a["start"], a["end"])
        occ_b = (os.path.relpath(os.path.join(app, b["name"]), app), b["start"], b["end"])
        code_a, code_b = literal_pairs(occ_a, occ_b)
        if len(code_b) < DUP_MIN_LINES:
            continue
        clones.append({"a": occ_a, "b": occ_b, "lines": len(code_b), "code": {occ_a: code_a, occ_b: code_b}})
    return clones


def code_lines(text, lang):
    """Line numbers (1-based) holding code: not blank, not a comment-only line."""
    lines = set()
    in_block = False
    hash_comments = lang in ("python", "php")
    for i, raw in enumerate(text.splitlines(), 1):
        s = raw.strip()
        if in_block:
            if "*/" in s:
                in_block = False
                s = s.split("*/", 1)[1].strip()
            else:
                continue
        if not s:
            continue
        if s.startswith("/*"):
            if "*/" not in s[2:]:
                in_block = True
                continue
            s = s[s.index("*/", 2) + 2:].strip()
            if not s:
                continue
        if s.startswith("//") or (hash_comments and s.startswith("#")) or s.startswith("*"):
            continue
        lines.add(i)
    return lines


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------

def profile(units, key, limits):
    total = sum(u["nloc"] for u in units) or 1
    rows = []
    for bound, cap in limits:
        share = sum(u["nloc"] for u in units if u[key] > bound) / total
        rows.append({"above": bound, "share": round(share, 4), "limit": cap, "ok": share <= cap})
    return rows


def worst(units, key, n=8):
    ranked = sorted(units, key=lambda u: (-u[key], u["file"], u["start"]))[:n]
    return [f"{u['file']}:{u['start']} {u['name']} ({u[key]})" for u in ranked]


def duplication_profile(app, clones, files_by_lang, limit=DUPLICATION_LIMIT):
    """Redundant code lines per language, two ways.

    "duplication" follows SIG's definition directly: every window of 6
    consecutive code lines, compared without whitespace, that already occurred
    earlier in a file of the same language makes its lines redundant (so N
    copies count N-1 times). Windows made only of brackets are skipped.

    "duplication_jscpd" is the cross-check from jscpd's clone pairs: the
    literally equal code lines of each pair's second occurrence. jscpd reports
    clones pairwise and needs 30 tokens, so it finds fewer clones than SIG."""
    lines_of, code = {}, {}
    for rel, lang in files_by_lang.items():
        text = read_text(os.path.join(app, rel))
        lines_of[rel] = text.splitlines()
        code[rel] = code_lines(text, lang)
    windows = collections.defaultdict(dict)
    redundant = collections.defaultdict(set)
    for rel in sorted(files_by_lang):
        seen = windows[files_by_lang[rel]]
        seq = [(n, "".join(lines_of[rel][n - 1].split())) for n in sorted(code[rel])]
        for i in range(len(seq) - DUP_MIN_LINES + 1):
            win = seq[i:i + DUP_MIN_LINES]
            key = tuple(t for _n, t in win)
            if all(len(t) <= 2 for t in key):
                continue
            if key in seen and seen[key] != (rel, i):
                redundant[rel].update(n for n, _t in win)
            else:
                seen.setdefault(key, (rel, i))
    by_jscpd = collections.defaultdict(set)
    for c in clones:
        f = c["b"][0]
        if f in code:
            by_jscpd[f].update(c["code"][c["b"]])

    def row(dup, total):
        share = dup / total if total else 0.0
        return {"code_lines": total, "redundant_lines": dup, "share": round(share, 4),
                "limit": limit, "ok": share <= limit}
    out = {}
    for lang in sorted(set(files_by_lang.values())):
        files = [f for f, lg in files_by_lang.items() if lg == lang]
        total = sum(len(code[f]) for f in files)
        out[lang] = (row(sum(len(redundant[f]) for f in files), total),
                     row(sum(len(by_jscpd[f]) for f in files), total))
    return out


# ---- module structure ------------------------------------------------------

def php_dependencies(app, files):
    """{module: set(modules it depends on)} for PHP files that declare a class
    in a namespace. Dependencies are `use` imports, fully-qualified names, and
    bare class names resolved in the file's own namespace."""
    fqcn, ns_of, srcs = {}, {}, {}
    for rel in files:
        src = read_text(os.path.join(app, rel))
        m = re.search(r"^namespace\s+([^;]+);", src, re.M)
        if not m:
            continue
        ns = m.group(1).strip()
        ns_of[rel] = ns
        srcs[rel] = re.sub(r"/\*.*?\*/|//[^\n]*", "", src, flags=re.S)
        fqcn[f"{ns}\\{os.path.basename(rel)[:-4]}"] = rel
    deps = {}
    for rel, body in srcs.items():
        targets = set()
        for imp in re.findall(r"^use\s+([^;]+);", body, re.M):
            prefix = ""
            group = re.match(r"(.*)\\\{(.*)\}$", imp.strip())
            parts = group.group(2).split(",") if group else imp.split(",")
            if group:
                prefix = group.group(1).strip().lstrip("\\") + "\\"
            for part in parts:
                name = prefix + part.strip().split(" as ")[0].strip().lstrip("\\")
                if name in fqcn:
                    targets.add(fqcn[name])
        for ident in set(re.findall(r"\b([A-Z][A-Za-z0-9_]*)\b", body)):
            t = fqcn.get(f"{ns_of[rel]}\\{ident}")
            if t:
                targets.add(t)
        for fq in re.findall(r"\\?([A-Z][A-Za-z0-9_]*(?:\\[A-Za-z0-9_]+)+)", body):
            if fq in fqcn:
                targets.add(fqcn[fq])
        deps[rel] = targets - {rel}
    return deps


def python_dependencies(app, files):
    """{module: set(modules it imports)} for Python files, resolving absolute
    imports against the repository root and every `src`-style parent, and
    relative imports against the file's package."""
    index = {}
    for rel in files:
        mod = rel[:-3].replace("/", ".")
        if mod.endswith(".__init__"):
            mod = mod[: -len(".__init__")]
        parts = mod.split(".")
        for i in range(len(parts)):
            index.setdefault(".".join(parts[i:]), rel)

    def resolve(name):
        while name:
            if name in index:
                return index[name]
            name = name.rpartition(".")[0]
        return None

    deps = {}
    for rel in files:
        src = read_text(os.path.join(app, rel))
        pkg = rel[:-3].replace("/", ".").split(".")[:-1]
        targets = set()
        for m in re.finditer(r"^\s*import\s+([\w., ]+)", src, re.M):
            for part in m.group(1).split(","):
                t = resolve(part.strip().split(" as ")[0].strip())
                if t:
                    targets.add(t)
        for m in re.finditer(r"^\s*from\s+(\.*)([\w.]*)\s+import\s+(\([^)]*\)|[^\n#]+)", src, re.M):
            dots, base, names = m.group(1), m.group(2), m.group(3).strip("() \n")
            if dots:
                anchor = pkg[: len(pkg) - (len(dots) - 1)] if len(dots) > 1 else pkg
                base = ".".join([*anchor, base] if base else anchor)
            for n in names.replace("\n", " ").split(","):
                n = n.strip().split(" as ")[0].strip()
                t = resolve(f"{base}.{n}" if n else base) if base else None
                if t:
                    targets.add(t)
        deps[rel] = targets - {rel}
    return deps


def component_of_factory(files):
    """Components are directories. Start at the repository root and descend
    while one child directory holds more than 80% of the modules under the
    current root: lib/ in a Nextcloud app, src/api/ in a Python service. (In
    the fleet's apps lib/Service holds 50 to 71% of lib/, so it stays a
    component next to lib/Db and lib/Controller.) A component is a first-level
    directory below that root, and "(root)" for files directly in it. A module
    outside the root belongs to its own top-level directory ("(top)" for a file
    at the repository root)."""
    root = ""
    while files:
        children = collections.Counter()
        inside = [f for f in files if not root or f.startswith(root + "/")]
        for f in inside:
            rest = f[len(root) + 1:] if root else f
            if "/" in rest:
                children[rest.split("/")[0]] += 1
        if not children:
            break
        top, count = children.most_common(1)[0]
        if count * 5 <= len(inside) * 4:
            break
        root = f"{root}/{top}" if root else top

    def component(rel):
        if not root or rel.startswith(root + "/"):
            rest = rel[len(root) + 1:] if root else rel
            return rest.split("/")[0] if "/" in rest else "(root)"
        return rel.split("/")[0] if "/" in rel else "(top)"
    return root, component


def violation_degree(lines):
    """SIG communication violation degree from {(src, dst): weight}: direct
    cycles, then indirect cycles on what remains, then transitive lines.
    Each line is counted as at most one violation."""
    total = sum(lines.values()) or 1
    violated = {}
    for (a, b), w in lines.items():
        if (b, a) in lines and a < b:
            w2 = lines[(b, a)]
            low = min(w, w2)
            if w <= w2:
                violated[(a, b)] = ("cyclic", low)
            if w2 <= w:
                violated[(b, a)] = ("cyclic", low)
    remaining = {k: v for k, v in lines.items() if k not in violated}

    def find_cycle(graph):
        adj = collections.defaultdict(list)
        for (a, b) in graph:
            adj[a].append(b)
        state, stack = {}, []

        def dfs(n):
            state[n] = 1
            stack.append(n)
            for m in sorted(adj[n]):
                if state.get(m) == 1:
                    return stack[stack.index(m):] + [m]
                if not state.get(m):
                    c = dfs(m)
                    if c:
                        return c
            state[n] = 2
            stack.pop()
            return None
        for n in sorted(adj):
            if not state.get(n):
                c = dfs(n)
                if c:
                    return c
        return None

    while True:
        cyc = find_cycle(remaining)
        if not cyc:
            break
        edges = list(zip(cyc, cyc[1:]))
        weakest = min(edges, key=lambda e: (remaining[e], e))
        violated[weakest] = ("indirect-cyclic", remaining[weakest])
        del remaining[weakest]

    outgoing = collections.Counter(a for (a, _b) in remaining)
    adj = collections.defaultdict(set)
    for (a, b) in remaining:
        adj[a].add(b)

    def reach(start, skip):
        seen, todo = {start}, [start]
        while todo:
            n = todo.pop()
            for m in adj[n]:
                if (n, m) != skip and m not in seen:
                    seen.add(m)
                    todo.append(m)
        return seen

    rev = collections.defaultdict(set)
    for (a, b) in remaining:
        rev[b].add(a)

    def reach_back(start, skip):
        seen, todo = {start}, [start]
        while todo:
            n = todo.pop()
            for m in rev[n]:
                if (m, n) != skip and m not in seen:
                    seen.add(m)
                    todo.append(m)
        return seen

    for (a, b), w in sorted(remaining.items()):
        if not outgoing[b]:
            continue
        fwd, back = reach(a, (a, b)), reach_back(b, (a, b))
        if b not in fwd:
            continue
        on_paths = [remaining[(u, v)] for (u, v) in remaining
                    if (u, v) != (a, b) and u in fwd and v in back]
        if on_paths and w <= min(on_paths):
            violated[(a, b)] = ("transitive", w)
    degree = sum(w for _kind, w in violated.values()) / total
    kinds = collections.Counter(kind for kind, _w in violated.values())
    return round(degree, 4), dict(kinds), sorted(f"{a} -> {b} ({kind})" for (a, b), (kind, _w) in violated.items())


def structure(app, files, deps, prof=PROFILES[DEFAULT_PROFILE]):
    """Module coupling, component independence and entanglement for one language."""
    if not deps:
        return None
    modules = sorted(deps)
    loc = {m: len(code_lines(read_text(os.path.join(app, m)), files[m])) for m in modules}
    incoming = collections.defaultdict(set)
    for src, targets in deps.items():
        for t in targets:
            incoming[t].add(src)
    total = sum(loc.values()) or 1
    coupling = []
    for bound, cap in prof["limits"]["module_coupling"]:
        share = sum(loc[m] for m in modules if len(incoming[m]) > bound) / total
        coupling.append({"above": bound, "share": round(share, 4), "limit": cap, "ok": share <= cap})
    root, comp = component_of_factory(modules)
    hidden = sum(loc[m] for m in modules if all(comp(s) == comp(m) for s in incoming[m]))
    lines = collections.Counter()
    for t, srcs in incoming.items():
        for s in srcs:
            if comp(s) != comp(t):
                lines[(comp(s), comp(t))] += 1
    connected = {c for k in lines for c in k}
    density = len(lines) / max(len(connected), 1)
    degree, kinds, examples = violation_degree(dict(lines))
    comp_loc = collections.Counter()
    for m in modules:
        comp_loc[comp(m)] += loc[m]
    independence = hidden / total
    return {
        "modules": len(modules),
        "module_loc": total,
        "module_coupling": coupling,
        "highest_fan_in": [f"{m} (fan-in {len(incoming[m])}, {loc[m]} loc)"
                           for m in sorted(modules, key=lambda m: (-len(incoming[m]), m))[:10]],
        "component_root": root or ".",
        "components": dict(comp_loc.most_common()),
        "component_independence": {"hidden_share": round(independence, 4), "limit_min": prof["independence_min"],
                                   "ok": independence >= prof["independence_min"]},
        "component_entanglement": {
            "communication_lines": len(lines),
            "connected_components": len(connected),
            "communication_density": round(density, 2),
            "violation_degree": round(degree, 4),
            "violations": kinds,
            "violation_examples": examples[:12],
            "limit": prof["entanglement"],
            "ok": None,
            "note": "SIG normalises density and violation degree by benchmark maxima it does not publish, "
                    "so this is the two inputs, not the rated value. Lower is better on both.",
        },
    }


def build_report(app, lizard, jscpd, profile_name=DEFAULT_PROFILE):
    prof = PROFILES[profile_name]
    scope = Scope(app)
    files = production_files(app, scope)
    reader = UnitReader(lizard)
    units = []
    for rel, lang in sorted(files.items()):
        units.extend(reader.units(rel, lang, read_text(os.path.join(app, rel))))
    by_lang = collections.defaultdict(list)
    for u in units:
        by_lang[u["lang"]].append(u)
    clones = run_jscpd(app, jscpd, sorted(files)) if files else []
    dup = duplication_profile(app, clones, files, prof["duplication"])
    report = {
        "app": os.path.basename(os.path.abspath(app)),
        "head": (git(app, "rev-parse", "HEAD")[1] or "").strip() or None,
        "tools": {"lizard": LIZARD_VERSION, "jscpd": JSCPD_VERSION},
        "profile": profile_name,
        "stars": prof["stars"],
        "limits": prof["source"],
        "files": len(files),
        "skipped_files": reader.skipped,
        "languages": {},
    }
    for lang in sorted(set(files.values())):
        rows = by_lang.get(lang, [])
        report["languages"][lang] = {
            "files": sum(1 for v in files.values() if v == lang),
            "units": len(rows),
            "unit_loc": sum(u["nloc"] for u in rows),
            "unit_size": profile(rows, "nloc", prof["limits"]["unit_size"]),
            "unit_complexity": profile(rows, "ccn", prof["limits"]["unit_complexity"]),
            "unit_interfacing": profile(rows, "params", prof["limits"]["unit_interfacing"]),
            "duplication": dup[lang][0] if lang in dup else None,
            "duplication_jscpd": dup[lang][1] if lang in dup else None,
            "largest_units": worst(rows, "nloc"),
            "most_complex_units": worst(rows, "ccn"),
            "widest_units": worst(rows, "params"),
        }
    php = {f: lg for f, lg in files.items() if lg == "php" and f.startswith("lib/")}
    py = {f: lg for f, lg in files.items() if lg == "python"}
    report["structure"] = {}
    if php:
        report["structure"]["php"] = structure(app, php, php_dependencies(app, php), prof)
    if py:
        report["structure"]["python"] = structure(app, py, python_dependencies(app, py), prof)
    return report


def checks_of(report):
    """Every check of the report's profile as (label, ok)."""
    out = []
    for lang, d in report["languages"].items():
        for prop in ("unit_size", "unit_complexity", "unit_interfacing"):
            for row in d[prop]:
                out.append((f"{lang} {prop} >{row['above']}", row["ok"]))
        if d.get("duplication"):
            out.append((f"{lang} duplication", d["duplication"]["ok"]))
    for lang, s in report.get("structure", {}).items():
        if not s:
            continue
        for row in s["module_coupling"]:
            out.append((f"{lang} module_coupling >{row['above']}", row["ok"]))
        out.append((f"{lang} component_independence", s["component_independence"]["ok"]))
    return out


def pct(x):
    return f"{x * 100:.1f}%"


def markdown(report):
    out = [f"## SIG maintainability profile: {report['app']}", "",
           f"lizard {LIZARD_VERSION}, jscpd {JSCPD_VERSION}; limits: {report['limits']}. "
           f"Each cell is the share of code above the bound, against the {report['stars']} limit.", "",
           "| language | units | size >15/30/60 | complexity >5/10/25 | params 3+/5+/7+ | duplication | jscpd |",
           "|---|---|---|---|---|---|---|"]

    def cells(rows):
        return " / ".join(f"{pct(r['share'])}{'' if r['ok'] else ' ✗'}" for r in rows)
    for lang, d in report["languages"].items():
        dup = d.get("duplication")
        dcell = f"{pct(dup['share'])}{'' if dup['ok'] else ' ✗'}" if dup else "n/a"
        jdup = d.get("duplication_jscpd")
        jcell = pct(jdup["share"]) if jdup else "n/a"
        out.append(f"| {lang} | {d['units']} | {cells(d['unit_size'])} | {cells(d['unit_complexity'])} "
                   f"| {cells(d['unit_interfacing'])} | {dcell} | {jcell} |")
    for lang, s in report.get("structure", {}).items():
        if not s:
            continue
        e = s["component_entanglement"]
        ci = s["component_independence"]
        out += ["", f"{lang} structure ({s['modules']} modules, components under `{s['component_root']}`): "
                f"module coupling >10/20/50 {cells(s['module_coupling'])}; "
                f"component independence {pct(ci['hidden_share'])}{'' if ci['ok'] else ' ✗'} (min {pct(ci['limit_min'])}); "
                f"entanglement inputs: {e['communication_lines']} lines between {e['connected_components']} components, "
                f"density {e['communication_density']}, violation degree {e['violation_degree']}."]
    checks = checks_of(report)
    out += ["", f"{sum(1 for _c, ok in checks if ok)} of {len(checks)} {report['stars']} checks met. ✗ marks a miss."]
    if report["skipped_files"]:
        out += ["", f"{len(report['skipped_files'])} file(s) lizard could not read, NOT measured: "
                + ", ".join(s["file"] for s in report["skipped_files"][:10])]
    return "\n".join(out) + "\n"


def cmd_report(args, lizard, jscpd):
    report = build_report(args.app, lizard, jscpd, args.profile)
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(report, fh, indent=1)
    md = markdown(report)
    if args.md:
        with open(args.md, "w") as fh:
            fh.write(md)
    print(md)
    for s in report["skipped_files"]:
        print(f"  skipped (lizard): {s['file']}: {s['reason']}")
    if not report["files"]:
        print(f"{GATE}: no measured source file in this repository (php, js, ts, vue, py outside tests and Sigrid's default excludes)")
        return 4
    checks = checks_of(report)
    missed = [c for c, ok in checks if not ok]
    units = sum(d["units"] for d in report["languages"].values())
    print(f"{GATE}: report: {units} unit(s) "
          f"in {report['files']} file(s), languages {', '.join(report['languages'])}; "
          f"{len(checks) - len(missed)} of {len(checks)} {report['stars']} checks met"
          + (f"; missed: {', '.join(missed)}" if missed else ""))
    return 0


# --------------------------------------------------------------------------
# ratchet
# --------------------------------------------------------------------------

def added_lines(app, base, rel):
    rc, out = git(app, "diff", "-U0", "--no-color", base, "HEAD", "--", rel)
    lines = set()
    for line in out.splitlines():
        m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
        if m:
            start, count = int(m.group(1)), int(m.group(2) or 1)
            lines.update(range(start, start + count))
    return lines


def changed_paths(app, base):
    """{new path: old path or None} for files added, copied, modified or renamed."""
    rc, out = git(app, "diff", "--name-status", "-M", "--diff-filter=ACMR", base, "HEAD")
    paths = {}
    for line in out.splitlines():
        parts = line.split("\t")
        if parts[0].startswith(("R", "C")) and len(parts) == 3:
            paths[parts[2]] = parts[1] if parts[0].startswith("R") else None
        elif len(parts) == 2:
            paths[parts[1]] = parts[1] if parts[0] != "A" else None
    return paths


def cmd_ratchet(args, lizard, jscpd_exe):
    app = args.app
    rc, mb = git(app, "merge-base", args.base_ref, "HEAD")
    if rc != 0 or not mb.strip():
        print(f"{GATE}: the base '{args.base_ref}' has no merge base with HEAD, so no change could be isolated")
        return 3
    mb = mb.strip()
    scope = Scope(app)
    changed = {}
    for new, old in changed_paths(app, mb).items():
        lang = scope.language(new)
        if lang and os.path.isfile(os.path.join(app, new)):
            changed[new] = (lang, old)
    if not changed:
        print(f"{GATE}: this change touches no measured source file (php, js, ts, vue, py outside tests and Sigrid's default excludes)")
        return 4

    reader = UnitReader(lizard)
    new_findings, inherited = [], []
    touched_units = 0
    added = {}
    for rel, (lang, old) in sorted(changed.items()):
        added[rel] = added_lines(app, mb, rel)
        head_units = reader.units(rel, lang, read_text(os.path.join(app, rel)))
        base_units = {}
        if old:
            rc, base_src = git(app, "show", f"{mb}:{old}")
            if rc == 0:
                for u in reader.units(old, lang, base_src):
                    base_units.setdefault(u["name"], u)
        for u in head_units:
            touched = any(u["start"] <= n <= u["end"] for n in added[rel])
            touched_units += touched
            before = base_units.get(u["name"])
            for key, bound in RATCHET.items():
                if u[key] <= bound:
                    continue
                f = {"file": rel, "line": u["start"], "unit": u["name"], "metric": key,
                     "value": u[key], "rule": RATCHET_LABEL[key],
                     "before": before[key] if before else None}
                if not touched:
                    inherited.append(f)
                elif before is None or before[key] <= bound or u[key] > before[key]:
                    new_findings.append(f)
                else:
                    inherited.append(f)

    # Duplication: clones among every measured file of the languages this change touches.
    langs = {lang for lang, _old in changed.values()}
    corpus = sorted(f for f, lg in production_files(app, scope).items() if lg in langs)
    if not any(len(lines) >= DUP_MIN_LINES for lines in added.values()):
        corpus = []  # no file gained 6 lines, so no new clone is possible
    dup_new = 0
    for c in run_jscpd(app, jscpd_exe, corpus):
        hits = []
        for occ in (c["a"], c["b"]):
            f, s, e = occ
            if f in added and len(added[f] & c["code"][occ]) >= DUP_MIN_LINES:
                hits.append(occ)
        if hits:
            f, s, e = hits[0]
            other = c["b"] if hits[0] == c["a"] else c["a"]
            new_findings.append({"file": f, "line": s, "unit": f"lines {s}-{e}", "metric": "duplication",
                                 "value": c["lines"], "rule": f"duplicated fragment of {DUP_MIN_LINES}+ lines",
                                 "before": None, "other": f"{other[0]}:{other[1]}-{other[2]}"})
            dup_new += 1

    for s in reader.skipped:
        print(f"  unverified (lizard could not read it): {s['file']}: {s['reason']}")
    for f in new_findings:
        was = f" (was {f['before']})" if f.get("before") is not None else ""
        extra = f", same as {f['other']}" if f.get("other") else ""
        print(f"  {f['file']}:{f['line']} {f['unit']}: {f['rule']}: {f['value']}{was}{extra}")
    if inherited:
        print(f"  inherited, not counted: {len(inherited)} finding(s) on units this change did not touch "
              f"or did not make worse")
        for f in inherited[:10]:
            print(f"    {f['file']}:{f['line']} {f['unit']}: {f['rule']}: {f['value']}")
    tail = (f"lizard {LIZARD_VERSION}, jscpd {JSCPD_VERSION}; {len(inherited)} inherited"
            + (f"; {len(reader.skipped)} file(s) NOT measured" if reader.skipped else ""))
    if new_findings:
        print(f"{GATE}: FAIL: {len(new_findings)} finding(s) in {touched_units} changed unit(s) "
              f"({dup_new} duplicated fragment(s)); {tail}")
        return 1
    print(f"{GATE}: checked {touched_units} changed unit(s) in {len(changed)} file(s), 0 finding(s); {tail}")
    return 0


# --------------------------------------------------------------------------

def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    r = sub.add_parser("ratchet")
    r.add_argument("app")
    r.add_argument("--base-ref", required=True)
    p = sub.add_parser("report")
    p.add_argument("app")
    p.add_argument("--json")
    p.add_argument("--md")
    p.add_argument("--profile", default=os.environ.get("HYDRA_GATE_SIG_PROFILE") or DEFAULT_PROFILE,
                   help="limits to report against: " + ", ".join(PROFILES)
                        + " (default: HYDRA_GATE_SIG_PROFILE, else " + DEFAULT_PROFILE + ")")
    args = ap.parse_args(argv)
    args.app = os.path.abspath(args.app)
    if args.mode == "report" and args.profile not in PROFILES:
        print(f"{GATE}: unknown profile '{args.profile}'; choose one of {', '.join(PROFILES)}")
        return 2

    lizard, why = load_lizard()
    if not lizard:
        print(f"{GATE}: tooling: {why}")
        return 5
    jscpd, why = find_jscpd()
    if not jscpd:
        print(f"{GATE}: tooling: {why}")
        return 5
    if args.mode == "ratchet":
        return cmd_ratchet(args, lizard, jscpd)
    return cmd_report(args, lizard, jscpd)


# Sigrid's default excludes, verbatim, from
# github.com/Software-Improvement-Group/sigridci resources/default-excludes.txt
# (fetched 2026-10-29). Matched against "/" + the repo-relative path.
SIGRID_DEFAULT_EXCLUDES = r"""
.*/[.]cache/.*
.*/[.]sonarlint/.*
.*/[.]DS_Store
.*/[.]ipynb
.*/[.]class
.*/[.]classpath
.*/[.]project
.*/[.]hg/.*
.*/.*[.][Gg]en(enerated)?[.].*
.*/[.]circleci/.*
.*/[.]git/.*
.*/git[.]log
.*/[.]github/.*
.*/[.]gitlab/.*
.*/[.]gradle/.*
.*/[.]idea/.*
.*/[.]maven/.*
.*/[.]mvn/.*
.*/[.]phpstorm[.]meta[.]php/.*
.*/[.]prettierrc[.]js
.*/[.]settings/.*
.*/[.]svn/.*
.*/[.]teamcity/.*
.*/\$tf/.*
.*/__MACOSX/.*
.*/.*(-|.)min[.](css|js)
.*/.*[.]asm[.]js
.*/.*[.]conf(ig)?[.](js|ts|coffee)
.*/.*[.]es[.]js
.*/.*[.]eslintrc[.]js
.*/.*[.]excl[.]mendix
.*/.*[.]g[.]vb
.*/.*[.]out[.]js
.*/.*[.][Dd]esigner[.]cs
.*/.*[.]style[.](js|jsx|ts|tsx)
.*/.*[.]styles[.](js|jsx|ts|tsx)
.*/.*[.]umd[.]js
.*/.*[.]vendor[.](js|ts)
.*/.*[.]wasm[.]js
.*/3rd(party)?/.*
.*/AppData/.*
.*/[Aa]ssembly[Ii]nfo.*
.*/bin/.*
.*/bitbucket-pipelines[.]yml
.*bootstrap.*[.](js|css)
.*/modernizr.*[.]js
.*/bower_components/.*
.*/branches/.*
.*/build/.*
.*/build[.]rs
.*/contrib/.*
.*/[Dd]ebug/.*
.*/dist/.*
.*/(java)?doc(s)?/.*
.*/environment[.][\w.]*[.](t|j)s
.*/example(s)?/.*
.*/external-files/.*
.*/gen(enerated)?/.*
.*/gradle.*[.]properties
.*/gradlew[.]bat
.*/InvisibleStyleSheet[.]css
.*/jdiff/.*
.*/jquery.*[.](js|css)
.*/library-preload[.]js
.*/LICENSE[.]txt
.*/locale/.*[.]js
.*/log4j.*[.]properties
.*/mapping.*[.]txt
.*/META-INF/.*
.*[Mm]ock.*
.*/[Mm]igrations?/.*
.*/node_modules/.*
.*/open3rd/.*
.*/obj/.*
.*/out/.*
.*/package-info[.]java
.*/[Pp]ods/.*
.*/polyfills[.]js
.*/proguard-rules[.]pro
.*/project[.]properties
.*/public/components/.*
.*/[Rr]elease/.*
.*/Reference[.]cs
.*/sap/.*/libs/.*[.]js
.*/sapui5-rt.*
.*/Service References/.*
.*sigridci.*
.*/sigrid(-metadata)?[.]ya?ml
.*/src/test/resources/.*
.*stub.*
.*/tags/.*
.*/target(-eclipse)?/.*
.*/[Tt]emporary[Gg]enerated[Ff]ile.*
.*/theme/.*[.]css
.*/themes/.*[.]css
.*/[Tt]hird(_|-)?[Pp]arty/.*
.*/[Vv]endor/.*
.*/widgets/com[.]mendix[.].*
.*/widgets/.*/com/mendix/.*
.*/.*vendor.*[.]js
.*pom[.]xml
.*/webpack[.][^/]*[.]js
.*/webpack[.](js|ts)
.*/wwwroot/assets/.*
.*/App[.]config
.*tinymce.*
.*toastify.*
.*x-editable.*
.*/.*[.]editorConfig[.]js
.*/.*[.]editorPreview[.]js
.*[.]gradle
.*[.]gradle[.]kts
.*[.]lock[.]hcl
.*AssemblyInfo[.]cs
.*/[.]sigrid/.*
""".strip().splitlines()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
