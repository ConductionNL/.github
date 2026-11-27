<?php

declare(strict_types=1);

namespace Fixture;

// Each test file covers one branch, so only a merge of both shards covers both.
final class Beta
{
    public function parity(int $n): string
    {
        if ($n % 2 === 0) {
            $word = 'even';
        } else {
            $word = 'odd';
        }

        return $word;
    }
}
