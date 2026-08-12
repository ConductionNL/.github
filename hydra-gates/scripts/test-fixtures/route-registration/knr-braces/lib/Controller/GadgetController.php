<?php
// SPDX-License-Identifier: EUPL-1.2
declare(strict_types=1);

namespace OCA\Fixture\Controller;

/**
 * THE ANTI-WIDENING HALF of this fixture.
 *
 * `gadget#run` returns a `JSONResponse`, is written in the SAME K&R braces,
 * and appears in no route table — so it is a genuine 404 and gate-14
 * invariant 1 MUST still report it.
 *
 * Without this half, "stop reading ahead when the signature line already opens
 * the body" could have been implemented as "skip K&R files", and the gate
 * would have gone silent for every app that adopts Nextcloud's coding
 * standard — which is the entire fleet. The two controllers here differ by
 * exactly one thing: whether a route names the method.
 */
class GadgetController extends Controller {
	#[NoAdminRequired]
	public function run(): JSONResponse {
		return new JSONResponse([]);
	}
}
