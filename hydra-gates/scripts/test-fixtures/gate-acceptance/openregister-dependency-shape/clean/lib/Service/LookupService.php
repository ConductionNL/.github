<?php
/**
 * @license EUPL-1.2
 * @copyright Conduction B.V.
 *
 * The conforming form of planted/'s PLANT 1. Same behaviour, same dependency —
 * declared where a reader and a gate can both see it.
 *
 * The docblock below deliberately NAMES the container form in prose. If the
 * check ever reads raw source instead of comment-free source, this arm turns
 * red and says so, which is the only way a "gate switched off by prose" defect
 * gets caught before it ships rather than after.
 *
 * Was: $this->container->get('OCA\OpenRegister\Service\ObjectService')
 */

namespace OCA\OrDepFixture\Service;

use OCA\OpenRegister\Service\ObjectService;

class LookupService {

	public function __construct(
		private readonly ObjectService $objectService,
	) {
	}

	public function accounts(string $programmeId): array {
		return $this->objectService->findAll(config: ['filters' => ['programmeId' => $programmeId]]);
	}
}
