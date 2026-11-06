<?php
// SPDX-License-Identifier: EUPL-1.2
declare(strict_types=1);

namespace OCA\Fixture\Controller;

// NO route anywhere. MUST be reported in both fixtures of the pair.
class GadgetController extends Controller
{
    public function run(): JSONResponse
    {
        return new JSONResponse(['ran' => true]);
    }
}
