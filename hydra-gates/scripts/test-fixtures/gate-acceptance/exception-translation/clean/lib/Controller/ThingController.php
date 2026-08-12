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

    /**
     * Purge a thing.
     *
     * Same shape as the planted arm's second method — docblock, then a PHP
     * attribute, then the declaration — but this one HANDLES the throw. It has
     * to be inspected AND accepted: a gate that simply cannot see methods
     * behind an attribute would also pass this arm, so the planted arm is what
     * proves it is seen and this arm is what proves seeing it did not turn
     * into a false positive.
     *
     * @param string $id the object id
     *
     * @return array the result
     */
    #[NoAdminRequired]
    public function purge(string $id): array {
        try {
            $obj = $this->objectService->deleteObject($id);
        } catch (\Throwable $e) {
            return ['error' => $e->getMessage()];
        }
        return ['ok' => $obj];
    }

    /**
     * A private helper with NO attribute.
     *
     * ITS ONLY JOB IS TO EXIST, BELOW purge(). The old regex could not END a
     * match at an attribute-bearing declaration, so it kept expanding to the
     * next declaration it COULD end at — an attribute-free one. Without this
     * method, purge() would be the last declaration in the file, the expansion
     * would find no later end, and the engine would fall back to matching
     * purge() directly: the swallowing would not reproduce and this fixture
     * would pass against the broken gate.
     *
     * Measured on portaliq's ContributionController: ONE match spanned lines
     * 167-334 and absorbed index(), inbox() and markRead() — every routed
     * endpoint between them.
     *
     * @return string a constant
     */
    private function helper(): string {
        return 'x';
    }
}
