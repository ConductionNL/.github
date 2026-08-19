<?php
/**
 * PLANT 1 — public by the LEGACY ANNOTATION, no volume ceiling.
 *
 * This is the shape the fleet sweep could not see. It line-anchored the
 * #[PublicPage] ATTRIBUTE and excluded docblock matches, so 199 endpoints
 * declared this way were reported as "fully throttled".
 *
 * Shape taken from openregister GraphQLController::execute, which answers 200
 * to an unauthenticated caller with only this annotation on it.
 *
 * SPDX-License-Identifier: EUPL-1.2
 */

namespace OCA\PetFixture\Controller;

use OCP\AppFramework\Controller;
use OCP\AppFramework\Http\JSONResponse;

class AnnotationController extends Controller {

	/**
	 * Execute a query.
	 *
	 * @return JSONResponse The response
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
