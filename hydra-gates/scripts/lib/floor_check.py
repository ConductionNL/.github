#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""The maintainability floor: an app's measured ratings may never go down.

Every app commits `.maintainability-floor.json` at its repository root:

    {
      "measured_at": "2026-11-11T16:40:00Z",
      "commit": "<sha the floor was measured on>",
      "tool_version": "<estimator digest, lizard and jscpd pins, profile>",
      "tolerance": 0.01,
      "overall": 3.91,
      "overall_range": [3.91, 4.02],
      "properties": {"volume": null, "duplication": 3.11, "unit_size": 3.71, ...}
    }

The ratings come from gate 122's estimator next to this file (its `report`
mode, `--profile five-star --components-from-scope`), rounded to 2 decimals, on the 0.5 to 5.5 scale. `overall` is the low end of the
estimator's overall range (power mean p = -1), the conservative reading;
`overall_range` is recorded for reference and is not compared. Volume is not
rated by the 2026 model and is recorded as null. A null on either side is not
compared, except that a value the base measured and the head no longer
measures fails: a property cannot leave the floor by leaving the scope.

TOLERANCE
---------
A value may drop by at most 0.01 (TOLERANCE, `--tolerance`). The ratings are
rounded to 2 decimals, so 0.01 is one rounding step: the same tree measured
twice can differ by that much when a share sits on a rounding edge. A drop of
more than 0.01 is a real change. `raise` takes no tolerance: it writes a new
floor only when no value is lower than the old one.

MODES
-----
compare <base> <head>            fail when any value of head drops more than
compare <head> --base-ref REF    the tolerance below base. With --base-ref the
                                 base is the merge base of REF and HEAD in the
                                 head clone, checked out into a temporary
                                 shared clone. When both trees are directories
                                 the committed floor file may be raised but
                                 not lowered or deleted by the change.
against-floor <clone>            fail when the clone measures below its
                                 committed floor (or --floor FILE).
raise <clone>                    write a new floor (or --floor FILE) only when
                                 every value is >= the old one and at least one
                                 is higher; with no floor file, write the first.
measure <clone>                  print the clone's floor values, write nothing.

A tree argument is a directory (measured) or a JSON file: a gate 122 report
or a floor file, read as is. The JSON form is what tests and callers that
already measured pass.

Measurements of a clean commit are cached by commit and estimator digest in
HYDRA_GATE_FLOOR_CACHE (default ~/.cache/hydra-gates/floor-cache), so a merge
base is measured once. A tree with uncommitted changes is never cached. The
estimator measures tracked files only: an untracked file is not measured.

Output ends in one line starting with `[maintainability-floor]`.
Exit: 0 holds (or written), 1 a value dropped (raise: refused), 2 usage or an
unreadable input, 3 raise: nothing higher to write, 4 not applicable (no floor
file, no measured source), 5 a pinned tool is unavailable.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

TAG = "[maintainability-floor]"
FLOOR_FILE = ".maintainability-floor.json"
TOLERANCE = 0.01
PROFILE = "five-star"
PROPERTIES = ("volume", "duplication", "unit_size", "unit_complexity", "unit_interfacing",
              "module_coupling", "component_independence", "component_entanglement")
EPS = 1e-9

OK, DROP, USAGE, NOTHING, NOT_APPLICABLE, TOOLING = 0, 1, 2, 3, 4, 5


class FloorError(Exception):
    def __init__(self, message, code=USAGE):
        super().__init__(message)
        self.code = code


def estimator_path():
    return os.environ.get("MAINTAINABILITY_FLOOR_ESTIMATOR") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "check_sig_maintainability.py")


def tool_version(path):
    with open(path, "rb") as fh:
        data = fh.read()
    text = data.decode("utf-8", "replace")
    pins = []
    for name, var in (("lizard", "LIZARD_VERSION"), ("jscpd", "JSCPD_VERSION")):
        m = re.search(rf'^{var}\s*=\s*"([^"]+)"', text, re.M)
        pins.append(f"{name} {m.group(1) if m else '?'}")
    return f"estimator sha256:{hashlib.sha256(data).hexdigest()[:12]}; {'; '.join(pins)}; profile {PROFILE}"


