<?php

/**
 * gate-30 fixture — role-resolvable + group-declared, clean case.
 *
 * Discoverable the same way `hydra-gate-initial-state` and the new
 * role-resolvable check both look: a `provideInitialState('primaryRole', ...)`
 * call site naming this class's resolving method. The literal `return`
 * statements below are exactly the manifest's `visibleIf.user.primaryRole.in`
 * literals ("admin", "viewer") — the good fixture is clean by construction,
 * so this file must never drift from `good/src/manifest.json`'s gate.
 *
 * The single `isInGroup()` call names the literal group 'viewers', which
 * `good/lib/Settings/items-register.json` declares in its authorization
 * block — so group-declared also reports zero findings for this fixture.
 *
 * SPDX-License-Identifier: EUPL-1.2
 * SPDX-FileCopyrightText: 2026 Conduction B.V.
 */

declare(strict_types=1);

namespace OCA\FixtureApp\Service;

use OCP\IGroupManager;
use OCP\IUser;

class RoleService {
	public function __construct(
		private readonly IGroupManager $groupManager,
	) {
	}

	public function resolvePrimaryRole(IUser $user): string {
		if ($this->groupManager->isAdmin($user->getUID()) === true) {
			return 'admin';
		}

		if ($this->groupManager->isInGroup($user->getUID(), 'viewers') === true) {
			return 'viewer';
		}

		return 'viewer';
	}
}

class PageController {
	public function __construct(
		private readonly RoleService $roleService,
	) {
	}

	public function index($initialState, IUser $user): void {
		$initialState->provideInitialState('primaryRole', $this->roleService->resolvePrimaryRole($user));
	}
}
