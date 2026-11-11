#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Open Source Health: how healthy the third-party dependencies of a repository are.

Rates five properties of the production dependencies from 1 to 5 stars,
following the Open Source Health quality model's guidance for producers
(sigridci docs/reference/quality-model-documents/open-source-health.md):

  vulnerabilities  known vulnerabilities in the locked versions (OSV.dev)
  freshness        how far each locked version is behind the latest release
  activity         how long ago each dependency last released anything
  licence          licence risk classes of the dependencies
  management       share of third-party code committed outside a package manager

WHAT IS MEASURED
----------------
Production dependencies from the lockfiles at the repository root:
composer.lock `packages` (not `packages-dev`), package-lock.json v2/v3
`packages` without `dev` or `devOptional`, and `name==version` lines of
requirements.txt. Licences come from the lockfiles themselves (composer.lock
and package-lock.json record them) and from PyPI for Python packages.
Release dates come from Packagist, the npm registry and PyPI. Vulnerabilities
come from the OSV.dev batch API. A property whose data cannot be fetched is
reported as null, never as a rating.

STARS
-----
The model publishes only the 4-star limits. 5 stars halves every share limit
(and asks for none in the strictest band); 3 and 2 stars double and quadruple
them. Those three levels are this script's derivation, not published values.
A share is the percentage of dependencies above a bound.

  vulnerabilities  4: nothing above moderate; 5: nothing at moderate or above;
                   3: at most 2 above moderate; 2: at most 5; else 1.
  freshness        4: >1y behind <=34.2%, >2y <=19.1%, >3.5y <=11.1%, none >5y.
  activity         4: last release >1y ago <=21.4%, >2y <=13.0%, >4y <=9.6%,
                   none >5.5y.
  licence          4: no critical, high or medium risk licence, at most 3 low;
                   5: no low either; 3: no critical or high; 2: no critical.
  management       4: <=6% unmanaged; 5: none; 3: <=12%; 2: <=24%.

For freshness and activity the absolute rule ("none older than N years")
caps the rating at 3 stars when it is broken. The overall rating is the
rounded mean of the rated properties.

Usage:
    check_open_source_health.py report <repo-dir> [--json FILE] [--offline]

