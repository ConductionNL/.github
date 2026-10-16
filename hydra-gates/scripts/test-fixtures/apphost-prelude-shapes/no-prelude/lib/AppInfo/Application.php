<?php
/**
 * Gate-64 fixture. Not a real app.
 *
 * @license  EUPL-1.2
 * @copyright 2026 Conduction B.V.
 */

declare(strict_types=1);

namespace OCA\NoPrelude\AppInfo;

use OCA\OpenRegister\AppHost\Bootstrap;
use OCP\AppFramework\Bootstrap\IRegistrationContext;

class Application {
	public function register(IRegistrationContext $context): void {
		if (class_exists(Bootstrap::class) === true) {
			Bootstrap::aliasStoreController(context: $context, appId: 'noprelude', controllerNs: 'OCA\\NoPrelude\\Controller');
		}
	}
}
