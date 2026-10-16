<?php
/**
 * Gate-64 fixture: decidiq lib/AppInfo at 03fdb9de, docblocks and line
 * comments removed, code unchanged.
 *
 * @license  EUPL-1.2
 * @copyright 2026 Conduction B.V.
 */

declare(strict_types=1);

namespace OCA\Decidiq\AppInfo\Registrar;

use OCA\Decidiq\AppInfo\Application;
use OCA\Decidiq\AppInfo\OpenRegisterAutoloader;
use OCA\OpenRegister\AppHost\Bootstrap;
use OCA\OpenRegister\Event\DeepLinkRegistrationEvent;
use OCP\App\IAppManager;
use OCP\AppFramework\Bootstrap\IRegistrationContext;
use Psr\Log\LoggerInterface;

class AppHostRegistrar {

	private const DEEP_LINK_LISTENER = 'OCA\\OpenRegister\\AppHost\\Listener\\GenericDeepLinkRegistrationListener';

	public const DEEP_LINK_LISTENER_SERVICE = 'OCA\\Decidiq\\Listener\\DeepLinkRegistrationListener';

	public function register(IRegistrationContext $context): void {
		$context->registerService(
			self::DEEP_LINK_LISTENER_SERVICE,
			static function ($c): object {
				$class = self::DEEP_LINK_LISTENER;
				return new $class(
					appId: Application::APP_ID,
					appManager: $c->get(IAppManager::class),
					logger: $c->get(LoggerInterface::class),
				);
			}
		);

		$listenerClass = self::DEEP_LINK_LISTENER_SERVICE;
		$context->registerEventListener(event: DeepLinkRegistrationEvent::class, listener: $listenerClass);

		$this->bindStoreController(context: $context);

	}//end register()

	private function bindStoreController(IRegistrationContext $context): void {
		OpenRegisterAutoloader::register();

		if (class_exists(Bootstrap::class) === true) {
			try {
				Bootstrap::aliasStoreController(
					context: $context,
					appId: Application::APP_ID,
					controllerNs: 'OCA\\Decidiq\\Controller'
				);
			} catch (\Throwable) {
			}
		}

	}//end bindStoreController()
}//end class
