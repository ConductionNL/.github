<?php

declare(strict_types=1);

namespace Fixture;

// No test loads this file: it must be in the merged report as uncovered.
final class Gamma
{
    public function unused(): int
    {
        $value = 42;

        return $value;
    }
}
