<?php
// SPDX-License-Identifier: EUPL-1.2
declare(strict_types=1);

namespace OCA\Fixture\Controller;

class SettingsController extends Controller
{
    #[NoAdminRequired]
    public function index(): JSONResponse
    {
        return new JSONResponse([]);
    }

    #[AuthorizedAdminSetting(Application::APP_ID)]
    public function create(): JSONResponse
    {
        return new JSONResponse([]);
    }

    #[AuthorizedAdminSetting(Application::APP_ID)]
    public function load(): JSONResponse
    {
        return new JSONResponse([]);
    }
}
