#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""E2E skip discipline — reads the RUN's Playwright report, not the source.

Every other e2e gate in this repo reads `tests/e2e/**` source. That is exactly
what this gate cannot do, and why it exists.

`check_e2e_coverage.py` (gate-19) already parses `test.skip(...)` statically and
is careful about it: it separates an unconditional `test.skip(true)` from a
conditional `test.skip(cond, reason)`, and issue #239 tightened the case of an
unconditional skip hidden inside an `if` guard. What no source reader can settle
is the form the fleet actually uses:

    const present = await someLiveQuery(page)
    test.skip(!present, 'Members tab not deployed on this instance')

At source level that is indistinguishable from a test that runs. Only the report
of an actual run knows whether it executed. Nothing read the report, so the
fleet accumulated 298 skipped tests across 3210 (9.3%) and 27 spec files that
execute ZERO tests — every one of them on a GREEN run.

MEASURED 2026-08-24 by this script, against the latest green `development` run
of each of 20 fleet apps. Fleet totals: 298/3210 skipped, V1=27, V2=61, V3=142.
The eight apps carrying it:

    buildiq   68/259 (26.3%)   6 zero-test specs
    decidiq   57/191 (29.8%)   1
    dossiq    38/137 (27.7%)   5
    pipelinq  40/324 (12.3%)   3
    learniq   27/457  (5.9%)   6
    shillinq  21/345  (6.1%)   3
    integriq  16/191  (8.4%)   2
    filinq     9/124  (7.3%)   1

(An earlier hand-rolled count of mine read double these, by summing the
report's own `report.json` roll-up alongside the per-file entries. This script
skips `report.json` for that reason — the per-file entries are the whole truth
and the roll-up repeats them.)

Three findings, in the order they matter.

**V1 — a spec file that executed zero tests.** It contributes nothing and reads
as coverage. Worse, gate-19 accepts it as the `@e2e` anchor for an openspec
scenario, so a scenario can be "covered" by a file that never runs.

**V2 — a skip that defers to a deploy state CI fully determines.** These are
real, copied verbatim from green runs:

    "decidiq not deployed on the shared instance — live-run deferred"
    "Members tab not deployed on this instance"
    "Deploy drift: the deployed decidiq predates minutes-ui-v1"
    "Sub-cases tab not present in the deployed build (deploy mismatch)"
    "leaves PR not deployed yet"

Every one was written for a SHARED DEV INSTANCE, where the deployed build really
can lag the test. CI is not that, and the claim fails there in one of two ways:

* About the app under test, it is **impossible**. The app IS the head commit, so
  "not deployed" and "deploy drift" cannot happen, and the same sentence can
  only mean the feature is missing or broken.
* About a dependency (decidiq's 46 all say "leaves PR not deployed yet", meaning
  the pinned `nextcloud-vue`), it is **deterministic**. The lockfile decides it,
  identically on every run. A test that quietly stands down because the pinned
  dependency is too old is not waiting for anything: either bump the dependency
  or drop the test.

Either way the guard is an unconditional escape hatch in the one environment
where the condition is not a matter of luck. Note the shape of decidiq's worst
case — `partial registry: 27/29 providers` skips an exact-count assertion, so a
registry that is 93% correct reads as "not deployed" rather than as a diff.

**V3 — a skip with no reason.** 142 of the 298 carry no description at all. A
reason is already required by gate-16 and gate-19 for their exclusions; a skip
is an exclusion decided at run time and the same rule applies. Without one there
is nothing to review and nothing to expire.

