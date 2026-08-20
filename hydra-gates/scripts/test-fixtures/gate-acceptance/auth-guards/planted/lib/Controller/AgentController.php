<?php
/**
 * The PLANTED arm for gate-7.
 *
 * Byte-for-byte the clean arm's structure, with the guard REMOVED from
 * `show()` and `update()`. Any authenticated user can read or overwrite any
 * agent by id — textbook IDOR (OWASP A01:2021, ADR-005 Rule 3).
 *
 * `diff()` KEEPS its verb-object guard through `loadAccessibleAgent()`. It is
 * here so the planted arm is not uniformly guilty: a checker that simply
 * flagged every `#[NoAdminRequired]` method would score 3/3 here and look
 * correct. It must find exactly the two that lost their guard.
 *
 * `archive()` is a FOURTH plant, added alongside the `canAccess(`
 * call-site fix (`ConductionNL/.github` — shillinq `security-endpoint-guards`,
 * 2026-08-20). Its CALL SITE (`$this->resolveScope($id)`) is byte-for-byte the
 * same as the clean arm's — only `resolveScope()`'s own BODY changed, to a
 * documented no-op that never reaches `AdministrationContextService::
 * canAccess()`. This is `DBAController::ensureAdministrationAccess()`'s shape
 * restated with a no-auth-token helper name: it proves the fix reads the
 * helper's BODY, not merely the presence of a call to something named
 * `resolveScope`, and that a guard-shaped call site which never actually
 * denies still fails the gate.
 *
 * @license EUPL-1.2
 * @copyright Conduction B.V.
 */

namespace OCA\ScopeFixture\Controller;

use OCA\ScopeFixture\Service\AdministrationContextService;
use OCA\ScopeFixture\Service\AgentAccessService;
use OCP\AppFramework\Controller;
use OCP\AppFramework\Http;
use OCP\AppFramework\Http\Attribute\NoAdminRequired;
use OCP\AppFramework\Http\JSONResponse;
use OCP\IRequest;
use Psr\Log\LoggerInterface;

class AgentController extends Controller {

	public function __construct(
		string $appName,
		IRequest $request,
		private readonly AgentAccessService $access,
		private readonly AdministrationContextService $context,
		private readonly LoggerInterface $logger,
		private readonly string $userId,
	) {
		parent::__construct($appName, $request);
	}

	/**
	 * PLANTED IDOR — no per-object guard of any kind.
	 */
	#[NoAdminRequired]
	public function show(int $id): JSONResponse {
		$agent = $this->access->findAgent($id);
		return new JSONResponse($agent);
	}

	/**
	 * PLANTED IDOR — writes to an arbitrary id.
	 */
	#[NoAdminRequired]
	public function update(int $id, array $data): JSONResponse {
		$agent = $this->access->findAgent($id);
		return new JSONResponse($this->access->apply($agent, $data));
	}

	/**
	 * NOT planted — keeps the verb-object guard via the loader.
	 */
	#[NoAdminRequired]
	public function diff(int $id): JSONResponse {
		$agent = $this->loadAccessibleAgent($id);
		if ($agent === null) {
			return new JSONResponse([], Http::STATUS_NOT_FOUND);
		}
		return new JSONResponse($this->access->diff($agent));
	}

	private function loadAccessibleAgent(int $id): ?array {
		$agent = $this->access->findAgent($id);
		if ($agent === null || !$this->canUserAccessAgent($agent, $this->userId)) {
			return null;
		}
		return $agent;
	}

	private function canUserAccessAgent(array $agent, string $userId): bool {
		return $agent['ownerId'] === $userId || $this->access->isShared($agent, $userId);
	}

	/**
	 * PLANTED IDOR — the call site is unchanged from the clean arm, but
	 * `resolveScope()` below is a documented no-op stub. Any authenticated
	 * user can archive any agent by id.
	 */
	#[NoAdminRequired]
	public function archive(int $id): JSONResponse {
		$this->resolveScope($id);
		return new JSONResponse($this->access->archive($id));
	}

	/**
	 * TODO: wire the real `AdministrationContextService::canAccess()` check
	 * once this endpoint's tenancy story is finalised. For now this only
	 * logs — a documented stub, not a guard.
	 */
	private function resolveScope(int $id): void {
		$this->logger->debug('resolveScope called', ['id' => $id]);
	}
}
