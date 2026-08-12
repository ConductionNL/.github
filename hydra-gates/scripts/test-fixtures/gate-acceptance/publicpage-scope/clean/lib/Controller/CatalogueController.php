<?php
/**
 * CLEAN arm — gate-7 `#[PublicPage]` scope.
 *
 * Identical to the planted arm except that `arbitraryId()` resolves the
 * caller's identifier INSIDE a scope the endpoint declares public, rather
 * than globally. That is the shape opencatalogi shipped in `963f832a`:
 * resolve the configured register/schema first, refuse if unconfigured, then
 * look the identifier up within it.
 *
 * ⚠️ THE ANNOTATION IS STILL `#[PublicPage]` ON EVERY METHOD. Without that,
 * this arm would only prove that a file with no public routes passes, and
 * "flag everything annotated `#[PublicPage]`" would be a passing repair. Its
 * job is to pin that the annotation is IGNORED, not PUNISHED.
 *
 * @license EUPL-1.2
 * @copyright Conduction B.V.
 */

namespace OCA\PublicPageFixture\Controller;

use OCA\PublicPageFixture\Service\CatalogueService;
use OCP\AppFramework\Controller;
use OCP\AppFramework\Http;
use OCP\AppFramework\Http\Attribute\NoCSRFRequired;
use OCP\AppFramework\Http\Attribute\PublicPage;
use OCP\AppFramework\Http\JSONResponse;
use OCP\IConfig;
use OCP\IRequest;

class CatalogueController extends Controller {

	public function __construct(
		string $appName,
		IRequest $request,
		private readonly CatalogueService $catalogue,
		private readonly IConfig $config,
	) {
		parent::__construct($appName, $request);
	}

	/**
	 * The same body, scoped. The caller still names the object; the NAMESPACE
	 * it is resolved in is one the endpoint declares, not one the caller can
	 * steer.
	 */
	#[PublicPage]
	#[NoCSRFRequired]
	public function arbitraryId(string $id): JSONResponse {
		$scope = $this->publishedScope();
		if ($scope === null) {
			return new JSONResponse([], Http::STATUS_SERVICE_UNAVAILABLE);
		}
		$theme = $this->catalogue->findInScope($id, $scope['register'], $scope['schema']);
		if ($theme === null) {
			return new JSONResponse([], Http::STATUS_NOT_FOUND);
		}
		return new JSONResponse($theme);
	}

	/**
	 * Control: no caller-supplied identifier at all.
	 */
	#[PublicPage]
	#[NoCSRFRequired]
	public function listing(): JSONResponse {
		return new JSONResponse($this->catalogue->listPublished());
	}

	/**
	 * Control: the identifier IS the capability.
	 */
	#[PublicPage]
	#[NoCSRFRequired]
	public function byToken(string $shareToken): JSONResponse {
		$theme = $this->catalogue->findByToken($shareToken);
		if ($theme === null) {
			return new JSONResponse([], Http::STATUS_NOT_FOUND);
		}
		return new JSONResponse($theme);
	}

	/**
	 * The register/schema pair this instance publishes anonymously.
	 */
	private function publishedScope(): ?array {
		$register = $this->config->getAppValue('publicpagefixture', 'theme_register');
		$schema   = $this->config->getAppValue('publicpagefixture', 'theme_schema');
		if ($register === '' || $schema === '') {
			return null;
		}
		return ['register' => $register, 'schema' => $schema];
	}
}
