<?php

/**
 * Static-analysis stub for OpenRegister's AppHost composition-root entry point.
 *
 * ANALYSIS-ONLY. Nothing autoloads or executes this file. It is referenced by
 * name from a consuming app's `psalm.xml` `<stubs>` and, where the app needs it,
 * from `phpstan.neon` `scanFiles`.
 *
 * It is deliberately NOT in `hydra-gates/contracts/`. Those two interfaces are
 * `require`d for real by a leaf app's PHPUnit bootstrap, and one of them is
 * documented for a phpstan `scanDirectories` over the whole directory. A file
 * that must never be loaded does not belong in a directory apps are told to load
 * wholesale.
 *
 * WHY IT EXISTS. `openregister` is a sibling Nextcloud app, not a composer
 * dependency, so `OCA\OpenRegister\AppHost\Bootstrap` genuinely is absent from
 * a leaf app's analysis path. Three apps, decidiq, filinq and planninq, adopted
 * the shared AppHost route table. It declares `/api/store/items` whether the app
 * wants it or not, so each of them binds the controller the same way:
 *
 *     if (class_exists(Bootstrap::class) === true) {
 *         Bootstrap::aliasStoreController(context: $context, ...);
 *     }
 *
 * With the class unresolvable, psalm decides the guarded block is dead and
 * reports `UnusedParam: Param context is never referenced in this method` about a
 * parameter that is passed on the very next line. Two of the three were red on
 * `development` for exactly this.
 *
 * A `@psalm-suppress` would hide the finding, and it would hide the next genuine
 * unused parameter in the same method too. A stub answers the real question,
 * which is what this class is, and leaves the call type-checked.
 *
 * DRIFT IS THE COST. Every signature below is mirrored from
 * `openregister/lib/AppHost/Bootstrap.php`. Only the public surface is stubbed;
 * the private constants and helpers are the engine's business. When the engine
 * changes a public signature, change this file with it. A stub that disagrees
 * with the engine is worse than no stub, because it makes a wrong call look
 * checked.
 *
 * @license   EUPL-1.2 https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12
 * @copyright 2026 Conduction B.V.
 *
 * SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl>
 * SPDX-License-Identifier: EUPL-1.2
 */

declare(strict_types=1);

namespace OCA\OpenRegister\AppHost;

use OCP\AppFramework\Bootstrap\IRegistrationContext;

/**
 * Declarative one-call bootstrap for AppHost leaf apps (ADR-040).
 *
 * Analysis-only stub. Mirrored from openregister/lib/AppHost/Bootstrap.php.
 */
class Bootstrap {

	/**
	 * Register all standard AppHost plumbing for a leaf app.
	 *
	 * @param IRegistrationContext $context The leaf app's registration context.
	 * @param string               $appId   The leaf app id.
	 * @param array<string, mixed> $options Optional overrides, documented on the engine.
	 *
	 * @return void
	 */
	public static function register(IRegistrationContext $context, string $appId, array $options = []): void {
	}//end register()

	/**
	 * Bind the store controller the shared route table already declares.
	 *
	 * For a leaf that composes its own registrars instead of calling
	 * `register()`, this is the one binding it still has to make: without it
	 * `/api/store/items` matches a controller class that does not exist and
	 * every request to it returns HTTP 500 rather than 404.
	 *
	 * @param IRegistrationContext $context      The leaf app's registration context.
	 * @param string               $appId        The leaf app id.
	 * @param string               $controllerNs The leaf's controller namespace.
	 *
	 * @return void
	 */
	public static function aliasStoreController(IRegistrationContext $context, string $appId, string $controllerNs): void {
	}//end aliasStoreController()
}//end class
