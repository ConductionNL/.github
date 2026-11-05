#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Build website/src/data/sig-matrix.json, the quality matrix, from one measurement.

Usage:
    python3 website/scripts/build-sig-matrix.py <report-dir> --clones DIR
        [--gates DIR] [--date YYYY-MM-DD] [--no-floors]

<report-dir> holds one `<app>.json` per app, written by gate 122
(`check_sig_maintainability.py report`). `--clones DIR/<app>` are the checkouts
that were measured; the own measures and the floors are read from them.
`--gates DIR/<app>/gates.json` is the full-scope gates run of each app
(run-hydra-gates.sh --full); without it the gate rows stay empty.

Sections of the matrix, top to bottom:
  1. SIG maintainability: every gate 122 check, rated 5 to 1 star on the
     STAR_BANDS of check_sig_maintainability.py.
  2. SIG's other models, where we measure them: the published 4-star value,
     met ("4") or missed ("<4").
  3. Our own banded measures (quality_measures.py, bands in BANDS).
  4. The gates, one row per category, with every gate below it.
"""
import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "hydra-gates", "scripts", "lib"))
sys.path.insert(0, HERE)
import check_sig_maintainability as sig  # noqa: E402
import quality_measures as qm  # noqa: E402
import sig_floors  # noqa: E402

OUT = os.path.join(ROOT, "website", "src", "data", "sig-matrix.json")
LANGUAGES = ["php", "javascript", "typescript", "vue", "python"]
UNIT_PROPS = [("unit_size", "unit size", ">"), ("unit_complexity", "unit complexity", ">"),
              ("unit_interfacing", "unit interfacing", ">=")]
CATEGORIES = [("security", "Security"), ("accessibility", "Accessibility"), ("architecture", "Architecture"),
              ("specs", "Specs and traceability"), ("licensing", "Licensing"), ("dependencies", "Dependencies"),
              ("ui", "UI conventions"), ("other", "Other")]
SIG_OTHER = [
    ("osh_vulnerabilities", "Open Source Health", "vulnerabilities above moderate", "4 stars: none"),
    ("osh_licence", "Open Source Health", "dependencies with a licence risk",
     "4 stars: no AGPL, GPL or other medium or worse, at most 3 low-risk (LGPL, EPL)"),
    ("osh_management", "Open Source Health", "unmanaged dependencies (%)", "4 stars: at most 6%"),
    ("arch_adjacency", "Architecture Quality", "component adjacency (estimate)",
     "4 stars: a component talks to at most 6 others on average"),
]


def pct(x):
    return f"{x * 100:.1f}%"


def bound_label(sign, above):
    return f">={above + 1}" if sign == ">=" else f">{above}"


def band_text(kind, index):
    """The share each star level allows, as text."""
    if kind == "component_independence":
        return f"5★ ≥{pct(sig.INDEPENDENCE_BANDS[5])}, 4★ ≥{pct(sig.INDEPENDENCE_BANDS[4])}, under that <4"
    if kind == "component_entanglement":
        return f"5★ ≤{sig.ENTANGLEMENT_BANDS[5]}, 4★ ≤{sig.ENTANGLEMENT_BANDS[4]}, under that <4"
    bands = sig.STAR_BANDS[kind]
    caps = {lvl: bands[lvl] if index is None else bands[lvl][index] for lvl in (5, 4, 3, 2)}
    return ", ".join(f"{lvl}★ ≤{pct(caps[lvl])}" for lvl in (5, 4, 3, 2)) + ", worse 1★"


def maintainability(reports):
    """Section 1: one group per language, one row per check."""
    langs = LANGUAGES + sorted({lg for r in reports.values() for lg in r["languages"]} - set(LANGUAGES))
    groups = []
    for lang in langs:
        rows = []
        for prop, label, sign in UNIT_PROPS:
            for i, above in enumerate(sig.BOUNDS[prop]):
                cells = {}
                for app, r in reports.items():
                    d = r["languages"].get(lang)
                    if d:
                        row = d[prop][i]
                        cells[app] = {"stars": sig.stars_of(prop, row["share"], i), "text": pct(row["share"])}
                rows.append((f"{lang}.{prop}.{above}", f"{label} {bound_label(sign, above)}", band_text(prop, i), cells))
        cells = {}
        for app, r in reports.items():
            dup = (r["languages"].get(lang) or {}).get("duplication")
            if dup:
                cells[app] = {"stars": sig.stars_of("duplication", dup["share"]), "text": pct(dup["share"])}
        rows.append((f"{lang}.duplication", "duplication", band_text("duplication", None), cells))
        for i, above in enumerate(sig.BOUNDS["module_coupling"]):
            cells = {}
            for app, r in reports.items():
                s = (r.get("structure") or {}).get(lang)
                if s:
                    share = s["module_coupling"][i]["share"]
                    cells[app] = {"stars": sig.stars_of("module_coupling", share, i), "text": pct(share)}
            rows.append((f"{lang}.module_coupling.{above}", f"module coupling fan-in >{above}",
                         band_text("module_coupling", i), cells))
        for kind, label in (("component_independence", "component independence"),
                            ("component_entanglement", "component entanglement (estimate, not floored)")):
            cells = {}
            for app, r in reports.items():
                s = (r.get("structure") or {}).get(lang)
                if s:
                    v = s[kind]["hidden_share"] if kind == "component_independence" else s[kind]["violation_degree"]
                    cells[app] = {"stars": sig.stars_of(kind, v),
                                  "text": pct(v) if kind == "component_independence" else f"{v:.3f}"}
            rows.append((f"{lang}.{kind}", label, band_text(kind, None), cells))
        rows = [{"id": i, "label": lb, "limits": lim, "cells": c} for i, lb, lim, c in rows if c]
        if rows:
            groups.append({"title": lang, "rows": rows})
    return groups


def fmt(value, unit):
    if value is None:
        return "n/a"
    return f"{value:.1f}{unit}" if isinstance(value, float) else f"{value}{unit}"


def own_measures(measures):
    """Section 3: one group per theme."""
    groups = {}
    for mid, (section, label, unit, higher, cuts, basis, _why) in qm.BANDS.items():
        cells = {}
        for app, m in measures.items():
            c = m.get(mid)
            if c and c["value"] is not None:
                cells[app] = {"stars": c["stars"], "text": fmt(c["value"], unit), "title": c["detail"]}
        op = "≥" if higher else "≤"
        limits = ", ".join(f"{lvl}★ {op}{cut}{unit}" for lvl, cut in zip(qm.LEVELS, cuts)) + ", worse 1★"
        groups.setdefault(section, []).append({"id": f"own.{mid}", "label": label, "limits": limits, "cells": cells})
    titles = {"tests": "Tests", "debt": "Debt", "security": "Security", "accessibility": "Accessibility and UI"}
    return [{"title": titles[s], "rows": rows} for s, rows in groups.items()]


def sig_other(others):
    groups = {}
    for rid, model, label, limit in SIG_OTHER:
        cells = {}
        for app, o in others.items():
            c = o.get(rid)
            if c and c["value"] is not None:
                cells[app] = {"stars": c["stars"], "text": fmt(c["value"], ""), "title": c["detail"]}
        groups.setdefault(model, []).append({"id": f"sig.{rid}", "label": label, "limits": limit, "cells": cells})
    return [{"title": m, "rows": rows} for m, rows in groups.items()]


def gate_rows(gates):
    """Section 4: per category a summary row, with one child row per gate."""
    groups = []
    for cat, title in CATEGORIES:
        names = {}
        per_app = {}
        for app, doc in gates.items():
            for g in doc["gates"]:
                if g["category"] != cat:
                    continue
                names[g["gate"]] = g["name"]
                per_app.setdefault(app, {})[g["gate"]] = g
        children = []
        for n in sorted(names):
            cells = {}
            for app, gs in per_app.items():
                g = gs.get(n)
                if not g or g["verdict"] in ("not-applicable",):
                    continue
                state = {"pass": "pass", "fail": "fail", "warning": "warn"}.get(g["verdict"], "skip")
                text = "pass" if state == "pass" else (str(g["findings"]) if g["findings"] is not None else g["verdict"])
                cells[app] = {"state": state, "text": text, "title": (g["reason"] or g["verdict"])[:300]}
            children.append({"id": f"gate.{n}", "label": f"{n} {names[n]}", "cells": cells})
        summary = {}
        for app, gs in per_app.items():
            judged = [g for g in gs.values() if g["verdict"] in ("pass", "fail", "warning")]
            if not judged:
                continue
            passing = sum(1 for g in judged if g["verdict"] == "pass")
            findings = sum(g["findings"] or 0 for g in judged)
            unrun = sum(1 for g in gs.values() if g["verdict"] in ("skipped", "not-run"))
            summary[app] = {"state": "pass" if passing == len(judged) else "fail",
                            "text": f"{passing}/{len(judged)}", "sub": f"{findings} findings",
                            "title": f"{passing} of {len(judged)} applicable gates pass, {findings} findings"
                                     + (f", {unrun} did not run" if unrun else "")}
        groups.append({"id": f"cat.{cat}", "title": title, "cells": summary, "gates": children})
    return groups


def build(report_dir, clones, gates_dir, date):
    names = sorted(f[:-5] for f in os.listdir(report_dir) if f.endswith(".json") and f.count(".") == 1)
    reports = {a: json.load(open(os.path.join(report_dir, f"{a}.json"), encoding="utf-8")) for a in names}
    gates = {}
    for a in names:
        path = os.path.join(gates_dir, a, "gates.json") if gates_dir else ""
        if path and os.path.isfile(path):
            gates[a] = json.load(open(path, encoding="utf-8"))
    measures, others = {}, {}
    for a in names:
        clone = os.path.join(clones, a)
        measures[a] = qm.measure(a, clone, reports[a], gates.get(a))
        others[a] = qm.sig_other(clone, reports[a], measures[a])
        print(f"measured {a}", file=sys.stderr)
    m_groups = maintainability(reports)
    apps = {}
    for a, r in reports.items():
        rated = [c["stars"] for g in m_groups for row in g["rows"] if not row["id"].endswith("entanglement")
                 for c in [row["cells"].get(a)] if c]
        apps[a] = {"head": r["head"], "checks": len(rated), "four": sum(1 for s in rated if s in (4, 5)),
                   "five": sum(1 for s in rated if s == 5), "gates_measured": a in gates}
    beyond = [{"label": label, "why": why, "basis": basis}
              for _mid, (_s, label, _u, _h, _c, basis, why) in qm.BANDS.items()]
    return {
        "measured": date,
        "guidance": sig.GUIDANCE,
        "apps": apps,
        "sections": [
            {"id": "maintainability", "title": "SIG maintainability", "groups": m_groups},
            {"id": "sig-other", "title": "SIG's other models", "groups": sig_other(others)},
            {"id": "own", "title": "Our own measures", "groups": own_measures(measures)},
        ],
        "gateCategories": gate_rows(gates),
        "beyond": beyond,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("report_dir")
    parser.add_argument("--clones", required=True, help="the measured checkouts, DIR/<app>")
    parser.add_argument("--gates", help="DIR/<app>/gates.json from a full-scope gates run")
    parser.add_argument("--date", help="measurement date, YYYY-MM-DD")
    parser.add_argument("--no-floors", action="store_true", help="keep the floors already in the output")
    args = parser.parse_args()
    date = args.date or datetime.date.today().isoformat()
    data = build(args.report_dir, args.clones, args.gates, date)
    if args.no_floors:
        with open(OUT, encoding="utf-8") as fh:
            old = json.load(fh)
        data["floors"] = old.get("floors")
        for app, info in data["apps"].items():
            info["floor"] = old["apps"].get(app, {}).get("floor")
    else:
        floors, per_app = sig_floors.collect(list(data["apps"]), args.clones)
        floors["read"] = date
        data["floors"] = floors
        for app, floor in per_app.items():
            data["apps"][app]["floor"] = floor
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1)
        fh.write("\n")
    rows = sum(len(g["rows"]) for s in data["sections"] for g in s["groups"])
    print(f"{OUT}: {len(data['apps'])} apps, {rows} rows, {len(data['gateCategories'])} gate categories, measured {date}")


if __name__ == "__main__":
    main()
