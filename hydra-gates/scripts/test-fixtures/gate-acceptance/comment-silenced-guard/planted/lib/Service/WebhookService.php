<?php
/**
 * @license EUPL-1.2
 * @copyright Conduction B.V.
 */

namespace OCA\CommentGuardFixture\Service;

class WebhookService {

	public function find(string $id): ?array {
		return ['id' => $id, 'ownerId' => 'alice'];
	}

	public function rotate(?array $agent): array {
		return ['id' => $agent['id'] ?? null, 'secret' => 'rotated'];
	}
}
