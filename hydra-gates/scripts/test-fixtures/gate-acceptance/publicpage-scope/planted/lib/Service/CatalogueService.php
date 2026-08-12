<?php
/**
 * @license EUPL-1.2
 * @copyright Conduction B.V.
 */

namespace OCA\PublicPageFixture\Service;

class CatalogueService {

	/**
	 * Resolves an identifier GLOBALLY — every register on the instance.
	 */
	public function find(string $id): ?array {
		return null;
	}

	/**
	 * Resolves an identifier only inside one register/schema pair.
	 */
	public function findInScope(string $id, string $register, string $schema): ?array {
		return null;
	}

	/**
	 * Resolves an unguessable share token.
	 */
	public function findByToken(string $shareToken): ?array {
		return null;
	}

	public function listPublished(): array {
		return [];
	}
}
