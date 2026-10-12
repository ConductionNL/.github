#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""gate-119 helper: procedure-code ratchet (decision 182).

Procedures are configuration, code is generic. An app that grows a
`BezwaarService` or a `WooPublicationController` is hard-coding a Dutch
procedure that should be a schema, a workflow or a template in configuration.
This gate counts the files that do it and holds the count to a committed
baseline, the way the custom-widget ratchet holds widgets.

WHAT COUNTS
-----------
PHP, JS, TS and Vue files under lib/ and src/ whose repo-relative path, or a
class/interface/trait/enum declared inside, contains a procedure token. The
token lists and the national-standard allowlist live in ONE file,
procedure_code_tokens.json next to this script. See its $comment.

THE RATCHET
-----------
The baseline is `.procedure-code-baseline.json` in the app root: {"count": N}.

  * no baseline file          -> NOT APPLICABLE (exit 4). Never PASS.
  * count  > baseline          -> FAIL: the change added procedure-named code.
  * count  < baseline          -> FAIL: the change removed some, so it must
                                  lower the baseline in the same PR. The
                                  message gives the number to write.
  * count == baseline          -> PASS.
  * baseline raised by the change (needs --base) -> FAIL. A ratchet whose
    ceiling can be lifted in the same PR that exceeds it is not a ratchet.
  * baseline unreadable        -> FAIL, naming the file.

Usage:
    check_procedure_code.py <app-dir> [--base <ref>] [--ref <ref>] [--config <file>]
                            [--list] [--json]

  --ref   count the tree of a git ref (git ls-tree + git grep) instead of the
          working tree. Read-only. This is how the fleet baselines were
          measured, and it agrees with the working-tree mode on a clean
          checkout of the same commit.
  --base  the ref the change started from, to compare baselines.
  --list  print every counted file.

Output always ends in one of
    [gate-119] procedure-code: counted N file(s), baseline B
    [gate-119] procedure-code: FAIL: K finding(s)
