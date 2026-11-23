#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Estimated modularity ratings of an app's PHP backend under five component definitions.

    python3 check_sig_maintainability.py report <app> --json /tmp/base.json
    python3 rate_component_views.py <app> --report /tmp/base.json [--components FILE]
        [--foundation NAME] [--merge NAME[,NAME]] [--json OUT]

The report gives every property that does not depend on the component definition (unit size,
duplication, the JavaScript structure and so on). For the PHP backend this script recomputes the
structure with the gate-122 scorer's own structure() for each definition, puts it in a copy of the
report and runs the scorer's rating_estimate() on it:

- A the backend as one component: every file under lib/ in one component;
- B every directory under lib/ (the scorer's directory rule, without a `components:` block);
- C the functional areas of the components file (default <app>/sigrid.components.yaml);
- D as C, with the --merge components (default Core) renamed into the --foundation component
  (default Kernel): a shared foundation the other areas build on;
- E as D, without the references from the foundation to the other areas. This is a simulation of
  a foundation that is only depended on, not a measurement of existing code.

An app without a components file gets A and B only; C, D and E are skipped with a message. D and
E are also skipped when no component carries the foundation's name after the merge.

For C the script also splits the exposed code by kind of file (exposed_by_kind) and by component
(exposed_by_component), and for D it lists the foundation's references to each other component
(foundation_backrefs). `targets` gives, per rating, the largest exposed share and violation degree
that still earn it, from the scorer's own rating scale.

All ratings are estimates on the scorer's 0.5 to 5.5 scale; only the 4-star limits are published.
"""
import argparse
import collections
import copy
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyse_dependencies as analysis  # noqa: E402
import check_sig_maintainability as tool  # noqa: E402

FOUNDATION = "Kernel"
MERGE = ("Core",)


def one_component():
    """A `components:` definition that puts every file under lib/ in one component."""
    return {"components": [{"name": "Backend", "include": [re.compile(r".*/lib/.*")], "exclude": []}]}


def merge_into_foundation(definition, foundation=FOUNDATION, merge=MERGE):
    """A copy of `definition` with the `merge` components renamed to `foundation`. The first
    matching component owns a file, so a shared name merges them without reordering."""
    out = {"components": [dict(c) for c in definition["components"]]}
    for c in out["components"]:
        if c["name"] in merge:
            c["name"] = foundation
    return out


def has_component(definition, name):
    return any(c["name"] == name for c in definition["components"])


def without_foundation_backrefs(deps, comp, foundation=FOUNDATION):
    """deps without the edges from a foundation file to a file of another component."""
    return {src: {d for d in targets if not (comp(src) == foundation and comp(d) != foundation)}
            for src, targets in deps.items()}


def kind_of(rel, text):
    """The kind of a PHP file, by its declaration and name: interface, trait, exception, event,
    entity, mapper or concrete class. An entity that does not extend Entity directly counts as a
    concrete class."""
    name = os.path.basename(rel)
    if re.search(r"^\s*interface\s", text, re.M):
        return "interface"
    if re.search(r"^\s*trait\s", text, re.M):
        return "trait"
    if name.endswith("Exception.php") or re.search(r"extends \\?\w*Exception\b", text):
        return "exception"
    if name.endswith("Event.php"):
        return "event"
    if "/Db/" in rel and re.search(r"extends \\?(OCP\\AppFramework\\Db\\)?Entity\b", text):
        return "entity"
    if name.endswith("Mapper.php"):
        return "mapper"
    return "concrete class"


def exposed_by_kind(app, deps, comp):
    """{kind: {"files": n, "loc": lines}} of the files another component references."""
    incoming = collections.defaultdict(set)
    for src, targets in deps.items():
        for t in targets:
            incoming[t].add(src)
    out = collections.defaultdict(lambda: {"files": 0, "loc": 0})
    for rel in deps:
        if any(comp(s) != comp(rel) for s in incoming[rel]):
            text = tool.read_text(os.path.join(app, rel))
            row = out[kind_of(rel, text)]
            row["files"] += 1
            row["loc"] += len(tool.code_lines(text, "php"))
    return dict(sorted(out.items(), key=lambda kv: -kv[1]["loc"]))


def exposed_by_component(app, deps, comp):
    """{component: {"loc": lines, "exposed_loc": lines another component references}}."""
    incoming = collections.defaultdict(set)
    for src, targets in deps.items():
        for t in targets:
            incoming[t].add(src)
    out = collections.defaultdict(lambda: {"loc": 0, "exposed_loc": 0})
    for rel in deps:
        lines = len(tool.code_lines(tool.read_text(os.path.join(app, rel)), "php"))
        row = out[comp(rel)]
        row["loc"] += lines
        if any(comp(s) != comp(rel) for s in incoming[rel]):
            row["exposed_loc"] += lines
    return dict(sorted(out.items(), key=lambda kv: -kv[1]["loc"]))


def max_value_for(kind, rating):
    """The largest value of an exposed share or violation degree that still rates `rating`."""
    caps = tool.rating_caps(kind)
    lo, hi = 0.0, 1.0
    for _ in range(50):
        mid = (lo + hi) / 2
        if tool.interpolate(mid, caps) >= rating:
            lo = mid
        else:
            hi = mid
    return round(lo, 4)


def targets(ratings=(4.0, 4.5, 5.0, 5.5)):
    """{rating: {"exposed_share": max, "violation_degree": max}}."""
    return {str(r): {"exposed_share": max_value_for("component_independence", r),
                     "violation_degree": max_value_for("component_entanglement", r)} for r in ratings}


def foundation_backrefs(deps, comp, foundation=FOUNDATION):
    """{component: file references from the foundation to it}, heaviest first."""
    out = collections.Counter(comp(d) for src, targets in deps.items() if comp(src) == foundation
                              for d in targets if comp(d) != foundation)
    return dict(out.most_common())


def rate(report, structure):
    rep = copy.deepcopy(report)
    rep.setdefault("structure", {})["php"] = structure
    rating = tool.rating_estimate(rep)
    ci, ce = structure["component_independence"], structure["component_entanglement"]
    out = {
        "components": len(structure["components"]),
        "hidden_share": ci["hidden_share"],
        "violation_degree": ce["violation_degree"],
        "violations": ce["violations"],
        "independence": rating["properties"]["component_independence"]["rating"],
        "entanglement": rating["properties"]["component_entanglement"]["rating"],
        "modularity": rating["subcharacteristics"]["modularity"],
        "overall": rating["overall"]["range"],
    }
    if structure.get("warning"):
        out["warning"] = structure["warning"]
    return out


def structure_under(app, files, deps, definition):
    """(the scorer's structure(), its component function) with `definition` as the components;
    None means the scorer's directory rule."""
    with analysis.components_of(definition):
        st = tool.structure(app, files, deps)
    if definition is None:
        return st, tool.component_of_factory(sorted(deps))[1]
    return st, tool.scope_component_factory(definition)[1]


def views(report, app, components_file=None, foundation=FOUNDATION, merge=MERGE):
    """{view: rating} for A and B, and for C, D and E when the app has a components file.
    Skipped views are listed under "skipped" with the reason."""
    files = {rel: lang for rel, lang in tool.production_files(app, tool.Scope(app)).items() if lang == "php"}
    deps = tool.php_dependencies(app, files)
    if not deps:
        raise SystemExit(f"no PHP classes in {app}")
    out, skipped = {}, {}
    for key, definition in (("A", one_component()), ("B", None)):
        out[key] = rate(report, structure_under(app, files, deps, definition)[0])
    path = components_file or analysis.default_components_file(app)
    functional = analysis.read_components(path)
    if functional is None:
        reason = f"no `components:` block in {path}"
        skipped.update(C=reason, D=reason, E=reason)
    else:
        st, comp = structure_under(app, files, deps, functional)
        out["C"] = rate(report, st)
        out["C"]["exposed_by_kind"] = exposed_by_kind(app, deps, comp)
        out["C"]["exposed_by_component"] = exposed_by_component(app, deps, comp)
        merged = merge_into_foundation(functional, foundation, merge)
        if not has_component(merged, foundation):
            reason = f"no component named {foundation} after merging {', '.join(merge) or 'nothing'}"
            skipped.update(D=reason, E=reason)
        else:
            st, comp = structure_under(app, files, deps, merged)
            out["D"] = rate(report, st)
            out["D"]["foundation_backrefs"] = foundation_backrefs(deps, comp, foundation)
            pruned = without_foundation_backrefs(deps, comp, foundation)
            out["E"] = rate(report, structure_under(app, files, pruned, merged)[0])
    if skipped:
        out["skipped"] = skipped
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("app", help="root of the app the report was made of")
    ap.add_argument("--report", required=True, help="JSON written by check_sig_maintainability.py report")
    ap.add_argument("--components", help=f"file with the `components:` block (default <app>/{analysis.COMPONENTS_FILE})")
    ap.add_argument("--foundation", default=FOUNDATION, help=f"the shared foundation component of D and E (default {FOUNDATION})")
    ap.add_argument("--merge", default=",".join(MERGE),
                    help=f"comma-separated components merged into the foundation for D and E (default {','.join(MERGE)})")
    ap.add_argument("--json", help="write the results here")
    args = ap.parse_args(argv)
    with open(args.report, encoding="utf-8") as fh:
        report = json.load(fh)
    merge = tuple(n.strip() for n in args.merge.split(",") if n.strip())
    out = views(report, os.path.abspath(args.app), args.components, args.foundation, merge)
    out["targets"] = targets()
    for key, v in out.items():
        if key in ("targets", "skipped"):
            continue
        rng = v["overall"]
        overall = f"{rng[0]} to {rng[1]}" if rng else "not rated"
        line = (f"{key}: {v['components']} components, hidden {v['hidden_share']:.1%}, "
                f"violation degree {v['violation_degree']:.4f}; independence {v['independence']}, "
                f"entanglement {v['entanglement']}, modularity {v['modularity']}, overall {overall}")
        print(line + (f" ({v['warning']})" if v.get("warning") else ""))
    for key, reason in out.get("skipped", {}).items():
        print(f"{key}: skipped, {reason}")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
