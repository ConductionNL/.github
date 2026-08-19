<?php
/**
 * Transition coordinator.
 *
 * @license  EUPL-1.2
 * @copyright 2026 Conduction B.V.
 */

namespace OCA\SemAuthzFx\Service;

/**
 * The caller seam. In the planted arm moveTo() does the state change WITHOUT
 * consulting the guard; here the same method consults it. Nothing else about
 * the two arms differs, so this pair tests whether gate-6 reads CALLERS and
 * not merely whether it can see a guard-shaped method.
 */
class TransitionCoordinator
{

    /**
     * @var TransitionService
     */
    private TransitionService $transitions;


    /**
     * Constructor.
     *
     * @param TransitionService $transitions The guard holder.
     */
    public function __construct(TransitionService $transitions)
    {
        $this->transitions = $transitions;

    }//end __construct()


    /**
     * Moves a record into a state.
     *
     * @param string $userId The acting user.
     * @param string $state  The target state.
     *
     * @return boolean
     */
    public function moveTo(string $userId, string $state): bool
    {
        if ($this->transitions->isTransitionAllowed($userId, $state) === false) {
            return false;
        }

        return ($state !== '');

    }//end moveTo()


}//end class
