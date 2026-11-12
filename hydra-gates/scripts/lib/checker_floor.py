#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""The checker floor: an app's Common Ground checker results may never get worse.

Every app commits `.checker-floor.json` at its repository root:

    {
      "measured_at": "2026-11-12T12:00:00Z",
      "commit": "<sha the floor was measured on>",
      "tool": "common-ground-checker scan-local",
      "tool_version": "<checker package version>+<checker commit>",
      "scoring_digest": "<digest of the scoring configuration>",
      "score": 89,
      "criteria": {"license": "pass", "maintainability": "warn", ...}
    }

The values come from the Common Ground component checker's local scan
(`scripts/scan-local.ts` in the checker repository), run on the checkout with
the scoring configuration next to this file (checker_scoring.json). A status
ranks pass > warn > info > fail; the score is the checker's 0 to 100 score.

MODES
-----
record <checkout>                write the floor: per criterion the best status
                                 of the old floor and the measurement, and the
                                 higher score. --reset writes the measurement
                                 as is (after a checker or scoring change).
compare <checkout> --base-ref R  the floor is the best of the floor file
                                 committed at the merge base of R and HEAD and
                                 the checkout's own floor file. FAIL when a
                                 criterion's status is worse than the floor,
                                 the score is lower, or the change lowers or
                                 deletes the committed floor file.
measure <checkout>               print the measured floor values, write nothing.

--scan FILE reads a scan document the checker already wrote instead of
scanning. A scan of a clean commit is cached by commit, checker commit and
scoring digest in HYDRA_GATE_FLOOR_CACHE/checker (default
~/.cache/hydra-gates/floor-cache/checker), so a merge base is scanned once.

THE SCANNER
-----------
CHECKER_HOME names a checker checkout with its node modules installed. Without
it the checker is cloned from CHECKER_REPO at CHECKER_REF into
~/.cache/hydra-gates/checker and installed with `npm ci`, refreshed at most
once an hour. A scanner that cannot be installed or run, and a scan that
reports a criterion of the floor as unmeasured (its tool or service did not
run), is NO RESULT: exit 2, never a pass.

