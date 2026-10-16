<?php
/**
 * Gate-64 fixture. Not a real app.
 *
 * @license  EUPL-1.2
 * @copyright 2026 Conduction B.V.
 */

declare(strict_types=1);

namespace OCA\LarpinqShape\AppInfo;

use OCA\OpenRegister\AppHost\Bootstrap;
use OCP\AppFramework\Bootstrap\IRegistrationContext;

class Application {
	public function register(IRegistrationContext $context): void {
		OpenRegisterAutoloader::register();

		if (class_exists(Bootstrap::class) === true) {
			Bootstrap::aliasStoreController(
				context: $context,
				appId: 'leaf',
				controllerNs: 'OCA\\LarpinqShape\\Controller'
			);
		}
	}
}