Exit status: 0 a report, 2 bad arguments, 4 no dependency data to rate.
"""
import argparse
import concurrent.futures
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

USER_AGENT = "open-source-health-check (+https://github.com/ConductionNL/.github)"
HTTP_TIMEOUT = 20
WORKERS = 8
CACHE_TTL_SECONDS = 24 * 3600

ECOSYSTEM_OSV = {"composer": "Packagist", "npm": "npm", "pypi": "PyPI"}

# Licence risk classes of the model; checked in this order, so LGPL is low before GPL is medium.
LICENCE_CLASSES = [
    ("critical", re.compile(r"\bAGPL", re.I)),
    ("high", re.compile(r"CC-BY-NC|CC-BY-SA", re.I)),
    ("low", re.compile(r"\bLGPL|CDDL|\bEPL\b|Eclipse", re.I)),
    ("medium", re.compile(r"\bGPL|\bMPL|Mozilla|CC-BY-ND", re.I)),
]
LICENCE_ORDER = ["none", "low", "medium", "high", "critical"]

UNMANAGED = re.compile(r"(^|/)(vendor|third[-_]party|3rdparty)/|\.min\.(js|css)$")
SEVERITY_ORDER = ["unknown", "low", "moderate", "high", "critical"]

# 4-star share limits (percentages) per bound in years, and the absolute bound.
FRESHNESS_LIMITS = [(1.0, 34.2), (2.0, 19.1), (3.5, 11.1)]
FRESHNESS_MAX_YEARS = 5.0
ACTIVITY_LIMITS = [(1.0, 21.4), (2.0, 13.0), (4.0, 9.6)]
ACTIVITY_MAX_YEARS = 5.5
MANAGEMENT_LIMIT = 6.0


# --------------------------------------------------------------------------
# dependencies
# --------------------------------------------------------------------------

def _load_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def read_dependencies(repo):
    """Production dependencies as dicts: ecosystem, name, version, licences (list or None)."""
    deps = []
    lock = _load_json(os.path.join(repo, "composer.lock"))
    if isinstance(lock, dict):
        for pkg in lock.get("packages") or []:
            if pkg.get("name") and pkg.get("version"):
                deps.append({"ecosystem": "composer", "name": pkg["name"],
                             "version": pkg["version"].lstrip("v"), "licences": pkg.get("license") or []})
    lock = _load_json(os.path.join(repo, "package-lock.json"))
    if isinstance(lock, dict):
        for key, pkg in (lock.get("packages") or {}).items():
            if not key or pkg.get("dev") or pkg.get("devOptional") or pkg.get("link") or not pkg.get("version"):
                continue
            name = key.split("node_modules/")[-1]
            licence = pkg.get("license")
            deps.append({"ecosystem": "npm", "name": name, "version": pkg["version"],
                         "licences": split_licence_expression(licence) if isinstance(licence, str) else []})
    path = os.path.join(repo, "requirements.txt")
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                match = re.match(r"^\s*([A-Za-z0-9._-]+)\s*==\s*([^\s;#]+)", line)
                if match:
                    deps.append({"ecosystem": "pypi", "name": match.group(1), "version": match.group(2),
                                 "licences": None})
    unique = {(d["ecosystem"], d["name"], d["version"]): d for d in deps}
    return list(unique.values())


def split_licence_expression(expression):
    """`(MIT OR Apache-2.0)` -> ["MIT", "Apache-2.0"]; an AND keeps both terms."""
    parts = re.split(r"\s+(?:OR|AND)\s+|[()]", expression or "")
    return [part.strip() for part in parts if part.strip()]


def unmanaged_share(repo, deps):
    """Percentage of dependencies that are third-party code committed into the repository."""
    try:
        files = subprocess.run(["git", "-C", repo, "ls-files"], capture_output=True, text=True,
                               check=True).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError):
        return None, "not a git checkout"
    libraries = set()
    for path in files:
        match = UNMANAGED.search(path)
        if match and not path.startswith(("tests/", "test/", "node_modules/")):
            libraries.add(path[:match.end()] if match.group(2) else path)
    total = len(deps) + len(libraries)
    if total == 0:
        return None, "no dependencies"
    return 100.0 * len(libraries) / total, f"{len(libraries)} unmanaged of {total} dependencies"


# --------------------------------------------------------------------------
# network
# --------------------------------------------------------------------------

class Fetcher:
    """HTTP JSON with a file cache; `offline` serves only what the cache holds."""

    def __init__(self, cache_path=None, offline=False, now=None):
        self.cache_path = cache_path
        self.offline = offline
        self.now = now or datetime.datetime.now(datetime.timezone.utc).timestamp()
        self.cache = (_load_json(cache_path) or {}) if cache_path else {}
        self.errors = []

    def get(self, url, body=None, reduce=None):
        """JSON from `url` (POSTing `body` when given); `reduce` trims it before it is cached."""
        key = url if body is None else f"{url} {hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()}"
        hit = self.cache.get(key)
        if hit and (self.offline or self.now - hit["at"] < CACHE_TTL_SECONDS):
            return hit["data"]
        if self.offline:
            return None
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(url, data=data, headers={
            "User-Agent": USER_AGENT, "Accept": "application/json",
            **({"Content-Type": "application/json"} if data else {})})
        try:
            with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
                result = json.loads(response.read().decode("utf-8"))
            if reduce is not None:
                result = reduce(result)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                result = None
            else:
                self.errors.append(f"{url}: HTTP {error.code}")
                return None
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as error:
            self.errors.append(f"{url}: {error}")
            return None
        self.cache[key] = {"at": self.now, "data": result}
        return result

    def save(self):
        if not self.cache_path:
            return
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as handle:
            json.dump(self.cache, handle)


def _parse_time(value):
    try:
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (AttributeError, ValueError):
        return None


def release_history(fetcher, dep):
    """(release time of the locked version, time of the latest release, licences) or Nones."""
    ecosystem, name, version = dep["ecosystem"], dep["name"], dep["version"]
    times, licences = {}, None
    if ecosystem == "composer":
        data = fetcher.get(f"https://repo.packagist.org/p2/{name}.json", reduce=lambda doc: {"packages": {
            name: [{k: e.get(k) for k in ("version", "version_normalized", "time")}
                   for e in ((doc or {}).get("packages") or {}).get(name, [])]}})
        for entry in ((data or {}).get("packages") or {}).get(name, []):
            stamp = _parse_time(entry.get("time"))
            if stamp and not re.search(r"dev|alpha|beta|rc", entry.get("version", ""), re.I):
                times[entry.get("version_normalized") or entry["version"]] = stamp
                times[entry["version"].lstrip("v")] = stamp
    elif ecosystem == "npm":
        data = fetcher.get(f"https://registry.npmjs.org/{name.replace('/', '%2F')}",
                           reduce=lambda doc: {"time": (doc or {}).get("time") or {}})
        for key, value in ((data or {}).get("time") or {}).items():
            if key not in ("created", "modified") and "-" not in key:
                stamp = _parse_time(value)
                if stamp:
                    times[key] = stamp
    elif ecosystem == "pypi":
        data = fetcher.get(f"https://pypi.org/pypi/{name}/json", reduce=lambda doc: {
            "info": {k: ((doc or {}).get("info") or {}).get(k) for k in ("license", "license_expression")},
            "releases": {v: [{"upload_time_iso_8601": f.get("upload_time_iso_8601")} for f in files]
                         for v, files in ((doc or {}).get("releases") or {}).items()}})
        for key, files in ((data or {}).get("releases") or {}).items():
            stamps = [_parse_time(f.get("upload_time_iso_8601")) for f in files]
            stamps = [s for s in stamps if s]
            if stamps and not re.search(r"[a-z]", key, re.I):
                times[key] = min(stamps)
        info = (data or {}).get("info") or {}
        licences = split_licence_expression(info.get("license_expression") or info.get("license") or "") or None
    if not times:
        return None, None, licences
    return times.get(version), max(times.values()), licences


def osv_severity(vulnerability):
    """The vulnerability's severity as low/moderate/high/critical, or unknown."""
    label = str((vulnerability.get("database_specific") or {}).get("severity") or "").lower()
    if label in ("low", "moderate", "medium", "high", "critical"):
        return "moderate" if label == "medium" else label
    for entry in vulnerability.get("severity") or []:
        match = re.search(r"(\d+(\.\d+)?)$", str(entry.get("score", "")))
        if match and entry.get("type", "").startswith("CVSS") and "/" not in match.group(1):
            score = float(match.group(1))
            return "critical" if score >= 9 else "high" if score >= 7 else "moderate" if score >= 4 else "low"
    return "unknown"


