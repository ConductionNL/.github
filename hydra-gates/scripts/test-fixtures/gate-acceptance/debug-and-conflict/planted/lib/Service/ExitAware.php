<?php
/**
 * Present in BOTH arms on purpose. Here it must stay silent while Debugger.php
 * fires, so the planted arm's finding count distinguishes "the rule works" from
 * "the rule was switched off".
 *
 * @license  EUPL-1.2
 * @copyright 2026 Conduction B.V.
 */

declare(strict_types=1);

namespace OCA\GateAccept\Service;

class ExitAware
{
	private int $exitCode = 0;

	private function exit(): void
	{
		$this->exitCode = 1;
	}

	public function code(): int
	{
		return $this->exitCode;
	}
}
