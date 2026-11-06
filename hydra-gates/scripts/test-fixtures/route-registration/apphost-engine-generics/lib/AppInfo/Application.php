<?php
// SPDX-License-Identifier: EUPL-1.2
declare(strict_types=1);

namespace OCA\Fixture\AppInfo;

// Binds the ONE generic this app routes itself, as the engine does for its
// health and metrics endpoints; the resolver maps the namespaced route name
// to lib/AppHost/Controller/ through this binding.
class Application
{
    public function register($context): void
    {
        $context->registerService(
            'AppHost\\Controller\\GenericHealthController',
            static fn ($c) => new \OCA\Fixture\AppHost\Controller\GenericHealthController()
        );
    }
}
