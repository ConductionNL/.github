<?php
// SPDX-License-Identifier: EUPL-1.2
declare(strict_types=1);

namespace OCA\Fixture\Controller;

// Routed, conventional — the control that the engine's own endpoints are
// still enumerated and still judged.
class PingController extends Controller
{
    #[PublicPage]
    public function index(): JSONResponse
    {
        return new JSONResponse(['pong' => true]);
    }
}
