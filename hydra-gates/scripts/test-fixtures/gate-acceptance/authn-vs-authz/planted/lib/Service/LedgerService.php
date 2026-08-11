<?php
/**
 * @license EUPL-1.2
 * @copyright Conduction B.V.
 */

namespace OCA\AuthnFixture\Service;

class LedgerService {

	public function find(string $entryId): array {
		return ['id' => $entryId, 'ownerId' => 'alice'];
	}

	public function findOwned(string $entryId, string $userId): array {
		$entry = $this->find($entryId);
		if ($entry['ownerId'] !== $userId) {
			throw new \RuntimeException('Not found');
		}
		return $entry;
	}

	public function canAccessEntry(string $entryId, string $userId): bool {
		return $this->find($entryId)['ownerId'] === $userId;
	}
}
