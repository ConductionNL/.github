<?php

declare(strict_types=1);

namespace Fixture\Tests;

use Fixture\Beta;
use PHPUnit\Framework\TestCase;

final class BetaTest extends TestCase
{
    public function testOdd(): void
    {
        $this->assertSame('odd', (new Beta())->parity(3));
    }
}
