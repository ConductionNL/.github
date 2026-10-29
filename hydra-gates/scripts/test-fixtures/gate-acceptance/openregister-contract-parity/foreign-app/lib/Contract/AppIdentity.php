<?php

declare(strict_types=1);

namespace OCA\OpenCatalogi\Contract;

/**
 * Fixture stand-in for an app's own contract, unrelated to OpenRegister's.
 */
interface AppIdentity {

	/**
	 * The app's id.
	 *
	 * @return string
	 */
	public function getAppId(): string;
}
