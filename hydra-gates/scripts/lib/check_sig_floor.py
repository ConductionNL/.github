#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""gate-123 helper: the SIG score floor, checked on every change.

Gate 122 ratchets single units. This gate guards the app's whole risk profile:
every SIG 4-star check the app meets must still be met after the change, and
the set of guarded checks only grows.

A CHECK is one row of gate 122's report, named as `checks_of()` names it:
`php unit_size >30`, `vue unit_complexity >10`, `php duplication`,
`php module_coupling >20`, `php component_independence` and so on. The
measurement is gate 122's report (lizard 1.24.3, Sigrid's default excludes,
the app's sigrid.yaml excludes, SIG's 6-line window duplication). The jscpd
cross-check is not needed for any check, so it does not run here.

THE FLOOR
---------
`.github/sig-floor.json` in the app lists the checks the app has committed to.
`write` generates it from the current tree. The floor that judges a change is

    the committed floor AT THE BASE  ∪  every check met at the merge base

so a change can neither lower its own floor (the file is read from the base)
nor lose a check development already meets, even before the file is raised.

VERDICT, per floored check that the head misses
    met at the base                     NEW: the change breaks it -> FAIL
    missed at the base, head worse      NEW: it erodes a broken floor -> FAIL
    missed at the base, head not worse  INHERITED: development must fix
                                        forward; reported, not counted
A change that removes a check from the committed floor file fails as well.

A floored check the head no longer measures at all (its language left the
measured scope) fails, unless the same change edits sigrid.yaml: an explicit
scope change may take checks out of the floor, file included. A check that the
base did not measure either left in an earlier change and is not judged again.

Without a floor file the gate is NOT APPLICABLE (exit 4) before any tool is
loaded or any base resolved.

