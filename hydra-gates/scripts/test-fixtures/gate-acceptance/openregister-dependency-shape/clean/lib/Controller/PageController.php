<?php
/**
 * @license EUPL-1.2
 * @copyright Conduction B.V.
 *
 * The conforming default route (ADR-083 rule 3).
 *
 * Core dependencies only — IAppManager and IInitialState — so the container can
 * construct it on an instance where OpenRegister is not installed. It publishes
 * availability and lets the frontend render an install prompt instead of a 500.
 *
 * StatsService still exists in this arm and still injects ObjectService. That is
 * the point: rule 3 is about what the START SCREEN reaches, not about banning
 * the dependency. A checker that flagged the app for merely CONTAINING an
 * OpenRegister-dependent service would fail this arm.
 */

namespace OCA\OrDepFixture\Controller;

use OCP\App\IAppManager;
use OCP\AppFramework\Services\IInitialState;

class PageController {

	public function __construct(
		private readonly IAppManager $appManager,
		private readonly IInitialState $initialState,
	) {
	}

	public function index(): void {
		$this->initialState->provideInitialState(
			'openregister_available',
			$this->appManager->isInstalled('openregister')
		);
	}
}
