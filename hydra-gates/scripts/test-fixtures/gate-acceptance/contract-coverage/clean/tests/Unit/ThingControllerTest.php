<?php

namespace OCA\Fx25\Tests\Unit;

use PHPUnit\Framework\TestCase;

class ThingControllerTest extends TestCase {
    public function testListThings(): void {
        $c = new \OCA\Fx25\Controller\ThingController();
        $this->assertSame([], $c->listThings());
    }

    public function testFarAttribute(): void {
        $c = new \OCA\Fx25\Controller\ThingController();
        $this->assertSame([], $c->farAttribute());
    }
}
