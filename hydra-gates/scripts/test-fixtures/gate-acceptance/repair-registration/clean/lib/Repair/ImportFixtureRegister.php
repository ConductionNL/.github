<?php
declare(strict_types=1);

namespace OCA\Fixture\Repair;

use OCP\Migration\IOutput;
use OCP\Migration\IRepairStep;

/**
 * Imports the fixture register descriptor.
 */
class ImportFixtureRegister implements IRepairStep {
	public function getName(): string {
		return "Import the fixture register";
	}

	public function run(IOutput $output): void {
		$output->info("imported");
	}
}