Output ends in one line starting with `[checker-floor]`.
Exit: 0 holds (record: written), 1 a criterion or the score got worse,
2 no result (usage, unreadable input, the scanner could not run, a floor
criterion unmeasured), 3 not applicable (no floor file), 4 improved: holds
and is better than the floor somewhere, raise it with `record`.
"""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time

TAG = "[checker-floor]"
FLOOR_FILE = ".checker-floor.json"
SCORING_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "checker_scoring.json")
RANK = {"fail": 0, "info": 1, "warn": 2, "pass": 3}
CHECKER_REPO = "https://github.com/rubenvdlinde/CommonGroundChecker"
CHECKER_REF = "scan/local-build"
SCAN_TIMEOUT = 1800

OK, WORSE, NO_RESULT, NOT_APPLICABLE, IMPROVED = 0, 1, 2, 3, 4


class FloorError(Exception):
    def __init__(self, message, code=NO_RESULT):
        super().__init__(message)
        self.code = code


def git(cwd, *args):
    p = subprocess.run(["git", "-c", "safe.directory=*", *args], cwd=cwd,
                       capture_output=True, text=True, errors="replace")
    return p.returncode, p.stdout.strip()


def cache_root():
    return os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")


def scan_cache_dir():
    base = os.environ.get("HYDRA_GATE_FLOOR_CACHE") or os.path.join(cache_root(), "hydra-gates", "floor-cache")
    return os.path.join(base, "checker")


def refresh_checker(home):
    """Clone or update the checker at CHECKER_REF and install it; at most once an hour."""
    repo = os.environ.get("CHECKER_REPO", CHECKER_REPO)
    ref = os.environ.get("CHECKER_REF", CHECKER_REF)
    os.makedirs(os.path.dirname(home), exist_ok=True)
    stamp = home + ".stamp"
    with open(home + ".lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        fresh = os.path.isfile(stamp) and time.time() - os.path.getmtime(stamp) < 3600
        if fresh and os.path.isfile(os.path.join(home, "node_modules", ".bin", "tsx")):
            return
        if not os.path.isdir(os.path.join(home, ".git")):
            p = subprocess.run(["git", "clone", "-q", repo, home], capture_output=True, text=True)
            if p.returncode != 0:
                raise FloorError(f"cannot clone the checker from {repo}: {p.stderr.strip()[-200:]}")
        rc, _ = git(home, "fetch", "-q", "origin", ref)
        if rc != 0:
            raise FloorError(f"cannot fetch {ref} of the checker")
        _, before = git(home, "rev-parse", "HEAD")
        git(home, "checkout", "-q", "--detach", "FETCH_HEAD")
        _, after = git(home, "rev-parse", "HEAD")
        if before != after or not os.path.isfile(os.path.join(home, "node_modules", ".bin", "tsx")):
            p = subprocess.run(["npm", "ci", "--no-audit", "--no-fund", "--ignore-scripts"], cwd=home,
                               capture_output=True, text=True, errors="replace")
            if p.returncode != 0:
                raise FloorError(f"npm ci failed for the checker: {(p.stderr or p.stdout).strip()[-200:]}")
        with open(stamp, "w"):
            pass


def checker_home():
    home = os.environ.get("CHECKER_HOME")
    if not home:
        home = os.path.join(cache_root(), "hydra-gates", "checker")
        refresh_checker(home)
    for need in ("scripts/scan-local.ts", "node_modules/.bin/tsx"):
        if not os.path.isfile(os.path.join(home, need)):
            raise FloorError(f"the checker at {home} has no {need}")
    return home


def scoring_path():
    path = os.environ.get("CHECKER_SCORING") or SCORING_FILE
    if not os.path.isfile(path):
        raise FloorError(f"scoring configuration {path} not found")
    return path


def file_digest(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


def clean_commit(tree):
    rc, head = git(tree, "rev-parse", "HEAD")
    if rc != 0:
        return None
    rc, dirty = git(tree, "status", "--porcelain")
    return head if rc == 0 and not dirty else None


def run_scan(tree):
    """The scan document of a checkout, from the cache when the commit is clean and scanned before."""
    home = checker_home()
    scoring = scoring_path()
    _, checker_sha = git(home, "rev-parse", "HEAD")
    commit = clean_commit(tree)
    cached = None
    if commit:
        key = hashlib.sha256(f"{commit}\n{checker_sha}\n{file_digest(scoring)}".encode()).hexdigest()[:24]
        cached = os.path.join(scan_cache_dir(), f"{key}.json")
        if os.path.isfile(cached):
            try:
                with open(cached) as fh:
                    return json.load(fh)
            except (OSError, ValueError):
                pass
    timeout = int(os.environ.get("CHECKER_SCAN_TIMEOUT", SCAN_TIMEOUT))
    with tempfile.TemporaryDirectory(prefix="checker-scan-") as tmp:
        out = os.path.join(tmp, "scan.json")
        cmd = [os.path.join(home, "node_modules", ".bin", "tsx"), os.path.join(home, "scripts", "scan-local.ts"),
               tree, "--scoring", scoring, "--out", out]
        try:
            p = subprocess.run(cmd, cwd=home, capture_output=True, text=True, errors="replace", timeout=timeout)
        except subprocess.TimeoutExpired:
            raise FloorError(f"the scan of {tree} did not finish within {timeout} s")
        except OSError as e:
            raise FloorError(f"the scanner could not start: {e}")
        if p.returncode != 0 or not os.path.isfile(out):
            tail = " ".join(p.stderr.strip().splitlines()[-2:])[-300:]
            raise FloorError(f"the scanner exited {p.returncode} on {tree}: {tail}")
        doc = read_scan(out)
    if cached:
        os.makedirs(os.path.dirname(cached), exist_ok=True)
        with open(cached, "w") as fh:
            json.dump(doc, fh)
    return doc


def read_scan(path):
    try:
        with open(path) as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as e:
        raise FloorError(f"cannot read {path}: {e}")
    if not isinstance(doc.get("criteria"), dict) or not isinstance(doc.get("score"), (int, float)):
        raise FloorError(f"{path} is not a checker scan document")
    for cid, c in doc["criteria"].items():
        if (c or {}).get("status") not in RANK:
            raise FloorError(f"{path}: criterion {cid} has no known status")
    return doc


def values_from_scan(doc):
    return {
        "commit": doc.get("commit"),
        "tool": doc.get("tool"),
        "tool_version": doc.get("toolVersion"),
        "scoring_digest": doc.get("scoringDigest"),
        "score": doc["score"],
        "criteria": {cid: c["status"] for cid, c in sorted(doc["criteria"].items())},
        "unmeasured": sorted(doc.get("unmeasured") or []),
    }


def measure(tree, scan_file=None):
    if scan_file:
        return values_from_scan(read_scan(scan_file))
    if not os.path.isdir(tree):
        raise FloorError(f"{tree} is not a directory")
    return values_from_scan(run_scan(os.path.abspath(tree)))


def read_floor(path):
    if not os.path.isfile(path):
        return None
    try:
        with open(path) as fh:
            data = json.load(fh)
    except (OSError, ValueError) as e:
        raise FloorError(f"cannot read {path}: {e}")
    if not isinstance(data.get("criteria"), dict) or any(s not in RANK for s in data["criteria"].values()):
        raise FloorError(f"{path} is not a checker floor file")
    return data


def floor_at_commit(tree, commit):
    rc, text = git(tree, "show", f"{commit}:{FLOOR_FILE}")
    if rc != 0:
        return None
    try:
        data = json.loads(text)
    except ValueError:
        raise FloorError(f"{FLOOR_FILE} at {commit[:10]} is not JSON")
    if not isinstance(data.get("criteria"), dict) or any(s not in RANK for s in data["criteria"].values()):
        raise FloorError(f"{FLOOR_FILE} at {commit[:10]} is not a checker floor file")
    return data


def best(a, b):
    """The per criterion best of two floors, and the higher score when both use the same scoring."""
    if a is None:
        return b
    if b is None:
        return a
    criteria = dict(a["criteria"])
    for cid, status in b["criteria"].items():
        if cid not in criteria or RANK[status] > RANK[criteria[cid]]:
            criteria[cid] = status
    out = dict(b)
    out["criteria"] = criteria
    if a.get("scoring_digest") == b.get("scoring_digest"):
        out["score"] = max(a.get("score", 0), b.get("score", 0))
    return out


def verdict(floor, head):
    """(worse, better, unmeasured, notes) of a measurement against a floor."""
    worse, better, unmeasured, notes = [], [], [], []
    for cid, status in sorted(floor["criteria"].items()):
        h = head["criteria"].get(cid)
        if cid in head["unmeasured"]:
            unmeasured.append(cid)
        elif h is None:
            worse.append((cid, status, "missing"))
        elif RANK[h] < RANK[status]:
            worse.append((cid, status, h))
        elif RANK[h] > RANK[status]:
            better.append((cid, status, h))
    for cid in sorted(set(head["criteria"]) - set(floor["criteria"])):
        notes.append(f"{cid} is not in the floor ({head['criteria'][cid]}); record it to hold it")
    if floor.get("scoring_digest") and floor.get("scoring_digest") != head.get("scoring_digest"):
        notes.append("the score is not compared: the floor was recorded with another scoring configuration")
    elif head["score"] < floor.get("score", 0):
        worse.append(("score", floor["score"], head["score"]))
    elif head["score"] > floor.get("score", 0):
        better.append(("score", floor["score"], head["score"]))
    if floor.get("tool_version") and floor.get("tool_version") != head.get("tool_version"):
        notes.append(f"the floor was recorded with checker {floor['tool_version']}, this scan is {head.get('tool_version')}")
    return worse, better, unmeasured, notes


def lowered(old, new):
    """Problems with a floor file between the merge base and the head."""
    if old is None:
        return []
    if new is None:
        return [f"the change deletes {FLOOR_FILE}"]
    out = []
    for cid, status in sorted(old["criteria"].items()):
        n = new["criteria"].get(cid)
        if n is None or RANK[n] < RANK[status]:
            out.append(f"the change lowers {cid} in {FLOOR_FILE} ({status} -> {n or 'removed'})")
    if old.get("scoring_digest") == new.get("scoring_digest") and new.get("score", 0) < old.get("score", 0):
        out.append(f"the change lowers the score in {FLOOR_FILE} ({old['score']} -> {new['score']})")
    return out


def table(floor, head):
    lines = [f"  {'':22} {'floor':>6} {'head':>6}"]
    for cid in sorted(set(floor["criteria"]) | set(head["criteria"])):
        h = head["criteria"].get(cid, "-")
        if cid in head["unmeasured"]:
            h = f"{h}?"
        lines.append(f"  {cid:22} {floor['criteria'].get(cid, '-'):>6} {h:>6}")
    lines.append(f"  {'score':22} {floor.get('score', '-'):>6} {head['score']:>6}")
    return "\n".join(lines)


def floor_document(values):
    return {
        "measured_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit": values.get("commit"),
        "tool": values.get("tool"),
        "tool_version": values.get("tool_version"),
        "scoring_digest": values.get("scoring_digest"),
        "score": values.get("score"),
        "criteria": dict(sorted(values["criteria"].items())),
    }


def emit(args, data):
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(data, fh, indent=1)


def cmd_measure(args):
    values = measure(args.checkout, args.scan)
    emit(args, {"mode": "measure", "head": values})
    print(json.dumps(floor_document(values), indent=2))
    if values["unmeasured"]:
        print(f"  unmeasured: {', '.join(values['unmeasured'])}")
    print(f"{TAG} measured: score {values['score']}, {len(values['criteria'])} criteria")
    return OK


def cmd_record(args):
    path = args.floor or os.path.join(args.checkout, FLOOR_FILE)
    values = measure(args.checkout, args.scan)
    if values["unmeasured"]:
        raise FloorError(f"not recorded: unmeasured criteria {', '.join(values['unmeasured'])}")
    old = None if args.reset else read_floor(path)
    new = best(old, values)
    emit(args, {"mode": "record", "floor": old, "head": values})
    with open(path, "w") as fh:
        json.dump(floor_document(new), fh, indent=2)
        fh.write("\n")
    kept = [cid for cid in (old or {}).get("criteria", {}) if old["criteria"][cid] != values["criteria"].get(cid)]
    extra = f"; kept the better floor for {', '.join(kept)}" if kept else ""
    print(f"{TAG} WRITTEN: {path}, score {new['score']}, {len(new['criteria'])} criteria{extra}")
    return OK


def cmd_compare(args):
    head_tree = os.path.abspath(args.checkout)
    if not os.path.isdir(head_tree):
        raise FloorError(f"{head_tree} is not a directory")
    rc, mb = git(head_tree, "merge-base", args.base_ref, "HEAD")
    if rc != 0 or not mb:
        raise FloorError(f"no merge base between {args.base_ref} and HEAD in {head_tree}")
    base_floor = floor_at_commit(head_tree, mb)
    head_floor = read_floor(args.floor or os.path.join(head_tree, FLOOR_FILE))
    floor = best(base_floor, head_floor)
    if floor is None:
        print(f"{TAG} NOT APPLICABLE: no {FLOOR_FILE} at the merge base {mb[:10]} or in the checkout")
        return NOT_APPLICABLE
    problems = lowered(base_floor, head_floor)
    head = measure(head_tree, args.scan)
    worse, better, unmeasured, notes = verdict(floor, head)
    emit(args, {"mode": "compare", "merge_base": mb, "floor": floor, "head": head, "worse": worse,
                "better": better, "unmeasured": unmeasured, "problems": problems})
    print(table(floor, head))
    for cid, f, h in worse:
        print(f"  WORSE {cid}: {f} -> {h}")
    for p in problems:
        print(f"  {p}")
    for n in notes:
        print(f"  note: {n}")
    if worse or problems:
        what = ", ".join([f"{c} {f} -> {h}" for c, f, h in worse] + problems)
        print(f"{TAG} FAIL: worse than the checker floor (merge base {mb[:10]}): {what}")
        return WORSE
    if unmeasured:
        print(f"{TAG} NO RESULT: the scan did not measure {', '.join(unmeasured)}; this is not a pass")
        return NO_RESULT
    if better:
        what = ", ".join(f"{c} {f} -> {h}" for c, f, h in better)
        print(f"{TAG} IMPROVED: holds and is better than the floor ({what}); raise it: "
              f"python3 {os.path.abspath(__file__)} record {head_tree}")
        return IMPROVED
    print(f"{TAG} PASS: every criterion and the score hold the floor (merge base {mb[:10]})")
    return OK


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=("record", "compare", "measure"))
    ap.add_argument("checkout")
    ap.add_argument("--base-ref", help="compare: the floor committed at the merge base of REF and HEAD")
    ap.add_argument("--floor", help=f"the floor file (default <checkout>/{FLOOR_FILE})")
    ap.add_argument("--scan", help="read this scan document instead of scanning")
    ap.add_argument("--reset", action="store_true", help="record: write the measurement, ignoring the old floor")
    ap.add_argument("--json", help="write the values and the verdict here")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return NO_RESULT if e.code else OK
    if args.mode == "compare" and not args.base_ref:
        print(f"{TAG} NO RESULT: compare needs --base-ref")
        return NO_RESULT
    try:
        return {"record": cmd_record, "compare": cmd_compare, "measure": cmd_measure}[args.mode](args)
    except FloorError as e:
        label = "NOT APPLICABLE" if e.code == NOT_APPLICABLE else "NO RESULT"
        print(f"{TAG} {label}: {e}")
        return e.code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
