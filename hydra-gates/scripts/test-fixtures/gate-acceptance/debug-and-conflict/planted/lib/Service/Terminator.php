<?php
/**
 * `die` is a LANGUAGE CONSTRUCT, not a function, so the pre-2026-08-08 grep
 * `\bdie\(` never saw `die;`. It has its own file because it is named as a
 * gate-2 subject in expect.conf: if the construct rule is ever dropped to
 * silence the `function exit()` false positive, Debugger.php would still fire
 * on `var_dump (` and the verdict alone would not notice.
 *
 * @license  EUPL-1.2
 * @copyright 2026 Conduction B.V.
 */

declare(strict_types=1);

namespace OCA\GateAccept\Service;

class Terminator
{
	public function halt(): void
	{
		die;
	}
}