and exit status is a boolean: 0 clean, 1 findings, 4 no baseline (not
applicable), 2 the checker itself could not run. A traceback is exit 1 with
no summary line, which the runner reports as WIRING, never as a finding
(the gate-29 lesson: a count in the exit byte cannot tell a crash from a
finding).
"""

import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(HERE, "procedure_code_tokens.json")
BASELINE_NAME = ".procedure-code-baseline.json"

DECL_RE = re.compile(
    r"^\s*(?:export\s+(?:default\s+)?)?(?:(?:abstract|final|readonly)\s+)*"
    r"(?:class|interface|trait|enum)\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)
WORD_RE = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+")


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    for key in ("roots", "extensions", "substringTokens", "wordTokens", "allow"):
        if key not in cfg:
            raise ValueError("config %s lacks %r" % (path, key))
    cfg["substringTokens"] = [t.lower() for t in cfg["substringTokens"]]
    cfg["wordTokens"] = [t.lower() for t in cfg["wordTokens"]]
    cfg["allow"]["words"] = [w.lower() for w in cfg["allow"].get("words", [])]
    cfg["allow"]["pathPrefixes"] = [p.lower().rstrip("/") for p in cfg["allow"].get("pathPrefixes", [])]
    return cfg


def words_of(text):
    """Split a path or class name into lowercase words."""
    out = []
    for chunk in re.split(r"[^A-Za-z0-9]+", text):
        out.extend(w.lower() for w in WORD_RE.findall(chunk))
    return out


def _has_run(words, run):
    n = len(run)
    return any(words[i:i + n] == run for i in range(len(words) - n + 1))


def classify(path, class_names, cfg):
    """Return (counted, matched_tokens, excused_by). excused_by is '' unless excluded."""
    haystacks = [path] + list(class_names)
    low = [h.lower() for h in haystacks]
    wordlists = [words_of(h) for h in haystacks]
    hits = []
    for tok in cfg["substringTokens"]:
        if any(tok in h for h in low):
            hits.append(tok)
    for tok in cfg["wordTokens"]:
        if any(tok in ws for ws in wordlists):
            hits.append(tok)
    if not hits:
        return False, [], ""
    lp = path.lower()
    for pref in cfg["allow"]["pathPrefixes"]:
        if lp == pref or lp.startswith(pref + "/"):
            return False, hits, "path:" + pref
    for aw in cfg["allow"]["words"]:
        run = aw.split("-")
        if any(_has_run(ws, run) for ws in wordlists):
            return False, hits, "word:" + aw
    return True, hits, ""


def _in_scope(path, cfg):
    parts = path.split("/")
    if parts[0] not in cfg["roots"]:
        return False
    if any(p in cfg.get("ignoreDirs", []) for p in parts[:-1]):
        return False
    return path.rsplit(".", 1)[-1].lower() in cfg["extensions"] and "." in parts[-1]


def _git(app, *args):
    return subprocess.run(["git", "-c", "safe.directory=*", "-C", app] + list(args),
                          capture_output=True, text=True, errors="replace")


def collect_working(app, cfg):
    """path -> [class names], for the working tree (tracked files when in git)."""
    r = _git(app, "ls-files", "-z", "--", *cfg["roots"])
    if r.returncode == 0 and r.stdout:
        paths = [p for p in r.stdout.split("\0") if p]
    else:
        paths = []
        for root in cfg["roots"]:
            for dp, dn, fn in os.walk(os.path.join(app, root)):
                dn[:] = [d for d in dn if d not in cfg.get("ignoreDirs", [])]
                for f in fn:
                    paths.append(os.path.relpath(os.path.join(dp, f), app).replace(os.sep, "/"))
    found = {}
    for p in sorted(set(paths)):
        if not _in_scope(p, cfg) or not os.path.isfile(os.path.join(app, p)):
            continue
        try:
            with open(os.path.join(app, p), encoding="utf-8", errors="replace") as fh:
                found[p] = DECL_RE.findall(fh.read())
        except OSError:
            found[p] = []
    return found


def collect_ref(app, ref, cfg):
    r = _git(app, "ls-tree", "-r", "--name-only", "-z", ref, "--", *cfg["roots"])
    if r.returncode != 0:
        raise RuntimeError("git ls-tree %s failed: %s" % (ref, r.stderr.strip()))
    found = {p: [] for p in r.stdout.split("\0") if p and _in_scope(p, cfg)}
    g = _git(app, "grep", "-I", "-n", "--no-color", "-E",
             r"^\s*(export\s+(default\s+)?)?((abstract|final|readonly)\s+)*(class|interface|trait|enum)\s+[A-Za-z_]",
             ref, "--", *cfg["roots"])
    if g.returncode not in (0, 1):
        raise RuntimeError("git grep %s failed: %s" % (ref, g.stderr.strip()))
    prefix = ref + ":"
    for line in g.stdout.splitlines():
        if not line.startswith(prefix):
            continue
        rest = line[len(prefix):]
        path, _, tail = rest.partition(":")
        _, _, text = tail.partition(":")
        if path in found:
            found[path].extend(DECL_RE.findall(text))
    return found


def read_baseline(app, ref=None):
    """Return (state, value): ('missing', None) | ('ok', int) | ('bad', reason)."""
    if ref:
        r = _git(app, "show", "%s:%s" % (ref, BASELINE_NAME))
        if r.returncode != 0:
            return "missing", None
        raw = r.stdout
    else:
        p = os.path.join(app, BASELINE_NAME)
        if not os.path.isfile(p):
            return "missing", None
        with open(p, encoding="utf-8") as fh:
            raw = fh.read()
    try:
        data = json.loads(raw)
        n = data["count"]
        if isinstance(n, bool) or not isinstance(n, int) or n < 0:
            raise ValueError("count must be a non-negative integer")
        return "ok", n
    except (ValueError, KeyError, TypeError) as exc:
        return "bad", "%s is not a valid baseline (%s)" % (BASELINE_NAME, exc)


def count_tree(app, cfg, ref=None):
    files = collect_ref(app, ref, cfg) if ref else collect_working(app, cfg)
    counted, excused = [], []
    for path, names in sorted(files.items()):
        ok, hits, why = classify(path, names, cfg)
        if ok:
            counted.append((path, hits))
        elif why:
            excused.append((path, why))
    return counted, excused


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("app")
    ap.add_argument("--base")
    ap.add_argument("--ref")
    ap.add_argument("--config", default=os.environ.get("HYDRA_GATE_PROCEDURE_CONFIG") or DEFAULT_CONFIG)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        cfg = load_config(a.config)
        counted, excused = count_tree(a.app, cfg, a.ref)
    except (OSError, ValueError, RuntimeError) as exc:
        print("[gate-119] procedure-code: ERROR: %s" % exc)
        return 2
    n = len(counted)
    if a.json:
        print(json.dumps({"count": n, "excluded": len(excused)}))
        return 0
    if a.list:
        for path, hits in counted:
            print("  counted %s [%s]" % (path, ",".join(hits)))
        for path, why in excused:
            print("  allowlisted %s (%s)" % (path, why))
    state, base_n = read_baseline(a.app, a.ref)
    if state == "missing":
        print("[gate-119] procedure-code: counted %d file(s), no %s" % (n, BASELINE_NAME))
        return 4
    findings = []
    if state == "bad":
        findings.append("  %s" % base_n)
    else:
        if n > base_n:
            findings.append("  %d procedure-named file(s), baseline %d: the change added %d. Procedures are configuration "
                            "(decision 182); put it in a schema, workflow or template. Counted files: see --list." % (n, base_n, n - base_n))
        elif n < base_n:
            findings.append("  %d procedure-named file(s), baseline %d: the change removed %d, so lower %s to "
                            '{"count": %d} in this same PR.' % (n, base_n, base_n - n, BASELINE_NAME, n))
        if a.base:
            bstate, bn = read_baseline(a.app, a.base)
            if bstate == "ok" and base_n > bn:
                findings.append("  %s was raised from %d to %d. The baseline only goes down." % (BASELINE_NAME, bn, base_n))
    print("[gate-119] procedure-code: counted %d file(s), baseline %s, %d allowlisted" %
          (n, base_n if state == "ok" else "unreadable", len(excused)))
    if findings:
        for f in findings:
            print(f)
        print("[gate-119] procedure-code: FAIL: %d finding(s)" % len(findings))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
