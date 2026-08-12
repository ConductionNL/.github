<?php
/**
 * Transition service.
 *
 * @license  EUPL-1.2
 * @copyright 2026 Conduction B.V.
 */

namespace OCA\SemAuthzFx\Service;

/**
 * Holds one access-control predicate and one reference-data predicate.
 *
 * The two differ ONLY in whether they carry an authorisation-domain signal:
 * isTransitionAllowed takes a subject parameter and its name carries the
 * `Allowed` token; isValidCode takes a bare string and carries neither.
 * Both are uncalled, in both arms.
 */
class TransitionService
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


    /**
     * Reference-data lookup. Not an access control.
     *
     * @param string $code The code to look up.
     *
     * @return boolean
     */
    public function isValidCode(string $code): bool
    {
        return (strlen($code) === 4);

    }//end isValidCode()


}//end class
