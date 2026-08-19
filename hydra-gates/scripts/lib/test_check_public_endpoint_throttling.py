#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Tests for the ADR-082 public-endpoint throttling gate.

The controls that matter are the first two classes: the gate must FLAG a shape
proven vulnerable on the running server, and must CLEAR a shape proven
throttled. A gate that has only ever been watched to pass has not been tested.
"""

from __future__ import annotations

import unittest

from check_public_endpoint_throttling import is_controller, public_methods


def _one(src: str):
    got = public_methods(src)
    return got[0] if got else None


class AnnotationFormIsSeen(unittest.TestCase):
    """The form the earlier sweep could not see.

    Shape taken from openregister GraphQLController::execute, which answers
    200 to an unauthenticated caller with only this annotation on it.
    """

    SRC = '''<?php
class GraphQLController extends Controller {

	/**
	 * Execute a GraphQL query.
	 *
	 * @NoAdminRequired
	 *
	 * @NoCSRFRequired
	 *
	 * @PublicPage
	 *
	 * @CORS
	 */
	public function execute(): JSONResponse {
		return new JSONResponse([]);
	}
}
'''

    def test_af_the_annotation_form_is_detected_at_all(self):
        self.assertEqual(_one(self.SRC)[0], 'execute')

    def test_af_it_is_reported_as_the_annotation_form(self):
        self.assertEqual(_one(self.SRC)[1], 'annotation')

    def test_af_it_is_reported_unthrottled(self):
        self.assertFalse(_one(self.SRC)[2])


class ThrottledEndpointIsCleared(unittest.TestCase):
    """Shape taken from openregister FederationController, which was throttled
    in this programme and must not be flagged again."""

    SRC = '''<?php
class FederationController extends Controller {

	/**
	 * Accept a share.
	 */
	#[PublicPage]
	#[NoCSRFRequired]
	#[AnonRateLimit(limit: 60, period: 60)]
	#[BruteForceProtection(action: self::THROTTLE_ACTION)]
	public function acceptShare(): JSONResponse {
		return new JSONResponse([]);
	}
}
'''

    def test_te_the_attribute_form_is_detected(self):
        self.assertEqual(_one(self.SRC)[1], 'attribute')

    def test_te_a_throttled_endpoint_is_cleared(self):
        self.assertTrue(_one(self.SRC)[2])


class ProseDoesNotMakeAnEndpointPublic(unittest.TestCase):
    """The overcount this gate must not reintroduce.

    An earlier fleet figure counted the attribute NAME where it appeared
    inside docblock prose, inflating the total by ~30% in the alarming
    direction. The annotation is only a declaration on its own tag line.
    """

    def test_pr_a_docblock_mention_of_the_attribute_is_not_a_declaration(self):
        src = '''<?php
class C {
	/**
	 * Unlike #[PublicPage] handlers, this one requires a session.
	 */
	public function internalOnly(): JSONResponse {
		return new JSONResponse([]);
	}
}
'''
        self.assertEqual(public_methods(src), [])

    def test_pr_the_word_publicpage_in_prose_is_not_a_declaration(self):
        src = '''<?php
class C {
	/**
	 * See the @PublicPage docs for why this is NOT one.
	 */
	public function internalOnly(): JSONResponse {
		return new JSONResponse([]);
	}
}
'''
        self.assertEqual(public_methods(src), [])


class EitherCeilingSatisfiesTheGate(unittest.TestCase):

    def _src(self, attr: str) -> str:
        return '''<?php
class C {
	/**
	 * @PublicPage
	 */
	%s
	public function handle(): JSONResponse {
		return new JSONResponse([]);
	}
}
''' % attr

    def test_ec_anon_rate_limit_counts(self):
        self.assertTrue(_one(self._src('#[AnonRateLimit(limit: 10, period: 60)]'))[2])

    def test_ec_user_rate_limit_counts(self):
        self.assertTrue(_one(self._src('#[UserRateLimit(limit: 10, period: 60)]'))[2])

    def test_ec_brute_force_counts(self):
        self.assertTrue(_one(self._src("#[BruteForceProtection(action: 'x')]"))[2])

    def test_ec_an_unrelated_attribute_does_not_count(self):
        self.assertFalse(_one(self._src('#[NoCSRFRequired]'))[2])


class MixedFormsAreScoredOnce(unittest.TestCase):
    """A method carrying both markers is one endpoint, not two."""

    def test_mf_both_forms_on_one_method_is_a_single_finding(self):
        src = '''<?php
class C {
	/**
	 * @PublicPage
	 */
	#[PublicPage]
	public function handle(): JSONResponse {
		return new JSONResponse([]);
	}
}
'''
        got = public_methods(src)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0][1], 'both')


class NonPublicMethodsAreIgnored(unittest.TestCase):

    def test_np_a_method_with_no_block_is_not_public(self):
        src = '''<?php
class C {
	public function plain(): JSONResponse {
		return new JSONResponse([]);
	}
}
'''
        self.assertEqual(public_methods(src), [])

    def test_np_no_admin_required_alone_is_not_public(self):
        src = '''<?php
class C {
	/**
	 * @NoAdminRequired
	 */
	public function loggedInOnly(): JSONResponse {
		return new JSONResponse([]);
	}
}
'''
        self.assertEqual(public_methods(src), [])

    def test_np_a_previous_methods_block_does_not_leak_downward(self):
        """The backward scan must stop at real code, or one public method
        would make every method below it look public too."""
        src = '''<?php
class C {
	/**
	 * @PublicPage
	 */
	public function open(): JSONResponse {
		return new JSONResponse([]);
	}

	public function closed(): JSONResponse {
		return new JSONResponse([]);
	}
}
'''
        got = public_methods(src)
        self.assertEqual([g[0] for g in got], ['open'])


class OnlyRoutableClassesCount(unittest.TestCase):
    """An annotation on a class the router never reaches is inert.

    Shape taken from opencatalogi `lib/Service/PublicationService.php`, which
    carries three real @PublicPage annotations copy-pasted from a controller.
    It declares `class PublicationService {`, extends nothing, and appears
    nowhere in appinfo/routes.php.
    """

    def test_or_a_plain_service_class_is_not_a_controller(self):
        self.assertFalse(is_controller('<?php\nclass PublicationService {\n}\n'))

    def test_or_a_class_named_controller_counts(self):
        self.assertTrue(is_controller('<?php\nclass CatalogiController {\n}\n'))

    def test_or_a_class_extending_controller_counts(self):
        self.assertTrue(
            is_controller('<?php\nclass Foo extends Controller {\n}\n'))

    def test_or_a_project_local_controller_base_counts(self):
        """The generous test exists so the gate cannot HIDE a real controller —
        the one failure it must never have."""
        self.assertTrue(
            is_controller('<?php\nclass Foo extends PortalBaseController {\n}\n'))

    def test_or_an_fq_parent_counts(self):
        self.assertTrue(
            is_controller('<?php\nclass Foo extends \\OCP\\AppFramework\\ApiController {\n}\n'))

    def test_or_a_service_extending_a_service_base_does_not_count(self):
        self.assertFalse(
            is_controller('<?php\nclass FooService extends AbstractService {\n}\n'))


if __name__ == '__main__':
    unittest.main()
