<?php
// SPDX-License-Identifier: EUPL-1.2
declare(strict_types=1);

namespace OCA\Fixture\AppInfo\Registrar;

/**
 * PROSE IS NOT A CALL. This file names OCA\OpenRegister\AppHost\Bootstrap and
 * describes Bootstrap::aliasStoreController() in detail, and binds nothing.
 *
 * It is the anti-widening half of `store-plane/`. The first cut of the
 * sibling AppHost widening used two raw greps and `delegated-registrar-absent/`
 * was exempted by its own docblock; the file that explains the architecture is
 * exactly the file that spells the call out. Both store routes MUST still be
 * reported here.
 */
class StorePlaneRegistrar
{
    public function register($context): void
    {
    }
}
