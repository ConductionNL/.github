<?php
// SPDX-License-Identifier: EUPL-1.2

namespace OCA\Fixture\Controller;

use OCP\AppFramework\Controller;
use OCP\AppFramework\Http\JSONResponse;
use OCP\AppFramework\Http\Attribute\AuthorizedAdminSetting;
use OCA\Fixture\AppInfo\Application;

/**
 * Fixture controller — the routed method's auth attribute is REAL, spans
 * three lines, and sits above twenty-nine lines of ordinary docblock.
 *
 * Before ConductionNL/.github#423 the contiguous annotation run broke at the
 * `)]` line and the 20-line slice no longer reached the `#[`, so this file
 * FAILED gate-5 while a byte-identical file with a two-line docblock PASSED.
 * The gate was reading the length of the explanation as the absence of the
 * attribute.
 */
class SettingsController extends Controller
{
    #[AuthorizedAdminSetting(
        Application::APP_ID
    )]
    /**
     * Save the admin settings.
     *
     * Line 1 of an ordinary explanation: what this endpoint validates,
     * which ADR it implements, and why the register is optional here.
     * Line 2 of an ordinary explanation: what this endpoint validates,
     * which ADR it implements, and why the register is optional here.
     * Line 3 of an ordinary explanation: what this endpoint validates,
     * which ADR it implements, and why the register is optional here.
     * Line 4 of an ordinary explanation: what this endpoint validates,
     * which ADR it implements, and why the register is optional here.
     * Line 5 of an ordinary explanation: what this endpoint validates,
     * which ADR it implements, and why the register is optional here.
     * Line 6 of an ordinary explanation: what this endpoint validates,
     * which ADR it implements, and why the register is optional here.
     * Line 7 of an ordinary explanation: what this endpoint validates,
     * which ADR it implements, and why the register is optional here.
     * Line 8 of an ordinary explanation: what this endpoint validates,
     * which ADR it implements, and why the register is optional here.
     * Line 9 of an ordinary explanation: what this endpoint validates,
     * which ADR it implements, and why the register is optional here.
     * Line 10 of an ordinary explanation: what this endpoint validates,
     * which ADR it implements, and why the register is optional here.
     * Line 11 of an ordinary explanation: what this endpoint validates,
     * which ADR it implements, and why the register is optional here.
     * Line 12 of an ordinary explanation: what this endpoint validates,
     * which ADR it implements, and why the register is optional here.
     * Line 13 of an ordinary explanation: what this endpoint validates,
     * which ADR it implements, and why the register is optional here.
     */
    public function save(array $data): JSONResponse
    {
        return new JSONResponse($data);
    }
}
