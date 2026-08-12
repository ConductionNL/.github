<?php
/**
 * The CLEAN arm for `.github#365` — every method here is genuinely guarded,
 * and every one of them ALSO carries the `no user -> 401` preamble.
 *
 * THE PREAMBLE IS DELIBERATELY KEPT. Without it, this arm would prove only
 * that a file with no preamble passes, and the fix could have been "flag any
 * method containing a 401" — which would turn all four of these into findings
 * and re-create the false-positive problem that cost gate-7 its credibility
 * (`#353`, `#360`). The clean arm's job is to pin that the preamble is not
 * being PUNISHED; it is being IGNORED. What clears each method is the guard
 * that comes after it.
 *
 * Four guard shapes, one per method, chosen because each is a distinct route
 * through the checker and a fix that widens one of them must not blind another:
 *
 *   ownershipCheck()  in-body comparison, answered 403   (`_GUARD_BODY_RE`)
 *   tenancy404()      in-body comparison, answered 404   (Pattern 7 — the
 *                     anti-oracle refusal gate-7's own FAIL message endorses)
 *   collaborator()    resolved collaborator predicate    (Pattern 4a)
 *   handoff()         session identity passed into the data call (Pattern 6 —
 *                     doriath's shape, hand-verified as zero real exposure)
 *
 * This file must produce ZERO findings. Under the pre-`#365` checker it also
 * produced zero — but for the WRONG reason: the preamble alone cleared all
 * four, so the guards below were never consulted. That is why the planted arm
 * is the load-bearing half of this bundle and this one is the abuse control.
 *
 * @license EUPL-1.2
 * @copyright Conduction B.V.
 */

namespace OCA\AuthnFixture\Controller;

use OCA\AuthnFixture\Service\LedgerService;
use OCP\AppFramework\Controller;
use OCP\AppFramework\Http;
use OCP\AppFramework\Http\Attribute\NoAdminRequired;
use OCP\AppFramework\Http\JSONResponse;
use OCP\IRequest;
use OCP\IUserSession;

class LedgerController extends Controller {

	public function __construct(
		string $appName,
		IRequest $request,
		private readonly LedgerService $ledger,
		private readonly IUserSession $userSession,
	) {
		parent::__construct($appName, $request);
	}

	/**
	 * Shape 1 — in-body ownership comparison, answered with 403.
	 */
	#[NoAdminRequired]
	public function ownershipCheck(string $entryId): JSONResponse {
		$user = $this->userSession->getUser();
		if ($user === null) {
			return new JSONResponse(['error' => 'Unauthorized'], Http::STATUS_UNAUTHORIZED);
		}
		$entry = $this->ledger->find($entryId);
		if ($entry['ownerId'] !== $user->getUID()) {
			return new JSONResponse(['error' => 'Forbidden'], Http::STATUS_FORBIDDEN);
		}
		return new JSONResponse($entry);
	}

	/**
	 * Shape 2 — the same comparison answered with 404 ON PURPOSE, so that a 403
	 * cannot become an existence oracle for another owner's ids.
	 */
	#[NoAdminRequired]
	public function tenancy404(string $entryId): JSONResponse {
		$user = $this->userSession->getUser();
		if ($user === null) {
			return new JSONResponse(['error' => 'Unauthorized'], Http::STATUS_UNAUTHORIZED);
		}
		$entry = $this->ledger->find($entryId);
		if ($entry['ownerId'] !== $user->getUID()) {
			return new JSONResponse(['error' => 'Not found'], Http::STATUS_NOT_FOUND);
		}
		return new JSONResponse($entry);
	}

	/**
	 * Shape 3 — the predicate lives on an injected collaborator and is read out
	 * of that class's own source.
	 */
	#[NoAdminRequired]
	public function collaborator(string $entryId): JSONResponse {
		$user = $this->userSession->getUser();
		if ($user === null) {
			return new JSONResponse(['error' => 'Unauthorized'], Http::STATUS_UNAUTHORIZED);
		}
		if ($this->ledger->canAccessEntry($entryId, $user->getUID()) === false) {
			return new JSONResponse(['error' => 'Not found'], Http::STATUS_NOT_FOUND);
		}
		return new JSONResponse($this->ledger->find($entryId));
	}

	/**
	 * Shape 4 — the caller's identity is handed to the data layer alongside the
	 * caller-supplied id, so the lookup is scoped to a value the caller cannot
	 * forge. This is how doriath writes almost every endpoint.
	 */
	#[NoAdminRequired]
	public function handoff(string $entryId): JSONResponse {
		$userId = $this->sessionUserId();
		if ($userId === null) {
			return new JSONResponse(['error' => 'Unauthorized'], Http::STATUS_UNAUTHORIZED);
		}
		return new JSONResponse($this->ledger->findOwned(entryId: $entryId, userId: $userId));
	}

	private function sessionUserId(): ?string {
		$user = $this->userSession->getUser();
		if ($user === null) {
			return null;
		}
		return $user->getUID();
	}
}
