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
use OCA\PublicPageFixture\Service\EnvelopeService;
use OCP\AppFramework\Controller;
use OCP\AppFramework\Http;
use OCP\AppFramework\Http\Attribute\NoCSRFRequired;
use OCP\AppFramework\Http\Attribute\PublicPage;
use OCP\AppFramework\Http\DataDisplayResponse;
use OCP\AppFramework\Http\JSONResponse;
use OCP\IRequest;

class CatalogueController extends Controller {

	public function __construct(
		string $appName,
		IRequest $request,
		private readonly CatalogueService $catalogue,
		private readonly EnvelopeService $envelopes,
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

	/**
	 * THE SECOND PLANT — `ConductionNL/.github#413`. The selector never
	 * appears in the signature.
	 *
	 * This method takes NO PARAMETERS. Everything the caller chose — the
	 * operation as well as its subject — arrives inside the request body and
	 * is handed straight to a collaborator that acts on both. That makes it
	 * strictly more powerful than `arbitraryId()` above, and until `#413` it
	 * was invisible to a gate that decides scope from the parameter list.
	 *
	 * MEASURED as three arms in one file: `arbitraryId(string $id)` reported,
	 * this body reported NOTHING, and the WSSE-verified twin reported nothing
	 * either — the middle arm being the defect.
	 *
	 * ⚠️ NOTE FOR WHOEVER TOUCHES THIS: what makes it a plant is that
	 * `EnvelopeService::dispatch()` in THIS arm authenticates nobody. Adding a
	 * guard there — or a refusing `if` here — clears it and this half of the
	 * fixture silently stops proving anything. The clean arm is where the
	 * guard belongs.
	 */
	#[PublicPage]
	#[NoCSRFRequired]
	public function rawBodyDispatch(): DataDisplayResponse {
		return new DataDisplayResponse($this->envelopes->dispatch(
			rawBody: file_get_contents('php://input'),
			service: 'cases'
		));
	}
}
