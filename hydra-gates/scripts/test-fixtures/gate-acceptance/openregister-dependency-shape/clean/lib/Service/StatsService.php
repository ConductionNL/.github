<?php
/**
 * @license EUPL-1.2
 * @copyright Conduction B.V.
 *
 * PLANT 3 of 3 (the dependency half) — ADR-083 rule 3.
 *
 * Note what this file is NOT: it injects ObjectService as a typed constructor
 * property, which is exactly the shape rule 1 asks for. On its own it is
 * correct and must not be reported.
 *
 * The violation is one level up — PageController, the app's default route,
 * injects THIS service, so the start screen cannot be constructed without
 * OpenRegister. That is the transitive case convention cannot catch, and the
 * reason gate-66 walks the constructor graph rather than reading one file.
 */

namespace OCA\OrDepFixture\Service;

use OCA\OpenRegister\Service\ObjectService;

class StatsService {

	public function __construct(
		private readonly ObjectService $objectService,
	) {
	}

	public function totals(): array {
		return $this->objectService->findAll(config: ['limit' => 10]);
	}
}
