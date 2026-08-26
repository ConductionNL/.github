<?php

/**
 * SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl>
 * SPDX-License-Identifier: EUPL-1.2
 *
 * PERMITTED, and present in BOTH arms on purpose.
 *
 * A migration seeding the app's own shipped registers has no user to act for:
 * nobody is present. If the gate flagged this too, the planted arm would pass
 * for the wrong reason and the rule would read as "never elevate", which is
 * not the rule.
 */

declare(strict_types=1);

namespace OCA\Fixture\Migration;

class SeedShippedRegisters {

	public function run(): void {
		$this->objectService->runAsSystem(
			static fn (): bool => true
		);
	}
}
