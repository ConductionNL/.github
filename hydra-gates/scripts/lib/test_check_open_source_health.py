#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Tests for the Open Source Health report (check_open_source_health.py).

No network: registry and OSV responses come from a stub fetcher, and the
repositories are temporary git checkouts with hand-written lockfiles.

  1. DEPENDENCIES: production packages from composer.lock, package-lock.json
     (dev and devOptional skipped) and pinned requirements.txt lines.
  2. RATINGS: every star boundary of vulnerabilities, freshness, activity,
     licence and management, and the absolute age cap.
  3. SEVERITY: OSV database severity labels and CVSS scores.
  4. BANDS: the thresholds per level that the report publishes, and that the
     ratings agree with them.
  5. REPORT: a full report on a stubbed repository; an unreachable OSV gives a
     null rating, never a good one.

Run: python3 scripts/lib/test_check_open_source_health.py
"""
import datetime
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_open_source_health as osh  # noqa: E402

NOW = datetime.datetime(2026, 11, 1, tzinfo=datetime.timezone.utc).timestamp()
YEAR = 365.25 * 24 * 3600


def iso(years_ago):
    return datetime.datetime.fromtimestamp(NOW - years_ago * YEAR, datetime.timezone.utc).isoformat()


class StubFetcher(osh.Fetcher):
    def __init__(self, responses):
        super().__init__(cache_path=None, offline=False, now=NOW)
        self.responses = responses

    def get(self, url, body=None, reduce=None):
        for prefix, value in self.responses.items():
            if url.startswith(prefix):
                return value(body) if callable(value) else value
        return None


def make_repo(files):
    repo = tempfile.mkdtemp()
    for path, content in files.items():
        full = os.path.join(repo, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as handle:
            handle.write(content if isinstance(content, str) else json.dumps(content))
    subprocess.run(["git", "init", "-q", repo], check=True)
    subprocess.run(["git", "-C", repo, "add", "-A"], check=True)
    return repo


COMPOSER_LOCK = {
    "packages": [{"name": "acme/lib", "version": "v1.2.0", "license": ["MIT"]}],
    "packages-dev": [{"name": "phpunit/phpunit", "version": "10.0.0", "license": ["BSD-3-Clause"]}],
}
PACKAGE_LOCK = {
    "lockfileVersion": 3,
    "packages": {
        "": {"name": "app", "version": "1.0.0"},
        "node_modules/left-pad": {"version": "1.3.0", "license": "WTFPL"},
        "node_modules/@scope/ui": {"version": "2.0.0", "license": "AGPL-3.0-or-later"},
        "node_modules/eslint": {"version": "9.0.0", "license": "MIT", "dev": True},
        "node_modules/lightningcss": {"version": "1.0.0", "license": "MPL-2.0", "devOptional": True},
    },
}


class DependencyTests(unittest.TestCase):
    def test_reads_production_dependencies_only(self):
        repo = make_repo({"composer.lock": COMPOSER_LOCK, "package-lock.json": PACKAGE_LOCK,
                          "requirements.txt": "requests==2.31.0\nflask>=2\n# comment\n"})
        keys = sorted(osh.dep_key(d) for d in osh.read_dependencies(repo))
        self.assertEqual(keys, ["composer:acme/lib@1.2.0", "npm:@scope/ui@2.0.0", "npm:left-pad@1.3.0",
                                "pypi:requests@2.31.0"])

    def test_splits_licence_expressions(self):
        self.assertEqual(osh.split_licence_expression("(MIT OR Apache-2.0)"), ["MIT", "Apache-2.0"])

    def test_counts_committed_third_party_code_as_unmanaged(self):
        repo = make_repo({"js/vendor/jquery.js": "x", "css/bootstrap.min.css": "x", "tests/vendor/x.js": "x",
                          "src/app.js": "x"})
        share, note = osh.unmanaged_share(repo, [{}] * 8)
        self.assertAlmostEqual(share, 20.0)
        self.assertIn("2 unmanaged of 10", note)


class RatingTests(unittest.TestCase):
    def test_vulnerabilities(self):
        self.assertEqual(osh.rate_vulnerabilities({}), 5)
        self.assertEqual(osh.rate_vulnerabilities({"a": "low", "b": "moderate"}), 4)
        self.assertEqual(osh.rate_vulnerabilities({"a": "high", "b": "critical"}), 3)
        self.assertEqual(osh.rate_vulnerabilities({str(i): "high" for i in range(5)}), 2)
        self.assertEqual(osh.rate_vulnerabilities({str(i): "high" for i in range(6)}), 1)

    def test_freshness_at_the_four_star_limits(self):
        # 100 dependencies: 34 behind >1y, 19 of them >2y, 11 of those >3.5y.
        ages = [4.0] * 11 + [2.5] * 8 + [1.5] * 15 + [0.1] * 66
        self.assertEqual(osh.rate_age(ages, osh.FRESHNESS_LIMITS, osh.FRESHNESS_MAX_YEARS), 4)

    def test_freshness_five_stars_needs_half_the_limits(self):
        ages = [1.5] * 17 + [0.1] * 83
        self.assertEqual(osh.rate_age(ages, osh.FRESHNESS_LIMITS, osh.FRESHNESS_MAX_YEARS), 5)
        ages = [1.5] * 18 + [0.1] * 82
        self.assertEqual(osh.rate_age(ages, osh.FRESHNESS_LIMITS, osh.FRESHNESS_MAX_YEARS), 4)

    def test_one_dependency_beyond_the_absolute_bound_caps_at_three(self):
        ages = [6.0] + [0.1] * 99
        self.assertEqual(osh.rate_age(ages, osh.FRESHNESS_LIMITS, osh.FRESHNESS_MAX_YEARS), 3)

    def test_activity_one_star_when_most_are_abandoned(self):
        self.assertEqual(osh.rate_age([5.0] * 60 + [0.1] * 40, osh.ACTIVITY_LIMITS, osh.ACTIVITY_MAX_YEARS), 1)

    def test_no_ages_is_not_rated(self):
        self.assertIsNone(osh.rate_age([], osh.ACTIVITY_LIMITS, osh.ACTIVITY_MAX_YEARS))

    def test_licence_classes(self):
        self.assertEqual(osh.licence_class(["AGPL-3.0-or-later"]), "critical")
        self.assertEqual(osh.licence_class(["LGPL-2.1-only"]), "low")
        self.assertEqual(osh.licence_class(["GPL-3.0-only"]), "medium")
        self.assertEqual(osh.licence_class(["GPL-2.0-only", "MIT"]), "none")
        self.assertEqual(osh.licence_class([]), "none")

    def test_licence_ratings(self):
        base = dict.fromkeys(osh.LICENCE_ORDER, 0)
        self.assertEqual(osh.rate_licences(base), 5)
        self.assertEqual(osh.rate_licences({**base, "low": 3}), 4)
        self.assertEqual(osh.rate_licences({**base, "low": 4}), 3)
        self.assertEqual(osh.rate_licences({**base, "medium": 1}), 3)
        self.assertEqual(osh.rate_licences({**base, "high": 1}), 2)
        self.assertEqual(osh.rate_licences({**base, "critical": 1}), 1)

    def test_management(self):
        self.assertEqual(osh.rate_management(0.0), 5)
        self.assertEqual(osh.rate_management(6.0), 4)
        self.assertEqual(osh.rate_management(12.0), 3)
        self.assertEqual(osh.rate_management(24.0), 2)
        self.assertEqual(osh.rate_management(30.0), 1)
        self.assertIsNone(osh.rate_management(None))


class BandTests(unittest.TestCase):
    def test_age_bands_scale_the_four_star_limits(self):
        bands = osh.star_bands()["freshness"]
        first = bands["bounds"][0]
        self.assertEqual(first["years"], 1.0)
        self.assertEqual(first["max_percent"], {"5": 17.1, "4": 34.2, "3": 68.4, "2": 100.0})
        self.assertEqual(bands["absolute"], {"years": 5.0, "max_count": 0, "cap_stars": 3})
        activity = osh.star_bands()["activity"]
        self.assertEqual([b["years"] for b in activity["bounds"]], [1.0, 2.0, 4.0])
        self.assertEqual(activity["bounds"][2]["max_percent"]["3"], 19.2)
        self.assertEqual(activity["absolute"]["years"], 5.5)

    def test_count_and_share_bands(self):
        bands = osh.star_bands()
        self.assertEqual(bands["vulnerabilities"]["5"], {"critical_or_high": 0, "moderate": 0})
        self.assertEqual(bands["vulnerabilities"]["3"], {"critical_or_high": 2, "moderate": None})
        self.assertEqual(bands["licence"]["4"], {"critical": 0, "high": 0, "medium": 0, "low": 3})
        self.assertEqual(bands["licence"]["2"], {"critical": 0, "high": None, "medium": None, "low": None})
        self.assertEqual(bands["management"]["max_unmanaged_percent"], {"5": 0.0, "4": 6.0, "3": 12.0, "2": 24.0})

    def test_ratings_match_the_bands(self):
        bands = osh.star_bands()
        for level in ("5", "4", "3", "2"):
            limits = bands["licence"][level]
            counts = {"none": 0, **{key: 99 if limit is None else limit for key, limit in limits.items()}}
            self.assertEqual(osh.rate_licences(counts), int(level))
            share = bands["management"]["max_unmanaged_percent"][level]
            self.assertEqual(osh.rate_management(share), int(level))


class SeverityTests(unittest.TestCase):
    def test_database_label(self):
        self.assertEqual(osh.osv_severity({"database_specific": {"severity": "MODERATE"}}), "moderate")
        self.assertEqual(osh.osv_severity({"database_specific": {"severity": "medium"}}), "moderate")

    def test_numeric_cvss_score(self):
        self.assertEqual(osh.osv_severity({"severity": [{"type": "CVSS_V3", "score": "9.8"}]}), "critical")

    def test_vector_without_label_is_unknown(self):
        vector = {"severity": [{"type": "CVSS_V3", "score": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"}]}
        self.assertEqual(osh.osv_severity(vector), "unknown")


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.repo = make_repo({"package-lock.json": PACKAGE_LOCK})

    def responses(self, osv):
        return {
            "https://api.osv.dev/v1/querybatch": osv,
            "https://api.osv.dev/v1/vulns/GHSA-1": {"id": "GHSA-1", "database_specific": {"severity": "HIGH"}},
            "https://registry.npmjs.org/left-pad": {"time": {"1.3.0": iso(6.0), "created": iso(9)}},
            "https://registry.npmjs.org/@scope%2Fui": {"time": {"2.0.0": iso(0.5), "2.1.0": iso(0.2)}},
        }

    def test_full_report(self):
        def osv(body):
            names = [q["package"]["name"] for q in body["queries"]]
            return {"results": [{"vulns": [{"id": "GHSA-1"}]} if n == "left-pad" else {} for n in names]}

        report = osh.build_report(self.repo, StubFetcher(self.responses(osv)))
        props = report["properties"]
        self.assertEqual(report["dependencies"], 2)
        self.assertEqual(props["vulnerabilities"]["stars"], 3)
        self.assertEqual(props["vulnerabilities"]["affected"], {"npm:left-pad@1.3.0": "high"})
        self.assertEqual(props["licence"]["stars"], 1)
        self.assertEqual(props["activity"]["stars"], 1)
        self.assertEqual(props["management"]["stars"], 5)
        self.assertIsNotNone(report["overall"])
        self.assertEqual(report["bands"], osh.star_bands())

    def test_unreachable_osv_is_not_rated(self):
        report = osh.build_report(self.repo, StubFetcher(self.responses(None)))
        self.assertIsNone(report["properties"]["vulnerabilities"]["stars"])


if __name__ == "__main__":
    unittest.main()
