<?php
// SPDX-License-Identifier: EUPL-1.2
declare(strict_types=1);

namespace OCA\Fixture\Controller;

/**
 * K&R BRACES — Nextcloud's coding standard, and the shape the whole fleet is
 * migrating to.
 *
 * The layout is the one that broke the gate, reproduced from openconnector's
 * real UiController: a `__construct` that returns NOTHING, immediately
 * followed — inside the twelve-line read-ahead window — by a method that
 * returns a `TemplateResponse`. The signature line itself opens the body, so
 * the scanner's stop conditions (which only ever looked at the lines it read
 * AHEAD) never fired on it, and `__construct` inherited the return type of the
 * method below it.
 *
 * `ui#__construct` MUST NOT be reported. A constructor is not an endpoint and
 * no route table in the fleet names one.
 */
class UiController extends Controller {
	public function __construct(string $appName, IRequest $request) {
		parent::__construct($appName, $request);
	}

	/**
	 * The method whose return type leaked upward.
	 *
	 * @return TemplateResponse
	 */
	public function dashboard(): TemplateResponse {
		return new TemplateResponse('fixture', 'index');
	}
}
