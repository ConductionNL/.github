<?php
/**
 * Nested orphan handler.
 *
 * @license  EUPL-1.2
 * @copyright 2026 Conduction B.V.
 */

namespace OCA\GlobRecFx\Service\Object;

/**
 * One access-control predicate that nothing calls, at depth.
 *
 * A defined-but-uncalled authorisation method is identical to having no check
 * at all (OWASP A01:2021). gate-6 finds it only if it opens this file.
 */
class NestedOrphanHandler
{


    /**
     * Decides whether a user may move a record into a state.
     *
     * @param string $userId The acting user.
     * @param string $state  The target state.
     *
     * @return boolean
     */
    public function isTransitionAllowed(string $userId, string $state): bool
    {
        return ($userId !== '' && $state !== '');

    }//end isTransitionAllowed()


}//end class
