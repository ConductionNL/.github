<?php
/**
 * Thing controller.
 *
 * The header carries NO @throws. The identical tag now sits on destroy()'s own
 * docblock, which is the only place it can truthfully describe destroy().
 *
 * @license EUPL-1.2
 * @copyright Conduction
 */

namespace OCA\Fx49\Controller;

use OCP\AppFramework\Controller;

class ThingController extends Controller {
    /**
     * Delete a thing.
     *
     * @param string $id the object id
     *
     * @return array the result
     *
     * @throws \Throwable the caller translates; propagation is intentional
     */
    public function destroy(string $id): array {
        $obj = $this->objectService->deleteObject($id);
        return ['ok' => $obj];
    }
}
