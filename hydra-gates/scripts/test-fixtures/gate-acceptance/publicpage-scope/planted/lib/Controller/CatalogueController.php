<?php
/**
 * PLANTED arm — gate-7 `#[PublicPage]` scope.
 *
 * `arbitraryId()` is the plant: an unauthenticated caller, an identifier they
 * chose, and a lookup that resolves it across everything on the instance. It
 * is byte-for-byte the shape of opencatalogi#856 (`GET /api/themes/{id}`,
 * fixed in `963f832a`), which served an anonymous caller a municipal `zaak`
 * status record out of an unrelated register.
 *
 * The other two methods are here so the difference between the arms is the
 * SCOPE OF THE LOOKUP and nothing else — both arms keep `#[PublicPage]`, both
 * take a caller-supplied identifier, both reach the data layer.
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
use OCP\IRequest;

class CatalogueController extends Controller {

	public function __construct(
		string $appName,
		IRequest $request,
		private readonly CatalogueService $catalogue,
	) {
		parent::__construct($appName, $request);
	}

	/**
	 * THE PLANT. No session, a caller-chosen id, a global resolution.
	 */
	#[PublicPage]
	#[NoCSRFRequired]
	public function arbitraryId(string $id): JSONResponse {
		$theme = $this->catalogue->find($id);
		if ($theme === null) {
			return new JSONResponse([], Http::STATUS_NOT_FOUND);
		}
		return new JSONResponse($theme);
	}

	/**
	 * Control: no caller-supplied identifier at all, so there is nothing to
	 * steer. Must stay silent in BOTH arms.
	 */
	#[PublicPage]
	#[NoCSRFRequired]
	public function listing(): JSONResponse {
		return new JSONResponse($this->catalogue->listPublished());
	}

	/**
	 * Control: the identifier IS the capability — Nextcloud's own public-share
	 * convention. Must stay silent in BOTH arms.
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
}
