<?php
/**
 * CLEAN arm — the same raw-body collaborator, WITH the sender authentication.
 *
 * Byte-identical to the planted arm apart from `authenticateSender()` and the
 * three lines in `dispatch()` that consult it. That is the whole difference
 * between the two arms of this half of the bundle, and it is what the
 * `#413` widening must be able to tell apart.
 *
 * Nothing new in the checker recognises this: `authenticateSender()` refuses
 * with `STATUS_UNAUTHORIZED`, which makes it a strict guard, and `dispatch()`
 * calls it before any data access, which makes `dispatch()` transitively
 * guard-bearing — Pattern 4, reading this file, not the controller's.
 *
 * @license EUPL-1.2
 * @copyright Conduction B.V.
 */

namespace OCA\PublicPageFixture\Service;

use OCP\AppFramework\Http;

class EnvelopeService {

	/**
	 * Parse an inbound SOAP envelope and run whatever it asks for — once the
	 * sending system has proved who it is.
	 */
	public function dispatch(string|false $rawBody, string $service): string {
		$refusal = $this->authenticateSender($rawBody);
		if ($refusal !== null) {
			return $refusal;
		}
		$document = $this->parse($rawBody);
		return $this->respond($document, $service);
	}

	/**
	 * Match the envelope's WSSE UsernameToken against the sending endpoint's
	 * stored credentials. Fail-closed: an unconfigured endpoint refuses.
	 */
	private function authenticateSender(string|false $rawBody): ?string {
		if ($rawBody === false || str_contains($rawBody, 'wsse:UsernameToken') === false) {
			return $this->fault('Authentication failed', Http::STATUS_UNAUTHORIZED);
		}
		return null;
	}

	public function fault(string $message, int $statusCode): string {
		return $message;
	}

	public function parse(string|false $rawBody): array {
		return [];
	}

	public function respond(array $document, string $service): string {
		return '';
	}
}
