#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Tests for check_semantic_auth (gate-9). Run with:

    python3 scripts/lib/test_check_semantic_auth.py

WHY THIS SUITE EXISTS
---------------------
gate-9 shipped with NO tests. Its `public-page-annotation-with-auth-body`
rule produced 39 fleet findings of which 36 were false, and its remediation
text — *"remove `#[PublicPage]` or remove body auth check"* — would have
INTRODUCED a vulnerability in every one of those 36: the first half breaks
the endpoint (Nextcloud middleware rejects the remote caller before the
controller runs), the second half deletes its only authentication.

The fixtures below are the real call shapes, verbatim in structure:
openconnector's HMAC webhook, portaliq's portal `subject()` inbox,
openregister's bearer-share-token federation reader — against decidesk's
actual defect, a `#[PublicPage]` method that tests the SESSION.

Both ways, in the same class: the self-authenticating shapes must go quiet,
and the session-dependent shape must still fire.
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_semantic_auth as csa  # noqa: E402


def _scan(php: str) -> list[str]:
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "Controller.php"
        p.write_text(php, encoding="utf-8")
        buf = io.StringIO()
        with redirect_stdout(buf):
            csa.scan_file(str(p))
    return [ln for ln in buf.getvalue().splitlines() if ln.strip()]


def _rules(findings: list[str]) -> list[str]:
    return [f.split("rule=", 1)[1].split(" ", 1)[0] for f in findings]


CLASS = """<?php
namespace OCA\\Thing\\Controller;

class ThingController extends Controller
{
%s
}
"""

HMAC_WEBHOOK = CLASS % """
    #[PublicPage]
    #[NoCSRFRequired]
    public function webhook(): JSONResponse
    {
        $signature = $this->request->getHeader('X-Mollie-Signature');
        $expected = hash_hmac('sha256', $this->request->getContent(), $this->secret);
        if (hash_equals($expected, $signature) === false) {
            return new JSONResponse(['error' => 'bad signature'], Http::STATUS_UNAUTHORIZED);
        }
        return new JSONResponse(['ok' => true]);
    }
"""

PORTAL_INBOX = CLASS % """
    #[PublicPage]
    public function inbox(): JSONResponse
    {
        $subject = $this->portal->subject();
        if ($subject === null) {
            return new JSONResponse(['error' => 'no portal session'], Http::STATUS_UNAUTHORIZED);
        }
        return new JSONResponse($this->service->listFor($subject));
    }
"""

FEDERATION_BEARER = CLASS % """
    #[PublicPage]
    #[NoCSRFRequired]
    public function objects(string $shareToken): JSONResponse
    {
        $share = $this->shares->findByToken($shareToken);
        if ($share === null || $share->isRevoked()) {
            return new JSONResponse(['error' => 'unknown share'], Http::STATUS_FORBIDDEN);
        }
        return new JSONResponse($this->service->objectsFor($share));
    }
"""

# decidesk's real defect shape: annotated public, but the body tests the
# SESSION — a test that can only ever fail for the callers the annotation
# admits.
SESSION_DEPENDENT = CLASS % """
    #[PublicPage]
    public function load(): JSONResponse
    {
        $this->requireAdmin();
        return new JSONResponse($this->settings->all());
    }
"""

SESSION_NULL_CHECK = CLASS % """
    #[PublicPage]
    public function mine(): JSONResponse
    {
        if ($this->userSession->getUser() === null) {
            return new JSONResponse([], Http::STATUS_UNAUTHORIZED);
        }
        return new JSONResponse($this->service->forCurrentUser());
    }
"""

# 401 with no credential source anywhere: the shape that remains worth
# reporting, because nothing in the method says what it authenticates with.
UNSOURCED_DENIAL = CLASS % """
    #[PublicPage]
    public function report(): JSONResponse
    {
        if ($this->flags->closed()) {
            return new JSONResponse(['error' => 'closed'], Http::STATUS_FORBIDDEN);
        }
        return new JSONResponse($this->service->report());
    }
"""


