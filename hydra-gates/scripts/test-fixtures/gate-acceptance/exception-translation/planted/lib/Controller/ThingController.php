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

    /**
     * Purge a thing.
     *
     * THE SECOND PLANT, and the more serious one. This docblock is separated
     * from its declaration by a PHP ATTRIBUTE, which is ordinary Nextcloud
     * controller style. The old unbounded docblock group could not end at this
     * declaration — `\s*` cannot cross `#` — so the regex kept expanding from
     * an EARLIER `/**`, and because re.finditer returns NON-OVERLAPPING
     * matches, the match that began above swallowed this method whole.
     *
     * Not "credited with the wrong tag": NEVER INSPECTED. Measured 2026-08-12
     * on portaliq's ContributionController, the old regex saw 13 of 24
     * methods — the eleven it could not see included every routed
     * #[PublicPage] endpoint in the file. Fleet-wide over 8 apps and 413
     * controller files: 2,754 methods seen of 3,120, so 366 (11.7%) were
     * invisible to this gate, 27% of them in one app.
     *
     * So this method must appear in the finding list at all. If a future edit
     * reintroduces an unbounded group, `destroy()` above still reports and
     * only this one disappears — which is why the expect.conf subject names
     * THIS method and not that one.
     *
     * @param string $id the object id
     *
     * @return array the result
     */
    #[NoAdminRequired]
    public function purge(string $id): array {
        $obj = $this->objectService->deleteObject($id);
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
