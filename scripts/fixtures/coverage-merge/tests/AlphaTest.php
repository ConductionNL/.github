<?php

declare(strict_types=1);

namespace Fixture\Tests;

use Fixture\Alpha;
use Fixture\Beta;
use PHPUnit\Framework\TestCase;

final class AlphaTest extends TestCase
{
    public function testAdd(): void
    {
        $this->assertSame(5, (new Alpha())->add(2, 3));
    }

    public function testEven(): void
    {
        $this->assertSame('even', (new Beta())->parity(2));
    }
}
