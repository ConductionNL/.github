<?php
/**
 * A deliberately GUARD-FREE collaborator.
 *
 * It exists so neither arm can clear through Pattern 4: the verdict must turn
 * on the controller's own comparison, not on something this class does.
 *
 * @license EUPL-1.2
 * @copyright Conduction B.V.
 */

namespace OCA\RsgFixture\Service;

class CaseStore {
	public function find(string $id): array {
		return ['assignee' => ''];
	}

	public function write(string $id, array $payload): array {
		return ['id' => $id];
	}

	public function delete(string $id): bool {
		return true;
	}

	public function loadFor(string $uid): array {
		return [];
	}

	public function joinOrganisation(string $uuid, ?string $targetUserId): bool {
		return true;
	}
}
