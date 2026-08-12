<?php
/**
 * The CLEAN arm for `.github#373`, MECHANISM A.
 *
 * BYTE-FOR-BYTE the planted arm, INCLUDING THE COMMENT, with one change:
 * `loadAgent()` now makes a real decision — it compares object ownership
 * against the caller and answers `null`. Nothing else differs, and that is the
 * whole point of the pair.
 *
 * The comment is KEPT deliberately. `#373` did not make prose illegal, it made
 * prose uncountable, and this arm is what proves the difference: a helper that
 * says "throw … Forbidden" in a sentence AND decides in code must still clear
 * its caller. An arm that also deleted the sentence would have passed against
 * the broken checker too, and would have proved nothing.
 *
 * This file must produce ZERO findings. It reports TWO if the ownership-
 * comparison recognition added by `#373` is removed — `rotate()` because
 * `loadAgent()` stops clearing it, and `readOwned()` because `loadOwnedAgent()`
 * does. That is mechanism C, and this arm is the only place it can be seen.
 *
 * @license EUPL-1.2
 * @copyright Conduction B.V.
 */

namespace OCA\CommentGuardFixture\Controller;

use OCA\CommentGuardFixture\Service\WebhookService;
use OCP\AppFramework\Controller;
use OCP\AppFramework\Http\Attribute\NoAdminRequired;
use OCP\AppFramework\Http\JSONResponse;
use OCP\IRequest;

class WebhookController extends Controller {

	public function __construct(
		string $appName,
		IRequest $request,
		private readonly WebhookService $webhooks,
		private readonly string $userId,
	) {
		parent::__construct($appName, $request);
	}

	/**
	 * Identical to the planted arm. Cleared by the helper below.
	 */
	#[NoAdminRequired]
	public function rotate(string $id): JSONResponse {
		$agent = $this->loadAgent($id);
		return new JSONResponse($this->webhooks->rotate($agent));
	}

	/**
	 * The same helper, the same sentence — and now an actual decision.
	 */
	private function loadAgent(string $id): ?array {
		// The caller invokes this helper OUTSIDE its own try block, so a
		// throw here — Forbidden or otherwise — escapes as a framework 500.
		$agent = $this->webhooks->find($id);
		if ($agent['ownerId'] !== $this->userId) {
			return null;
		}
		return $agent;
	}

	/**
	 * Identical to the planted arm.
	 */
	#[NoAdminRequired]
	public function readOwned(string $id): JSONResponse {
		$agent = $this->loadOwnedAgent($id);
		return new JSONResponse($agent);
	}

	/**
	 * Identical to the planted arm.
	 */
	private function loadOwnedAgent(string $id): ?array {
		$agent = $this->webhooks->find($id);
		if ($agent['ownerId'] !== $this->userId) {
			return null;
		}
		return $agent;
	}
}
