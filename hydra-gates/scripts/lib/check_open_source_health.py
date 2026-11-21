#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Open Source Health: how healthy the third-party dependencies of a repository are.

Rates five properties of the production dependencies from 0.5 to 5.5, and in
1 to 5 stars,
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
caps the rating at 3 stars when it is broken. The report's `bands` lists these
thresholds per property and level, computed from the same constants.

RATING
------
Each property also gets a continuous `rating` from 0.5 to 5.5, two decimals,
on the quality model's scale: every star level is a band one wide, 4.5 to 5.5
being 5 stars, and x.5 belongs to the level above (rating_to_stars). The
rating always lies in the band of the property's stars.

  shares   (freshness, activity, management) per bound: 5.5 at 0%, k - 0.5
           exactly at the limit of level k, linear between two limits, and
           from 1.5 at the 2-star limit down to 0.5 at 100%. A property with
           several bounds takes its worst bound. A broken absolute bound caps
           the rating at 3.49, the top of the 3-star band.
  counts   (vulnerabilities, licence) per rated class: 0 rates 5.5. A count in
           the band of level k falls linearly from k + 0.5 at the largest
           count the level above allows (that count itself still rates as the
           level above) to k - 0.5 at the largest count level k allows. A level
           that allows any count, and 1 star, rate the band's midpoint k. The
           property takes its worst class. More findings never raise a rating.

  vulnerabilities  critical or high: 1 -> 3.0, 2 -> 2.5, 3 -> 2.17, 4 -> 1.83,
                   5 -> 1.5, 6 or more -> 1.0; moderate: 1 or more -> 4.0.
  licence          low: 1 -> 4.17, 2 -> 3.83, 3 -> 3.5, 4 or more -> 3.0;
                   medium -> 3.0; high -> 2.0; critical -> 1.0.

`overall_rating` is the mean of the property ratings, two decimals, and
`overall` its whole stars.

LICENCE EXCLUDES
----------------
`--exclude-licence REGEX` (repeatable) leaves every dependency whose name
fully matches REGEX out of the licence property only, for a dependency whose
licence the maintainers have reviewed and accepted. Such a dependency still counts for vulnerabilities, freshness, activity and management. The
licence detail reports how many were excluded.

Usage:
    check_open_source_health.py report <repo-dir> [--json FILE] [--offline]
                                       [--exclude-licence REGEX ...]

