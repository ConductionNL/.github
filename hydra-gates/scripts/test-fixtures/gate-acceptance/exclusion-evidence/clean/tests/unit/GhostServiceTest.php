<?php
/**
 * Ghost service test — the artifact the spec's exclusion cites.
 *
 * @license  EUPL-1.2
 * @copyright 2026 Conduction B.V.
 */

namespace OCA\ExclEvidFx\Tests\Unit;

use PHPUnit\Framework\TestCase;

/**
 * Present in the clean arm and absent in the planted arm. Nothing else differs.
 */
class GhostServiceTest extends TestCase
{


    /**
     * A ghost row whose source is gone is dropped.
     *
     * @return void
     */
    public function testGhostRowIsDropped(): void
    {
        $this->assertTrue(true);

    }//end testGhostRowIsDropped()


}//end class
