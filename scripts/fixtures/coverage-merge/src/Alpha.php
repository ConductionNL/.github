<?php

declare(strict_types=1);

namespace Fixture;

// Covered by AlphaTest only.
final class Alpha
{
    public function add(int $a, int $b): int
    {
        return $a + $b;
    }

    public function never(): string
    {
        return 'not covered by any test';
    }
}
