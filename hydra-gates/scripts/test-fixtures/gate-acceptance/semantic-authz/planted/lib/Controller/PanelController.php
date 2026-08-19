<?php
/**
 * Panel controller.
 *
 * @license  EUPL-1.2
 * @copyright 2026 Conduction B.V.
 */

namespace OCA\SemAuthzFx\Controller;

use OCP\AppFramework\Controller;
use OCP\AppFramework\Http\JSONResponse;

/**
 * The gate-9 mechanism, and nothing else.
 */
class PanelController extends Controller
{

    /**
     * Reads the admin panel state.
     *
     * @NoAdminRequired
     *
     * @return JSONResponse
     *
     * @throws \Throwable
     */
    public function adminPanelState(): JSONResponse
    {
        $this->requireAdmin();
        return new JSONResponse(['state' => 'ok']);

    }//end adminPanelState()


}//end class
