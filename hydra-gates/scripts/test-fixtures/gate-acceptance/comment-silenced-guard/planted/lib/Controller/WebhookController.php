<?php
/**
 * The PLANTED arm for `.github#373`, MECHANISM A — A SENTENCE IS NOT A GUARD.
 *
 * WHAT THIS FILE PINS
 * -------------------
 * Until `#373`, `_collect_guard_helpers` matched `_HELPER_GUARD_BODY_RE`
 * against the auth-blanked source, which still contained every COMMENT. So the
 * pattern read prose. MEASURED on hermiq `AgentWebhookController::loadOwnedAgent`,
 * whose body contains no `throw` statement at all — the word appears only in a
 * code comment explaining why the helper CATCHES one — and that one sentence
 * made the helper guard-bearing, which cleared ALL FOUR routed methods calling
 * it. `getObjectService()`, the same shape in code rather than in prose, is
 * pinned next door in ThemeController.
 *
 * `rotate()` here is the routed method. It has no guard of its own; the only
 * thing standing between it and a gate-7 finding is whether `loadAgent()`
 * counts as a guard. Under the merged checker it does not, and `rotate()` is
 * reported. Restore `body = src[...]` in `_collect_guard_helpers` — one line —
 * and the comment silences the gate again and this arm goes green.
 *
 * `readOwned()` is the NEGATIVE CONTROL, and it is load-bearing in the other
 * direction: `#373` narrowed the body test precisely because a real helper that
 * compares object ownership and answers `null` — the deliberate anti-oracle
 * choice — must still clear its callers. It is recognised by its CONDITION, not
 * by a token in its text. Delete that recognition and this arm reports two
 * findings instead of one, and the clean/ arm reports two instead of none.
 *
 * ⚠️ The per-method docblocks below are deliberately austere. gate-7's routed
 * method scan still reads comment-bearing text (a known, named, open leak), so
 * an explanatory docblock naming a status constant or an authorisation
 * exception would clear the very method this file plants — the fixture's own
 * prose satisfying the gate it is written to test. Everything explanatory lives
 * up here, outside every method body span.
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
	 * PLANTED — nothing here decides anything. See the file header.
	 */
	#[NoAdminRequired]
	public function rotate(string $id): JSONResponse {
		$agent = $this->loadAgent($id);
		return new JSONResponse($this->webhooks->rotate($agent));
	}

	/**
	 * The helper whose body is prose. It fetches and returns; it decides nothing.
	 */
	private function loadAgent(string $id): ?array {
		// The caller invokes this helper OUTSIDE its own try block, so a
		// throw here — Forbidden or otherwise — escapes as a framework 500.
		return $this->webhooks->find($id);
	}

	/**
	 * NEGATIVE CONTROL — must stay silent. See the file header.
	 */
	#[NoAdminRequired]
	public function readOwned(string $id): JSONResponse {
		$agent = $this->loadOwnedAgent($id);
		return new JSONResponse($agent);
	}

	/**
	 * A real decision, written as a comparison answered with null.
	 */
	private function loadOwnedAgent(string $id): ?array {
		$agent = $this->webhooks->find($id);
		if ($agent['ownerId'] !== $this->userId) {
			return null;
		}
		return $agent;
	}
}