def vulnerabilities(fetcher, deps):
    """{dependency key: worst severity} for every dependency with a known vulnerability, or None."""
    found = {}
    for start in range(0, len(deps), 500):
        chunk = deps[start:start + 500]
        queries = [{"package": {"name": d["name"], "ecosystem": ECOSYSTEM_OSV[d["ecosystem"]]},
                    "version": d["version"]} for d in chunk]
        data = fetcher.get("https://api.osv.dev/v1/querybatch", {"queries": queries})
        if data is None:
            return None
        for dep, result in zip(chunk, data.get("results") or []):
            ids = [v["id"] for v in result.get("vulns") or []]
            if ids:
                found[dep_key(dep)] = ids
    worst = {}
    for key, ids in found.items():
        levels = []
        for vuln_id in ids:
            detail = fetcher.get(f"https://api.osv.dev/v1/vulns/{vuln_id}", reduce=lambda doc: {
                k: (doc or {}).get(k) for k in ("id", "severity", "database_specific")})
            levels.append(osv_severity(detail) if detail else "unknown")
        worst[key] = max(levels, key=SEVERITY_ORDER.index)
    return worst


def dep_key(dep):
    return f"{dep['ecosystem']}:{dep['name']}@{dep['version']}"


# --------------------------------------------------------------------------
# ratings
# --------------------------------------------------------------------------

def licence_class(licences):
    """The risk class of one dependency; of alternative licences the lowest risk counts."""
    classes = [next((c for c, rx in LICENCE_CLASSES if rx.search(lic or "")), "none") for lic in licences or ["none"]]
    return min(classes, key=LICENCE_ORDER.index)


def rate_vulnerabilities(worst):
    severe = sum(1 for level in worst.values() if level in ("high", "critical"))
    moderate = sum(1 for level in worst.values() if level == "moderate")
    if severe == 0 and moderate == 0:
        return 5
    if severe == 0:
        return 4
    return 3 if severe <= 2 else 2 if severe <= 5 else 1


def rate_age(ages_years, limits, max_years):
    """Stars for a list of ages: shares above each bound against the scaled limits."""
    if not ages_years:
        return None
    total = len(ages_years)
    shares = [100.0 * sum(1 for age in ages_years if age > bound) / total for bound, _ in limits]
    stars = 1
    for level, factor in ((5, 0.5), (4, 1.0), (3, 2.0), (2, 4.0)):
        if all(share <= limit * factor for share, (_, limit) in zip(shares, limits)):
            stars = level
            break
    if any(age > max_years for age in ages_years):
        stars = min(stars, 3)
    return stars


