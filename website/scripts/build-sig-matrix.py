#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Build website/src/data/sig-matrix.json from gate 122 five-star reports.

Usage:
    python3 website/scripts/build-sig-matrix.py <report-dir> [--date YYYY-MM-DD]
        [--clones DIR | --no-floors]

<report-dir> holds one `<app>.json` per app, written by
`check_sig_maintainability.py --profile five-star` (gate 122). Files with a
second dot in the name (`<app>.artifacts.json`, `<app>.nosy.json`) are skipped.
The date defaults to the newest report's modification date.

Each check is rated against the gate's own profiles: 5 when it meets the
five-star yardstick, 4 when it meets the 4-star limit, and "below" otherwise.
The guidance gives no limits under 4 stars, so lower stars are not estimated.

The floors, baselines and ratchets of each app (sig_floors.py) are read from
its `development` branch through `gh api`, or from local clones under
`--clones DIR/<app>`. `--no-floors` keeps the floors already in the output.
"""
import argparse
import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "hydra-gates", "scripts", "lib"))
import check_sig_maintainability as sig  # noqa: E402
import sig_floors  # noqa: E402

OUT = os.path.join(ROOT, "website", "src", "data", "sig-matrix.json")
FOUR, FIVE = sig.PROFILES["four-star"], sig.PROFILES["five-star"]
LANGUAGES = ["php", "javascript", "typescript", "vue", "python"]
UNIT_PROPS = [("unit_size", "unit size", ">"), ("unit_complexity", "unit complexity", ">"),
              ("unit_interfacing", "unit interfacing", ">=")]


def bound_label(sign, above):
    """Interfacing counts parameters from above + 1; the others count above the bound."""
    return f">={above + 1}" if sign == ">=" else f">{above}"


def rows_for(lang):
    """Every check of one language as (id, label, kind, index)."""
    rows = []
    for prop, label, sign in UNIT_PROPS:
        for i, (above, _) in enumerate(FOUR["limits"][prop]):
            rows.append((f"{lang}.{prop}.{above}", f"{label} {bound_label(sign, above)}", prop, i))
    rows.append((f"{lang}.duplication", "duplication", "duplication", None))
    for i, (above, _) in enumerate(FOUR["limits"]["module_coupling"]):
        rows.append((f"{lang}.module_coupling.{above}", f"module coupling fan-in >{above}", "module_coupling", i))
    rows.append((f"{lang}.component_independence", "component independence", "component_independence", None))
    return rows


def limits(kind, index):
    """(4-star limit, 5-star limit) of one check."""
    if kind == "duplication":
        return FOUR["duplication"], FIVE["duplication"]
    if kind == "component_independence":
        return FOUR["independence_min"], FIVE["independence_min"]
    return FOUR["limits"][kind][index][1], FIVE["limits"][kind][index][1]


def share_of(report, lang, kind, index):
    """The measured share of one check, or None when the app has no such code."""
    if kind in ("unit_size", "unit_complexity", "unit_interfacing", "duplication"):
        data = report["languages"].get(lang)
        if not data:
            return None
        if kind == "duplication":
            return data["duplication"]["share"] if data.get("duplication") else None
        return data[kind][index]["share"]
    struct = report.get("structure", {}).get(lang)
    if not struct:
        return None
    if kind == "module_coupling":
        return struct["module_coupling"][index]["share"]
    return struct["component_independence"]["hidden_share"]


def level(kind, share, four, five):
    """5, 4 or "below"; independence is a minimum, every other check a maximum."""
    meets = (lambda lim: share >= lim) if kind == "component_independence" else (lambda lim: share <= lim)
    if meets(five):
        return 5
    return 4 if meets(four) else "below"


def build(report_dir, date):
    names = sorted(f[:-5] for f in os.listdir(report_dir) if f.endswith(".json") and f.count(".") == 1)
    reports = {a: json.load(open(os.path.join(report_dir, f"{a}.json"), encoding="utf-8")) for a in names}
    langs = LANGUAGES + sorted({lang for r in reports.values() for lang in r["languages"]} - set(LANGUAGES))
    apps = {a: {"head": r["head"], "checks": 0, "four": 0, "five": 0} for a, r in reports.items()}
    groups = []
    for lang in langs:
        rows = []
        for row_id, label, kind, index in rows_for(lang):
            four, five = limits(kind, index)
            cells = {}
            for app, report in reports.items():
                share = share_of(report, lang, kind, index)
                if share is None:
                    continue
                stars = level(kind, share, four, five)
                cells[app] = {"share": share, "stars": stars}
                apps[app]["checks"] += 1
                apps[app]["four"] += stars in (4, 5)
                apps[app]["five"] += stars == 5
            if cells:
                rows.append({"id": row_id, "label": label, "minimum": kind == "component_independence",
                             "four": four, "five": five, "cells": cells})
        if rows:
            groups.append({"language": lang, "rows": rows})
    for app, report in reports.items():
        five_ok = sum(ok for _, ok in sig.checks_of(report)) if report.get("stars") == "5-star" else None
        if five_ok is not None and five_ok != apps[app]["five"]:
            sys.exit(f"{app}: {apps[app]['five']} five-star checks here, {five_ok} in the gate's own report")
    return {"measured": date, "profile": FIVE["source"], "apps": apps, "groups": groups}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("report_dir")
    parser.add_argument("--date", help="measurement date, YYYY-MM-DD")
    parser.add_argument("--clones", help="read floors from local clones in DIR/<app> instead of GitHub")
    parser.add_argument("--no-floors", action="store_true", help="keep the floors already in the output")
    args = parser.parse_args()
    date = args.date
    if not date:
        newest = max(os.path.getmtime(os.path.join(args.report_dir, f)) for f in os.listdir(args.report_dir))
        date = datetime.date.fromtimestamp(newest).isoformat()
    data = build(args.report_dir, date)
    if args.no_floors:
        with open(OUT, encoding="utf-8") as fh:
            old = json.load(fh)
        data["floors"] = old.get("floors")
        for app, info in data["apps"].items():
            info["floor"] = old["apps"].get(app, {}).get("floor")
    else:
        floors, per_app = sig_floors.collect(list(data["apps"]), args.clones)
        floors["read"] = datetime.date.today().isoformat()
        data["floors"] = floors
        for app, floor in per_app.items():
            data["apps"][app]["floor"] = floor
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, sort_keys=False)
        fh.write("\n")
    total = sum(len(g["rows"]) for g in data["groups"])
    print(f"{OUT}: {len(data['apps'])} apps, {total} checks, measured {date}")


if __name__ == "__main__":
    main()
