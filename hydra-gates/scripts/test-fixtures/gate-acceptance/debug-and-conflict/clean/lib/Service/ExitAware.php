<?php
/**
 * gate-2 NEAR-MISSES. Every construct below is correct PHP that the gate
 * reported as a shipped debug helper before 2026-08-12.
 *
 * @license  EUPL-1.2
 * @copyright 2026 Conduction B.V.
 */

declare(strict_types=1);

namespace OCA\GateAccept\Service;

class ExitAware
{
	private int $exitCode = 0;

	/**
	 * `exit` is SEMI-RESERVED in PHP: illegal as a free function name, legal
	 * as a method name. The construct pattern saw the parameter list's `(`
	 * and reported this DECLARATION as a call to the language construct.
	 */
	private function exit(): void
	{
		$this->exitCode = 1;
	}

	private function &die(): array
	{
		return [];
	}

	public function run(): void
	{
		// A call through `->` or `::` was already silent; the header was not.
		$this->exit();
		self::exit();
	}

	public function code(): int
	{
		return $this->exitCode;
	}
}