def rate_licences(counts):
    if counts["critical"]:
        return 1
    if counts["high"]:
        return 2
    if counts["medium"] or counts["low"] > 3:
        return 3
    return 4 if counts["low"] else 5


def rate_management(share):
    if share is None:
        return None
    for level, limit in ((5, 0.0), (4, MANAGEMENT_LIMIT), (3, 2 * MANAGEMENT_LIMIT), (2, 4 * MANAGEMENT_LIMIT)):
        if share <= limit:
            return level
    return 1


def build_report(repo, fetcher):
    deps = read_dependencies(repo)
    now = fetcher.now
    year = 365.25 * 24 * 3600
    report = {"repository": os.path.abspath(repo), "dependencies": len(deps),
              "ecosystems": sorted({d["ecosystem"] for d in deps}), "properties": {}, "errors": []}

    worst = vulnerabilities(fetcher, deps) if deps else {}
    report["properties"]["vulnerabilities"] = {
        "stars": None if worst is None else rate_vulnerabilities(worst),
        "detail": None if worst is None else {
            level: sum(1 for value in worst.values() if value == level) for level in SEVERITY_ORDER},
        "affected": None if worst is None else dict(sorted(worst.items())),
    }

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        histories = list(pool.map(lambda d: release_history(fetcher, d), deps))
    behind, inactive, unknown = [], [], 0
    counts = dict.fromkeys(LICENCE_ORDER, 0)
    for dep, (used, latest, fetched_licences) in zip(deps, histories):
        if latest is None:
            unknown += 1
        else:
            inactive.append((now - latest) / year)
            if used is not None:
                behind.append(max(0.0, (latest - used) / year))
        licences = dep["licences"] if dep["licences"] is not None else fetched_licences
        counts[licence_class(licences)] += 1
    report["properties"]["freshness"] = {
        "stars": rate_age(behind, FRESHNESS_LIMITS, FRESHNESS_MAX_YEARS),
        "detail": age_detail(behind, FRESHNESS_LIMITS, FRESHNESS_MAX_YEARS), "unknown": len(deps) - len(behind)}
    report["properties"]["activity"] = {
        "stars": rate_age(inactive, ACTIVITY_LIMITS, ACTIVITY_MAX_YEARS),
        "detail": age_detail(inactive, ACTIVITY_LIMITS, ACTIVITY_MAX_YEARS), "unknown": unknown}
    report["properties"]["licence"] = {"stars": rate_licences(counts) if deps else None, "detail": counts}
    share, note = unmanaged_share(repo, deps)
    report["properties"]["management"] = {"stars": rate_management(share),
                                          "detail": {"unmanaged_percent": share, "note": note}}

    rated = [p["stars"] for p in report["properties"].values() if p["stars"] is not None]
    report["overall"] = round(sum(rated) / len(rated)) if rated else None
    report["errors"] = fetcher.errors[:20]
    return report


def age_detail(ages, limits, max_years):
    if not ages:
        return None
    total = len(ages)
    return {**{f">{bound}y": round(100.0 * sum(1 for a in ages if a > bound) / total, 1) for bound, _ in limits},
            f">{max_years}y count": sum(1 for a in ages if a > max_years), "rated": total}


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    rep = sub.add_parser("report")
    rep.add_argument("repo")
    rep.add_argument("--json")
    rep.add_argument("--offline", action="store_true", help="use only cached registry and OSV data")
    rep.add_argument("--cache", default=os.path.join(
        os.environ.get("HYDRA_GATE_TOOLS_DIR") or os.path.join(os.path.expanduser("~"), ".cache", "hydra-gates"),
        "open-source-health-cache.json"))
    args = parser.parse_args(argv)
    if not os.path.isdir(args.repo):
        print(f"not a directory: {args.repo}", file=sys.stderr)
        return 2
    fetcher = Fetcher(args.cache, offline=args.offline)
    report = build_report(args.repo, fetcher)
    fetcher.save()
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
    stars = {name: prop["stars"] for name, prop in report["properties"].items()}
    print(f"open-source-health: {report['dependencies']} dependencies; overall {report['overall']}; {stars}")
    return 0 if report["dependencies"] or report["properties"]["management"]["stars"] is not None else 4


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
