<?php

namespace OCA\Fx25\Controller;

use OCP\AppFramework\Controller;
use OCP\AppFramework\Http\Attribute\PublicPage;

class ThingController extends Controller {

    /**
     * List the things.
     */
    #[PublicPage]
    public function listThings(): array {
        return [];
    }

    /**
     * Purge every thing in the register.
     *
     * ADMINISTRATOR-ONLY. This method carries NO auth attribute of its own, so
     * Nextcloud's default admin-required posture applies. gate-25 must stay
     * silent about it in BOTH arms — flagging it is the false-positive half of
     * .github#363, produced by a fixed twenty-line window reaching back over
     * listThings()'s closing brace and reading ITS attribute.
     */
    public function adminOnlyPurge(): array {
        return [];
    }

    #[PublicPage]
    /**
     * Return the far thing.
     *
     * This docblock is long ON PURPOSE. The method's OWN public-page
     * attribute sits directly above it, separated from the declaration by
     * nothing but this one contiguous comment — legal PHP, and exactly what a
     * house style with long descriptions produces every day.
     *
     * That attribute is deliberately NOT spelled out anywhere in this prose.
     * Writing it here would satisfy the gate's auth regex from inside a
     * comment, and this arm would then go green for a reason that has nothing
     * to do with the binding it exists to test — the `.github#358` shape,
     * where documenting a gate silences it.
     *
     * That distance is the false-NEGATIVE half of .github#363: measured
     * against the twenty-line window, this method's own attribute fell outside
     * it and a genuinely public, genuinely untested endpoint was reported as
     * nothing at all. The silent half is the dangerous half, because detecting
     * a newly-exposed endpoint is the entire purpose of this gate.
     *
     * Note that none of the words the auth regex looks for appear anywhere in
     * this prose, so nothing but a real attribute can satisfy it.
     *
     * THE LENGTH IS THE FIXTURE. Measured against gate-25 at 57bcb2b, this
     * docblock has to push the declaration MORE THAN TWENTY LINES below the
     * attribute or the old window still reaches it and this arm goes green
     * against the very defect it exists to pin. A first draft of this file
     * had a distance of fourteen lines and did exactly that — it passed
     * against the broken gate, which is the same thing as not testing it.
     *
     * So if you shorten this comment, you silently delete an assertion. The
     * distance from the attribute to `public function farAttribute` is the
     * only property of these paragraphs that matters; their content is
     * deliberately inert filler and none of it is worth reading.
     */
    public function farAttribute(): array {
        return [];
    }
}