Exit status: 0 a report, 2 bad arguments, 4 no dependency data to rate.
"""
import argparse
import concurrent.futures
import datetime
import hashlib
import json
import math
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
# Factors on the 4-star share limits per level; a broken absolute bound caps the rating at AGE_CAP_STARS.
AGE_FACTORS = ((5, 0.5), (4, 1.0), (3, 2.0), (2, 4.0))
AGE_CAP_STARS = 3
MANAGEMENT_FACTORS = ((5, 0.0), (4, 1.0), (3, 2.0), (2, 4.0))
# Most dependencies allowed per level; a class or severity that is absent has no limit.
VULNERABILITY_BANDS = ((5, {"critical_or_high": 0, "moderate": 0}), (4, {"critical_or_high": 0}),
                       (3, {"critical_or_high": 2}), (2, {"critical_or_high": 5}))
LICENCE_BANDS = ((5, {"critical": 0, "high": 0, "medium": 0, "low": 0}),
                 (4, {"critical": 0, "high": 0, "medium": 0, "low": 3}),
                 (3, {"critical": 0, "high": 0}), (2, {"critical": 0}))


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


def rating_to_stars(rating):
    """Whole stars of a 0.5 to 5.5 rating: each level is a band one wide, x.5 rounds up."""
    return max(1, min(5, math.floor(rating + 0.5)))


def within_stars(raw, stars):
    """`raw` to two decimals, kept inside the band of `stars` so that rating_to_stars gives `stars` back."""
    top = 5.5 if stars == 5 else stars + 0.49
    return max(stars - 0.5, min(top, round(raw, 2)))


def share_rating(share, caps):
    """Continuous rating of one share against {5: cap, 4: cap, 3: cap, 2: cap}: 5.5 at 0, k - 0.5 at the cap
    of level k, linear in between, and from 1.5 at the 2-star cap down to 0.5 at 100%."""
    lower = 0.0
    for level in (5, 4, 3, 2):
        if share <= caps[level]:
            upper = caps[level]
            return level + 0.5 if upper <= lower else level + 0.5 - (share - lower) / (upper - lower)
        lower = caps[level]
    return max(0.5, 1.5 - (share - lower) / (100.0 - lower))


def count_rating(count, limits):
    """Continuous rating of one count against {level: most allowed}, a missing level allowing any count.

    0 rates 5.5. Within the band of level k the rating falls linearly from k + 0.5, at the largest count
    of the level above (which still rates as that level), to k - 0.5 at the largest count level k allows.
    A level that allows any count rates its midpoint k, and so does 1 star.
    """
    if count == 0:
        return 5.5
    above = -1
    for level in (5, 4, 3, 2):
        limit = limits.get(level)
        if limit is None:
            return float(level)
        if count <= limit:
            return level + 0.5 - (count - above) / (limit - above)
        above = limit
    return 1.0


def rate_counts(counts, bands):
    """The highest level whose limits all hold for `counts`, else 1."""
    for level, limits in bands:
        if all(counts[key] <= limit for key, limit in limits.items()):
            return level
    return 1


def counts_rating(counts, bands):
    """The continuous rating of `counts`: the worst rating of the rated classes."""
    raw = min(count_rating(counts[key], {level: limits.get(key) for level, limits in bands})
              for key in {key for _, limits in bands for key in limits})
    return within_stars(raw, rate_counts(counts, bands))


def vulnerability_counts(worst):
    return {"critical_or_high": sum(1 for level in worst.values() if level in ("high", "critical")),
            "moderate": sum(1 for level in worst.values() if level == "moderate")}


def rate_vulnerabilities(worst):
    return rate_counts(vulnerability_counts(worst), VULNERABILITY_BANDS)


def vulnerabilities_rating(worst):
    return counts_rating(vulnerability_counts(worst), VULNERABILITY_BANDS)


def age_caps(limit):
    """{level: largest share in percent} of one bound."""
    return {level: min(100.0, limit * factor) for level, factor in AGE_FACTORS}


def age_shares(ages_years, limits):
    total = len(ages_years)
    return [100.0 * sum(1 for age in ages_years if age > bound) / total for bound, _ in limits]


def rate_age(ages_years, limits, max_years):
    """Stars for a list of ages: shares above each bound against the scaled limits."""
    if not ages_years:
        return None
    shares = age_shares(ages_years, limits)
    stars = 1
    for level, _ in AGE_FACTORS:
        if all(share <= age_caps(limit)[level] for share, (_, limit) in zip(shares, limits)):
            stars = level
            break
    if any(age > max_years for age in ages_years):
        stars = min(stars, AGE_CAP_STARS)
    return stars


def age_rating(ages_years, limits, max_years):
    """The continuous rating of a list of ages: the worst bound's share rating, inside the band of rate_age,
    so a broken absolute bound caps it at the top of the 3-star band."""
    if not ages_years:
        return None
    raw = min(share_rating(share, age_caps(limit)) for share, (_, limit) in zip(age_shares(ages_years, limits), limits))
    return within_stars(raw, rate_age(ages_years, limits, max_years))


def rate_licences(counts):
    return rate_counts(counts, LICENCE_BANDS)


def licences_rating(counts):
    return counts_rating(counts, LICENCE_BANDS)


def management_caps():
    return {level: MANAGEMENT_LIMIT * factor for level, factor in MANAGEMENT_FACTORS}


def rate_management(share):
    if share is None:
        return None
    for level, cap in management_caps().items():
        if share <= cap:
            return level
    return 1


def management_rating(share):
    if share is None:
        return None
    return within_stars(share_rating(share, management_caps()), rate_management(share))


def age_bands(limits, max_years):
    """Per bound the largest share (percent) each level allows, and the absolute bound."""
    return {"bounds": [{"years": bound, "max_percent": {
                str(level): min(100.0, round(limit * factor, 2)) for level, factor in AGE_FACTORS}}
                       for bound, limit in limits],
            "absolute": {"years": max_years, "max_count": 0, "cap_stars": AGE_CAP_STARS}}


def count_bands(bands, keys):
    """Per level the most dependencies allowed for each key; None means no limit."""
    return {str(level): {key: limits.get(key) for key in keys} for level, limits in bands}


def star_bands():
    """The thresholds of every level from 5 down to 2 stars, per property; below them is 1 star."""
    return {
        "vulnerabilities": count_bands(VULNERABILITY_BANDS, ("critical_or_high", "moderate")),
        "freshness": age_bands(FRESHNESS_LIMITS, FRESHNESS_MAX_YEARS),
        "activity": age_bands(ACTIVITY_LIMITS, ACTIVITY_MAX_YEARS),
        "licence": count_bands(LICENCE_BANDS, ("critical", "high", "medium", "low")),
        "management": {"max_unmanaged_percent": {
            str(level): round(MANAGEMENT_LIMIT * factor, 2) for level, factor in MANAGEMENT_FACTORS}},
    }


def compile_licence_excludes(patterns, errors):
    """The valid patterns, compiled; an invalid one is reported in `errors` and skipped."""
    compiled = []
    for pattern in patterns or ():
        try:
            compiled.append(re.compile(pattern))
        except re.error as error:
            errors.append(f"licence exclude {pattern!r}: {error}")
    return compiled


def build_report(repo, fetcher, licence_excludes=()):
    deps = read_dependencies(repo)
    excludes = compile_licence_excludes(licence_excludes, fetcher.errors)
    now = fetcher.now
    year = 365.25 * 24 * 3600
    report = {"repository": os.path.abspath(repo), "dependencies": len(deps),
              "ecosystems": sorted({d["ecosystem"] for d in deps}), "properties": {}, "errors": []}

    worst = vulnerabilities(fetcher, deps) if deps else {}
    report["properties"]["vulnerabilities"] = {
        "stars": None if worst is None else rate_vulnerabilities(worst),
        "rating": None if worst is None else vulnerabilities_rating(worst),
        "detail": None if worst is None else {
            level: sum(1 for value in worst.values() if value == level) for level in SEVERITY_ORDER},
        "affected": None if worst is None else dict(sorted(worst.items())),
    }

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        histories = list(pool.map(lambda d: release_history(fetcher, d), deps))
    behind, inactive, unknown = [], [], 0
    counts = dict.fromkeys(LICENCE_ORDER, 0)
    excluded = 0
    for dep, (used, latest, fetched_licences) in zip(deps, histories):
        if latest is None:
            unknown += 1
        else:
            inactive.append((now - latest) / year)
            if used is not None:
                behind.append(max(0.0, (latest - used) / year))
        if any(rx.fullmatch(dep["name"]) for rx in excludes):
            excluded += 1
            continue
        licences = dep["licences"] if dep["licences"] is not None else fetched_licences
        counts[licence_class(licences)] += 1
    report["properties"]["freshness"] = {
        "stars": rate_age(behind, FRESHNESS_LIMITS, FRESHNESS_MAX_YEARS),
        "rating": age_rating(behind, FRESHNESS_LIMITS, FRESHNESS_MAX_YEARS),
        "detail": age_detail(behind, FRESHNESS_LIMITS, FRESHNESS_MAX_YEARS), "unknown": len(deps) - len(behind)}
    report["properties"]["activity"] = {
        "stars": rate_age(inactive, ACTIVITY_LIMITS, ACTIVITY_MAX_YEARS),
        "rating": age_rating(inactive, ACTIVITY_LIMITS, ACTIVITY_MAX_YEARS),
        "detail": age_detail(inactive, ACTIVITY_LIMITS, ACTIVITY_MAX_YEARS), "unknown": unknown}
    report["properties"]["licence"] = {"stars": rate_licences(counts) if deps else None,
                                       "rating": licences_rating(counts) if deps else None,
                                       "detail": {**counts, "excluded": excluded}}
    share, note = unmanaged_share(repo, deps)
    report["properties"]["management"] = {"stars": rate_management(share), "rating": management_rating(share),
                                          "detail": {"unmanaged_percent": share, "note": note}}

    rated = [p["rating"] for p in report["properties"].values() if p["rating"] is not None]
    report["overall_rating"] = round(sum(rated) / len(rated), 2) if rated else None
    report["overall"] = None if report["overall_rating"] is None else rating_to_stars(report["overall_rating"])
    report["bands"] = star_bands()
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
    rep.add_argument("--exclude-licence", action="append", default=[], metavar="REGEX",
                     help="leave dependencies whose name fully matches REGEX out of the licence property")
    rep.add_argument("--cache", default=os.path.join(
        os.environ.get("HYDRA_GATE_TOOLS_DIR") or os.path.join(os.path.expanduser("~"), ".cache", "hydra-gates"),
        "open-source-health-cache.json"))
    args = parser.parse_args(argv)
    if not os.path.isdir(args.repo):
        print(f"not a directory: {args.repo}", file=sys.stderr)
        return 2
    fetcher = Fetcher(args.cache, offline=args.offline)
    report = build_report(args.repo, fetcher, args.exclude_licence)
    fetcher.save()
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
    ratings = {name: prop["rating"] for name, prop in report["properties"].items()}
    print(f"open-source-health: {report['dependencies']} dependencies; overall {report['overall']} stars "
          f"({report['overall_rating']}); {ratings}")
    return 0 if report["dependencies"] or report["properties"]["management"]["stars"] is not None else 4


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
