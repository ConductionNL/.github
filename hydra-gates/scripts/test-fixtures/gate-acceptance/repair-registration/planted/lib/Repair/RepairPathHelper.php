<?php
declare(strict_types=1);

namespace OCA\Fixture\Repair;

/**
 * NOT a repair step — a plain helper that happens to live under lib/Repair/.
 *
 * Present in BOTH arms. The interface decides membership, not the directory: a
 * checker keyed on the path would demand an info.xml entry for this file and
 * fail the clean arm, and a gate that fails on files the framework never looks
 * for teaches people to stop reading it. Its docblock even names IRepairStep,
 * so a raw-text grep reports it too.
 */
final class RepairPathHelper {
	public function normalise(string $path): string {
		return rtrim($path, "/");
	}
}
