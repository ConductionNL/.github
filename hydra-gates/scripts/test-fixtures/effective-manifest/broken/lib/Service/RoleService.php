<?php

/**
 * gate-30 fixture — role-resolvable + group-declared, ONE seeded defect each.
 *
 * Defect 1 (role-resolvable): `broken/src/manifest.json`'s zaken-index-entry
 * gates on `["admin", "auditor"]`, but this resolver can only ever emit
 * "admin" or "behandelaar" — "auditor" is a literal the resolver can never
 * produce, the exact defect class fix-dead-role-gates exists to catch.
 *
 * Defect 2 (group-declared): the `isInGroup()` call below names the literal
 * group 'undeclared-auditors', which `broken/lib/Settings/zaken-register.json`
 * declares nowhere (its only authorization-bearing group is implicit and
 * unrelated) — the mirror-image defect: a role that can never be granted.
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

		if ($this->groupManager->isInGroup($user->getUID(), 'undeclared-auditors') === true) {
			return 'behandelaar';
		}

		return 'behandelaar';
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
