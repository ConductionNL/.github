<?php
/**
 * CLEAN arm of plant 2 — the attribute form, now with a ceiling.
 *
 * This one also carries a NON-public method below the public one. The gate
 * reads a method's markers by scanning UP from its `function` line, and if
 * that scan does not stop at real code it would inherit the public marker from
 * the method above and report a method that is not reachable at all.
 *
 * SPDX-License-Identifier: EUPL-1.2
 */

namespace OCA\PetFixture\Controller;

use OCP\AppFramework\Controller;
use OCP\AppFramework\Http\Attribute\AnonRateLimit;
use OCP\AppFramework\Http\Attribute\NoCSRFRequired;
use OCP\AppFramework\Http\Attribute\PublicPage;
use OCP\AppFramework\Http\JSONResponse;

class AttributeController extends Controller {

	/**
	 * Report health.
	 *
	 * @return JSONResponse The response
	 */
	#[PublicPage]
	#[NoCSRFRequired]
	#[AnonRateLimit(limit: 240, period: 60)]
	public function index(): JSONResponse {
		return new JSONResponse([]);
	}

	/**
	 * Not reachable without a session, and so not this gate's subject.
	 *
	 * @return JSONResponse The response
	 */
	public function internalOnly(): JSONResponse {
		return new JSONResponse([]);
	}
}
