<?php
// SPDX-License-Identifier: EUPL-1.2
declare(strict_types=1);

namespace OCA\Fixture\AppHost\Controller;

// The generic the engine ships for its leaf apps and does NOT route itself.
// In the engine (`apphost-engine-generics/`, lib/AppHost/Bootstrap.php present)
// this is a library class and NOT a finding; in a leaf that merely copied it
// (`apphost-engine-generics-leaf/`, no Bootstrap.php) both methods ARE.
class GenericDashboardController extends Controller
{
    #[NoAdminRequired]
    public function page(): TemplateResponse
    {
        return new TemplateResponse('fixture', 'index');
    }

    #[NoAdminRequired]
    public function catchAll(string $path): TemplateResponse
    {
        return new TemplateResponse('fixture', 'index');
    }
}
