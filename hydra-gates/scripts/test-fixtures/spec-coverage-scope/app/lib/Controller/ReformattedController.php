<?php
/**
 * SPDX-FileCopyrightText: 2026 Conduction
 * SPDX-License-Identifier: EUPL-1.2
 *
 * THE BEFORE SIDE OF A CODING-STANDARD REFORMAT (.github#395).
 *
 * Written in the style the fleet is migrating AWAY from: Allman braces, four
 * spaces, a double-quoted literal, no trailing comma in the multi-line
 * parameter list, and one long expression on a single line.
 *
 * Neither method carries an `@spec` tag, deliberately. That is what makes the
 * reformat arms falsifiable: if brace style counts as a change, both methods
 * become findings on a diff that changed nothing a user or a caller can see —
 * measured as 185 findings on ConductionNL/procest#819.
 *
 * The `.knr` sibling is this same file after php-cs-fixer; the `.knr-changed`
 * sibling is that reformat PLUS one genuinely altered operator, which must
 * still be reported through the normalisation.
 */

namespace OCA\SpecCoverageFixture\Controller;

class ReformattedController
{
    /**
     * Build a label for a row. No @spec — inherited debt, and it stays that way.
     */
    public function buildRowLabel(
        string $id,
        string $kind
    ): string {
        $prefix = "row";

        return $prefix . ':' . $kind . ':' . $id;
    }

    /**
     * Total the weights of the given rows. No @spec — inherited debt.
     */
    public function totalRowWeights(array $rows): int
    {
        $total = 0;
        foreach ($rows as $row) {
            $total = $total + (int) ($row['weight'] ?? 0);
        }

        return $total;
    }
}
