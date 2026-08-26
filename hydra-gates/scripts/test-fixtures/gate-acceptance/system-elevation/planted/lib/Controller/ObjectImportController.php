<?php

/**
 * SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl>
 * SPDX-License-Identifier: EUPL-1.2
 *
 * PLANTED: elevates from a controller.
 *
 * The shape this gate exists for. The author hit "this request has no owner",
 * found the elevating method on a service that was already injected, and the
 * refusal went away — so every import now runs with RBAC and tenancy off, on
 * a payload the caller supplied.
 */

declare(strict_types=1);

namespace OCA\Fixture\Controller;

class ObjectImportController {

	public function import(array $payload): array {
		return $this->objectService->runAsSystem(
			static fn (): array => $payload
		);
	}
}
