<?php
/**
 * Gate-64 fixture. Not a real app.
 *
 * @license  EUPL-1.2
 * @copyright 2026 Conduction B.V.
 */

declare(strict_types=1);

namespace OCA\OldForm\AppInfo;

use OCA\OpenRegister\AppHost\Bootstrap;
use OCP\AppFramework\Bootstrap\IRegistrationContext;

class Application {
	public function register(IRegistrationContext $context): void {
		try {
			$orPath = \OCP\Server::get(\OCP\App\IAppManager::class)->getAppPath('openregister');
			\OC_App::registerAutoloading('openregister', $orPath);
		} catch (\Throwable) {
		}

		Bootstrap::aliasStoreController(context: $context, appId: 'oldform', controllerNs: 'OCA\\OldForm\\Controller');
	}
}
