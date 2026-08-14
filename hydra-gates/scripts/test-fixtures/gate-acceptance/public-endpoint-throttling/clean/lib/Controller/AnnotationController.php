<?php
/**
 * CLEAN arm of plant 1 — the annotation form, now with a ceiling.
 *
 * Note the docblock below deliberately MENTIONS `#[PublicPage]` in prose. If
 * the gate ever matches the marker anywhere in a comment instead of requiring
 * the tag alone on its own line, this arm goes red — which is how the 30%
 * overcount that produced "223 public endpoints" gets caught here rather than
 * in a report to a human.
 *
 * SPDX-License-Identifier: EUPL-1.2
 */

namespace OCA\PetFixture\Controller;

use OCP\AppFramework\Controller;
use OCP\AppFramework\Http\Attribute\AnonRateLimit;
use OCP\AppFramework\Http\JSONResponse;

class AnnotationController extends Controller {

	/**
	 * Execute a query.
	 *
	 * Unlike the #[PublicPage] handlers elsewhere in this app, the ceiling on
	 * this one is expressed as an attribute rather than an annotation.
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
	#[AnonRateLimit(limit: 30, period: 60)]
	public function execute(): JSONResponse {
		return new JSONResponse([]);
	}
}
