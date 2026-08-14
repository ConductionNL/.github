<?php
/**
 * @license EUPL-1.2
 * @copyright Conduction B.V.
 *
 * PLANT 3 of 3 (the route half) — ADR-083 rule 3.
 *
 * This controller serves `/` (see appinfo/routes.php) and injects StatsService,
 * which injects OpenRegister's ObjectService. Without OpenRegister the
 * container cannot construct this controller, so the start screen 500s instead
 * of rendering the prompt that would tell the admin to install it.
 *
 * Measured on the real fleet 2026-08-14: hermiq's DashboardController does this
 * — it publishes `opencatalogi_available` AND injects
 * OCA\OpenRegister\Db\OrganisationMapper. The app most likely to have got this
 * right had not.
 */

namespace OCA\OrDepFixture\Controller;

use OCA\OrDepFixture\Service\StatsService;
use OCP\App\IAppManager;
use OCP\AppFramework\Services\IInitialState;

class PageController {

	public function __construct(
		private readonly IAppManager $appManager,
		private readonly IInitialState $initialState,
		private readonly StatsService $stats,
	) {
	}

	public function index(): void {
		$this->initialState->provideInitialState(
			'openregister_available',
			$this->appManager->isInstalled('openregister')
		);
	}
}
