<?php
/**
 * Transition coordinator.
 *
 * @license  EUPL-1.2
 * @copyright 2026 Conduction B.V.
 */

namespace OCA\SemAuthzFx\Service;

/**
 * The caller seam. In the planted arm it does the state change WITHOUT
 * consulting the guard; in the clean arm the same method consults it.
 * Nothing else about the two arms differs.
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
        return ($state !== '');

    }//end moveTo()


}//end class
