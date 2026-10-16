<?php
/**
 * Gate-64 fixture. Not a real app.
 *
 * @license  EUPL-1.2
 * @copyright 2026 Conduction B.V.
 */

declare(strict_types=1);

namespace OCA\LarpinqShape\AppInfo;

final class OpenRegisterAutoloader {
	private const OPENREGISTER_NAMESPACE = 'OCA\\OpenRegister\\';

	private static ?\Closure $loader = null;

	public static function register(?string $appId = null, ?\OCP\App\IAppManager $appManager = null): void {
		try {
			$appId ??= 'openregister';
			$appManager ??= \OCP\Server::get(\OCP\App\IAppManager::class);

			if (self::$loader !== null) {
				return;
			}

			$path = rtrim($appManager->getAppPath($appId), '/');
			self::$loader = static function (string $class) use ($path): void {
				if (str_starts_with($class, self::OPENREGISTER_NAMESPACE) === true) {
					require_once $path.'/lib/'.str_replace('\\', '/', substr($class, strlen(self::OPENREGISTER_NAMESPACE))).'.php';
				}
			};
			spl_autoload_register(self::$loader);
		} catch (\Throwable) {
		}
	}
}
