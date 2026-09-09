#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""Tests for gate-115's checker (check_stale_fleet_app_id.py).

The gate answers one question: does this repo name another fleet app by an id
or namespace that app no longer answers to? The answer is only useful if the
four exclusions hold, because each of them was a real false positive before it
was a rule, and any one of them regressing turns the gate into noise nobody
reads.

Arms 1 and 2 are the gate itself. Arms 3 to 6 are the four exclusions, each
pinned against the shape that produced it, and each with a control arm where
over-reach would silently under-report. Arm 7 is the one the fleet asked for
explicitly.

  1. A STALE LOOKUP IS A FINDING, in every shape that matters: an
     `isInstalled()` argument, a container FQCN, an `/apps/<old>/` path and a
     constant bound to a bare retired id. Drop any one of those patterns and
     this arm names which.
  2. A CURRENT LOOKUP IS NOT. The obvious half, pinned so that widening the
     patterns cannot start matching the names apps actually ship under.
  3. COMMENTS ARE PROSE. Explaining a rename is not committing one. 7 of
     dossiq's 16 pre-rule false positives were docblocks describing the very
     defect they sat beside.
  4. A DUAL-SPELLING LIST IS CORRECT, NOT STALE. An app that renamed its
     namespace with no compatibility alias has to be listened for under both
     names, newest first. Flagging that would push authors to delete the
     fallback and re-break every unmigrated instance, so this arm guards
     against the gate causing the bug it exists to find.
  5. AN APP'S OWN FORMER ID IS NEVER A FINDING. Migration repair steps and
     frozen handshake keys name it on purpose; renaming those orphans live
     records. Derived from `<id>` in appinfo/info.xml, so this arm also pins
     that the derivation works from the file rather than from configuration.
  6. A REGISTER SLUG IS STORED DATA. Integriq's entities live under the
     register slug `openconnector` and that slug is deliberately not renamed.
     This exclusion did not exist until the checker was run across all 21
     repos: dossiq holds no cross-app register slug, so a false-positive rate
     measured only there read as zero and was not.
  7. THE BLIND SPOT IS PRINTED ON A CLEAN RUN TOO. The gate reads NAMES. It
     cannot see whether the method or route you point at exists on the other
     side, and in the incident that prompted it two of seven defects were
     exactly that. A gate that clears the name half silently reads as coverage
     of both halves, so a PASS that says nothing is a wrong answer even when
     the count is right. Make the notice conditional on findings and this arm
     goes red.

Run: python3 scripts/lib/test_check_stale_fleet_app_id.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.join(HERE, "check_stale_fleet_app_id.py")

INFO_XML = """<?xml version="1.0"?>
<info>
    <id>{app_id}</id>
    <namespace>{ns}</namespace>
</info>
"""


