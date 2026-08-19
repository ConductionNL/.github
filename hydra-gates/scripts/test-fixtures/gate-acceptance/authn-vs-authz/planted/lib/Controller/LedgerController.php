<?php
/**
 * The PLANTED arm for `.github#365` — AUTHENTICATION IS NOT AUTHORISATION.
 *
 * THE THREE-ARM CONTROL THIS BUNDLE EXISTS FOR
 * --------------------------------------------
 * Arm 1 lives here as `bare()`   — an unguarded IDOR. gate-7 always found it.
 * Arm 2 lives here as `preamble()` — the SAME data-access body, preceded only
 *        by the house-style `no user -> 401` clause. gate-7 reported ZERO on
 *        this, in all eighteen fleet apps, for as long as the gate has existed.
 * Arm 3 lives in `clean/`        — the SAME body, the SAME 401 preamble, PLUS a
 *        real per-object guard. It must stay silent.
 *
 * Arms 1 and 2 differ by the preamble alone; arms 2 and 3 differ by the guard
 * alone. That is what makes the pair a control rather than two samples: the
 * only thing that can explain a verdict difference is the thing that changed.
 *
 * `readAsOwner()` KEEPS a real guard, so this arm is not uniformly guilty — a
 * checker that simply flagged every `#[NoAdminRequired]` method would score 4/4
 * here and look correct. It must find exactly the three that guard nothing.
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
	 * ARM 1 — bare unguarded IDOR. The control that proves the gate is live on
	 * this file and this shape. If this one stops firing, nothing else here
	 * means anything.
	 */
	#[NoAdminRequired]
	public function bare(string $entryId): JSONResponse {
		$entry = $this->ledger->find($entryId);
		return new JSONResponse($entry);
	}

	/**
	 * ARM 2 — THE DEFECT. Byte-identical to `bare()` below the preamble.
	 *
	 * "Is anyone logged in?" is AUTHENTICATION. Under `#[NoAdminRequired]`
	 * Nextcloud's middleware has already answered that question, so this clause
	 * cannot even fail — and it still bought the method a PASS.
	 */
	#[NoAdminRequired]
	public function preamble(string $entryId): JSONResponse {
		$user = $this->userSession->getUser();
		if ($user === null) {
			return new JSONResponse(['error' => 'Unauthorized'], Http::STATUS_UNAUTHORIZED);
		}
		$entry = $this->ledger->find($entryId);
		return new JSONResponse($entry);
	}

	/**
	 * ARM 2b — the same authentication clause answering 403 instead of 401.
	 *
	 * `#365` as filed proposes deleting `401`/`UNAUTHORIZED` from the guard
	 * regex. This method is what that repair leaves behind: one token of edit,
	 * made by someone chasing a green gate, and the silence is back — bought by
	 * making the response WORSE. It is here so that a future token-level
	 * "simplification" of the fix goes red.
	 */
	#[NoAdminRequired]
	public function preambleForbiddenCode(string $entryId): JSONResponse {
		$user = $this->userSession->getUser();
		if ($user === null) {
			return new JSONResponse(['error' => 'Forbidden'], Http::STATUS_FORBIDDEN);
		}
		$entry = $this->ledger->find($entryId);
		return new JSONResponse($entry);
	}

	/**
	 * ARM 4 — THE ABUSE CONTROL FOR `ConductionNL/.github#414`.
	 *
	 * `#414` normalises a leading `(string)` cast away before an expression is
	 * classified as the caller's identity, so that the clean arm's
	 * `handoffCastIdentity()` stops being a false positive. This method is the
	 * shape that normalisation must NOT clear: the cast sits on a value the
	 * CALLER chose, whose name merely happens to contain "uid".
	 *
	 * Without it, "strip the cast, then classify" would route `(string)$targetUid`
	 * past the declared-parameter veto — `_IDENTITY_TOKEN_RE` matches "uid" —
	 * and every endpoint that takes someone else's user id as a parameter would
	 * go silent. That is a false NEGATIVE on a security gate, which leaves no
	 * log to notice.
	 *
	 * No session value reaches the lookup here. It must report in both
	 * directions, before and after `#414`.
	 */
	#[NoAdminRequired]
	public function castCallerValue(string $entryId, string $targetUid): JSONResponse {
		return new JSONResponse(
			$this->ledger->findOwned(entryId: $entryId, userId: (string)$targetUid)
		);
	}

	/**
	 * NOT planted — a real per-object ownership check. Keeps the planted arm
	 * from being uniformly guilty.
	 */
	#[NoAdminRequired]
	public function readAsOwner(string $entryId): JSONResponse {
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
}
