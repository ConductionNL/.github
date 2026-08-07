#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Tests for check_semantic_auth (gate-9). Run with:

    python3 scripts/lib/test_check_semantic_auth.py

or via pytest:

    python3 -m pytest scripts/lib/test_check_semantic_auth.py

Gate-9 has two exemptions, and an exemption is a way for a real mismatch
to slip through. So every "must not fire" test below is paired with a
"must still fire" test built from the same PHP shape minus the one thing
that earns the exemption. A suite in which nothing fails proves nothing.

:class:`ProseDoesNotEarnTheExemption` is the one that matters most. The
self-auth exemption used to be matched against the raw source, so a
docblock reading "callers present a bearer token" exempted a method that
checked no such thing — the 2026-08-06 gate-64 failure mode, where a
commented-out call counted as a real one. Those tests fail if comment
stripping is ever removed.

Fixtures are written as realistic Nextcloud controllers rather than as
minimal echoes of the gate's own regexes (the gate-56 lesson).
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


def _scan(src: str) -> list[str]:
    """Write *src* to a throwaway .php file and return the finding lines."""
    with tempfile.TemporaryDirectory() as root:
        path = Path(root) / "SomeController.php"
        path.write_text(src, encoding="utf-8")
        buf = io.StringIO()
        with redirect_stdout(buf):
            csa.scan_file(str(path))
        return [ln for ln in buf.getvalue().splitlines() if ln.strip()]


_PROLOGUE = """\
<?php
namespace OCA\\Demo\\Controller;

use OCP\\AppFramework\\Controller;
use OCP\\AppFramework\\Http;
use OCP\\AppFramework\\Http\\Attribute\\NoAdminRequired;
use OCP\\AppFramework\\Http\\Attribute\\PublicPage;
use OCP\\AppFramework\\Http\\JSONResponse;

class DemoController extends Controller {
"""


def _controller(methods: str) -> str:
    return _PROLOGUE + methods + "\n}\n"


# ---------------------------------------------------------------------------
# The session-mismatch rule — a session gate hiding behind a public attribute.
# ---------------------------------------------------------------------------

class SessionGateBehindPublicPage(unittest.TestCase):
    """#[PublicPage] whose denial reads the session can only ever deny."""

    def test_user_session_null_check_is_flagged(self):
        src = _controller("""
    #[PublicPage]
    public function summary(): JSONResponse {
        if ($this->userSession->getUser() === null) {
            return new JSONResponse(['error' => 'sign in first'], Http::STATUS_UNAUTHORIZED);
        }

        return new JSONResponse($this->dashboardService->summarise());
    }
""")
        findings = _scan(src)
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("rule=public-page-annotation-with-session-auth-body", findings[0])

    def test_require_admin_is_flagged(self):
        src = _controller("""
    #[PublicPage]
    public function purgeCaches(): JSONResponse {
        $this->requireAdmin();

        $this->cacheService->purgeAll();
        return new JSONResponse(['purged' => true]);
    }
""")
        findings = _scan(src)
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("rule=public-page-annotation-with-session-auth-body", findings[0])

    def test_a_bearer_token_does_not_launder_a_session_gate(self):
        """Self-auth must not buy an exemption from the session rule.

        The session branch is checked first and has no exemption; a method
        that authenticates a token AND then consults the session is still
        contradicting its own attribute.
        """
        src = _controller("""
    #[PublicPage]
    public function dump(): JSONResponse {
        $presentedToken = (string) $this->request->getHeader('Authorization');
        if (hash_equals($this->expectedToken(), $presentedToken) === false) {
            return new JSONResponse(['error' => 'unauthorized'], Http::STATUS_UNAUTHORIZED);
        }

        $this->requireAdmin();

        return new JSONResponse($this->exportService->dumpEverything());
    }
""")
        findings = _scan(src)
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("rule=public-page-annotation-with-session-auth-body", findings[0])


# ---------------------------------------------------------------------------
# The unsourced-denial rule — 401/403 with no credential in the request.
# ---------------------------------------------------------------------------

class DenialWithoutACredential(unittest.TestCase):
    """A public endpoint that denies on app state, not on anything sent."""

    def test_feature_flag_denial_is_flagged(self):
        src = _controller("""
    #[PublicPage]
    public function index(): JSONResponse {
        if ($this->config->getAppValue('demo', 'portal_enabled', 'no') !== 'yes') {
            return new JSONResponse(['error' => 'portal disabled'], Http::STATUS_FORBIDDEN);
        }

        return new JSONResponse($this->portalService->landingPage());
    }
""")
        findings = _scan(src)
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("rule=public-page-annotation-with-unsourced-denial", findings[0])

    def test_published_flag_denial_is_flagged(self):
        src = _controller("""
    #[PublicPage]
    public function download(int $id): JSONResponse {
        if ($this->exportService->isPublished($id) === false) {
            return new JSONResponse(['error' => 'not available'], Http::STATUS_FORBIDDEN);
        }

        return new JSONResponse($this->exportService->payload($id));
    }
""")
        findings = _scan(src)
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("rule=public-page-annotation-with-unsourced-denial", findings[0])


