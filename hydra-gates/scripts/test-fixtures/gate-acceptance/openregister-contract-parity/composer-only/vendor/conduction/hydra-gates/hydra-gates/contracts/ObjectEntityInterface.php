<?php

declare(strict_types=1);

namespace OCA\OpenRegister\Contract;

/**
 * Fixture stand-in for the published entity contract.
 */
interface ObjectEntityInterface {

	/**
	 * The object's UUID.
	 *
	 * @return string|null
	 */
	public function getUuid(): ?string;
}