The 5-star checks (half of every 4-star limit, gate 122's five-star profile)
are reported next to the 4-star ones and never block.

When the head meets checks the committed floor does not list, `--proposed`
receives the raised floor file, for the workflow to offer as a pull request.

UNIT CACHE
----------
lizard is the slow part. `--cache FILE` keeps each file's units keyed by
(lizard version, unit reader version, extension, content), so a run re-reads
only the files whose content it has not seen. The base and the head share almost every file.

Usage:
    check_sig_floor.py check <app-dir> [--base-ref REF] [--floor PATH]
                       [--cache FILE] [--md FILE] [--json FILE] [--proposed FILE]
    check_sig_floor.py write <app-dir> [--floor PATH] [--cache FILE]

Output ends in one of
    [gate-123] sig-floor: PASS: ...
    [gate-123] sig-floor: FAIL: N floored check(s) ...
    [gate-123] sig-floor: wrote ...
Exit status: 0 pass (or written), 1 a floored check is lost, 3 the base does not
resolve, 4 no floor file, 5 a pinned tool is unavailable. A traceback is exit 1
with no summary line, which the runner reports as WIRING, never as a finding.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_sig_maintainability as sig  # noqa: E402

GATE = "[gate-123] sig-floor"
FLOOR_PATH = ".github/sig-floor.json"
SCHEMA = 1


# --------------------------------------------------------------------------
# measuring
# --------------------------------------------------------------------------

class CachedUnitReader(sig.UnitReader):
    """gate 122's UnitReader with a content-keyed cache. A file lizard did not
    finish in time is not cached: that depends on the machine, not the file."""

    def __init__(self, lizard, cache):
        super().__init__(lizard)
        self.cache = cache
        self.used = set()
        self.hits = self.misses = 0

    @staticmethod
    def key(rel, lang, code):
        h = hashlib.sha256()
        h.update(f"{sig.LIZARD_VERSION}\0{sig.UNIT_READER_VERSION}\0{os.path.splitext(rel)[1].lower()}\0{lang}\0".encode())
        h.update(code.encode("utf-8", errors="replace"))
        return h.hexdigest()

    def units(self, rel, lang, code):
        k = self.key(rel, lang, code)
        self.used.add(k)
        hit = self.cache.get(k)
        if hit is not None:
            self.hits += 1
            if hit.get("skipped"):
                self.skipped.append({"file": rel, "reason": hit["skipped"]})
                return []
            return [dict(u, file=rel, lang=lang) for u in hit["units"]]
        self.misses += 1
        before = len(self.skipped)
        out = super().units(rel, lang, code)
        if len(self.skipped) > before:
            reason = self.skipped[-1]["reason"]
            if "did not finish" not in reason:
                self.cache[k] = {"skipped": reason}
            return out
        self.cache[k] = {"units": [{f: u[f] for f in u if f not in ("file", "lang")} for u in out]}
        return out


def load_cache(path):
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    if data.get("lizard") != sig.LIZARD_VERSION or data.get("reader") != sig.UNIT_READER_VERSION:
        return {}
    return data.get("files", {})


def save_cache(path, cache, used):
    if not path:
        return
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as fh:
        json.dump({"lizard": sig.LIZARD_VERSION, "reader": sig.UNIT_READER_VERSION, "files": {k: v for k, v in cache.items() if k in used}}, fh)


def measure(app, lizard, reader):
    """gate 122's four-star report of `app`, without the jscpd cross-check."""
    return sig.build_report(app, lizard, None, "four-star", reader=reader)


def check_rows(report, profile_name):
    """{label: {"share", "limit", "ok", "higher_is_better"}} for every check of
    the report, judged against `profile_name`. Labels are gate 122's."""
    prof = sig.PROFILES[profile_name]
    rows = {}
    for lang, d in report["languages"].items():
        for prop in ("unit_size", "unit_complexity", "unit_interfacing"):
            for i, row in enumerate(d[prop]):
                cap = prof["limits"][prop][i][1]
                rows[f"{lang} {prop} >{row['above']}"] = {
                    "share": row["share"], "limit": cap, "ok": row["share"] <= cap, "higher_is_better": False}
        dup = d.get("duplication")
        if dup:
            rows[f"{lang} duplication"] = {"share": dup["share"], "limit": prof["duplication"],
                                           "ok": dup["share"] <= prof["duplication"], "higher_is_better": False}
    for lang, s in report.get("structure", {}).items():
        if not s:
            continue
        for i, row in enumerate(s["module_coupling"]):
            cap = prof["limits"]["module_coupling"][i][1]
            rows[f"{lang} module_coupling >{row['above']}"] = {
                "share": row["share"], "limit": cap, "ok": row["share"] <= cap, "higher_is_better": False}
        h = s["component_independence"]["hidden_share"]
        rows[f"{lang} component_independence"] = {
            "share": h, "limit": prof["independence_min"], "ok": h >= prof["independence_min"],
            "higher_is_better": True}
    return rows


def worse(row_head, row_base):
    if row_base is None:
        return True
    if row_head["higher_is_better"]:
        return row_head["share"] < row_base["share"]
    return row_head["share"] > row_base["share"]


# --------------------------------------------------------------------------
# git
# --------------------------------------------------------------------------

def git(app, *args):
    p = subprocess.run(["git", "-c", "safe.directory=*", *args], cwd=app,
                       capture_output=True, text=True, errors="replace")
    return p.returncode, p.stdout


def floor_at(app, ref, path):
    """The committed floor (a list of labels) at `ref`, or None when absent."""
    rc, out = git(app, "show", f"{ref}:{path}")
    if rc != 0:
        return None
    return parse_floor(out, f"{ref}:{path}")


def parse_floor(text, where):
    data = json.loads(text)
    checks = data.get("checks")
    if not isinstance(checks, list) or not all(isinstance(c, str) for c in checks):
        raise ValueError(f"{where}: `checks` must be a list of check names")
    return checks


def floor_document(app, labels):
    head = (git(app, "rev-parse", "HEAD")[1] or "").strip() or None
    return {
        "about": "SIG 4-star checks this app meets and must keep meeting (gate 123, sig-floor). "
                 "Generated by check_sig_floor.py write; raised by the workflow, never lowered by hand.",
        "schema": SCHEMA,
        "profile": "four-star",
        "tools": {"lizard": sig.LIZARD_VERSION},
        "measured_at": head,
        "checks": sorted(labels),
    }


def floor_present(app, path, base_ref):
    """Whether a floor file exists at the head or at `base_ref`. Asked before
    any tool is loaded or any merge base resolved, so an app without a floor
    is NOT APPLICABLE however its tooling or history looks."""
    if os.path.isfile(os.path.join(app, path)):
        return True
    return bool(base_ref) and git(app, "cat-file", "-e", f"{base_ref}:{path}")[0] == 0


def sigrid_changed(app, mb):
    rc, out = git(app, "diff", "--name-only", mb, "HEAD", "--", "sigrid.yaml", "sigrid.yml")
    return rc == 0 and bool(out.strip())


def measure_base(app, mb, lizard, reader):
    """Measure the tree at commit `mb` in a temporary worktree."""
    tmp = tempfile.mkdtemp(prefix="sig-floor-base-")
    wt = os.path.join(tmp, os.path.basename(os.path.abspath(app)))
    try:
        rc, _ = git(app, "worktree", "add", "--quiet", "--detach", wt, mb)
        if rc != 0:
            return None
        return measure(wt, lizard, reader)
    finally:
        git(app, "worktree", "remove", "--force", wt)
        shutil.rmtree(tmp, ignore_errors=True)
        git(app, "worktree", "prune")


# --------------------------------------------------------------------------
# verdict
# --------------------------------------------------------------------------

def judge(floor, head4, base4, scope_changed=False):
    """(new, inherited) breaches of `floor`: lists of (label, why).

    A floored check the head no longer measures may leave the floor only when
    the change edits sigrid.yaml (an explicit scope change), or when the base
    did not measure it either (it left in an earlier change)."""
    new, inherited = [], []
    for label in sorted(floor):
        h = head4.get(label)
        b = base4.get(label) if base4 is not None else None
        if h is None:
            if scope_changed or (base4 is not None and b is None):
                inherited.append((label, "no longer measured; it left the measured scope through sigrid.yaml"))
            else:
                new.append((label, "no longer measured (its language or module structure left the measured scope "
                                   "without a sigrid.yaml change)"))
            continue
        if h["ok"]:
            continue
        cmp = "<" if h["higher_is_better"] else ">"
        why = f"{sig.pct(h['share'])} {cmp} limit {sig.pct(h['limit'])}"
        if b is not None and b["ok"]:
            new.append((label, f"{why}; met at the base ({sig.pct(b['share'])})"))
        elif base4 is None:
            new.append((label, why))
        elif worse(h, b):
            new.append((label, f"{why}; already missed at the base ({sig.pct(b['share'])}) and this change makes it worse"))
        else:
            inherited.append((label, f"{why}; already missed at the base ({sig.pct(b['share']) if b else 'n/a'})"))
    return new, inherited


def markdown(app_name, floor, head4, head5, base4, new, inherited, lowered, proposed):
    def cell(r):
        return "n/a" if r is None else sig.pct(r["share"]) + ("" if r["ok"] else " ✗")

    out = [f"## SIG score floor: {app_name}", "",
           "Every 4-star check in the floor must stay met. 5-star (half of each 4-star limit) "
           "is reported only and never blocks. ✗ marks a miss.", "",
           "| check | base | head | 4-star limit | floored | 5-star |", "|---|---|---|---|---|---|"]
    for label in sorted(set(head4) | set(floor) | set(base4 or {})):
        h, b, h5 = head4.get(label), (base4 or {}).get(label), head5.get(label)
        lim = h or b
        lim = (">= " if lim["higher_is_better"] else "<= ") + sig.pct(lim["limit"]) if lim else "n/a"
        out.append(f"| {label} | {cell(b) if base4 is not None else '-'} | {cell(h)} | {lim} "
                   f"| {'yes' if label in floor else ''} | {cell(h5)} |")
    met4 = sum(1 for r in head4.values() if r["ok"])
    met5 = sum(1 for r in head5.values() if r["ok"])
    out += ["", f"Head: {met4} of {len(head4)} 4-star checks met, {met5} of {len(head5)} 5-star checks met; "
                f"{len(floor)} check(s) floored."]
    if new:
        out += ["", "**Floor broken by this change:**"] + [f"- {lbl}: {why}" for lbl, why in new]
    if lowered:
        out += ["", "**This change removes checks from the committed floor:** " + ", ".join(lowered)]
    if inherited:
        out += ["", "Inherited (development already misses these; fix forward):"] + \
               [f"- {lbl}: {why}" for lbl, why in inherited]
    five_missed = sorted(lbl for lbl, r in head5.items() if not r["ok"])
    if five_missed:
        out += ["", f"5-star findings (not blocking): {len(five_missed)} check(s) above half the 4-star limit: "
                + ", ".join(five_missed)]
    if proposed:
        out += ["", "The head meets checks the committed floor does not list yet: " + ", ".join(proposed)
                + ". The floor is raised after this reaches development."]
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------

def cmd_write(args, lizard):
    cache = load_cache(args.cache)
    reader = CachedUnitReader(lizard, cache)
    report = measure(args.app, lizard, reader)
    save_cache(args.cache, cache, reader.used)
    if not report["files"]:
        print(f"{GATE}: no measured source file in this repository, so there is no floor to write")
        return 4
    rows = check_rows(report, "four-star")
    met = [lbl for lbl, r in rows.items() if r["ok"]]
    path = os.path.join(args.app, args.floor)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(floor_document(args.app, met), fh, indent=1)
        fh.write("\n")
    print(f"{GATE}: wrote {args.floor}: {len(met)} of {len(rows)} 4-star checks met and floored")
    return 0


def no_floor(path):
    print(f"{GATE}: this repository has no {path}; generate it with "
          f"`check_sig_floor.py write .` to adopt the floor")
    return 4


def cmd_check(args, lizard):
    app = args.app
    mb = None
    if args.base_ref:
        rc, out = git(app, "merge-base", args.base_ref, "HEAD")
        if rc != 0 or not out.strip():
            print(f"{GATE}: the base '{args.base_ref}' has no merge base with HEAD, so the floor cannot be read")
            return 3
        mb = out.strip()

    head_file = os.path.join(app, args.floor)
    head_floor = parse_floor(sig.read_text(head_file), args.floor) if os.path.isfile(head_file) else None
    base_floor = floor_at(app, mb, args.floor) if mb else None
    committed = base_floor if base_floor is not None else head_floor
    if committed is None:
        return no_floor(args.floor)
    scope_changed = bool(mb) and sigrid_changed(app, mb)
    removed = sorted(set(base_floor) - set(head_floor or [])) if base_floor is not None else []

    cache = load_cache(args.cache)
    reader = CachedUnitReader(lizard, cache)
    head_report = measure(app, lizard, reader)
    head4, head5 = check_rows(head_report, "four-star"), check_rows(head_report, "five-star")
    base4 = None
    if mb:
        base_report = measure_base(app, mb, lizard, reader)
        if base_report is None:
            print(f"{GATE}: could not check out the merge base {mb[:12]} to measure it")
            return 3
        base4 = check_rows(base_report, "four-star")
    save_cache(args.cache, cache, reader.used)

    floor = set(committed) | ({lbl for lbl, r in base4.items() if r["ok"]} if base4 else set())
    new, inherited = judge(floor, head4, base4, scope_changed)
    # A check may leave the file only when it also left the measurement, as judge() allows.
    gone = {lbl for lbl, _why in inherited if lbl not in head4}
    lowered = [lbl for lbl in removed if lbl not in gone]
    met_head = {lbl for lbl, r in head4.items() if r["ok"]}
    raise_to = sorted(met_head - set(committed))
    proposal = (set(committed) - gone) | met_head
    if args.proposed and proposal != set(committed) and not new and not lowered:
        with open(args.proposed, "w") as fh:
            json.dump(floor_document(app, proposal), fh, indent=1)
            fh.write("\n")

    md = markdown(os.path.basename(os.path.abspath(app)), floor, head4, head5, base4,
                  new, inherited, lowered, raise_to)
    if args.md:
        with open(args.md, "w") as fh:
            fh.write(md)
    if args.json:
        with open(args.json, "w") as fh:
            json.dump({"floor": sorted(floor), "committed": sorted(committed), "head": head4,
                       "head_five_star": head5, "base": base4, "new": new, "inherited": inherited,
                       "lowered": lowered, "raise": raise_to}, fh, indent=1)

    for s in head_report["skipped_files"]:
        print(f"  unverified (lizard could not read it): {s['file']}: {s['reason']}")
    for lbl, why in new:
        print(f"  {lbl}: {why}")
    if lowered:
        print(f"  this change removes {len(lowered)} check(s) from the committed floor: {', '.join(lowered)}")
    for lbl, why in inherited:
        print(f"  inherited, not counted: {lbl}: {why}")
    five = sum(1 for r in head5.values() if not r["ok"])
    tail = (f"{len(met_head)} of {len(head4)} 4-star checks met at head; {five} 5-star finding(s), not blocking; "
            f"{len(inherited)} inherited; lizard {sig.LIZARD_VERSION}, cache {reader.hits} hit(s) {reader.misses} miss(es)"
            + (f"; {len(raise_to)} check(s) above the committed floor" if raise_to else ""))
    if new or lowered:
        print(f"{GATE}: FAIL: {len(new) + len(lowered)} floored check(s) lost "
              f"({len(new)} no longer met, {len(lowered)} removed from the floor file); {tail}")
        return 1
    print(f"{GATE}: PASS: {len(floor)} floored check(s) held; {tail}")
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    c = sub.add_parser("check")
    c.add_argument("app")
    c.add_argument("--base-ref")
    c.add_argument("--floor", default=FLOOR_PATH)
    c.add_argument("--cache")
    c.add_argument("--md")
    c.add_argument("--json")
    c.add_argument("--proposed")
    w = sub.add_parser("write")
    w.add_argument("app")
    w.add_argument("--floor", default=FLOOR_PATH)
    w.add_argument("--cache")
    args = ap.parse_args(argv)
    args.app = os.path.abspath(args.app)
    if args.mode == "check" and not floor_present(args.app, args.floor, args.base_ref):
        return no_floor(args.floor)
    lizard, why = sig.load_lizard()
    if not lizard:
        print(f"{GATE}: tooling: {why}")
        return 5
    if args.mode == "write":
        return cmd_write(args, lizard)
    return cmd_check(args, lizard)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
