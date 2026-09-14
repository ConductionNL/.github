<?php

/**
 * The PLANTED arm for gate-7's `request-sourced-object-guard` rule
 * (ConductionNL/dossiq#799).
 *
 * `submitResult()` and `purge()` each carry a per-object guard that CANNOT
 * REFUSE ANYBODY, because the value it compares the caller against is supplied
 * by that same caller. Both must be flagged.
 *
 * `prefs()` and `join()` are the NEGATIVE CONTROLS and must never appear. They
 * are here so the planted arm is not uniformly guilty: a rule that flagged
 * every identity comparison against request input would score 4 here, and that
 * over-flagging is what the clean arm and these two rows catch. Both are
 * copied unchanged from the clean arm.
 *
 * @license EUPL-1.2
 * @copyright Conduction B.V.
 */

namespace OCA\RsgFixture\Controller;

use OCA\RsgFixture\Service\CaseStore;
use OCP\AppFramework\Controller;
use OCP\AppFramework\Http\Attribute\NoAdminRequired;
use OCP\AppFramework\Http\JSONResponse;
use OCP\AppFramework\OCS\OCSForbiddenException;

class InspectionController extends Controller {

	/** @var CaseStore */
	private CaseStore $store;

	/**
	 * FLAGGED. dossiq#799 verbatim, admin wrapper included.
	 *
	 * `assignedInspector` comes off the wire, is compared to the caller's own
	 * uid, and is then handed to nothing, read by nothing and stored nowhere.
	 * Omit it and the `!== ''` conjunct is false; send your own uid and the
	 * second conjunct is false. There is no third outcome.
	 */
	#[NoAdminRequired]
	public function submitResult(string $id): JSONResponse {
		$user = $this->userSession->getUser();
		if ($user === null) {
			throw new OCSForbiddenException('Not authenticated');
		}

		$params = $this->request->getParams();
		if ($this->groupManager->isAdmin($user->getUID()) === false) {
			$assignedUid = $params['assignedInspector'] ?? '';
			if ($assignedUid !== '' && $assignedUid !== $user->getUID()) {
				throw new OCSForbiddenException('Not authorized to submit this inspection result');
			}
		}

		return new JSONResponse($this->store->write($id, $params));
	}

	/**
	 * FLAGGED. The same defect without the presence test: the compared value
	 * is read straight off the body, matched against the caller, and then used
	 * for nothing. The object actually deleted is `$id`, which the comparison
	 * never mentions.
	 */
	#[NoAdminRequired]
	public function purge(string $id): JSONResponse {
		$user = $this->userSession->getUser();
		$claimed = $this->request->getParam('ownerUid');
		if ($claimed !== $user->getUID()) {
			throw new OCSForbiddenException('Not authorized');
		}

		return new JSONResponse($this->store->delete($id));
	}

	/**
	 * NEGATIVE CONTROL. `$userId` is request-sourced AND is the lookup key;
	 * pinning it to the caller IS the scoping. Must never be reported.
	 */
	#[NoAdminRequired]
	public function prefs(string $userId): JSONResponse {
		$user = $this->userSession->getUser();
		if ($userId !== $user->getUID()) {
			throw new OCSForbiddenException('Not authorized');
		}

		return new JSONResponse($this->store->loadFor($userId));
	}

	/**
	 * NEGATIVE CONTROL, measured on openregister `OrganisationController`.
	 *
	 * Omitting `userId` does skip the refusal, and that is harmless: the
	 * callee resolves an absent target to the session user, so absent means
	 * "me". A value the callee RECEIVES is a parameter, not a decoration.
	 * Must never be reported.
	 */
	#[NoAdminRequired]
	public function join(string $uuid): JSONResponse {
		$user = $this->userSession->getUser();
		$userId = $this->request->getParam('userId');
		if ($userId !== null && $userId !== $user->getUID()
			&& $this->canManageMembers($uuid) === false
		) {
			return new JSONResponse(['error' => 'Not authorized'], 403);
		}

		return new JSONResponse($this->store->joinOrganisation($uuid, $userId));
	}

	/**
	 * Owner check for `join()`, decided from stored state.
	 */
	private function canManageMembers(string $uuid): bool {
		$user = $this->userSession->getUser();
		$org = $this->store->find($uuid);

		return ($org['assignee'] === $user->getUID());
	}
}
