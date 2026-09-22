<?php
// SPDX-License-Identifier: EUPL-1.2
declare(strict_types=1);

namespace OCA\Fixture\AppInfo;

use OCA\Fixture\AppInfo\Registrar\StorePlaneRegistrar;

class Application
{
    public function register($context): void
    {
        (new StorePlaneRegistrar())->register(context: $context);
    }
}
