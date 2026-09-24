<?php
// SPDX-License-Identifier: EUPL-1.2
declare(strict_types=1);

namespace OCA\Fixture\AppInfo\Registrar;

// A stale import: nothing below calls the engine's Bootstrap.
use OCA\OpenRegister\AppHost\Bootstrap;

class StorePlaneRegistrar
{
    public function register($context): void
    {
        $this->aliasStoreController(context: $context);
    }

    private function aliasStoreController($context): void
    {
    }
}