class SelfAuthenticatingPublicEndpoints(unittest.TestCase):
    """The 36 false positives."""

    def test_fp_hmac_signed_webhook_is_not_a_finding(self):
        self.assertEqual(_scan(HMAC_WEBHOOK), [])

    def test_fp_portal_subject_resolution_is_not_a_finding(self):
        self.assertEqual(_scan(PORTAL_INBOX), [])

    def test_fp_bearer_share_token_is_not_a_finding(self):
        self.assertEqual(_scan(FEDERATION_BEARER), [])


class SessionDependentPublicPage(unittest.TestCase):
    """The 3 true positives — these MUST still fire."""

    def test_tp_require_admin_under_public_page_still_fires(self):
        self.assertEqual(_rules(_scan(SESSION_DEPENDENT)),
                         ["public-page-annotation-with-session-auth-body"])

    def test_tp_user_session_null_check_under_public_page_still_fires(self):
        self.assertEqual(_rules(_scan(SESSION_NULL_CHECK)),
                         ["public-page-annotation-with-session-auth-body"])

    def test_tp_a_session_check_fires_even_alongside_a_token(self):
        # Self-authentication excuses an UNSOURCED denial, never a session
        # test. A method that reads a token AND requires a session is still
        # contradicting its own annotation.
        php = CLASS % """
    #[PublicPage]
    public function mixed(string $shareToken): JSONResponse
    {
        $share = $this->shares->findByToken($shareToken);
        $this->requireAdmin();
        return new JSONResponse($share);
    }
"""
        self.assertEqual(_rules(_scan(php)),
                         ["public-page-annotation-with-session-auth-body"])

    def test_tp_a_denial_with_no_credential_source_is_reported(self):
        self.assertEqual(_rules(_scan(UNSOURCED_DENIAL)),
                         ["public-page-annotation-with-unsourced-denial"])


class RemediationTextIsSafe(unittest.TestCase):
    """The advice itself is part of the gate. If it tells a developer to open
    the endpoint, the gate is a vulnerability generator regardless of its
    precision. These assertions are on the STRING, deliberately."""

    def _advice(self, php: str) -> str:
        found = _scan(php)
        self.assertTrue(found, "expected a finding to inspect the advice of")
        return found[0]

    def test_advice_never_says_to_remove_the_public_page_annotation(self):
        for php in (SESSION_DEPENDENT, SESSION_NULL_CHECK, UNSOURCED_DENIAL):
            with self.subTest(php=php[:60]):
                advice = self._advice(php)
                self.assertNotIn("remove #[PublicPage] or", advice)

    def test_advice_never_says_to_remove_the_auth_check(self):
        for php in (SESSION_DEPENDENT, SESSION_NULL_CHECK, UNSOURCED_DENIAL):
            with self.subTest(php=php[:60]):
                advice = self._advice(php)
                self.assertNotIn("remove body auth check", advice)
                self.assertIn("Do NOT", advice)

    def test_advice_names_the_request_borne_alternative(self):
        advice = self._advice(SESSION_DEPENDENT)
        self.assertIn("route token", advice)


class NoAdminRequiredRuleUnchanged(unittest.TestCase):
    """The rule gate-9 was actually built for. It was RIGHT — 3 of 3 real —
    and nothing above may weaken it."""

    def test_tp_no_admin_required_with_an_admin_body_still_fires(self):
        php = CLASS % """
    #[NoAdminRequired]
    public function load(): JSONResponse
    {
        $this->requireAdmin();
        return new JSONResponse($this->settings->all());
    }
"""
        self.assertEqual(_rules(_scan(php)),
                         ["no-admin-required-annotation-with-admin-body"])

    def test_fp_a_plain_no_admin_required_method_is_clean(self):
        php = CLASS % """
    #[NoAdminRequired]
    public function index(): JSONResponse
    {
        return new JSONResponse($this->service->listForCurrentUser());
    }
"""
        self.assertEqual(_scan(php), [])


class GateIsNotBlind(unittest.TestCase):
    def test_the_scanner_still_reads_methods_at_all(self):
        # If `_find_method_bodies` ever returns nothing, every `assertEqual([])`
        # above passes. This asserts the floor directly.
        php = CLASS % """
    #[PublicPage]
    public function a(): JSONResponse { $this->requireAdmin(); return new JSONResponse([]); }

    #[PublicPage]
    public function b(): JSONResponse { $this->requireAdmin(); return new JSONResponse([]); }
"""
        self.assertEqual(len(_scan(php)), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