def r2(x):
    return None if x is None else round(float(x), 2)


def git(cwd, *args):
    p = subprocess.run(["git", "-c", "safe.directory=*", *args], cwd=cwd,
                       capture_output=True, text=True, errors="replace")
    return p.returncode, p.stdout.strip()


def values_from_report(report):
    """Floor values of one gate 122 report."""
    rating = report.get("rating") or {}
    rng = (rating.get("overall") or {}).get("range")
    props = {k: r2((rating.get("properties", {}).get(k) or {}).get("rating")) for k in PROPERTIES}
    return {"overall": r2(rng[0]) if rng else None,
            "overall_range": [r2(rng[0]), r2(rng[1])] if rng else None,
            "properties": props}


def read_json_tree(path):
    try:
        with open(path) as fh:
            data = json.load(fh)
    except (OSError, ValueError) as e:
        raise FloorError(f"cannot read {path}: {e}")
    if "rating" in data:
        return values_from_report(data)
    if "properties" in data:
        return {"overall": data.get("overall"), "overall_range": data.get("overall_range"),
                "properties": {k: data["properties"].get(k) for k in PROPERTIES}}
    raise FloorError(f"{path} is neither a gate 122 report nor a floor file")


def cache_dir():
    return os.environ.get("HYDRA_GATE_FLOOR_CACHE") or os.path.join(
        os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache"),
        "hydra-gates", "floor-cache")


def clean_commit(clone):
    rc, head = git(clone, "rev-parse", "HEAD")
    if rc != 0:
        return None
    rc, dirty = git(clone, "status", "--porcelain", "--untracked-files=no")
    return head if rc == 0 and not dirty else None


def measure_dir(clone):
    est = estimator_path()
    if not os.path.isfile(est):
        raise FloorError(f"estimator not found at {est}", TOOLING)
    version = tool_version(est)
    commit = clean_commit(clone)
    cached = None
    if commit:
        key = hashlib.sha256(f"{commit}\n{version}".encode()).hexdigest()[:24]
        cached = os.path.join(cache_dir(), f"{key}.json")
        if os.path.isfile(cached):
            try:
                with open(cached) as fh:
                    return json.load(fh)
            except (OSError, ValueError):
                pass
    with tempfile.TemporaryDirectory(prefix="floor-") as tmp:
        out = os.path.join(tmp, "report.json")
        p = subprocess.run([sys.executable, est, "report", clone, "--profile", PROFILE,
                            "--components-from-scope", "--json", out],
                           capture_output=True, text=True, errors="replace")
        tail = (p.stdout + p.stderr).strip().splitlines()[-3:]
        if p.returncode == 4:
            raise FloorError(f"no measured source in {clone}", NOT_APPLICABLE)
        if p.returncode == 5:
            raise FloorError(f"estimator tooling unavailable: {' '.join(tail)}", TOOLING)
        if p.returncode != 0 or not os.path.isfile(out):
            raise FloorError(f"estimator exited {p.returncode} on {clone}: {' '.join(tail)}", TOOLING)
        with open(out) as fh:
            values = values_from_report(json.load(fh))
    values["commit"] = commit or git(clone, "rev-parse", "HEAD")[1]
    values["tool_version"] = version
    if cached:
        os.makedirs(os.path.dirname(cached), exist_ok=True)
        with open(cached, "w") as fh:
            json.dump(values, fh)
    return values


def measure(tree):
    if os.path.isdir(tree):
        return measure_dir(os.path.abspath(tree))
    if os.path.isfile(tree):
        return read_json_tree(tree)
    raise FloorError(f"{tree} is neither a directory nor a JSON file")


