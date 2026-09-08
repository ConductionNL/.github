<?php
/**
 * Nested thing controller.
 *
 * @license  EUPL-1.2
 * @copyright 2026 Conduction B.V.
 */

namespace OCA\GlobRecFx\Controller\Api\V1;

use OCP\AppFramework\Controller;
use OCP\AppFramework\Http\JSONResponse;

/**
 * Carries two defects at once, three directories below lib/Controller/.
 */
class NestedThingController extends Controller
{


    /**
     * Reads one object by id, for any authenticated user, with no guard.
     *
     * The classic IDOR: the id comes from the request and nothing checks that
     * the acting user may see it. gate-7's subject.
     *
     * @NoAdminRequired
     *
     * @param string $id The object id, straight from the URL.
     *
     * @return JSONResponse
     */
    public function show(string $id): JSONResponse
    {
        return new JSONResponse(['id' => $id, 'secret' => 'exposed']);

    }//end show()


    /**
     * Reads admin state behind an annotation that contradicts the body.
     *
     * The attribute says any authenticated user; the body requires an admin.
     * gate-9's subject: the mismatch, not either half alone.
     *
     * @NoAdminRequired
     *
     * @return JSONResponse
     */
    public function adminState(): JSONResponse
    {
        $this->requireAdmin();
        return new JSONResponse(['state' => 'ok']);

    }//end adminState()


}//end class
