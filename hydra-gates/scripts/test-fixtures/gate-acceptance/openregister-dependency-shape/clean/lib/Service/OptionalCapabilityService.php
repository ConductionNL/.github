<?php
/**
 * @license EUPL-1.2
 * @copyright Conduction B.V.
 *
 * NEGATIVE CONTROL — an availability-guarded lookup, which is CORRECT.
 *
 * This file contains the exact construct planted/LookupService.php is reported
 * for, and it must NOT be reported here, because the reach is behind an
 * `isInstalled('openregister')` check and the method returns a clean answer
 * when the app is absent.
 *
 * Converting this to constructor injection would be a REGRESSION: the service
 * would stop being constructable on an instance without OpenRegister, and the
 * message below would become a 500 — the failure ADR-083 rule 3 exists to
 * prevent. Measured on portaliq 2026-08-14, and it is what stopped a
 * fleet-wide script from running over 1,263 call sites.
 *
 * If the lookup check ever loses its availability clause, this arm goes red.
 */

namespace OCA\OrDepFixture\Service;

use OCP\App\IAppManager;
use Psr\Container\ContainerInterface;

class OptionalCapabilityService {

	public function __construct(
		private readonly IAppManager $appManager,
		private readonly ContainerInterface $container,
	) {
	}

	public function isOpenRegisterAvailable(): bool {
		return $this->appManager->isInstalled('openregister');
	}

	public function importConfiguration(): array {
		if ($this->isOpenRegisterAvailable() === false) {
			return [
				'success' => false,
				'message' => 'OpenRegister is not installed or enabled.',
			];
		}

		$configurationService = $this->container->get('OCA\OpenRegister\Service\ConfigurationService');

		return $configurationService->importFromApp();
	}
}
