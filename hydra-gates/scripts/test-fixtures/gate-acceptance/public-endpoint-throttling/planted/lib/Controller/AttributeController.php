<?php
/**
 * PLANT 2 — public by the ATTRIBUTE, no volume ceiling.
 *
 * A separate plant from the annotation one on purpose: a checker that handled
 * only the form it was written against would satisfy one arm and miss the
 * other, and the whole point of gate-82 is that BOTH forms are live.
 *
 * Shape taken from openregister GenericHealthController::index — the one
 * attribute-form endpoint the fleet sweep missed.
 *
 * SPDX-License-Identifier: EUPL-1.2
 */

namespace OCA\PetFixture\Controller;

use OCP\AppFramework\Controller;
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
	public function index(): JSONResponse {
		return new JSONResponse([]);
	}
}
