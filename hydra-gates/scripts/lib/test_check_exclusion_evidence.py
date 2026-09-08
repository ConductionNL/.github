#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Tests for check_exclusion_evidence (gate-113). Run with:

    python3 scripts/lib/test_check_exclusion_evidence.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_exclusion_evidence as cee  # noqa: E402


def _write(root: Path, rel: str, content: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _spec(reason: str, tag: str = "e2e") -> str:
    return (
        "## Requirements\n\n"
        "### Requirement: A thing\n\n"
        "#### Scenario: The thing happens\n\n"
        f"@{tag} exclude {reason}\n\n"
        "- **WHEN** a thing\n"
        "- **THEN** it happens\n"
    )


_PHP_TEST = """\
<?php
namespace OCA\\Demo\\Tests\\Unit;

class ProjectRepositoryTest extends TestCase
{
    public function testArchivedExcluded(): void {}
    public function testActiveIncluded(): void {}
}
"""


class ExclusionEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _buckets(self) -> dict:
        return cee.analyse(self.root)["totals"]

    # -- resolution ---------------------------------------------------------

    def test_a_named_php_test_that_exists_resolves(self):
        _write(self.root, "tests/unit/ProjectRepositoryTest.php", _PHP_TEST)
        _write(self.root, "openspec/specs/projects/spec.md",
               _spec("asserted by ProjectRepositoryTest"))
        self.assertEqual(self._buckets()[cee.RESOLVED], 1)

    def test_a_named_method_that_exists_resolves(self):
        _write(self.root, "tests/unit/ProjectRepositoryTest.php", _PHP_TEST)
        _write(self.root, "openspec/specs/projects/spec.md",
               _spec("asserted by ProjectRepositoryTest::testArchivedExcluded"))
        self.assertEqual(self._buckets()[cee.RESOLVED], 1)

    def test_a_cited_SUBJECT_resolves_on_the_class_alone(self):
        # `AcknowledgementServiceTest::isOutstanding` names the method UNDER
        # test, not a test method, and the class does assert it. Demanding a
        # `function isOutstanding()` inside the test class accuses a correct
        # citation. Only a `test*` method is checked by name.
        _write(self.root, "tests/unit/ProjectRepositoryTest.php", _PHP_TEST)
        _write(self.root, "openspec/specs/projects/spec.md",
               _spec("asserted in ProjectRepositoryTest::archivedAreExcluded"))
        b = self._buckets()
        self.assertEqual(b[cee.RESOLVED], 1)
        self.assertEqual(b[cee.UNRESOLVED], 0)

    def test_a_named_method_that_does_not_exist_is_unresolved(self):
        # The class is here and the method is not. This is the shape a rename
        # leaves behind, and it is the whole reason the gate looks at methods.
        _write(self.root, "tests/unit/ProjectRepositoryTest.php", _PHP_TEST)
        _write(self.root, "openspec/specs/projects/spec.md",
               _spec("asserted by ProjectRepositoryTest::testLongGone"))
        b = self._buckets()
        self.assertEqual(b[cee.UNRESOLVED], 1)
        self.assertEqual(b[cee.RESOLVED], 0)

    def test_a_citation_naming_ANOTHER_repo_is_cross_repo_not_unresolved(self):
        # hermiq: "covered by nextcloud-vue `tests/components/CnFlowEdge.spec.js`"
        # — that file exists, in nextcloud-vue. This checkout will never contain
        # it, so calling it a broken citation accuses a correct one.
        _write(self.root, "openspec/specs/canvas/spec.md",
               _spec("covered by nextcloud-vue tests/components/CnFlowEdge.spec.js"))
        b = self._buckets()
        self.assertEqual(b[cee.CROSS_REPO], 1)
        self.assertEqual(b[cee.UNRESOLVED], 0)

    def test_the_SHORT_form_of_a_repo_name_is_also_cross_repo(self):
        # pipelinq: "engine-level behaviour covered by nc-vue
        # `useWalkthrough.spec.js`" — and nextcloud-vue/tests/composables/
        # useWalkthrough.spec.js exists. Matching only the long name accused a
        # correct citation, which is the defect this bucket exists to prevent.
        _write(self.root, "openspec/specs/nav/spec.md",
               _spec("engine-level behaviour covered by nc-vue useWalkthrough.spec.js"))
        b = self._buckets()
        self.assertEqual(b[cee.CROSS_REPO], 1)
        self.assertEqual(b[cee.UNRESOLVED], 0)

    def test_a_cross_repo_citation_does_not_fail_the_gate(self):
        _write(self.root, "openspec/specs/logs/spec.md",
               _spec("asserted in OpenRegister by ProcessingLogControllerTest"))
        self.assertEqual(cee.main(["x", str(self.root)]), cee.EXIT_PASS)

    def test_a_LOCAL_missing_citation_still_fails(self):
        # The control. Naming no other repo, it stays a finding — the
        # downgrade must not have switched the check off.
        _write(self.root, "openspec/specs/gis/spec.md",
               _spec("asserted by GeoServiceTest"))
        b = self._buckets()
        self.assertEqual(b[cee.UNRESOLVED], 1)
        self.assertEqual(b[cee.CROSS_REPO], 0)
        self.assertEqual(cee.main(["x", str(self.root)]), cee.EXIT_FAIL)

    def test_a_named_class_that_does_not_exist_is_unresolved(self):
        # procest cites GeoServiceTest, CaseGeoControllerTest and WfsServiceTest.
        # None of the three exists anywhere in that repo.
        _write(self.root, "openspec/specs/gis/spec.md",
               _spec("asserted by GeoServiceTest"))
        self.assertEqual(self._buckets()[cee.UNRESOLVED], 1)

    def test_a_js_spec_file_resolves_by_name(self):
        _write(self.root, "src/utils/versionCompare.spec.ts", "// unit test\n")
        _write(self.root, "openspec/specs/versions/spec.md",
               _spec("pure comparison, covered by versionCompare.spec.ts"))
        self.assertEqual(self._buckets()[cee.RESOLVED], 1)

    def test_a_missing_js_spec_is_unresolved(self):
        _write(self.root, "openspec/specs/versions/spec.md",
               _spec("covered by versionCompare.spec.ts"))
        self.assertEqual(self._buckets()[cee.UNRESOLVED], 1)

    def test_a_collection_resolves_by_name(self):
        _write(self.root, "tests/integration/demo.postman_collection.json", "{}")
        _write(self.root, "openspec/specs/api/spec.md",
               _spec("wire contract in demo.postman_collection.json"))
        self.assertEqual(self._buckets()[cee.RESOLVED], 1)

    def test_a_gate_number_is_accepted_without_a_local_lookup(self):
        # Gate numbers are registered in ConductionNL/.github, which an app
        # checkout cannot see. Inventing a failure it cannot answer would be
        # worse than accepting the citation.
        _write(self.root, "openspec/specs/copy/spec.md",
               _spec("mechanically enforced by gate-96"))
        self.assertEqual(self._buckets()[cee.RESOLVED], 1)

    # -- the other two buckets ---------------------------------------------

    def test_a_tier_claimed_without_a_member_is_unverifiable(self):
        _write(self.root, "openspec/specs/projects/spec.md",
               _spec("asserted by PHPUnit"))
        b = self._buckets()
        self.assertEqual(b[cee.UNVERIFIABLE], 1)
        self.assertEqual(b[cee.UNRESOLVED], 0)

    def test_vitest_without_a_file_is_unverifiable(self):
        _write(self.root, "openspec/specs/projects/spec.md",
               _spec("pure predicate, covered by unit tests in vitest"))
        self.assertEqual(self._buckets()[cee.UNVERIFIABLE], 1)

    def test_a_reason_naming_no_evidence_is_no_claim(self):
        _write(self.root, "openspec/specs/projects/spec.md",
               _spec("depends on test data state"))
        self.assertEqual(self._buckets()[cee.NO_CLAIM], 1)

    def test_a_bare_marker_is_left_to_gates_16_and_19(self):
        # `@e2e exclude` with no reason is already their finding. Counting it
        # here too would report one defect as two.
        _write(self.root, "openspec/specs/projects/spec.md",
               _spec("").replace("@e2e exclude \n", "@e2e exclude\n"))
        self.assertEqual(self._buckets()["exclusions"], 0)

    # -- families ------------------------------------------------------------

    def test_a_trailing_star_names_a_family_of_methods(self):
        # buildiq: `CopilotServiceTest::testHealthReports*` stands for the three
        # methods that begin with it. Reading the * literally accuses a
        # citation that is MORE precise than a bare class name.
        _write(self.root, "tests/unit/CopilotServiceTest.php",
               "<?php\nclass CopilotServiceTest {\n"
               "  public function testHealthReportsNoProvider(): void {}\n"
               "  public function testHealthReportsAvailable(): void {}\n}\n")
        _write(self.root, "openspec/specs/copilot/spec.md",
               _spec("probe verified by CopilotServiceTest::testHealthReports*"))
        b = self._buckets()
        self.assertEqual(b[cee.RESOLVED], 1)
        self.assertEqual(b[cee.UNRESOLVED], 0)

    def test_a_star_family_with_no_member_is_still_unresolved(self):
        _write(self.root, "tests/unit/CopilotServiceTest.php",
               "<?php\nclass CopilotServiceTest {\n"
               "  public function testSomethingElse(): void {}\n}\n")
        _write(self.root, "openspec/specs/copilot/spec.md",
               _spec("probe verified by CopilotServiceTest::testHealthReports*"))
        self.assertEqual(self._buckets()[cee.UNRESOLVED], 1)

    def test_a_brace_group_expands_to_its_members(self):
        for n in ("Map", "Roadmap"):
            _write(self.root, f"tests/components/{n}PageEditor.spec.js", "// t\n")
        _write(self.root, "openspec/specs/pages/spec.md",
               _spec("component contracts in "
                     "tests/components/{Map,Roadmap}PageEditor.spec.js"))
        b = self._buckets()
        self.assertEqual(b[cee.RESOLVED], 1)
        self.assertEqual(b[cee.UNRESOLVED], 0)

    def test_a_brace_member_that_is_missing_is_still_RECORDED(self):
        # Pins the expansion, and pins a LIMITATION with it. `classify` buckets
        # a reason as RESOLVED as soon as one artifact resolves, keeping the
        # rest under "missing". So a group where three of four exist reads as
        # resolved, and the fourth is visible only in the detail. That
        # any-not-all rule is older than brace expansion and applies to every
        # multi-artifact reason, so changing it is a separate measured change,
        # not a side effect of this one.
        _write(self.root, "tests/components/MapPageEditor.spec.js", "// t\n")
        _write(self.root, "openspec/specs/pages/spec.md",
               _spec("component contracts in "
                     "tests/components/{Map,Roadmap}PageEditor.spec.js"))
        self.assertEqual(self._buckets()[cee.RESOLVED], 1)
        bucket, detail = cee.classify(
            "component contracts in tests/components/{Map,Roadmap}PageEditor.spec.js",
            cee._Artifacts(self.root),
        )
        self.assertEqual(bucket, cee.RESOLVED)
        self.assertEqual(detail["resolved"], ["MapPageEditor.spec.js"])
        self.assertEqual(detail["missing"], ["RoadmapPageEditor.spec.js"])

    def test_the_brace_TAIL_alone_is_not_counted_as_a_file(self):
        # The control. Leaving the brace form in the plain scan would also pick
        # up the bare tail and report a fifth file nobody cited.
        for n in ("Map", "Roadmap"):
            _write(self.root, f"tests/components/{n}PageEditor.spec.js", "// t\n")
        _write(self.root, "openspec/specs/pages/spec.md",
               _spec("contracts in tests/components/{Map,Roadmap}PageEditor.spec.js"))
        self.assertEqual(self._buckets()[cee.UNRESOLVED], 0)

    # -- a reason that wraps ------------------------------------------------

    def test_a_citation_on_a_CONTINUATION_line_is_read(self):
        # integriq cited the same non-existent Playwright spec three times and
        # only one was reported: in the other two the marker and the filename
        # sat on different lines. The gate undercounted, which is the worse
        # direction — a PASS meant less than it looked.
        _write(self.root, "openspec/specs/flows/spec.md",
               "#### Scenario: A thing\n\n"
               "@e2e exclude needs a runnable seeded flow, covered by\n"
               "tests/e2e/ci/flow-controls.spec.ts and the engine's unit tests\n"
               "\n- **THEN** it happens\n")
        b = self._buckets()
        self.assertEqual(b[cee.UNRESOLVED], 1)

    def test_a_wrapped_citation_that_EXISTS_resolves(self):
        _write(self.root, "tests/unit/ProjectRepositoryTest.php", _PHP_TEST)
        _write(self.root, "openspec/specs/projects/spec.md",
               "#### Scenario: A thing\n\n"
               "@e2e exclude backend-only, with no UI surface, and it is\n"
               "asserted by ProjectRepositoryTest\n"
               "\n- **THEN** it happens\n")
        b = self._buckets()
        self.assertEqual(b[cee.RESOLVED], 1)
        self.assertEqual(b[cee.UNRESOLVED], 0)

    def test_the_scenarios_own_bullets_are_NOT_swallowed(self):
        # The control, and the reason the terminator list exists. GIVEN/WHEN/
        # THEN prose names services and controllers constantly. Reading them as
        # part of the reason would invent findings out of the scenario body.
        _write(self.root, "openspec/specs/projects/spec.md",
               "#### Scenario: A thing\n\n"
               "@e2e exclude depends on test data state\n"
               "- **GIVEN** GeoServiceTest and CaseGeoControllerTest are absent\n"
               "- **THEN** nothing here is a citation\n")
        b = self._buckets()
        self.assertEqual(b[cee.NO_CLAIM], 1)
        self.assertEqual(b[cee.UNRESOLVED], 0)

    def test_a_blank_line_ends_the_reason(self):
        _write(self.root, "openspec/specs/projects/spec.md",
               "#### Scenario: A thing\n\n"
               "@e2e exclude depends on test data state\n"
               "\n"
               "Prose about GeoServiceTest that is not part of the reason.\n")
        b = self._buckets()
        self.assertEqual(b[cee.NO_CLAIM], 1)
        self.assertEqual(b[cee.UNRESOLVED], 0)

    def test_an_html_comment_marker_reads_to_its_terminator(self):
        # buildiq wraps its exclusions in `<!-- ... -->`, across lines.
        _write(self.root, "tests/composables/useManifestValidator.spec.js", "// t\n")
        _write(self.root, "openspec/specs/theme/spec.md",
               "#### Scenario: A thing\n\n"
               "<!-- @e2e exclude pure manifest validation, covered by\n"
               "tests/composables/useManifestValidator.spec.js. -->\n"
               "\n- **THEN** it happens\n")
        b = self._buckets()
        self.assertEqual(b[cee.RESOLVED], 1)

    def test_the_join_is_bounded(self):
        # A missing terminator must not swallow the rest of the file.
        body = "\n".join(f"line {i} mentioning GeoServiceTest" for i in range(40))
        _write(self.root, "openspec/specs/projects/spec.md",
               "#### Scenario: A thing\n\n@e2e exclude a reason\n" + body + "\n")
        r = cee.analyse(self.root)
        found = [e for k in ("unresolved", "no_claim", "unverifiable",
                             "resolved", "cross_repo") for e in r.get(k, [])]
        self.assertEqual(len(found), 1, found)
        self.assertNotIn("line 20", found[0]["reason"])

    # -- scope --------------------------------------------------------------

    def test_all_four_exclusion_tags_are_judged(self):
        for tag in ("e2e", "spec", "contract", "visual"):
            _write(self.root, f"openspec/specs/{tag}-thing/spec.md",
                   _spec("asserted by PHPUnit", tag=tag))
        self.assertEqual(self._buckets()["exclusions"], 4)

    def test_flat_spec_files_are_read_like_gate_19_reads_them(self):
        _write(self.root, "openspec/specs/projects.md",
               _spec("asserted by PHPUnit"))
        self.assertEqual(self._buckets()["exclusions"], 1)

    def test_readme_is_not_a_spec(self):
        _write(self.root, "openspec/specs/README.md", _spec("asserted by PHPUnit"))
        self.assertEqual(self._buckets()["exclusions"], 0)

    def test_vendor_tests_do_not_resolve_our_citations(self):
        # A dependency's ProjectRepositoryTest must not satisfy our claim.
        _write(self.root, "vendor/acme/lib/tests/ProjectRepositoryTest.php", _PHP_TEST)
        _write(self.root, "openspec/specs/projects/spec.md",
               _spec("asserted by ProjectRepositoryTest"))
        self.assertEqual(self._buckets()[cee.UNRESOLVED], 1)

    # -- exit codes ---------------------------------------------------------

    def test_no_exclusions_is_not_applicable(self):
        _write(self.root, "openspec/specs/projects/spec.md",
               "#### Scenario: A thing\n\n- **THEN** it happens\n")
        self.assertEqual(cee.main(["x", str(self.root)]), cee.EXIT_NOT_APPLICABLE)

    def test_unverifiable_alone_does_not_fail_the_gate(self):
        # 2,791 findings on day one is a gate nobody can turn on. Only a
        # provably wrong citation fails.
        _write(self.root, "openspec/specs/projects/spec.md",
               _spec("asserted by PHPUnit"))
        self.assertEqual(cee.main(["x", str(self.root)]), cee.EXIT_PASS)

    def test_an_unresolvable_citation_fails_the_gate(self):
        _write(self.root, "openspec/specs/gis/spec.md",
               _spec("asserted by GeoServiceTest"))
        self.assertEqual(cee.main(["x", str(self.root)]), cee.EXIT_FAIL)

    def test_report_mode_always_exits_zero(self):
        _write(self.root, "openspec/specs/gis/spec.md",
               _spec("asserted by GeoServiceTest"))
        self.assertEqual(
            cee.main(["x", str(self.root), "--mode", "report"]), cee.EXIT_PASS
        )

    def test_a_missing_directory_is_an_error_not_a_pass(self):
        self.assertEqual(cee.main(["x", str(self.root / "nope")]), cee.EXIT_ERROR)


if __name__ == "__main__":
    unittest.main()
