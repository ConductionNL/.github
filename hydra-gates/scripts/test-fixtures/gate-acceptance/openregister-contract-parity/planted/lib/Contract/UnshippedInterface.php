<?php

declare(strict_types=1);

namespace OCA\OpenRegister\Contract;

/**
 * Canonical but not shipped — a leaf app's tests cannot load it.
 */
interface UnshippedInterface {

	/**
	 * @return void
	 */
	public function nothing(): void;
}
