<?php
/**
 * @license EUPL-1.2
 * @copyright Conduction B.V.
 *
 * PLANT 2 of 3 — ADR-083 rule 2 (OpenRegister type in a class header).
 *
 * This is the fatal form. The reference sits in the CLASS HEADER, so it is
 * resolved at autoload rather than at construction: on an instance without
 * OpenRegister every route dies, including the start screen that exists to
 * explain the problem.
 *
 * It does NOT contain a container lookup and is NOT reachable from the default
 * route, so the row naming this file is satisfied by the `header` check alone.
 */

namespace OCA\OrDepFixture\Service;

class InheritingService extends \OCA\OpenRegister\Service\ObjectService {

	public function label(): string {
		return 'inherits the vendor class';
	}
}