class CredentialInTheRequestIsNotAMismatch(unittest.TestCase):
    """Public by necessity, 401 by correctness — the 36-of-39 shape."""

    def test_hmac_signed_webhook_is_not_flagged(self):
        src = _controller("""
    #[PublicPage]
    public function webhook(): JSONResponse {
        $payload  = file_get_contents('php://input');
        $expected = 'sha256=' . hash_hmac('sha256', $payload, $this->sharedSecret());

        if (hash_equals($expected, (string) $this->request->getHeader('X-Hub-Signature-256')) === false) {
            return new JSONResponse(['error' => 'bad signature'], Http::STATUS_FORBIDDEN);
        }

        return new JSONResponse([], 202);
    }
""")
        self.assertEqual(_scan(src), [])

    def test_route_share_token_is_not_flagged(self):
        src = _controller("""
    #[PublicPage]
    public function share(string $shareToken): JSONResponse {
        $share = $this->shareMapper->findByToken($shareToken);
        if ($share === null || $share->getExpired() === true) {
            return new JSONResponse(['error' => 'unknown share'], Http::STATUS_UNAUTHORIZED);
        }

        return new JSONResponse($this->shareService->contents($share));
    }
""")
        self.assertEqual(_scan(src), [])

    def test_login_endpoint_is_not_flagged(self):
        """The credential is a password, not a token.

        openconnector UserController::login (2026-08-07): correct code that
        the token-only pattern list reported as an unsourced denial.
        """
        src = _controller("""
    #[NoCSRFRequired]
    #[PublicPage]
    public function login(): JSONResponse {
        $data        = $this->request->getParams();
        $credentials = $this->securityService->validateLoginCredentials($data);
        $username    = $credentials['username'];
        $password    = $credentials['password'];

        $user = $this->userManager->checkPassword($username, $password);
        if ($user === false) {
            $this->securityService->recordFailedLoginAttempt($username, $this->clientIp());
            return new JSONResponse(['error' => 'invalid credentials'], Http::STATUS_UNAUTHORIZED);
        }

        return new JSONResponse(['uid' => $user->getUID()]);
    }
""")
        self.assertEqual(_scan(src), [])

    def test_named_argument_and_helper_resolved_token_is_not_flagged(self):
        """hermiq McpRunController::handle / EgressAuthorizeController::authorize.

        The credential is resolved by a helper (`bearerToken()`) and handed
        over as a named argument (`token:`). Neither shape is one of the
        six verbs the pattern list started with, and the only reason these
        two used to pass was the word "bearer" in their own comments — so
        they are the pair that would silently break if the comment-stripping
        change were made without widening the idioms alongside it.
        """
        src = _controller("""
    #[PublicPage]
    #[NoCSRFRequired]
    public function handle(): JSONResponse {
        $binding = $this->runTokenService->verify(token: $this->bearerToken());
        if ($binding === null) {
            return new JSONResponse(['error' => 'invalid_token'], Http::STATUS_UNAUTHORIZED);
        }

        return new JSONResponse($this->mcpService->dispatch($binding, $this->readRawBody()));
    }
""")
        self.assertEqual(_scan(src), [])

    def test_password_protected_share_is_not_flagged(self):
        src = _controller("""
    #[PublicPage]
    public function unlock(string $slug): JSONResponse {
        $folder = $this->folderMapper->findBySlug($slug);

        if (password_verify((string) $this->request->getParam('password'), $folder->getPasswordHash()) === false) {
            return new JSONResponse(['error' => 'wrong password'], Http::STATUS_UNAUTHORIZED);
        }

        return new JSONResponse($this->folderService->listing($folder));
    }
""")
        self.assertEqual(_scan(src), [])


class ProseDoesNotEarnTheExemption(unittest.TestCase):
    """Only executable code counts as authenticating a credential."""

    def test_docblock_describing_a_token_check_is_still_flagged(self):
        src = _controller("""
    /**
     * Download an export.
     *
     * Callers must present a signed capability token in the Authorization
     * header. $presentedToken is compared against the stored secret with
     * hash_equals() before any payload is returned.
     */
    #[PublicPage]
    public function download(int $id): JSONResponse {
        if ($this->exportService->isPublished($id) === false) {
            return new JSONResponse(['error' => 'not available'], Http::STATUS_FORBIDDEN);
        }

        return new JSONResponse($this->exportService->payload($id));
    }
""")
        findings = _scan(src)
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("rule=public-page-annotation-with-unsourced-denial", findings[0])

    def test_commented_out_credential_check_is_still_flagged(self):
        src = _controller("""
    #[PublicPage]
    public function receive(): JSONResponse {
        // TODO re-enable once the partner rotates their key:
        // $presentedToken = (string) $this->request->getHeader('X-Api-Key');
        // if (hash_equals($this->expectedKey(), $presentedToken) === false) {
        if ($this->importService->isAcceptingUploads() === false) {
            return new JSONResponse(['error' => 'closed'], Http::STATUS_UNAUTHORIZED);
        }

        return new JSONResponse([], 202);
    }
""")
        findings = _scan(src)
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("rule=public-page-annotation-with-unsourced-denial", findings[0])


