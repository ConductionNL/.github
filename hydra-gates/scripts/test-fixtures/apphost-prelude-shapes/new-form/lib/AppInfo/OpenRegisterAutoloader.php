<?php
/**
 * Gate-64 fixture. Not a real app.
 *
 * @license  EUPL-1.2
 * @copyright 2026 Conduction B.V.
 */

declare(strict_types=1);

namespace OCA\NewForm\AppInfo;

final class OpenRegisterAutoloader {
	private const OPENREGISTER_NAMESPACE = 'OCA\\OpenRegister\\';

	public static function register(): void {
		try {
			$path = rtrim(\OCP\Server::get(\OCP\App\IAppManager::class)->getAppPath('openregister'), '/');
			spl_autoload_register(static function (string $class) use ($path): void {
				if (str_starts_with($class, self::OPENREGISTER_NAMESPACE) === true) {
					require_once $path.'/lib/'.str_replace('\\', '/', substr($class, strlen(self::OPENREGISTER_NAMESPACE))).'.php';
				}
			});
		} catch (\Throwable) {
		}
	}
}
