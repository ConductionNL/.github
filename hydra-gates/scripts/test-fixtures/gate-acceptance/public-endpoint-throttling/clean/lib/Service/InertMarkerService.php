<?php
/**
 * An @PublicPage annotation on a class the router never reaches.
 *
 * Carried in the CLEAN arm on purpose. This is copy-pasted-from-a-controller
 * shape, found for real in opencatalogi lib/Service/PublicationService.php,
 * which carries three of these on index/uses/used. The class extends nothing
 * and appears nowhere in routes.php, so Nextcloud never reads the marker and
 * no rate limit could ever apply.
 *
 * If the gate ever counts it, this arm goes red — which is the difference
 * between a gate that reports fixable findings and one that reports three
 * nobody can act on.
 *
 * SPDX-License-Identifier: EUPL-1.2
 */

namespace OCA\PetFixture\Service;

class InertMarkerService {

	/**
	 * Look something up.
	 *
	 * @return array The result
	 *
	 * @NoAdminRequired
	 *
	 * @NoCSRFRequired
	 *
	 * @PublicPage
	 */
	public function index(): array {
		return [];
	}
}
