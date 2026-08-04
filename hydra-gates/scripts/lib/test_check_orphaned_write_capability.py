#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Tests for check_orphaned_write_capability (gate-52). Run with:

    python3 scripts/lib/test_check_orphaned_write_capability.py

or via pytest:

    python3 -m pytest scripts/lib/test_check_orphaned_write_capability.py
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_orphaned_write_capability as owc  # noqa: E402


class _AppFixture:
    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._old_cwd = None

    def __enter__(self):
        self._old_cwd = os.getcwd()
        os.chdir(self._tmp.name)
        return self._tmp.name

    def __exit__(self, *exc):
        os.chdir(self._old_cwd)
        self._tmp.cleanup()

    def write(self, rel_path: str, content: str) -> str:
        full = os.path.join(self._tmp.name, rel_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
        return full


def _run_main(*service_paths: str) -> list[str]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        owc.main(["check_orphaned_write_capability.py", *service_paths])
    return [ln for ln in buf.getvalue().splitlines() if ln.strip()]


class OrphanFlaggedTest(unittest.TestCase):
    def test_zero_caller_write_method_flagged(self):
        with _AppFixture() as root:
            path = self.write(
                root,
                "lib/Service/OrphanService.php",
                "<?php\nnamespace OCA\\Fixture\\Service;\nclass OrphanService {\n"
                "    public function postJournalEntry(array $data): void { /* posts GL, never called */ }\n"
                "}\n",
            )
            out = _run_main(path)
            self.assertEqual(len(out), 1, out)
            self.assertIn("rule=orphaned-write-capability", out[0])
            self.assertIn("method=postJournalEntry", out[0])

    def write(self, root, rel_path, content):
        full = os.path.join(root, rel_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
        return full


class DirectCallerNotFlaggedTest(unittest.TestCase):
    def test_method_with_direct_caller_not_flagged(self):
        with _AppFixture() as root:
            svc_path = self.write(
                root,
                "lib/Service/WiredService.php",
                "<?php\nnamespace OCA\\Fixture\\Service;\nclass WiredService {\n"
                "    public function createInvoice(array $data): void {}\n"
                "}\n",
            )
            self.write(
                root,
                "lib/Controller/InvoiceController.php",
                "<?php\nnamespace OCA\\Fixture\\Controller;\nclass InvoiceController {\n"
                "    public function store(): void { $this->wiredService->createInvoice([]); }\n"
                "}\n",
            )
            out = _run_main(svc_path)
            self.assertEqual(out, [])

    def write(self, root, rel_path, content):
        full = os.path.join(root, rel_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
        return full


class RegisterHandlerSeamTest(unittest.TestCase):
    def test_method_invoked_only_via_registerd_handler_not_flagged(self):
        with _AppFixture() as root:
            self.write(
                root,
                "lib/Settings/register.d/fixture.json",
                '{"transitions": {"submit": {"handler": '
                '"OCA\\\\Fixture\\\\Service\\\\HandlerOnlyService::generateReport"}}}',
            )
            svc_path = self.write(
                root,
                "lib/Service/HandlerOnlyService.php",
                "<?php\nnamespace OCA\\Fixture\\Service;\nclass HandlerOnlyService {\n"
                "    public function generateReport(): void { /* OR-invoked, no PHP caller */ }\n"
                "}\n",
            )
            out = _run_main(svc_path)
            self.assertEqual(out, [])

    def write(self, root, rel_path, content):
        full = os.path.join(root, rel_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
        return full


class EventListenerSeamTest(unittest.TestCase):
    def test_class_registered_as_event_listener_not_flagged(self):
        with _AppFixture() as root:
            self.write(
                root,
                "lib/AppInfo/Application.php",
                "<?php\nnamespace OCA\\Fixture\\AppInfo;\nclass Application {\n"
                "    public function register($context): void {\n"
                "        $context->registerEventListener(\n"
                "            \\OCA\\OpenRegister\\Event\\ObjectUpdatedEvent::class,\n"
                "            \\OCA\\Fixture\\Service\\NotificationDispatchService::class\n"
                "        );\n"
                "    }\n}\n",
            )
            svc_path = self.write(
                root,
                "lib/Service/NotificationDispatchService.php",
                "<?php\nnamespace OCA\\Fixture\\Service;\nclass NotificationDispatchService {\n"
                "    public function notifyOnTransition(): void { /* invoked as event listener */ }\n"
                "}\n",
            )
            out = _run_main(svc_path)
            self.assertEqual(out, [])

    def write(self, root, rel_path, content):
        full = os.path.join(root, rel_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
        return full


class BackgroundJobSeamTest(unittest.TestCase):
    def test_class_registered_as_background_job_not_flagged(self):
        with _AppFixture() as root:
            self.write(
                root,
                "appinfo/info.xml",
                "<?xml version=\"1.0\"?><info><background-jobs>"
                "<job>OCA\\Fixture\\Service\\ExportGeneratorService</job>"
                "</background-jobs></info>",
            )
            svc_path = self.write(
                root,
                "lib/Service/ExportGeneratorService.php",
                "<?php\nnamespace OCA\\Fixture\\Service;\nclass ExportGeneratorService {\n"
                "    public function run(): void {}\n"
                "    public function exportLedger(): void { /* invoked from run() via the job scheduler */ }\n"
                "}\n",
            )
            out = _run_main(svc_path)
            self.assertEqual(out, [])

    def write(self, root, rel_path, content):
        full = os.path.join(root, rel_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
        return full


class LogAdapterSeamTest(unittest.TestCase):
    def test_log_only_adapter_class_exempt(self):
        with _AppFixture() as root:
            svc_path = self.write(
                root,
                "lib/Service/LogCreditScoreFetchAdapter.php",
                "<?php\nnamespace OCA\\Fixture\\Service;\nclass LogCreditScoreFetchAdapter {\n"
                "    public function notifyCreditScoreFetch(): void { /* intentional log-only seam */ }\n"
                "}\n",
            )
            out = _run_main(svc_path)
            self.assertEqual(out, [])

    def write(self, root, rel_path, content):
        full = os.path.join(root, rel_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
        return full


class ExcludeAnnotationTest(unittest.TestCase):
    def test_docblock_exclude_annotation_suppresses(self):
        with _AppFixture() as root:
            svc_path = self.write(
                root,
                "lib/Service/PlannedService.php",
                "<?php\nnamespace OCA\\Fixture\\Service;\nclass PlannedService {\n"
                "    /**\n"
                "     * @orphaned-write-capability exclude Wired in the next PR (issue #999)\n"
                "     */\n"
                "    public function publishReport(): void {}\n"
                "}\n",
            )
            out = _run_main(svc_path)
            self.assertEqual(out, [])

    def write(self, root, rel_path, content):
        full = os.path.join(root, rel_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
        return full


class GetterMethodsNeverFlaggedTest(unittest.TestCase):
    def test_getter_and_guard_shaped_methods_ignored(self):
        with _AppFixture() as root:
            svc_path = self.write(
                root,
                "lib/Service/ReadOnlyService.php",
                "<?php\nnamespace OCA\\Fixture\\Service;\nclass ReadOnlyService {\n"
                "    public function getBalance(): float { return 0.0; }\n"
                "    public function isValid(): bool { return true; }\n"
                "    public function findAll(): array { return []; }\n"
                "}\n",
            )
            out = _run_main(svc_path)
            self.assertEqual(out, [])

    def write(self, root, rel_path, content):
        full = os.path.join(root, rel_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
        return full


class _FleetFixture:
    """A parent dir holding several sibling NC app checkouts, mirroring the
    real ``apps-extra/`` layout that gate-57 runs inside. Each app gets an
    ``appinfo/info.xml`` so ``_find_sibling_app_roots`` recognises it.

    ``cwd`` is a deliberate KNOB, not a baked-in assumption. Gate-56's
    fixtures all chdir'd into the app root, which is precisely why its
    ``os.getcwd()`` bug survived a green suite and then produced 242 false
    positives the first time it ran from a foreign cwd (hydra#108/#109). A
    fixture must not encode the same assumption the gate makes, so this one
    can also run from the sweep parent — the way the fleet sweep really
    invokes the gate. See ForeignCwdTest.
    """

    def __init__(self, app_name: str, cwd: str = "app"):
        self._tmp = tempfile.TemporaryDirectory()
        self._app_name = app_name
        self._cwd_mode = cwd
        self._old_cwd = None

    def __enter__(self):
        self.parent = self._tmp.name
        self.app_root = self.add_app(self._app_name)
        self._old_cwd = os.getcwd()
        os.chdir(self.app_root if self._cwd_mode == "app" else self.parent)
        return self

    def __exit__(self, *exc):
        os.chdir(self._old_cwd)
        self._tmp.cleanup()

    def add_app(self, name: str) -> str:
        root = os.path.join(self.parent, name)
        os.makedirs(os.path.join(root, "lib"), exist_ok=True)
        self.write(root, "appinfo/info.xml", "<?xml version='1.0'?><info></info>\n")
        return root

    def write(self, root: str, rel_path: str, content: str) -> str:
        full = os.path.join(root, rel_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
        return full


# Models the real openregister ObjectService::clearCurrents() —
# openconnector's EndpointService is its only caller (hydra#106).
_FOUNDATION_SVC = (
    "<?php\nnamespace OCA\\OpenRegister\\Service;\nclass ObjectService {\n"
    "    public function clearCurrents(): void { /* live: resets request-scoped cache */ }\n"
    "    public function generateNeverCalledReport(): void { /* genuinely dead */ }\n"
    "}\n"
)


class CrossAppCallerTest(unittest.TestCase):
    """hydra#106 FP class 1 — a foundation repo's public method whose only
    callers live in a sibling app must NOT be reported dead."""

    def test_foundation_method_called_only_from_sibling_is_not_flagged(self):
        with _FleetFixture("openregister") as fx:
            svc = fx.write(fx.app_root, "lib/Service/ObjectService.php", _FOUNDATION_SVC)
            consumer = fx.add_app("openconnector")
            fx.write(
                consumer,
                "lib/Service/EndpointService.php",
                "<?php\nnamespace OCA\\OpenConnector\\Service;\nclass EndpointService {\n"
                "    public function handle(): void {\n"
                "        $this->objectService->getOpenRegisters()->clearCurrents();\n"
                "    }\n"
                "}\n",
            )
            out = _run_main(svc)
            self.assertNotIn(
                "clearCurrents",
                "\n".join(out),
                "regression: live cross-app-called method reported dead (hydra#106)",
            )

    def test_genuinely_dead_foundation_method_still_flagged(self):
        """The true positive must survive the fix: no sibling calls this."""
        with _FleetFixture("openregister") as fx:
            svc = fx.write(fx.app_root, "lib/Service/ObjectService.php", _FOUNDATION_SVC)
            consumer = fx.add_app("openconnector")
            fx.write(
                consumer,
                "lib/Service/EndpointService.php",
                "<?php\nnamespace OCA\\OpenConnector\\Service;\nclass EndpointService {\n"
                "    public function handle(): void {\n"
                "        $this->objectService->getOpenRegisters()->clearCurrents();\n"
                "    }\n"
                "}\n",
            )
            out = _run_main(svc)
            self.assertEqual(len(out), 1, out)
            self.assertIn("method=generateNeverCalledReport", out[0])

    def test_foundation_repo_without_siblings_reports_nothing(self):
        """FAIL SAFE: consumers not on disk => deadness unprovable => silent.
        A missing sibling must never turn a live method into a 'dead'
        verdict."""
        with _FleetFixture("openregister") as fx:
            svc = fx.write(fx.app_root, "lib/Service/ObjectService.php", _FOUNDATION_SVC)
            out = _run_main(svc)
            self.assertEqual(out, [])

    def test_leaf_app_verdicts_unaffected_by_siblings(self):
        """A leaf app's services are consumed only by that app (ADR-022), so
        its zero-caller verdicts stay sound — the shillinq true positives
        must not be weakened by the cross-app fix."""
        with _FleetFixture("shillinq") as fx:
            svc = fx.write(
                fx.app_root,
                "lib/Service/DisposalJournalEmitter.php",
                "<?php\nnamespace OCA\\Shillinq\\Service;\nclass DisposalJournalEmitter {\n"
                "    public function emitDisposalJournal(): void { /* posts GL, dead */ }\n"
                "}\n",
            )
            fx.add_app("openregister")
            out = _run_main(svc)
            self.assertEqual(len(out), 1, out)
            self.assertIn("method=emitDisposalJournal", out[0])


class ForeignCwdTest(unittest.TestCase):
    """The app root must come from the FILE'S path, never the process cwd.

    Every other fixture in this file chdir's into the app root, so all of
    them would still pass if the gate read ``os.getcwd()`` — the exact blind
    spot that let gate-56 ship a cwd bug behind a green suite (hydra#108/
    #109, 242 false positives). These tests run from the sweep PARENT, the
    way the real fleet sweep invokes the gate, and pass a repo-qualified
    relative path. Under the cwd-derived behaviour ``_is_foundation`` saw
    basename ``apps-extra``, never scanned siblings, and reported the live
    ``clearCurrents`` dead all over again."""

    def _fleet(self):
        fx = _FleetFixture("openregister", cwd="parent")
        return fx

    def test_cross_app_caller_seen_when_invoked_from_sweep_parent(self):
        """MUST PASS: live foundation method, sweep run from apps-extra/."""
        with self._fleet() as fx:
            fx.write(fx.app_root, "lib/Service/ObjectService.php", _FOUNDATION_SVC)
            consumer = fx.add_app("openconnector")
            fx.write(
                consumer,
                "lib/Service/EndpointService.php",
                "<?php\nnamespace OCA\\OpenConnector\\Service;\nclass EndpointService {\n"
                "    public function handle(): void {\n"
                "        $this->objectService->getOpenRegisters()->clearCurrents();\n"
                "    }\n"
                "}\n",
            )
            # Repo-qualified relative path, exactly as a sweep from the
            # parent passes it — cwd is the parent, NOT the app root.
            out = _run_main(os.path.join("openregister", "lib", "Service", "ObjectService.php"))
            self.assertNotIn(
                "clearCurrents",
                "\n".join(out),
                "regression: gate read app root from cwd, missed the sibling "
                "caller and named live code dead (hydra#106)",
            )

    def test_genuine_orphan_still_flagged_from_sweep_parent(self):
        """MUST STILL FAIL: the true positive survives the foreign cwd."""
        with self._fleet() as fx:
            fx.write(fx.app_root, "lib/Service/ObjectService.php", _FOUNDATION_SVC)
            consumer = fx.add_app("openconnector")
            fx.write(
                consumer,
                "lib/Service/EndpointService.php",
                "<?php\nnamespace OCA\\OpenConnector\\Service;\nclass EndpointService {\n"
                "    public function handle(): void {\n"
                "        $this->objectService->getOpenRegisters()->clearCurrents();\n"
                "    }\n"
                "}\n",
            )
            out = _run_main(os.path.join("openregister", "lib", "Service", "ObjectService.php"))
            self.assertEqual(len(out), 1, out)
            self.assertIn("method=generateNeverCalledReport", out[0])

    def test_seams_resolve_from_foreign_cwd(self):
        """A register.d handler seam must still exempt its method when the
        gate runs from the parent: a cwd-derived app_root looked for
        <parent>/lib/Settings, found nothing, and every seam came back empty
        — turning all seam-exempt methods into false positives."""
        with _FleetFixture("pipelinq", cwd="parent") as fx:
            fx.write(
                fx.app_root,
                "lib/Service/PosGuardService.php",
                "<?php\nnamespace OCA\\Pipelinq\\Service;\nclass PosGuardService {\n"
                "    public function confirmPosTransaction(): void { /* register.d handler */ }\n"
                "}\n",
            )
            fx.write(
                fx.app_root,
                "lib/Settings/register.d/10-pos.json",
                '{"handlers":[{"handler":'
                '"OCA\\\\Pipelinq\\\\Service\\\\PosGuardService::confirmPosTransaction"}]}\n',
            )
            out = _run_main(os.path.join("pipelinq", "lib", "Service", "PosGuardService.php"))
            self.assertEqual(out, [], "seam lost from a foreign cwd")

    def test_files_from_two_apps_in_one_invocation(self):
        """A sweep hands the gate files from several repos at once; each must
        be judged against its OWN app root, seams and caller index."""
        with _FleetFixture("openregister", cwd="parent") as fx:
            fx.write(fx.app_root, "lib/Service/ObjectService.php", _FOUNDATION_SVC)
            consumer = fx.add_app("openconnector")
            fx.write(
                consumer,
                "lib/Service/EndpointService.php",
                "<?php\nnamespace OCA\\OpenConnector\\Service;\nclass EndpointService {\n"
                "    public function handle(): void {\n"
                "        $this->objectService->getOpenRegisters()->clearCurrents();\n"
                "    }\n"
                "}\n",
            )
            leaf = fx.add_app("shillinq")
            fx.write(
                leaf,
                "lib/Service/DisposalJournalEmitter.php",
                "<?php\nnamespace OCA\\Shillinq\\Service;\nclass DisposalJournalEmitter {\n"
                "    public function emitDisposalJournal(): void { /* dead */ }\n"
                "}\n",
            )
            out = _run_main(
                os.path.join("openregister", "lib", "Service", "ObjectService.php"),
                os.path.join("shillinq", "lib", "Service", "DisposalJournalEmitter.php"),
            )
            joined = "\n".join(out)
            self.assertNotIn("clearCurrents", joined)
            self.assertIn("method=generateNeverCalledReport", joined)
            self.assertIn("method=emitDisposalJournal", joined)


class InterfaceDeclarationTest(unittest.TestCase):
    """hydra#106 FP class 2 — a bodiless declaration cannot be dead."""

    def test_interface_method_declaration_not_flagged(self):
        with _AppFixture() as root:
            svc = _write(
                root,
                "lib/Service/External/Mollie/MolliePaymentAdapterInterface.php",
                "<?php\nnamespace OCA\\Shillinq\\Service\\External\\Mollie;\n"
                "interface MolliePaymentAdapterInterface {\n"
                "    public function createPayment(array $payload): MolliePaymentResult;\n"
                "}\n",
            )
            self.assertEqual(_run_main(svc), [])

    def test_abstract_method_declaration_not_flagged(self):
        with _AppFixture() as root:
            svc = _write(
                root,
                "lib/Service/AbstractEmitter.php",
                "<?php\nnamespace OCA\\Fixture\\Service;\n"
                "abstract class AbstractEmitter {\n"
                "    abstract public function emitThing(): void;\n"
                "    public function createThing(string $sep = ';'): void { /* dead */ }\n"
                "}\n",
            )
            out = _run_main(svc)
            self.assertEqual(len(out), 1, out)
            self.assertIn("method=createThing", out[0])

    def test_trait_method_still_scanned_for_concrete_bodies(self):
        """A trait is skipped as a type declaration, mirroring interfaces."""
        with _AppFixture() as root:
            svc = _write(
                root,
                "lib/Service/EmitterTrait.php",
                "<?php\nnamespace OCA\\Fixture\\Service;\ntrait EmitterTrait {\n"
                "    public function emitViaTrait(): void {}\n"
                "}\n",
            )
            self.assertEqual(_run_main(svc), [])


class GitEnumerationTest(unittest.TestCase):
    """hydra#106 FP class 3 — a nested custom_apps/ must neither mask the
    repo's own files nor pollute the caller index with a vendored copy."""

    def _git(self, root, *args):
        import subprocess

        subprocess.run(
            ["git", "-C", root, *args],
            check=True,
            capture_output=True,
        )

    def test_custom_apps_sibling_does_not_supply_phantom_callers(self):
        """The sibling scan must not treat a nested Nextcloud server tree
        (`custom_apps/`, which carries a vendored copy of every app and its
        own appinfo/info.xml) as a consumer repo — a stale vendored call
        site there would suppress a genuine finding."""
        with _FleetFixture("openregister") as fx:
            svc = fx.write(fx.app_root, "lib/Service/ObjectService.php", _FOUNDATION_SVC)
            fx.add_app("openconnector")
            vendored = fx.add_app("custom_apps")
            fx.write(
                vendored,
                "lib/Service/Vendored.php",
                "<?php\nclass Vendored {\n"
                "    public function run(): void {\n"
                "        $this->svc->generateNeverCalledReport();\n"
                "    }\n"
                "}\n",
            )
            self.assertNotIn(
                vendored,
                owc._find_sibling_app_roots(fx.app_root),
                "custom_apps/ must never be treated as a sibling app repo",
            )
            out = _run_main(svc)
            self.assertIn(
                "method=generateNeverCalledReport",
                "\n".join(out),
                "regression: vendored copy under custom_apps/ suppressed a real finding",
            )

    def test_git_ls_files_skips_untracked_vendored_tree(self):
        with _FleetFixture("openregister") as fx:
            svc = fx.write(fx.app_root, "lib/Service/ObjectService.php", _FOUNDATION_SVC)
            fx.add_app("openconnector")
            try:
                self._git(fx.app_root, "init", "-q")
                self._git(fx.app_root, "add", "-A")
            except Exception:  # pragma: no cover - git absent
                self.skipTest("git unavailable")
            # Untracked AND gitignored — must not reach the caller index.
            fx.write(fx.app_root, ".gitignore", "ignored/\n")
            fx.write(
                fx.app_root,
                "lib/ignored/Phantom.php",
                "<?php\nclass Phantom {\n"
                "    public function run(): void { $this->s->generateNeverCalledReport(); }\n"
                "}\n",
            )
            out = _run_main(svc)
            self.assertIn("method=generateNeverCalledReport", "\n".join(out))


def _write(root, rel_path, content):
    full = os.path.join(root, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(content)
    return full


if __name__ == "__main__":
    unittest.main()
