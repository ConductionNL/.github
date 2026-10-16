<?php
/**
 * Gate-64 fixture: decidiq lib/AppInfo at 03fdb9de, docblocks and line
 * comments removed, code unchanged.
 *
 * @license  EUPL-1.2
 * @copyright 2026 Conduction B.V.
 */

declare(strict_types=1);

namespace OCA\Decidiq\AppInfo;

final class OpenRegisterAutoloader {

	private const OPENREGISTER_APP_ID = 'openregister';

	private const OPENREGISTER_NAMESPACE = 'OCA\\OpenRegister\\';

	private static ?\Closure $loader = null;

	public static function register(?\OCP\App\IAppManager $appManager=null): bool {
		try {
			$appManager ??= \OCP\Server::get(\OCP\App\IAppManager::class);

			if ($appManager->isEnabledForAnyone(self::OPENREGISTER_APP_ID) === false) {
				self::unregister();
				return false;
			}

			if (self::$loader !== null) {
				return true;
			}

			$path = rtrim($appManager->getAppPath(self::OPENREGISTER_APP_ID), '/');
			if (is_dir($path.'/lib') === false) {
				return false;
			}

			self::$loader = static function (string $class) use ($path): void {
				$file = self::classFile(appPath: $path, class: $class);
				if ($file !== null && is_file($file) === true) {
					require_once $file;
				}
			};
			spl_autoload_register(self::$loader);

			return true;
		} catch (\Throwable) {
			return false;
		}//end try

	}//end register()

	public static function unregister(): void {
		if (self::$loader !== null) {
			spl_autoload_unregister(self::$loader);
			self::$loader = null;
		}

	}//end unregister()

	public static function classFile(string $appPath, string $class): ?string {
		if (str_starts_with($class, self::OPENREGISTER_NAMESPACE) === false) {
			return null;
		}

		$relative = substr($class, strlen(self::OPENREGISTER_NAMESPACE));
		if ($relative === '') {
			return null;
		}

		return $appPath.'/lib/'.str_replace('\\', '/', $relative).'.php';

	}//end classFile()
}//end class
