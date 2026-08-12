<?php
/**
 * The PLANTED arm for `.github#373`, MECHANISM B — A SERVICE LOCATOR IS NOT A GUARD.
 *
 * WHAT THIS FILE PINS
 * -------------------
 * `_HELPER_GUARD_BODY_RE` used to accept a BARE `throw` as proof that a helper
 * performed an authorisation action. `getObjectService()` — the fleet's standard
 * OpenRegister accessor, present in 36 controller files across 7 apps — throws
 * when OpenRegister is absent. So a locator that answers "this dependency is
 * missing" was read as an answer to "may this caller touch this object?", and it
 * cleared EVERY method that calls it before its first write. That is how the fix
 * for gate-7's `#[PublicPage]` scope hid its own motivating case: Pattern 8 was
 * written and green on its rig while opencatalogi `ThemesController::show`
 * stayed silent.
 *
 * `#373` narrowed the alternative so a `throw` must NAME an authorisation
 * exception. Widen it back to a bare `\bthrow\b` — one token — and
 * `getObjectService()` is a guard again, `show()` is cleared again, and this arm
 * goes green.
 *
 * MECHANISM B IS INDEPENDENT OF MECHANISM A. The locator's `throw` is in CODE,
 * not in a comment, so restoring comment-bearing text (mechanism A) does not
 * clear `show()`, and narrowing the throw alternative (mechanism B) does not
 * clear `rotate()`. Each arm has exactly one revert that turns it green, which
 * is what makes the two rows in expect.conf worth having separately.
 *
 * `showShared()` is the NEGATIVE CONTROL: a genuine verb-object predicate, so
 * this arm is not uniformly guilty.
 *
 * ⚠️ Austere per-method docblocks, for the reason given in WebhookController.
 *
 * @license EUPL-1.2
 * @copyright Conduction B.V.
 */

namespace OCA\CommentGuardFixture\Controller;

use OCA\CommentGuardFixture\Service\ThemeService;
use OCP\AppFramework\Controller;
use OCP\AppFramework\Http;
use OCP\AppFramework\Http\Attribute\NoAdminRequired;
use OCP\AppFramework\Http\JSONResponse;
use OCP\IRequest;

class ThemeController extends Controller {

	public function __construct(
		string $appName,
		IRequest $request,
		private readonly ThemeService $themes,
		private readonly string $userId,
	) {
		parent::__construct($appName, $request);
	}

	/**
	 * PLANTED — resolves the dependency, then reads any id. See the file header.
	 */
	#[NoAdminRequired]
	public function show(string $id): JSONResponse {
		$objects = $this->getObjectService();
		return new JSONResponse($objects->find($id));
	}

	/**
	 * NEGATIVE CONTROL — must stay silent. See the file header.
	 */
	#[NoAdminRequired]
	public function showShared(string $id): JSONResponse {
		$theme = $this->themes->find($id);
		if ($theme === null || !$this->canUserAccessTheme($theme, $this->userId)) {
			return new JSONResponse([], Http::STATUS_NOT_FOUND);
		}
		return new JSONResponse($theme);
	}

	/**
	 * The locator. It reports a missing dependency and decides nothing else.
	 */
	private function getObjectService(): ThemeService {
		if (!class_exists('\OCA\OpenRegister\Service\ObjectService')) {
			throw new \RuntimeException('OpenRegister is not installed');
		}
		return $this->themes;
	}

	private function canUserAccessTheme(array $theme, string $userId): bool {
		return $theme['ownerId'] === $userId || $this->themes->isShared($theme, $userId);
	}
}