def keys(values):
    yield "overall", values.get("overall")
    for k in PROPERTIES:
        yield k, (values.get("properties") or {}).get(k)


def drops(base, head, tolerance):
    """[(key, base, head)] for every value of head more than tolerance below base."""
    head_values = dict(keys(head))
    out = []
    for k, b in keys(base):
        if b is None:
            continue
        h = head_values.get(k)
        if h is None or b - h > tolerance + EPS:
            out.append((k, b, h))
    return out


def rises(old, new):
    """(lower, higher): keys where new is below old, and keys where it is above."""
    new_values = dict(keys(new))
    lower, higher = [], []
    for k, o in keys(old):
        n = new_values.get(k)
        if o is None:
            if n is not None:
                higher.append(k)
            continue
        if n is None or n < o - EPS:
            lower.append(k)
        elif n > o + EPS:
            higher.append(k)
    return lower, higher


def fmt(v):
    return "none" if v is None else f"{v:.2f}"


def table(base, head, left, right):
    lines = [f"  {'':24} {left:>8} {right:>8}"]
    head_values = dict(keys(head))
    for k, b in keys(base):
        lines.append(f"  {k:24} {fmt(b):>8} {fmt(head_values.get(k)):>8}")
    return "\n".join(lines)


def read_floor(path):
    if not os.path.isfile(path):
        return None
    return read_json_tree(path)


def floor_document(values, tolerance):
    return {
        "measured_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit": values.get("commit"),
        "tool_version": values.get("tool_version"),
        "tolerance": tolerance,
        "overall": values.get("overall"),
        "overall_range": values.get("overall_range"),
        "properties": {k: (values.get("properties") or {}).get(k) for k in PROPERTIES},
    }


def write_floor(path, values, tolerance):
    with open(path, "w") as fh:
        json.dump(floor_document(values, tolerance), fh, indent=2)
        fh.write("\n")


