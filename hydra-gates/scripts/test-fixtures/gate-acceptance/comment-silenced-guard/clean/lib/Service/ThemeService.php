<?php
/**
 * @license EUPL-1.2
 * @copyright Conduction B.V.
 */

namespace OCA\CommentGuardFixture\Service;

class ThemeService {

	public function find(string $id): ?array {
		return ['id' => $id, 'ownerId' => 'alice'];
	}

	public function isShared(array $theme, string $userId): bool {
		return in_array($userId, $theme['sharedWith'] ?? [], true);
	}
}
