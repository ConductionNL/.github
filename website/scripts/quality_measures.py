# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Our own banded measures for the quality matrix, per app.

Each measure is a value plus a star level from bands defined here. BANDS holds
every band and its basis; the docs page prints the same table. Inputs per app:
a checkout of `development`, gate 122's report (`<app>.json`) and the runner's
gates.json. Network is used for `composer audit` and `npm audit`
(lockfile only, nothing is installed) and for the CI coverage report (`gh api`).
"""
import io
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ElementTree
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIB = os.path.join(ROOT, "hydra-gates", "scripts", "lib")
sys.path.insert(0, LIB)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_sig_maintainability as sig  # noqa: E402
import sig_floors  # noqa: E402

HEITLAGER = "Heitlager, Kuipers and Visser 2007: unit test coverage ++ 95-100%, + 80-95%, o 60-80%, - 20-60%, -- 0-20%"

# id: (section, label, unit, higher_is_better, cuts for 5/4/3/2 stars, basis, why)
BANDS = {
    "php_coverage": ("tests", "PHP line coverage", "%", True, (95, 80, 60, 20), HEITLAGER,
                     "SIG rates no tests. Coverage shows how much of the code a unit or integration test runs."),
    "spec_coverage": ("tests", "spec coverage (gate 16)", "%", True, (95, 80, 60, 20),
                      "our choice: Heitlager's coverage bands applied to traceability",
                      "Share of in-scope methods that name the spec they implement, so a change can be traced to a requirement."),
    "e2e_coverage": ("tests", "e2e scenario coverage (gate 19)", "%", True, (95, 80, 60, 20),
                     "our choice: Heitlager's coverage bands applied to spec scenarios",
                     "Share of non-excluded spec scenarios a running Playwright test cites: the behaviour a user sees is proven."),
    "test_ratio": ("tests", "test code ratio", "%", True, (120, 100, 75, 25),
                   "Sigrid: a 100% test code ratio is roughly 80% coverage, so Heitlager's 95/80/60/20% coverage "
                   "bands become 120/100/75/25% test code",
                   "SIG's own test volume figure (test LOC / production LOC), shown in Sigrid without stars."),
    "baseline_debt": ("debt", "baselined findings per kLOC PHP", "", False, (1, 5, 10, 25),
                      "our own bands; no published benchmark",
                      "psalm, phpstan and phpmd baselines hide findings from the gates. Each entry is debt a reviewer no longer sees."),
    "suppressions": ("debt", "suppressions per kLOC", "", False, (0.5, 2, 5, 10),
                     "our own bands; no published benchmark",
                     "Inline @psalm-suppress, @phpstan-ignore, @SuppressWarnings, phpcs:ignore and eslint-disable "
                     "silence a tool where SIG still counts the code."),
    "security_findings": ("security", "security gate findings", "", False, (0, 2, 5, 15),
                          "our own bands; 0 is the only passing state of each gate",
                          "Gates 5-9, 11, 30, 48, 50, 82, 97 and 121 find missing auth, IDOR and fail-open checks "
                          "that SAST tools do not know about Nextcloud."),
    "audit": ("security", "vulnerable dependencies, high or critical", "", False, (0, 0, 2, 5),
              "SIG Open Source Health: 4 stars means no vulnerability above moderate; 5 stars also no moderate",
              "composer audit and npm audit on the lockfiles; SIG rates the same CVEs in Open Source Health."),
    "unmanaged": ("security", "unmanaged dependencies", "%", False, (0, 6, 12, 25),
                  "SIG Open Source Health: 4 stars at most 6% unmanaged; 3 and 2 stars double that",
                  "Third-party code committed into the repository (minified or vendored files) gets no security updates."),
    "a11y_density": ("accessibility", "accessibility findings per .vue file", "", False, (0, 0.05, 0.2, 0.5),
                     "our own bands; WCAG 2.2 AA asks for none",
                     "SIG has no accessibility model. Gates 12 and 31-45 check WCAG 2.2 AA rules in the source."),
    "ui_findings": ("accessibility", "UI convention findings", "", False, (0, 5, 20, 50),
                    "our own bands; 0 is the only passing state of each gate",
                    "The UI gates keep every app on the shared nextcloud-vue patterns, so users meet one interface."),
}
LEVELS = (5, 4, 3, 2)
SECURITY_GATES = {5, 6, 7, 8, 9, 11, 30, 48, 50, 82, 97, 121}
SUPPRESS = re.compile(r"@psalm-suppress|@phpstan-ignore|@SuppressWarnings|phpcs:ignore|phpcs:disable|"
                      r"eslint-disable|@ts-ignore|@ts-expect-error")
UNMANAGED = re.compile(r"(^|/)(vendor|third[-_]party|3rdparty)/|\.min\.(js|css)$")
COVERAGE_ARTIFACT = "coverage-report"


def stars(measure_id, value):
    if value is None:
        return None
    _s, _l, _u, higher, cuts, *_ = BANDS[measure_id]
    for level, cut in zip(LEVELS, cuts):
        if (value >= cut) if higher else (value <= cut):
            return level
    return 1


def cell(measure_id, value, detail):
    return {"value": None if value is None else round(value, 2), "stars": stars(measure_id, value), "detail": detail}


def git_files(clone):
    out = subprocess.run(["git", "-C", clone, "ls-files"], capture_output=True, text=True).stdout
    return [f for f in out.splitlines() if f]


def code_loc(clone, files):
    total = 0
    for rel in files:
        lang = sig.LANG_OF_EXT.get(os.path.splitext(rel)[1].lower())
        if lang:
            total += len(sig.code_lines(sig.read_text(os.path.join(clone, rel)), lang))
    return total


def test_ratio(clone, files, report):
    tests = [f for f in files if sig.LANG_OF_EXT.get(os.path.splitext(f)[1].lower())
             and any(re.fullmatch(p, "/" + f) for p in sig.TEST_PATTERNS)
             and not f.startswith(("vendor/", "node_modules/"))]
    prod = sum(d["duplication"]["code_lines"] for d in report["languages"].values() if d.get("duplication"))
    t = code_loc(clone, tests)
    return (100 * t / prod if prod else None), f"{t} test LOC / {prod} production LOC"


def spec_coverage(clone):
    import check_spec_coverage as g16
    from pathlib import Path
    app = Path(clone)
    tag = re.compile(r"@spec(\s+)openspec/")
    untagged, total = 0, 0
    for rel in g16._iter_in_scope_files(app):
        try:
            text = (app / rel).read_text(encoding="utf-8")
        except OSError:
            continue
        lines = set(range(1, len(text.splitlines()) + 2))
        for body, bucket in ((text, "now"), (tag.sub(r"@nospec\1x/", text), "all")):
            out = []
            if rel.endswith(".php"):
                if not g16._is_backend(rel):
                    continue
                g16.check_php_file(rel, body, lines, out)
            elif g16._is_frontend_in_scope(rel):
                g16.check_frontend_file(rel, body, lines, out)
            if bucket == "now":
                untagged += len(set(out))
            else:
                total += len(set(out))
    if not total:
        return None, "no in-scope method"
    return 100 * (total - untagged) / total, f"{total - untagged} of {total} in-scope methods tagged"


def e2e_coverage(clone):
    p = subprocess.run([sys.executable, os.path.join(LIB, "check_e2e_coverage.py"), "--mode", "report", clone],
                       capture_output=True, text=True, timeout=900)
    try:
        d = json.loads(p.stdout)
    except ValueError:
        return None, "no report"
    t = d.get("totals") or {}
    need = t.get("scenarios", 0) - t.get("excluded", 0)
    if not need:
        return None, "no scenario outside the exclusions"
    return d.get("coverage_pct"), f"{t.get('covered')} of {need} scenarios (excluded {t.get('excluded')})"


def clover_coverage(xml):
    """(percentage, covered, statements) from the project metrics of a clover report."""
    metrics = ElementTree.fromstring(xml).find("project").find("metrics")
    statements, covered = int(metrics.get("statements")), int(metrics.get("coveredstatements"))
    return (100 * covered / statements if statements else None), covered, statements


def gh_api(path):
    return subprocess.run(["gh", "api", path], check=True, capture_output=True).stdout


def latest_coverage_artifact(app):
    """The newest CI coverage report of the app's own repository: from `development` if one
    is kept, otherwise from any branch. CI keeps these 14 days, which bounds their age."""
    fallback = None
    page = 1
    while True:
        listing = json.loads(gh_api(f"repos/{sig_floors.ORG}/{app}/actions/artifacts"
                                    f"?name={COVERAGE_ARTIFACT}&per_page=100&page={page}"))
        for artifact in listing["artifacts"]:
            run = artifact.get("workflow_run") or {}
            if artifact["expired"] or run.get("head_repository_id") != run.get("repository_id"):
                continue
            if run.get("head_branch") == "development":
                return artifact
            fallback = fallback or artifact
        if len(listing["artifacts"]) < 100:
            return fallback
        page += 1


def ci_coverage(app):
    """PHP statement coverage from the newest CI clover report, with where it came from."""
    try:
        artifact = latest_coverage_artifact(app)
        if artifact is None:
            return None, "no coverage report kept by CI"
        archive = gh_api(f"repos/{sig_floors.ORG}/{app}/actions/artifacts/{artifact['id']}/zip")
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            value, covered, statements = clover_coverage(bundle.read("clover.xml"))
    except (subprocess.CalledProcessError, ValueError, KeyError, AttributeError, TypeError,
            zipfile.BadZipFile, ElementTree.ParseError):
        return None, "CI coverage report unreadable"
    run = artifact["workflow_run"]
    return value, (f"{covered} of {statements} statements, CI clover from {run['head_branch']} "
                   f"at {run['head_sha'][:8]}, {artifact['created_at'][:10]}")


def stale_floor(clone):
    """(floor, date) of the committed coverage-guard floor, or (None, None) without one."""
    path = os.path.join(clone, ".coverage-baseline")
    if not os.path.isfile(path):
        return None, None
    try:
        floor = float(open(path).read().strip())
    except ValueError:
        return None, None
    date = subprocess.run(["git", "-C", clone, "log", "-1", "--format=%cs", "--", ".coverage-baseline"],
                          capture_output=True, text=True).stdout.strip()
    return floor, date or "unknown date"


def php_coverage(app, clone):
    """The CI clover cell; without a readable report, the committed floor marked stale with its date."""
    value, detail = ci_coverage(app)
    if value is not None:
        return cell("php_coverage", value, detail)
    floor, date = stale_floor(clone)
    if floor is None:
        return cell("php_coverage", None, detail)
    print(f"WARNING {app}: {detail}; php_coverage falls back to the stale floor {floor} of {date}",
          file=sys.stderr)
    out = cell("php_coverage", floor, f"STALE: {detail}. Shows the coverage-guard floor in "
                                      f".coverage-baseline, last changed {date}, not a measurement")
    out["stale"] = date
    return out


def audits(clone):
    high, crit, notes = 0, 0, []
    if os.path.isfile(os.path.join(clone, "composer.lock")):
        p = subprocess.run(["composer", "audit", "--locked", "--format=json", "--no-interaction"],
                           cwd=clone, capture_output=True, text=True, timeout=600)
        try:
            adv = json.loads(p.stdout).get("advisories") or {}
            pk = {k: {(a.get("severity") or "").strip().lower() for a in (v.values() if isinstance(v, dict) else v)}
                  for k, v in adv.items()}
            # Composer leaves severity empty for advisories without a rating; those cannot be shown to be below high.
            h = sum(1 for s in pk.values() if s & {"high", ""} and "critical" not in s)
            c = sum(1 for s in pk.values() if "critical" in s)
            unrated = sum(1 for s in pk.values() if "" in s and not s & {"high", "critical"})
            high, crit = high + h, crit + c
            notes.append(f"composer {h} high, {c} critical"
                         + (f" ({unrated} without a severity, counted as high)" if unrated else ""))
        except ValueError:
            notes.append("composer audit unreadable")
    if os.path.isfile(os.path.join(clone, "package-lock.json")):
        p = subprocess.run(["npm", "audit", "--package-lock-only", "--json"], cwd=clone,
                           capture_output=True, text=True, timeout=600)
        try:
            v = json.loads(p.stdout)["metadata"]["vulnerabilities"]
            high, crit = high + v.get("high", 0), crit + v.get("critical", 0)
            notes.append(f"npm {v.get('high', 0)} high, {v.get('critical', 0)} critical")
        except (ValueError, KeyError):
            notes.append("npm audit unreadable")
    return high + crit, "; ".join(notes) or "no lockfile"


def unmanaged(clone, files):
    libs = set()
    for f in files:
        m = UNMANAGED.search(f)
        if m and not f.startswith(("tests/", "node_modules/")):
            libs.add(f[:m.end()] if m.group(2) else f)
    managed = 0
    for name, key in (("composer.json", ("require",)), ("package.json", ("dependencies",))):
        path = os.path.join(clone, name)
        if os.path.isfile(path):
            try:
                data = json.load(open(path, encoding="utf-8"))
            except ValueError:
                continue
            managed += sum(1 for k in data.get(key[0], {}) if k != "php" and not k.startswith("ext-"))
    total = managed + len(libs)
    return (100 * len(libs) / total if total else None), f"{len(libs)} unmanaged of {total} dependencies"


def measure(app, clone, report, gates):
    files = git_files(clone)
    prod = [f for f in files if sig.LANG_OF_EXT.get(os.path.splitext(f)[1].lower())
            and not any(re.fullmatch(p, "/" + f) for p in sig.TEST_PATTERNS)
            and not f.startswith(("vendor/", "node_modules/", "js/", "l10n/"))]
    php_loc = sum(d["duplication"]["code_lines"] for lang, d in report["languages"].items()
                  if lang == "php" and d.get("duplication"))
    all_loc = sum(d["duplication"]["code_lines"] for d in report["languages"].values() if d.get("duplication"))
    out = {}
    out["php_coverage"] = php_coverage(app, clone)
    out["spec_coverage"] = cell("spec_coverage", *spec_coverage(clone))
    out["e2e_coverage"] = cell("e2e_coverage", *e2e_coverage(clone))
    out["test_ratio"] = cell("test_ratio", *test_ratio(clone, files, report))
    source = sig_floors.CloneSource(os.path.dirname(clone), os.path.basename(clone))
    cells, _floor = sig_floors.collect_app(source)
    base = sum(cells[k]["value"] for k in ("psalm", "phpstan", "phpmd") if k in cells)
    out["baseline_debt"] = cell("baseline_debt", 1000 * base / php_loc if php_loc else None,
                                f"{base} baseline entries over {php_loc} PHP LOC")
    sup = 0
    for f in prod:
        sup += len(SUPPRESS.findall(sig.read_text(os.path.join(clone, f))))
    out["suppressions"] = cell("suppressions", 1000 * sup / all_loc if all_loc else None,
                               f"{sup} suppressions over {all_loc} LOC")
    out["audit"] = cell("audit", *audits(clone))
    out["unmanaged"] = cell("unmanaged", *unmanaged(clone, files))
    if gates:
        by = {g["gate"]: g for g in gates["gates"]}
        sec = [g for n, g in by.items() if n in SECURITY_GATES and g["verdict"] in ("pass", "fail", "warning")]
        out["security_findings"] = cell("security_findings", sum(g["findings"] or 0 for g in sec),
                                        f"{len(sec)} security gates judged")
        vue = sum(1 for f in prod if f.endswith(".vue"))
        a11y = [g for g in gates["gates"] if g["category"] == "accessibility" and g["verdict"] in ("pass", "fail", "warning")]
        n = sum(g["findings"] or 0 for g in a11y)
        out["a11y_density"] = cell("a11y_density", n / vue if vue else None, f"{n} findings over {vue} .vue files")
        ui = [g for g in gates["gates"] if g["category"] == "ui" and g["verdict"] in ("pass", "fail", "warning")]
        out["ui_findings"] = cell("ui_findings", sum(g["findings"] or 0 for g in ui), f"{len(ui)} UI gates judged")
    return out


# SIG Open Source Health licence classes (2025 guidance); EUPL is not listed and counts as none.
LICENCE_CLASS = [
    ("critical", re.compile(r"\bAGPL", re.I)),
    ("high", re.compile(r"CC-BY-NC|CC-BY-SA", re.I)),
    ("low", re.compile(r"\bLGPL|CDDL|\bEPL|Eclipse", re.I)),
    ("medium", re.compile(r"\bGPL|\bMPL|Mozilla|CC-BY-ND", re.I)),
]


def licence_class(licences):
    """The worst SIG risk class among one package's licences; dual licences take the best option."""
    order = ["none", "low", "medium", "high", "critical"]
    classes = []
    for lic in licences or ["none"]:
        cls = next((c for c, rx in LICENCE_CLASS if rx.search(lic or "")), "none")
        classes.append(cls)
    return min(classes, key=order.index)