class StaleFleetAppIdTest(unittest.TestCase):

    def run_check(self, files, app_id="opencatalogi", ns="OpenCatalogi"):
        """Write a fixture repo and run the checker over it."""
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "appinfo"), exist_ok=True)
            with open(os.path.join(root, "appinfo", "info.xml"), "w") as fh:
                fh.write(INFO_XML.format(app_id=app_id, ns=ns))
            for rel, body in files.items():
                path = os.path.join(root, rel)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w") as fh:
                    fh.write(textwrap.dedent(body))
            proc = subprocess.run(
                [sys.executable, CHECKER, root],
                capture_output=True, text=True, timeout=120,
            )
            return proc.returncode, proc.stdout + proc.stderr

    # -- arm 1 ---------------------------------------------------------------

    def test_every_stale_lookup_shape_is_a_finding(self):
        shapes = {
            "an isInstalled argument":
                "<?php\nif ($m->isInstalled('openconnector')) { go(); }\n",
            "a container FQCN":
                "<?php\n$s = $c->get('OCA\\\\Docudesk\\\\Service\\\\DocumentService');\n",
            "an apps path":
                "const u = generateUrl('/apps/openconnector/api/pdok')\n",
            "a constant bound to a retired id, USED as one":
                "<?php\nprivate const TARGET = 'decidesk';\n"
                "public function go($m) { return $m->isInstalled(self::TARGET); }\n",
        }
        for label, body in shapes.items():
            with self.subTest(shape=label):
                ext = ".js" if "generateUrl" in body else ".php"
                rc, out = self.run_check({f"lib/Probe{ext}": body})
                self.assertEqual(rc, 1, f"{label} must be a finding\n{out}")

    # -- arm 2 ---------------------------------------------------------------

    def test_a_current_name_is_not_a_finding(self):
        rc, out = self.run_check({
            "lib/Probe.php": """\
                <?php
                if ($m->isInstalled('integriq')) { go(); }
                $s = $c->get('OCA\\\\Filinq\\\\Service\\\\DocumentService');
                """,
            "src/api.js": "const u = generateUrl('/apps/integriq/api/pdok')\n",
        })
        self.assertEqual(rc, 0, f"current names must be clean\n{out}")

    # -- arm 3 ---------------------------------------------------------------

    def test_a_comment_naming_the_old_app_is_prose(self):
        rc, out = self.run_check({
            "lib/Probe.php": """\
                <?php
                // Was isInstalled('openconnector') before the rename.
                /* OCA\\Docudesk\\Service\\DocumentService moved to OCA\\Filinq. */
                 * and /apps/openconnector/api/pdok 404s now.
                """,
        })
        self.assertEqual(rc, 0, f"comments are prose, not bindings\n{out}")

    def test_a_block_comment_without_leading_asterisks_is_still_prose(self):
        """Whether a line is prose is stateful, not a prefix test.

        The `<!-- ... -->` header of a Vue SFC is house style, and its
        continuation lines start with an ordinary word. A prefix rule reads
        every one of them as code, which is how learniq's App.vue header,
        explaining in prose which integriq routes it calls, was reported as
        two stale bindings.
        """
        rc, out = self.run_check({
            "src/App.vue": """\
                <!-- SPDX-License-Identifier: EUPL-1.2 -->

                <!--
                 openconnector is SOFT. Learniq forwards an LTI launch to
                 `/apps/openconnector/api/lti/deployments/{id}/launch` and
                 calls `/apps/openconnector/api/payments/initiate`.
                -->
                <template><div /></template>
                """,
        })
        self.assertEqual(rc, 0, f"a block comment is prose throughout\n{out}")

    def test_a_binding_after_the_block_closes_is_still_judged(self):
        """The control. A stateful skip that never turns off blinds the file.

        Without this arm, an unterminated block would swallow every finding
        below it and the gate would report a confident zero.
        """
        rc, out = self.run_check({
            "src/App.vue": """\
                <!--
                 openconnector was the old name.
                -->
                <script>
                const u = generateUrl('/apps/openconnector/api/pdok')
                </script>
                """,
        })
        self.assertEqual(rc, 1, f"code after the block closes is judged\n{out}")

    # -- arm 4 ---------------------------------------------------------------

    def test_a_dual_spelling_list_is_correct_not_stale(self):
        rc, out = self.run_check({
            "lib/Registrar.php": """\
                <?php
                private const EVENTS = [
                    'OCA\\\\Decidiq\\\\Event\\\\DecisionConcludedEvent',
                    'OCA\\\\Decidesk\\\\Event\\\\DecisionConcludedEvent',
                ];
                """,
        })
        self.assertEqual(
            rc, 0,
            "a fallback listed beside the current name is the fix, not the bug: "
            f"flagging it pushes authors to delete the fallback\n{out}")

    def test_documenting_a_known_gap_does_not_switch_the_finding_off(self):
        """The launchpad case, and the reason the accept is statement-scoped.

        launchpad's sweep left two lookups deliberately unrepointed because
        their targets do not exist, and wrote comments naming `integriq` and
        `dossiq` to record what had been read. Under a file-wide accept both
        findings vanished, and the gate reported 1 where 2 were stale.

        The trigger is perverse and that is what makes this arm load-bearing:
        explaining a known gap is exactly the behaviour we want, and it was
        what turned the gate off. Widen the accept back to the file and this
        goes red.
        """
        rc, out = self.run_check({
            "src/services/tiles.js": """\
                // Not repointed: integriq publishes no such route under
                // either name, so correcting the id alone would 404 louder.
                const a = generateUrl('/apps/openconnector/api/livetile')

                // Left as-is: no fleet app serves this shape, dossiq included.
                const b = generateUrl('/apps/procest/graphql')
                """,
        })
        self.assertEqual(rc, 1, f"a documented gap is still a gap\n{out}")
        self.assertEqual(
            out.count("src/services/tiles.js:"), 2,
            f"BOTH stale lookups must be reported, not one\n{out}")

    def test_prose_inside_the_statement_does_not_vouch_either(self):
        """A comment is not a binding, even when it sits in the statement.

        The launchpad arm above happens to put its comments in neighbouring
        statements, so it passes whether or not prose is allowed to vouch.
        This arm removes that luck: the note naming the successor sits INSIDE
        the call it annotates. Join comment lines into the statement text and
        this goes red, which is the assertion the phrase "only code lines are
        considered" is actually making.
        """
        rc, out = self.run_check({
            "src/tile.js": """\
                const a = generateUrl(
                    // integriq publishes no such route, so this stays put.
                    '/apps/openconnector/api/livetile',
                )
                export default a
                """,
        })
        self.assertEqual(
            rc, 1,
            f"a comment naming the successor is documentation, not a fallback\n{out}")

    def test_a_successor_in_a_different_statement_does_not_vouch(self):
        """A sibling binding vouches. A distant one does not.

        Without this, any file that happens to name the new id anywhere in
        code is exempt, which is the file-wide bug wearing a smaller hat.
        """
        rc, out = self.run_check({
            "lib/Probe.php": """\
                <?php
                private const CURRENT = 'integriq';
                public function go() {
                    $x = 1;
                }
                private const STALE = 'openconnector';
                public function probe($m) { return $m->isInstalled(self::STALE); }
                """,
        })
        self.assertEqual(rc, 1, f"a distant binding does not vouch\n{out}")

    def test_the_old_name_alone_in_that_same_file_IS_a_finding(self):
        """The control for arm 4. Without it, arm 4 could pass by matching nothing."""
        rc, out = self.run_check({
            "lib/Registrar.php": """\
                <?php
                private const EVENTS = [
                    'OCA\\\\Decidesk\\\\Event\\\\DecisionConcludedEvent',
                ];
                """,
        })
        self.assertEqual(rc, 1, f"the old name ALONE is stale\n{out}")

    # -- arm 5 ---------------------------------------------------------------

    def test_an_app_does_not_flag_its_own_former_id(self):
        files = {"lib/Repair/Migrate.php":
                 "<?php\nprivate const OLD_APP_ID = 'procest';\n"
                 "public function go($m) { return $m->isInstalled(self::OLD_APP_ID); }\n"}
        rc, out = self.run_check(files, app_id="dossiq", ns="Dossiq")
        self.assertEqual(rc, 0, f"an app's own former id is a migration\n{out}")
        self.assertIn("procest, Procest, are excluded", out, out)

        # The control: the SAME line in a repo that is not dossiq is stale.
        rc, out = self.run_check(files, app_id="opencatalogi", ns="OpenCatalogi")
        self.assertEqual(rc, 1, f"another app naming 'procest' is stale\n{out}")

    def test_an_app_does_not_flag_its_own_former_namespace_either(self):
        """The other half of exclusion 3, and it is the same rule.

        An app rewriting rows it wrote itself under its old name has to spell
        that old name. integriq's MigrateStoredJobClasses holds
        `OLD_CLASS_PREFIX = 'OCA\\OpenConnector\\'`, thematiq's
        MigrateStoredClassNames names `OCA\\NLDesign\\Mail\\...`, and stackiq's
        MigrateBackgroundJobClasses lists four `OCA\\SoftwareCatalog\\...`
        classes. Flagging those asks each app to break its own migration.
        """
        files = {"lib/Repair/MigrateStoredJobClasses.php":
                 "<?php\nprivate const OLD_CLASS_PREFIX = 'OCA\\\\OpenConnector\\\\';\n"}
        rc, out = self.run_check(files, app_id="integriq", ns="Integriq")
        self.assertEqual(rc, 0, f"an app's own former namespace is a migration\n{out}")

        # The control: the SAME line in a repo that is not integriq is stale.
        rc, out = self.run_check(files, app_id="opencatalogi", ns="OpenCatalogi")
        self.assertEqual(rc, 1, f"another app naming OCA\\OpenConnector is stale\n{out}")

    # -- arm 6 ---------------------------------------------------------------

    def test_a_register_slug_is_a_finding_listed_under_its_own_heading(self):
        """This rule has been wrong twice, and the arm records both corrections.

        It began as a plain exclusion citing integriq's own docblock saying the
        `openconnector` slug is "deliberately NOT renamed". That docblock was
        stale, so the rule became "report but do not count, the policy is
        unsettled". The policy is now settled the other way: the freeze was the
        error. Nine apps ship a slug-rename repair step and every renamed app's
        register json declares the new slug, so a consumer naming an old slug
        reads zero rows on a migrated instance and calls it "no data".

        That is a DEFECT, so it is counted. It keeps its own heading because
        the FIX differs: both slugs are live depending on whether an instance
        has run the repair, so swapping the literal breaks everyone who has
        not migrated.
        """
        rc, out = self.run_check({
            "lib/Service/Egress.php": """\
                <?php
                public const SOURCE_REGISTER = 'openconnector';
                private const CONNECTOR_REGISTER = 'openconnector';
                $s = $o->find(id: $x, register: 'openconnector', schema: 'source');
                """,
        })
        self.assertEqual(rc, 1, f"a migrated slug is a defect, so it counts\n{out}")
        self.assertIn("register slug reference(s)", out, out)
        self.assertIn("DO NOT SWAP THE LITERAL", out,
                      f"the heading must say why the fix is not a literal swap\n{out}")
        self.assertNotIn("unsettled", out,
                         f"the policy is settled; the wording must not still hedge\n{out}")
        self.assertEqual(
            out.count("[register slug"), 3,
            f"every slug reference is listed, not just counted\n{out}")

    def test_a_slug_finding_does_not_inflate_the_stale_name_count(self):
        """Two categories, two counts, one exit code.

        A slug is a defect but it is not a stale-name lookup, and merging the
        counts would tell a repo working down its stale names that it had made
        no progress. The runner reads both numbers and adds them; the headline
        count must still describe only what it names.
        """
        rc, out = self.run_check({
            "lib/Service/Egress.php":
                "<?php\npublic const SOURCE_REGISTER = 'openconnector';\n",
        })
        self.assertEqual(rc, 1, out)
        self.assertIn("0 cross-app lookup(s)", out,
                      f"a slug is not a stale-name lookup\n{out}")
        self.assertIn("1 OpenRegister register slug reference(s)", out, out)

    def test_the_design_system_id_is_not_an_app_id(self):
        """`nldesign` names two different things and only one of them moved.

        nextcloud-vue's `useScopedTheme.apply()` hard-compares
        `theme.source !== 'nldesign'` and bails. "Correcting" that to thematiq
        stops every saved theme applying, in every app that offers a theme
        picker. A bare binding cannot say which sense is meant, so it is judged
        only where the context disambiguates.
        """
        rc, out = self.run_check({
            "src/dialogs/ThemePickerDialog.vue":
                "const theme = {\n    source: 'nldesign',\n    tokenSet: c.tokenSet,\n}\n",
        })
        self.assertEqual(rc, 0, f"a design-system id is not an app id\n{out}")

    def test_an_unambiguous_nldesign_app_path_is_still_a_finding(self):
        """The control. Dropping it from the bind rule must not blind the
        contexts where it can only mean the app."""
        rc, out = self.run_check({
            "src/util.js": "const u = generateUrl('/apps/nldesign/img/icons/Star.svg')\n",
        })
        self.assertEqual(rc, 1, f"an /apps/nldesign/ path is unambiguous\n{out}")

    def test_a_name_that_merely_starts_with_register_is_still_judged(self):
        """The slug rule anchors on the END of the binding name.

        `REGISTERED_APP` is an app id, not a slug. Anchor the rule loosely and
        this arm goes red, which is the point: an exclusion that swallows real
        findings is worse than no exclusion.
        """
        rc, out = self.run_check({
            "lib/Service/Thing.php":
                "<?php\nprivate const REGISTERED_APP = 'openconnector';\n"
                "public function go($m) { return $m->isInstalled(self::REGISTERED_APP); }\n",
        })
        self.assertEqual(rc, 1, f"REGISTERED_APP is an app id\n{out}")

    def test_a_persisted_provenance_stamp_is_stored_data(self):
        """A constant is judged by its USE SITE, not its name.

        hermiq's `SOURCE_APP_STAMP = 'scholiq'` is written into a required
        `sourceApp` schema property whose seeded rows already carry that
        value. Renaming it in code does not migrate the rows, it splits the
        field into two vocabularies. Nothing in the NAME distinguishes it from
        a lookup key, which is why the name heuristic that preceded this
        reported it.
        """
        rc, out = self.run_check({
            "lib/Service/Engine.php": """\
                <?php
                class Engine {
                    private const SOURCE_APP_STAMP = 'scholiq';

                    public function record(array $row): array {
                        $row['sourceApp'] = self::SOURCE_APP_STAMP;
                        return $row;
                    }
                }
                """,
        })
        self.assertEqual(
            rc, 0,
            f"a value persisted onto a row is stored data, not a lookup\n{out}")

    def test_the_same_constant_IS_a_finding_once_a_lookup_reads_it(self):
        """The control. Byte-identical declaration, one extra use site.

        Widen the use-site test to accept any reference and this stays green
        while the provenance arm goes red; drop the use-site test altogether
        and the provenance arm goes red instead. Only a rule that reads the
        USE passes both.
        """
        rc, out = self.run_check({
            "lib/Service/Engine.php": """\
                <?php
                class Engine {
                    private const SOURCE_APP_STAMP = 'scholiq';

                    public function record($appManager): bool {
                        return $appManager->isInstalled(self::SOURCE_APP_STAMP);
                    }
                }
                """,
        })
        self.assertEqual(rc, 1, f"the same constant, read by a lookup, is stale\n{out}")

    def test_a_comment_cannot_vouch_that_a_constant_is_a_lookup_key(self):
        """The use-site scan reads code, not prose.

        A note explaining that a constant is NOT passed to isInstalled()
        contains both the reference and the call, so a scan over raw text
        marks the constant as used and reports a stored value as stale.
        """
        rc, out = self.run_check({
            "lib/Service/Engine.php": """\
                <?php
                class Engine {
                    private const SOURCE_APP_STAMP = 'scholiq';

                    // NOTE: self::SOURCE_APP_STAMP is a persisted stamp. It is
                    // never handed to $appManager->isInstalled(self::SOURCE_APP_STAMP).
                    public function record(array $row): array {
                        $row['sourceApp'] = self::SOURCE_APP_STAMP;
                        return $row;
                    }
                }
                """,
        })
        self.assertEqual(rc, 0, f"a comment is not a use site\n{out}")

    def test_a_stale_import_followed_by_the_new_name_is_still_a_finding(self):
        """The control for import grouping: the run must END at the last import.

        Hold it open past the imports and the statement that follows joins the
        block, so a line naming the successor vouches for an import that has no
        fallback beside it at all.
        """
        rc, out = self.run_check({
            "lib/EventListener/Listener.php": """\
                <?php
                use OCA\\Decidesk\\Event\\DecisionConcludedEvent as DecideskEvent;
                $current = 'OCA\\Decidiq\\Event\\DecisionConcludedEvent';
                """,
        })
        self.assertEqual(
            rc, 1,
            f"the import run ends at the last import, not at the next semicolon\n{out}")

    def test_an_aliased_import_pair_is_one_dual_spelling_declaration(self):
        """stackiq's shape: exclusion 2 written as imports rather than an array.

        Each `use` ends in its own semicolon, so statement scoping alone puts
        the fallback in a statement by itself and flags it. A run of
        consecutive imports is one declaration region.
        """
        rc, out = self.run_check({
            "lib/EventListener/Listener.php": """\
                <?php
                namespace OCA\\Stackiq\\EventListener;

                use OCA\\Decidiq\\Event\\DecisionConcludedEvent as DecidiqEvent;
                use OCA\\Decidesk\\Event\\DecisionConcludedEvent as DecideskEvent;
                use OCP\\EventDispatcher\\Event;
                """,
        })
        self.assertEqual(rc, 0, f"an aliased import pair is a fallback\n{out}")

    def test_a_lone_stale_import_is_still_a_finding(self):
        """The control for the import grouping. Without it, grouping could
        swallow every stale import in a file's header block."""
        rc, out = self.run_check({
            "lib/EventListener/Listener.php": """\
                <?php
                namespace OCA\\Stackiq\\EventListener;

                use OCA\\Decidesk\\Event\\DecisionConcludedEvent as DecideskEvent;
                use OCP\\EventDispatcher\\Event;
                """,
        })
        self.assertEqual(rc, 1, f"a lone stale import is stale\n{out}")

    # -- arm 7 ---------------------------------------------------------------

    def test_the_blind_spot_is_stated_on_a_clean_run_too(self):
        """The condition the fleet set for shipping this gate at all.

        It reads names. It cannot see whether the method or route you point at
        exists on the other side, and a repoint that lands on a missing method
        fails exactly as silently as the stale name did. A clean run that says
        only PASS invites the reader to conclude the cross-app surface is
        sound, which this gate has never checked.
        """
        for label, files in (
            ("clean", {"lib/Probe.php": "<?php\n$x = 1;\n"}),
            ("dirty", {"lib/Probe.php": "<?php\n$m->isInstalled('openconnector');\n"}),
        ):
            with self.subTest(run=label):
                _, out = self.run_check(files)
                self.assertIn("reads NAMES only", out, out)
                self.assertIn("cross-repo surface reading", out, out)

    def test_the_count_line_prints_even_at_zero(self):
        """An empty scope is not a pass, and must not print like one."""
        _, out = self.run_check({"lib/Probe.php": "<?php\n$x = 1;\n"})
        self.assertIn("0 cross-app lookup(s)", out, out)

    # -- the map itself ------------------------------------------------------

    def test_the_namespace_map_survives_someone_correcting_it(self):
        """`OCA\\OpenBuilt` is not a typo, and this arm is what says so.

        buildiq shipped its PSR-4 root as `OCA\\OpenBuilt`, which no rule
        deriving a namespace from the app id would produce. It reads like a
        misspelling of `OpenBuild`, and someone tidying this map will one day
        "fix" it. That edit is invisible: the map still looks right, the gate
        still runs, and every buildiq binding in the fleet stops being
        detected without a single error. A docstring saying "read from that
        app's composer.json history, never inferred" is not enough, because
        the person making the edit is the person who did not read it.

        The same trap sits under every entry here, so the arm asserts the
        detection rather than the literal: a stale `OCA\\OpenBuilt` binding is
        a finding, and a current `OCA\\Buildiq` one is not.
        """
        rc, out = self.run_check({
            "lib/Service/Probe.php":
                "<?php\n$s = $c->get('OCA\\\\OpenBuilt\\\\Service\\\\PageService');\n",
        })
        self.assertEqual(
            rc, 1,
            "OCA\\OpenBuilt is buildiq's real former namespace. If this arm is "
            f"red, check whether someone 'corrected' it to OpenBuild\n{out}")
        self.assertIn("OpenBuilt -> Buildiq", out, out)

        rc, out = self.run_check({
            "lib/Service/Probe.php":
                "<?php\n$s = $c->get('OCA\\\\Buildiq\\\\Service\\\\PageService');\n",
        })
        self.assertEqual(rc, 0, f"the current namespace is not a finding\n{out}")

    # -- scope ---------------------------------------------------------------

    def test_a_repo_with_nothing_to_scan_says_so_rather_than_passing(self):
        with tempfile.TemporaryDirectory() as root:
            proc = subprocess.run(
                [sys.executable, CHECKER, root],
                capture_output=True, text=True, timeout=120,
            )
        self.assertEqual(
            proc.returncode, 4,
            "no scope is exit 4, never exit 0: 'nothing was checked' and "
            f"'nothing was wrong' must not report the same thing\n{proc.stdout}")


if __name__ == "__main__":
    unittest.main()
