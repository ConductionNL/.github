<?php

/**
 * SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl>
 * SPDX-License-Identifier: EUPL-1.2
 *
 * CLEAN: the same controller, refusing instead of elevating.
 *
 * It also MENTIONS the forbidden call twice — once in prose and once in a
 * string literal — because a gate that reads raw text reports the sentence
 * describing the rule as a violation of it, and this arm is what proves the
 * comment/string mask is load-bearing rather than decorative.
 */

declare(strict_types=1);

namespace OCA\Fixture\Controller;

class ObjectImportController {

	/**
	 * Never calls ->runAsSystem( — an import acts as the person importing.
	 */
	public function import(array $payload): array {
		if ($this->userSession->getUser() === null) {
			throw new \RuntimeException(
				'Refusing to import: nothing names who this acts as. '
				. 'Do not reach for ->runAsSystem( here.'
			);
		}

		return $payload;
	}
}