class StringLiteralsStillCount(unittest.TestCase):
    """Comment stripping must not take the literals the idioms live in.

    ``'Bearer '``, ``'HTTP_AUTHORIZATION'`` and the header name handed to
    ``getHeader()`` are string literals in every real handler. Blanking them
    alongside comments would turn correct code into findings — the exact
    failure gate-9 was rewritten to stop.
    """

    def test_bearer_prefix_in_a_literal_is_not_flagged(self):
        src = _controller("""
    #[PublicPage]
    public function ingest(): JSONResponse {
        $header    = (string) $this->request->getHeader('Authorization');
        $presented = str_replace('Bearer ', '', $header);

        if ($this->apiKeyService->authorize($presented) === false) {
            return new JSONResponse(['error' => 'unauthorized'], Http::STATUS_UNAUTHORIZED);
        }

        return new JSONResponse([], 202);
    }
""")
        self.assertEqual(_scan(src), [])

    def test_server_superglobal_header_is_not_flagged(self):
        src = _controller("""
    #[PublicPage]
    public function ping(): JSONResponse {
        $presented = $_SERVER['HTTP_AUTHORIZATION'] ?? '';

        if (hash_equals($this->expectedKey(), (string) $presented) === false) {
            return new JSONResponse(['error' => 'unauthorized'], Http::STATUS_UNAUTHORIZED);
        }

        return new JSONResponse(['pong' => true]);
    }
""")
        self.assertEqual(_scan(src), [])

    def test_a_url_with_a_double_slash_does_not_swallow_the_rest(self):
        """`//` inside a literal must not be read as a comment start.

        If it were, everything after it — including the credential check —
        would be blanked and the method would be reported unsourced.
        """
        src = _controller("""
    #[PublicPage]
    public function callback(): JSONResponse {
        $issuer    = 'https://idp.example.org/realms/demo';
        $presented = (string) $this->request->getHeader('Authorization');

        if ($this->oidcService->verifyIdToken($presented, $issuer) === false) {
            return new JSONResponse(['error' => 'unauthorized'], Http::STATUS_UNAUTHORIZED);
        }

        return new JSONResponse(['issuer' => $issuer]);
    }
""")
        self.assertEqual(_scan(src), [])


# ---------------------------------------------------------------------------
# The #[NoAdminRequired] rule, and silence on ordinary controllers.
# ---------------------------------------------------------------------------

class NoAdminRequiredWithAdminBody(unittest.TestCase):

    def test_require_admin_under_no_admin_required_is_flagged(self):
        src = _controller("""
    #[NoAdminRequired]
    public function destroy(int $id): JSONResponse {
        $this->requireAdmin();

        $this->registerService->delete($id);
        return new JSONResponse([], 204);
    }
""")
        findings = _scan(src)
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("rule=no-admin-required-annotation-with-admin-body", findings[0])

    def test_is_admin_guard_with_forbidden_return_is_flagged(self):
        src = _controller("""
    #[NoAdminRequired]
    public function settings(): JSONResponse {
        if ($this->groupManager->isAdmin($this->userId) === false) {
            return new JSONResponse(['error' => 'admins only'], Http::STATUS_FORBIDDEN);
        }

        return new JSONResponse($this->settingsService->all());
    }
""")
        findings = _scan(src)
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("rule=no-admin-required-annotation-with-admin-body", findings[0])

    def test_yoda_comparison_is_flagged(self):
        src = _controller("""
    #[NoAdminRequired]
    public function purge(): JSONResponse {
        if (false === $this->groupManager->isAdmin($this->userId)) {
            throw new OCSForbiddenException('admins only');
        }

        $this->cacheService->purgeAll();
        return new JSONResponse(['purged' => true]);
    }
""")
        findings = _scan(src)
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("rule=no-admin-required-annotation-with-admin-body", findings[0])

    def test_a_non_admin_predicate_is_not_flagged(self):
        """The guard has to be about being an admin, not merely an `if`."""
        src = _controller("""
    #[NoAdminRequired]
    public function publish(int $id): JSONResponse {
        if ($this->publicationService->isReviewed($id) === false) {
            return new JSONResponse(['error' => 'not reviewed yet'], Http::STATUS_FORBIDDEN);
        }

        return new JSONResponse($this->publicationService->publish($id));
    }
""")
        self.assertEqual(_scan(src), [])


class OrdinaryControllersProduceNoFindings(unittest.TestCase):

    def test_plain_authenticated_endpoints_are_silent(self):
        src = _controller("""
    #[NoAdminRequired]
    public function index(): JSONResponse {
        return new JSONResponse($this->objectService->findAll());
    }

    #[NoAdminRequired]
    public function show(int $id): JSONResponse {
        return new JSONResponse($this->objectService->find($id));
    }
""")
        self.assertEqual(_scan(src), [])

    def test_an_admin_endpoint_with_no_attribute_is_silent(self):
        src = _controller("""
    public function reindex(): JSONResponse {
        $this->searchService->reindexEverything();
        return new JSONResponse(['queued' => true]);
    }
""")
        self.assertEqual(_scan(src), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
