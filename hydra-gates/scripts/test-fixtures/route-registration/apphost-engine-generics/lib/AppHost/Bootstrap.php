<?php
// SPDX-License-Identifier: EUPL-1.2
declare(strict_types=1);

namespace OCA\Fixture\AppHost;

// THE ENGINE MARKER. A leaf app imports `OCA\OpenRegister\AppHost\Bootstrap`
// and calls `Bootstrap::register()`; only the engine ships this file. Its
// presence, as a class named Bootstrap with a register() method, is what
// makes lib/AppHost/Controller/Generic* a library here rather than this
// app's unrouted endpoints.
class Bootstrap
{
    public static function register($context, array $options = []): void
    {
        // Binds the generics in the leaf's container; the leaf names their
        // routes through Routes::standard().
    }
}
