<?php

declare(strict_types=1);

namespace OCA\OpenRegister\Contract;

/**
 * Fixture stand-in for the published contract.
 *
 * Deliberately NOT the real file: the gate compares two copies against each
 * other, never against a hard-coded expectation, so any pair works and the
 * fixture stays readable.
 */
interface ObjectServiceInterface {

	/**
	 * Find a single object.
	 *
	 * @param string|int $id The object id or UUID.
	 *
	 * @return ObjectEntityInterface|null The object, or null.
	 */
	public function find(string|int $id): ?ObjectEntityInterface;

	/**
	 * A method the canonical copy does not declare.
	 *
	 * @return int The count.
	 */
	public function count(): int;
}
