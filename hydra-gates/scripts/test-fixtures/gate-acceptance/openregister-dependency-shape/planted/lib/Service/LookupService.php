<?php
/**
 * @license EUPL-1.2
 * @copyright Conduction B.V.
 *
 * PLANT 1 of 3 — ADR-083 rule 1 (container lookup).
 *
 * The dependency is real but announced only as a string, so it is absent from
 * the constructor, from the type system, and from every tool that reads this
 * file. Nothing else in this fixture triggers the `lookup` check, so the row
 * naming this file cannot be satisfied by either of the other two plants.
 */

namespace OCA\OrDepFixture\Service;

use Psr\Container\ContainerInterface;

class LookupService {

	public function __construct(
		private readonly ContainerInterface $container,
	) {
	}

	public function accounts(string $programmeId): array {
		$objectService = $this->container->get('OCA\OpenRegister\Service\ObjectService');

		return $objectService->findAll(config: ['filters' => ['programmeId' => $programmeId]]);
	}
}
