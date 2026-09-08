<?php
/**
 * Nested stub job.
 *
 * @license  EUPL-1.2
 * @copyright 2026 Conduction B.V.
 */

namespace OCA\GlobRecFx\BackgroundJob\Nested;

use OCP\BackgroundJob\TimedJob;

/**
 * A scheduled job whose run() does nothing, two directories down.
 *
 * It is registered, it fires, and it has no effect. gate-3's subject.
 */
class NestedStubJob extends TimedJob
{


    /**
     * Runs the job.
     *
     * @param mixed $argument The job argument.
     *
     * @return void
     */
    protected function run($argument): void
    {
        // In a complete implementation this would reconcile the nested
        // objects. Nothing happens here.

    }//end run()


}//end class
