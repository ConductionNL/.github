<?php
// SPDX-License-Identifier: EUPL-1.2
declare(strict_types=1);

namespace OCA\Fixture\AppInfo\Registrar;

use OCA\OpenRegister\AppHost\Bootstrap;

/**
 * THE ONE FILE THIS FIXTURE PAIR DIFFERS BY. Its sibling
 * `store-plane-absent/` is identical apart from this call living in a
 * docblock instead of in code, and there gate-14 must report both store
 * routes.
 *
 * Note this app does NOT call Bootstrap::register(): that helper also
 * re-binds SettingsService and the admin settings, which an app binding its
 * own controllers by hand must not take.
 */
class StorePlaneRegistrar
{
    public function register($context): void
    {
        Bootstrap::aliasStoreController(
            context: $context,
            appId: 'fixture',
            controllerNs: 'OCA\\Fixture\\Controller'
        );
    }
}