NOT a finding: a skip that names an optional Nextcloud app or external service
the CI instance genuinely does not have ("No chat backend reachable", "requires
a TaskProcessing LLM provider"). Those describe a real absence the app does not
control. They must still carry a reason (V3), but they are allowed to skip.

Modes, following the `app:check-code` precedent in quality.yml: `report` always
exits 0 and prints the table, `enforce` exits 1 on any violation. Day one is
report-only per app, because a gate that turns eight apps red at once is a gate
nobody can turn on.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import sys
import zipfile
from pathlib import Path

# Reasons that defer to a deploy state CI fully determines — impossible for the
# app under test, deterministic for a pinned dependency. Each entry was taken
# from a real skip annotation on a green fleet run, not invented. Matched
# case-insensitively against the whole reason string.
DEPLOY_STATE = (
	"not deployed",
	"not yet deployed",
	"deploy drift",
	"deploy mismatch",
	"not present in the deployed build",
	"predates",
	"not yet wired",
	"deployed build",
	"on the shared instance",
	"in target instance",
	"on this instance",
)

# A reason may name a genuinely absent optional dependency even though it also
# trips a phrase above ("no Talk backend reachable on this instance"). These
# phrases mark that shape and are checked FIRST, so a real environment gap is
# never reported as a deploy claim.
ENVIRONMENT_ABSENCE = (
	"not reachable",
	"no chat backend",
	"unreachable",
	"credential",
	"llm provider",
	"not provisioned",
	"not installed",
	"session does not survive",
)

# Tolerate further attributes between the id and the closing bracket. Playwright
# writes `<script id="playwrightReportBase64">data:...` today; pinning that exact
# adjacency would let a future attribute silently turn this gate into a no-op,
# and a no-op gate is indistinguishable from a clean fleet.
_BLOB = re.compile(
	r'id="playwrightReportBase64"[^>]*>\s*data:application/zip;base64,([A-Za-z0-9+/=]+)'
)


def _load_report(report_dir: Path) -> zipfile.ZipFile:
	"""Locate and open the zip embedded in a Playwright HTML report.

	:param report_dir: Directory holding (or containing) ``index.html``.
	:return:           The opened in-memory zip archive.
	:raises SystemExit: When no readable report is found.
	"""
	candidates = []
	if report_dir.is_file():
		candidates = [report_dir]
	else:
		candidates = sorted(report_dir.glob("**/index.html"))
	for html in candidates:
		text = html.read_text(encoding="utf-8", errors="replace")
		match = _BLOB.search(text)
		if match is None:
			continue
		return zipfile.ZipFile(io.BytesIO(base64.b64decode(match.group(1))))
	sys.stderr.write(
		f"::error::no Playwright HTML report with an embedded result blob under {report_dir}. "
		"This gate reads the REPORT, so a missing report is a missing measurement, "
		"not a pass. Ensure the `html` reporter ran and its directory is the one passed here.\n"
	)
	raise SystemExit(2)


# Playwright records a run-time exclusion under two annotation types, and both
# stop a test from running: `skip` and `fixme`. Reading only `skip` reported 45
# fleet-wide fixme-only tests as "no reason recorded", 2 of which carried a
# perfectly good one — dossiq's `BUG #427: Cases "Add" opens the generic empty
# CnFormDialog …` and filinq's `blocked by #339 …`. A gate that cries wolf on
# the honestly-marked cases is a gate people learn to scroll past.
EXCLUSION_TYPES = ("skip", "fixme")


def _skip_reason(test: dict) -> str:
	"""Return the exclusion reason recorded for a test, or the empty string.

	Accepts both annotation types: a `fixme` is as much a test that did not run
	as a `skip` is, and it carries its reason in the same field.

	:param test: One test entry from the report.
	:return:     The reason text, stripped; empty when none was recorded.
	"""
	sources = list(test.get("annotations") or [])
	for result in test.get("results") or []:
		sources.extend(result.get("annotations") or [])
	for annotation in sources:
		if annotation.get("type") not in EXCLUSION_TYPES:
			continue
		description = (annotation.get("description") or "").strip()
		if description:
			return description
	return ""


def _skip_location(test: dict) -> str:
	"""Return ``file:line`` of the guard that skipped the test, best-effort.

	:param test: One test entry from the report.
	:return:     A ``file:line`` string, or the test's own location.
	"""
	sources = list(test.get("annotations") or [])
	for result in test.get("results") or []:
		sources.extend(result.get("annotations") or [])
	for annotation in sources:
		if annotation.get("type") not in EXCLUSION_TYPES:
			continue
		loc = annotation.get("location") or {}
		if loc.get("file"):
			return f"{os.path.basename(str(loc['file']))}:{loc.get('line', '?')}"
	loc = test.get("location") or {}
	return f"{loc.get('file', '?')}:{loc.get('line', '?')}"


def classify(reason: str) -> str:
	"""Classify a skip reason.

	:param reason: The recorded reason, possibly empty.
	:return:       One of ``no-reason``, ``deploy-state`` or ``allowed``.
	"""
	if reason == "":
		return "no-reason"
	low = reason.lower()
	# Environment absence wins: it describes something the app genuinely does
	# not control, even when the sentence also mentions the instance.
	for phrase in ENVIRONMENT_ABSENCE:
		if phrase in low:
			return "allowed"
	for phrase in DEPLOY_STATE:
		if phrase in low:
			return "deploy-state"
	return "allowed"


def collect(archive: zipfile.ZipFile) -> dict:
	"""Read every per-file result entry out of the report archive.

	:param archive: The opened report zip.
	:return:        Mapping of spec file name to its outcome tallies + skips.
	"""
	files: dict[str, dict] = {}
	for name in archive.namelist():
		if not name.endswith(".json") or name == "report.json":
			continue
		try:
			payload = json.loads(archive.read(name))
		except (ValueError, KeyError):
			continue
		entries = payload.get("files") or ([payload] if "tests" in payload else [])
		for entry in entries:
			file_name = entry.get("fileName") or "(unknown)"
			bucket = files.setdefault(
				file_name, {"executed": 0, "skipped": 0, "skips": []}
			)
			for test in entry.get("tests") or []:
				outcome = test.get("outcome") or test.get("status") or "?"
				if outcome == "skipped":
					bucket["skipped"] += 1
					reason = _skip_reason(test)
					bucket["skips"].append(
						{
							"title": test.get("title") or "",
							"reason": reason,
							"kind": classify(reason),
							"where": _skip_location(test),
						}
					)
				else:
					bucket["executed"] += 1
	return files


def main() -> int:
	"""Entry point.

	:return: Process exit code.
	"""
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"--report",
		required=True,
		help="Playwright HTML report directory (or its index.html).",
	)
	parser.add_argument(
		"--mode",
		choices=("report", "enforce"),
		default="report",
		help="report: always exit 0. enforce: exit 1 on any violation.",
	)
	parser.add_argument(
		"--summary",
		default="",
		help="Optional path to append a markdown summary to (e.g. $GITHUB_STEP_SUMMARY).",
	)
	args = parser.parse_args()

	files = collect(_load_report(Path(args.report)))
	if not files:
		sys.stderr.write(
			"::error::the report parsed but contained no test entries. "
			"A report with no tests is not a clean run.\n"
		)
		return 2

	zero_test = sorted(
		name
		for name, data in files.items()
		if data["executed"] == 0 and data["skipped"] > 0
	)
	impossible: list[tuple[str, dict]] = []
	no_reason: list[tuple[str, dict]] = []
	allowed = 0
	for name, data in sorted(files.items()):
		for skip in data["skips"]:
			if skip["kind"] == "deploy-state":
				impossible.append((name, skip))
			elif skip["kind"] == "no-reason":
				no_reason.append((name, skip))
			else:
				allowed += 1

	total_executed = sum(d["executed"] for d in files.values())
	total_skipped = sum(d["skipped"] for d in files.values())
	total = total_executed + total_skipped
	pct = (100.0 * total_skipped / total) if total else 0.0

	lines: list[str] = []
	lines.append(
		f"{total_skipped}/{total} tests skipped ({pct:.1f}%) across {len(files)} spec files"
	)
	lines.append("")
	lines.append(f"  V1 spec files executing ZERO tests : {len(zero_test)}")
	lines.append(f"  V2 skips deferring to a deploy state CI decides : {len(impossible)}")
	lines.append(f"  V3 skips/fixmes with no reason recorded : {len(no_reason)}")
	lines.append(f"  -- allowed (named a real absence) : {allowed}")

	if zero_test:
		lines.append("")
		lines.append("V1 — these spec files ran nothing. gate-19 still accepts them")
		lines.append("     as the @e2e anchor for an openspec scenario:")
		for name in zero_test:
			lines.append(f"       {name} ({files[name]['skipped']} skipped, 0 executed)")

	if impossible:
		lines.append("")
		lines.append("V2 — CI decides this state: impossible for the app under test (it IS")
		lines.append("     the head commit), deterministic for a pinned dependency. Assert it")
		lines.append("     or drop the test — do not stand down:")
		for name, skip in impossible[:40]:
			lines.append(f"       {name} :: {skip['where']}")
			lines.append(f"         {skip['reason'][:150]}")
		if len(impossible) > 40:
			lines.append(f"       ... and {len(impossible) - 40} more")

	if no_reason:
		lines.append("")
		lines.append("V3 — a skip or fixme is a run-time exclusion; gate-16 and gate-19")
		lines.append("     both require exclusions to carry a reason. These carry none:")
		shown: dict[str, int] = {}
		for name, _skip in no_reason:
			shown[name] = shown.get(name, 0) + 1
		for name, count in sorted(shown.items(), key=lambda kv: -kv[1])[:25]:
			lines.append(f"       {count:4d}  {name}")

	report_text = "\n".join(lines)
	print(report_text)

	if args.summary:
		try:
			with open(args.summary, "a", encoding="utf-8") as handle:
				handle.write("\n### E2E skip discipline\n\n```\n")
				handle.write(report_text)
				handle.write("\n```\n")
		except OSError as error:
			sys.stderr.write(f"::warning::could not append the summary: {error}\n")

	violations = len(zero_test) + len(impossible) + len(no_reason)
	if violations == 0:
		print("\nEvery skip names a real absence and every spec file ran something.")
		return 0

	if args.mode == "enforce":
		sys.stderr.write(
			f"::error::{violations} e2e skip-discipline violations. "
			"A skipped test is not a passing test.\n"
		)
		return 1

	sys.stderr.write(
		f"::warning::{violations} e2e skip-discipline violations (report-only). "
		"Flip `e2e-skip-blocking: true` for this app once they are worked down.\n"
	)
	return 0


if __name__ == "__main__":
	sys.exit(main())
