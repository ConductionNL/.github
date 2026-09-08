<?php
/**
 * Permission handler.
 *
 * @license  EUPL-1.2
 * @copyright 2026 Conduction B.V.
 */

namespace OCA\GlobRecFx\Service\Object;

/**
 * The real CWE-863 shape gate-8 missed for months in openregister, at the
 * depth it missed it: lib/Service/Object/, one level below the directory a
 * non-recursive `lib/Service/*.php` glob enumerates.
 */
class PermissionHandler
{


    /**
     * Resolves the authorization service.
     *
     * Fails open: an unavailable service is indistinguishable from an allowed
     * action once the caller treats null as "no check to run".
     *
     * @return object|null
     */
    private function getAuthorizationService(): ?object
    {
        try {
            return \OC::$server->get('OCA\\GlobRecFx\\Service\\AuthorizationService');
        } catch (\Throwable) {
            return null;
        }

    }//end getAuthorizationService()


    /**
     * Decides whether the acting user may write the object.
     *
     * @param string $userId   The acting user.
     * @param string $objectId The object.
     *
     * @return boolean
     */
    public function mayWrite(string $userId, string $objectId): bool
    {
        $auth = $this->getAuthorizationService();
        if ($auth !== null) {
            return $auth->check($userId, $objectId);
        }

        return true;

    }//end mayWrite()


}//end class
