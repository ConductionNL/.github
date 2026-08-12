<?php
/**
 * Panel controller.
 *
 * @license  EUPL-1.2
 * @copyright 2026 Conduction B.V.
 */

namespace OCA\SemAuthzFx\Controller;

use OCA\SemAuthzFx\AppInfo\Application;
use OCP\AppFramework\Controller;
use OCP\AppFramework\Http;
use OCP\AppFramework\Http\JSONResponse;
use OCP\AppFramework\Http\Attribute\AuthorizedAdminSetting;
use OCP\AppFramework\Http\Attribute\PublicPage;

/**
 * The clean arm of the gate-9 pair, plus the near-miss.
 */
class PanelController extends Controller
{

    /**
     * Reads the admin panel state.
     *
     * The body is byte-identical to the planted arm's. Only the attribute
     * moved, which is what makes this pair a test of the SEMANTIC match
     * rather than of whether the gate can find requireAdmin().
     *
     * @return JSONResponse
     *
     * @throws \Throwable
     */
    #[AuthorizedAdminSetting(Application::APP_ID)]
    public function adminPanelState(): JSONResponse
    {
        $this->requireAdmin();
        return new JSONResponse(['state' => 'ok']);

    }//end adminPanelState()


    /**
     * A genuinely public endpoint that authenticates its caller from the
     * REQUEST rather than from the session, and denies when it cannot.
     *
     * This is the anti-widening near-miss. It is #[PublicPage] and it
     * returns 401, which is the shape gate-9's unsourced-denial rule reports
     * — but the credential is resolved here, in code, so the rule must stay
     * silent. A gate-9 that stopped reading the credential surface, or that
     * went back to earning the exemption from a docblock, turns THIS arm red.
     *
     * @return JSONResponse
     *
     * @throws \Throwable
     */
    #[PublicPage]
    public function ingest(): JSONResponse
    {
        $presentedToken = $this->request->getHeader('Authorization');
        if ($presentedToken === '') {
            return new JSONResponse([], Http::STATUS_UNAUTHORIZED);
        }

        return new JSONResponse(['accepted' => true]);

    }//end ingest()


}//end class