def merge_base_snapshot(head, ref, tmp):
    rc, mb = git(head, "merge-base", ref, "HEAD")
    if rc != 0 or not mb:
        raise FloorError(f"no merge base between {ref} and HEAD in {head}")
    dest = os.path.join(tmp, "base")
    p = subprocess.run(["git", "-c", "safe.directory=*", "clone", "-q", "--shared", "--no-checkout", head, dest],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise FloorError(f"cannot snapshot {mb[:10]}: {p.stderr.strip()[:200]}")
    rc, _ = git(dest, "checkout", "-q", "--detach", mb)
    if rc != 0:
        raise FloorError(f"cannot check out {mb[:10]}")
    return dest, mb


def committed_floor_lowered(base_dir, head_dir):
    """Problems with the committed floor file between two directory trees."""
    old = read_floor(os.path.join(base_dir, FLOOR_FILE))
    if old is None:
        return []
    new = read_floor(os.path.join(head_dir, FLOOR_FILE))
    if new is None:
        return [f"the change deletes {FLOOR_FILE}"]
    lower, _ = rises(old, new)
    return [f"the change lowers {k} in {FLOOR_FILE}" for k in lower]


def cmd_compare(args):
    with tempfile.TemporaryDirectory(prefix="floor-base-") as tmp:
        if args.base_ref:
            if len(args.trees) != 1:
                raise FloorError("compare --base-ref takes one tree: the head clone")
            head_tree = args.trees[0]
            base_tree, mb = merge_base_snapshot(os.path.abspath(head_tree), args.base_ref, tmp)
            label = f"merge base {mb[:10]}"
        else:
            if len(args.trees) != 2:
                raise FloorError("compare takes <base> <head>, or <head> --base-ref REF")
            base_tree, head_tree = args.trees
            label = "base"
        base = measure(base_tree)
        head = measure(head_tree)
        problems = []
        if os.path.isdir(base_tree) and os.path.isdir(head_tree):
            problems = committed_floor_lowered(base_tree, head_tree)
    found = drops(base, head, args.tolerance)
    emit(args, {"mode": "compare", "base": base, "head": head, "drops": found, "problems": problems})
    print(table(base, head, "base", "head"))
    for k, b, h in found:
        print(f"  DROP {k}: {fmt(b)} -> {fmt(h)}")
    for p in problems:
        print(f"  {p}")
    if found or problems:
        what = ", ".join([f"{k} {fmt(b)} -> {fmt(h)}" for k, b, h in found] + problems)
        print(f"{TAG} FAIL: the change lowers the maintainability floor against the {label}: {what}")
        return DROP
    print(f"{TAG} PASS: no value drops more than {args.tolerance:.2f} against the {label}")
    return OK


def floor_path(args, clone):
    if args.floor:
        return args.floor
    if os.path.isdir(clone):
        return os.path.join(clone, FLOOR_FILE)
    raise FloorError("pass --floor FILE when the tree is a JSON file")


def cmd_against(args):
    path = floor_path(args, args.trees[0])
    floor = read_floor(path)
    if floor is None:
        print(f"{TAG} NOT APPLICABLE: no {FLOOR_FILE} at {path}")
        return NOT_APPLICABLE
    head = measure(args.trees[0])
    found = drops(floor, head, args.tolerance)
    emit(args, {"mode": "against-floor", "floor": floor, "head": head, "drops": found})
    print(table(floor, head, "floor", "measured"))
    if found:
        what = ", ".join(f"{k} {fmt(b)} -> {fmt(h)}" for k, b, h in found)
        print(f"{TAG} FAIL: below the committed floor: {what}")
        return DROP
    print(f"{TAG} PASS: at or above the committed floor (tolerance {args.tolerance:.2f})")
    return OK


def cmd_raise(args):
    clone = args.trees[0]
    path = floor_path(args, clone)
    old = read_floor(path)
    new = measure(clone)
    emit(args, {"mode": "raise", "floor": old, "head": new})
    if old is None:
        write_floor(path, new, args.tolerance)
        print(f"{TAG} WRITTEN: first floor at {path}, overall {fmt(new.get('overall'))}")
        return OK
    print(table(old, new, "floor", "measured"))
    lower, higher = rises(old, new)
    if lower:
        print(f"{TAG} REFUSED: not raised, lower than the floor: {', '.join(lower)}")
        return DROP
    if not higher:
        print(f"{TAG} UNCHANGED: every value equals the floor")
        return NOTHING
    write_floor(path, new, args.tolerance)
    print(f"{TAG} RAISED: {', '.join(higher)} at {path}")
    return OK


def cmd_measure(args):
    values = measure(args.trees[0])
    emit(args, {"mode": "measure", "head": values})
    print(json.dumps(floor_document(values, args.tolerance), indent=2))
    print(f"{TAG} measured: overall {fmt(values.get('overall'))}")
    return OK


def emit(args, data):
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(data, fh, indent=1)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=("compare", "against-floor", "raise", "measure"))
    ap.add_argument("trees", nargs="+")
    ap.add_argument("--base-ref", help="compare: the base is the merge base of REF and HEAD")
    ap.add_argument("--floor", help=f"the floor file (default <clone>/{FLOOR_FILE})")
    ap.add_argument("--tolerance", type=float, default=TOLERANCE)
    ap.add_argument("--json", help="write the measured values and the verdict here")
    args = ap.parse_args(argv)
    if args.mode != "compare" and len(args.trees) != 1:
        print(f"{TAG} {args.mode} takes one tree")
        return USAGE
    try:
        return {"compare": cmd_compare, "against-floor": cmd_against,
                "raise": cmd_raise, "measure": cmd_measure}[args.mode](args)
    except FloorError as e:
        label = {NOT_APPLICABLE: "NOT APPLICABLE", TOOLING: "TOOLING"}.get(e.code, "ERROR")
        print(f"{TAG} {label}: {e}")
        return e.code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
