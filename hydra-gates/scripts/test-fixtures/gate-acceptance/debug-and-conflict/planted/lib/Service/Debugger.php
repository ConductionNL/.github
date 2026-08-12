<?php
/**
 * gate-2 TRUE POSITIVE: `var_dump (` with the space PHP permits between the
 * name and the argument list, which `\bvar_dump\(` required to be absent.
 *
 * @license  EUPL-1.2
 * @copyright 2026 Conduction B.V.
 */

declare(strict_types=1);

namespace OCA\GateAccept\Service;

class Debugger
{
	public function trace(array $payload): void
	{
		var_dump ($payload);
	}
}
