<?php

/**
 * The CLEAN arm for gate-7's `request-sourced-object-guard` rule
 * (ConductionNL/dossiq#799).
 *
 * Byte-for-byte the planted arm's structure, with `submitResult()` and
 * `purge()` repaired the way dossiq repaired them: the comparison is made
 * against STORED state, read back from the store, rather than against a value
 * the caller sent. `prefs()` and `join()` are unchanged, because they were
 * never wrong.
 *
 * THIS FILE MUST PRODUCE ZERO FINDINGS, and it must do so for a reason the
 * planted arm does not share. That is the whole contract: a rule that simply
 * flagged every identity comparison touching request input would score 2 here
 * as well, and the two arms together are what rule that out.
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
	 * CLEAN. The permitted uid is read back off the stored case, so the caller
	 * cannot supply it, cannot omit it, and cannot change it.
	 */
	#[NoAdminRequired]
	public function submitResult(string $id): JSONResponse {
		$user = $this->userSession->getUser();
		if ($user === null) {
			throw new OCSForbiddenException('Not authenticated');
		}

		$case = $this->store->find($id);
		if ($this->groupManager->isAdmin($user->getUID()) === false) {
			if ($case['assignee'] !== $user->getUID()) {
				throw new OCSForbiddenException('Not authorized to submit this inspection result');
			}
		}

		$params = $this->request->getParams();

		return new JSONResponse($this->store->write($id, $params));
	}

	/**
	 * CLEAN. The owner is whatever the store says it is.
	 */
	#[NoAdminRequired]
	public function purge(string $id): JSONResponse {
		$user = $this->userSession->getUser();
		$owner = $this->store->find($id);
		if ($owner['assignee'] !== $user->getUID()) {
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
