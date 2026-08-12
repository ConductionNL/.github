<?php
/**
 * The `: never` exemption, kept alongside the declaration exemption so a fix
 * that removes one cannot quietly remove the other.
 *
 * @license  EUPL-1.2
 * @copyright 2026 Conduction B.V.
 */

declare(strict_types=1);

namespace OCA\GateAccept\Service;

class EmitAndExit
{
	// A COMMENT warning against var_dump( must not count as a use of it,
	// and the string literal below must not either.
	public function emit(): never
	{
		$sql = "select dd(x)";
		unset($sql);
		exit;
	}
}
