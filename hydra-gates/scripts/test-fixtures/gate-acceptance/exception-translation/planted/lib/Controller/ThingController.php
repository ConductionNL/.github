<?php
/**
 * Thing controller.
 *
 * THE PLANT IS THIS LINE'S POSITION, not its text. `@throws \Throwable` is a
 * legitimate and deliberately-accepted escape hatch for gate-49 — but only for
 * the method that declares it. Here it sits in the FILE-HEADER docblock, where
 * it says nothing about destroy() at all, and destroy() itself declares
 * nothing and catches nothing.
 *
 * Before .github#343's family was fixed in gate-49, the METHOD_RE docblock
 * group was `(/\*\*[\s\S]*?\*/)?` — unbounded, so for the FIRST method in a
 * file it swallowed the span from this header down to the method's own
 * docblock and credited the header's tag to destroy(). One line at the top of
 * a file silenced the first method in it, fleet-wide and invisibly.
 *
 * @license EUPL-1.2
 * @copyright Conduction
 * @throws \Throwable
 */

namespace OCA\Fx49\Controller;

use OCP\AppFramework\Controller;

class ThingController extends Controller {
    /**
     * Delete a thing.
     *
     * Declares no @throws of its own and catches nothing.
     *
     * @param string $id the object id
     *
     * @return array the result
     */
    public function destroy(string $id): array {
        $obj = $this->objectService->deleteObject($id);
        return ['ok' => $obj];
    }
}
