<?php
/**
 * A typed COLLABORATOR whose `canAccess()` is the shape `ConductionNL/.github`
 * — shillinq `security-endpoint-guards`, 2026-08-20 — measured as 86/105 (82%)
 * mechanical-scan false positives: a real per-object membership check spelled
 * `is|has|can|may` + auth-token, not `authorize*`/`require*`/`ensure*`.
 *
 * Identical byte-for-byte in clean/ and planted/ — this file is not itself
 * under test, `AgentController::archive()`'s use of it is.
 *
 * @license EUPL-1.2
 * @copyright Conduction B.V.
 */

namespace OCA\ScopeFixture\Service;

class AdministrationContextService {

	/**
	 * @param array<int,string> $accessibleIds
	 */
	public function __construct(
		private readonly array $accessibleIds = ['1', '2', '3'],
	) {
	}

	public function canAccess(string $administrationId): bool {
		if ($administrationId === '') {
			return false;
		}
		return in_array($administrationId, $this->accessibleIds, true);
	}
}
