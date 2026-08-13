<?php
/**
 * PLANTED arm — the raw-body collaborator, UNGUARDED.
 *
 * `dispatch()` reads the operation and its subject out of the envelope the
 * caller composed and acts on both. Nothing here authenticates the sender.
 * This is procest's `StufSoapRequestDispatcher::dispatch()` as it shipped
 * before ConductionNL/procest#828.
 *
 * @license EUPL-1.2
 * @copyright Conduction B.V.
 */

namespace OCA\PublicPageFixture\Service;

class EnvelopeService {

	/**
	 * Parse an inbound SOAP envelope and run whatever it asks for.
	 */
	public function dispatch(string|false $rawBody, string $service): string {
		$document = $this->parse($rawBody);
		return $this->respond($document, $service);
	}

	public function parse(string|false $rawBody): array {
		return [];
	}

	public function respond(array $document, string $service): string {
		return '';
	}
}
