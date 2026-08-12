<?php
/**
 * The CLEAN arm for `.github#373`, MECHANISM B.
 *
 * BYTE-FOR-BYTE the planted arm, INCLUDING `getObjectService()` and its
 * `throw`, with one change: `show()` now makes its own per-object decision.
 *
 * The locator is KEPT deliberately, and unchanged. `#373` did not make it
 * illegal to resolve a dependency by throwing; it made that throw stop counting
 * as an answer to "may this caller touch this object?". So the locator must
 * still be here, still throwing, and the arm must still be silent — because the
 * silence is now bought by the comparison in `show()` and by nothing else. An
 * arm that had also deleted the locator would have passed against the broken
 * checker too.
 *
 * This file must produce ZERO findings.
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
	 * The same locator call, plus the decision the planted arm lacks.
	 */
	#[NoAdminRequired]
	public function show(string $id): JSONResponse {
		$objects = $this->getObjectService();
		$theme = $objects->find($id);
		if ($theme['ownerId'] !== $this->userId) {
			return new JSONResponse([], Http::STATUS_NOT_FOUND);
		}
		return new JSONResponse($theme);
	}

	/**
	 * Identical to the planted arm.
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
	 * Identical to the planted arm.
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