def dependency_licences(clone):
    """{class: count} over every package in composer.lock and package-lock.json."""
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "none": 0}
    path = os.path.join(clone, "composer.lock")
    if os.path.isfile(path):
        data = json.load(open(path, encoding="utf-8"))
        for pkg in data.get("packages", []):
            counts[licence_class(pkg.get("license") or [])] += 1
    path = os.path.join(clone, "package-lock.json")
    if os.path.isfile(path):
        data = json.load(open(path, encoding="utf-8"))
        for name, pkg in data.get("packages", {}).items():
            if not name or pkg.get("dev"):
                continue
            lic = pkg.get("license")
            counts[licence_class(re.split(r"\s+OR\s+|[()]", lic) if isinstance(lic, str) else [])] += 1
    return counts


def sig_other(clone, report, measures):
    """SIG's other models, where we measure them: {row id: cell}. A cell meets
    the published 4-star value ("4") or misses it ("<4"); no other level is published."""
    out = {}
    v = measures.get("audit", {}).get("value")
    out["osh_vulnerabilities"] = {"value": v, "stars": None if v is None else (4 if v == 0 else "<4"),
                                  "detail": measures["audit"]["detail"]}
    u = measures.get("unmanaged", {}).get("value")
    out["osh_management"] = {"value": u, "stars": None if u is None else (4 if u <= 6 else "<4"),
                             "detail": measures["unmanaged"]["detail"]}
    lic = dependency_licences(clone)
    risky = lic["critical"] + lic["high"] + lic["medium"]
    out["osh_licence"] = {"value": risky + lic["low"], "stars": 4 if risky == 0 and lic["low"] <= 3 else "<4",
                          "detail": ", ".join(f"{k} {n}" for k, n in lic.items())}
    s = (report.get("structure") or {}).get("php")
    # Each connected pair gives both of its components one neighbour. communication_lines
    # counts the two directions separately, so a report without connected_pairs gives no cell.
    pairs = s["component_entanglement"].get("connected_pairs") if s else None
    if pairs is not None:
        e = s["component_entanglement"]
        adj = 2 * pairs / max(e["connected_components"], 1)
        out["arch_adjacency"] = {"value": round(adj, 1), "stars": 4 if adj <= 6 else "<4",
                                 "detail": f"{pairs} connected pairs between "
                                           f"{e['connected_components']} components (estimate)"}
    return out
