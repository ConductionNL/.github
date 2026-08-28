#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl>
"""Gate 70 — an app that ships a Flows page must point its tour at it.

An app's automation surface is only discoverable by someone who already knows
it is there unless the getting-started tour says so. Measured across the 20
fleet manifests on 2026-08-27: **19 apps declared a walkthrough, 12 shipped a
`type:"flows"` page, and exactly ONE tour mentioned flows at all.**

Two findings, and they pull in opposite directions on purpose:

  missing-flows-stop
      A `type:"flows"` page exists and no tour step targets it. The surface is
      undiscoverable from the tour.

  forcing-flows-stop
      A step DOES target it but only advances on `object-created` with no
      `allowManualNext`. That turns "here is where flows live" into "build a
      flow before you may continue", which is the thing this gate exists to
      prevent as much as the absence is. A tour that cannot be finished
      without authoring an automation is worse than one that never mentions
      it — the user cannot even get to the end to find out what else exists.

Writes one `<file>:<pointer> rule=<rule> …` line per finding to the log path
given as argv[1]; exit status is reserved for CRASHES, so the caller can tell
"no findings" from "the checker never ran" (#147 / #249 / #262).
"""

import json
import os
import sys


def _load(path):
    """Parse a manifest, returning None when it is not readable JSON.

    A manifest that does not parse is gate-22's finding, not this gate's; it
    is skipped here rather than double-reported.

    :param path: Manifest path.
    :return: The parsed object, or None.
    """
    try:
        with open(path, encoding='utf-8') as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def _flows_pages(manifest):
    """Page ids of every flows surface, however the app declares it.

    NOT `type == "flows"` alone. Measured across the fleet on 2026-08-28:
    exactly ONE app declares that type. The other eight ship their automation
    surface as an ordinary schema-driven `type:"index"` page whose id and
    route are `Flows` — which is the shape the manifest renderer actually
    supports, and the shape every app that got a flows stop this week uses.

    A predicate matching only the rare declaration made this gate applicable
    to one repository while reading as though it covered twelve. It would
    have passed, silently and by NOT APPLYING, every app whose tour omits the
    flows surface — which is the entire defect it exists to catch.

    So the surface is recognised by any of:
      * `type: "flows"` — the explicit declaration;
      * a page whose id is `Flows`;
      * a page whose route is `/flows` (any capitalisation).

    :param manifest: Parsed manifest.
    :return: Set of page ids.
    """
    out = set()
    for page in manifest.get('pages') or []:
        if not isinstance(page, dict) or not page.get('id'):
            continue
        route = page.get('route')
        route = route.strip('/').lower() if isinstance(route, str) else ''
        if (page.get('type') == 'flows'
                or str(page['id']).lower() == 'flows'
                or route == 'flows'):
            out.add(page['id'])
    return out


def _menu_ids_for(manifest, page_ids):
    """Menu entry ids that route to one of `page_ids`.

    NOT what a tour step should reference — see `_targets_flows`. Kept because
    a step authored with the MENU id is the most common way to get this wrong,
    and the finding is far more useful when it can say so.

    :param manifest: Parsed manifest.
    :param page_ids: Flows page ids.
    :return: Set of menu ids.
    """
    out = set()
    for entry in manifest.get('menu') or []:
        if isinstance(entry, dict) and entry.get('route') in page_ids and entry.get('id'):
            out.add(entry['id'])
    return out


def _targets_flows(step, page_ids, menu_ids):
    """Whether a tour step points at the flows surface AT RUNTIME.

    Keyed on the ROUTE, because that is what actually resolves.
    `CnWalkthrough.resolveTarget()` looks a `nav-item` / `page` ref up as
    `[data-cn-route="<ref>"]`, and `CnAppNav` sets that attribute from
    `item.route`. A step authored with the MENU id therefore resolves to
    nothing — and an OPTIONAL step whose target is absent is SKIPPED, not
    re-centred:

        const el = this.resolveTarget(this.step)
        if (!el) { if (this.step.optional) { this.wt.skip(); return } }

    The anchorless-centred fallback in computeRect() applies only to a target
    that RESOLVED and has zero size (a collapsed nav group); an absent target
    never reaches it. So a mis-keyed stop does not degrade politely, it
    vanishes — and `optional: true` is exactly what this gate's own
    forcing-flows-stop rule requires, so the two rules meet here.

    Accepting the menu id here would make this gate accept a manifest the
    runtime cannot honour, which is the validator-and-executor-disagree
    failure the gate set exists to catch. `menu_ids` is used only to say so in
    the finding.

    :param step: A tour step.
    :param page_ids: Flows page ids (== route names).
    :param menu_ids: Menu ids routing to them, for diagnostics only.
    :return: True when the step targets flows.
    """
    target = step.get('target') or {}
    ref = target.get('ref')
    if target.get('kind') in ('nav-item', 'page') and ref in page_ids:
        return True
    advance = step.get('advanceOn') or {}
    return advance.get('type') == 'route-match' and advance.get('route') in page_ids


def _is_forcing(step):
    """Whether a step can only be completed by creating something.

    `allowManualNext` is the escape hatch; without it an `object-created`
    advance is a hard requirement.

    :param step: A tour step.
    :return: True when the step forces creation.
    """
    advance = step.get('advanceOn') or {}
    if advance.get('type') != 'object-created':
        return False
    return step.get('allowManualNext') is not True



# The first library release whose CnAppNav emits `data-cn-route` on its
# SETTINGS menu loop (nextcloud-vue#811, shipped in 2.21.0). Below this, a
# stop that targets a settings-section entry resolves nothing.
MIN_NC_VUE = (2, 21, 0)


def _locked_nc_vue(manifest_path):
    """The @conduction/nextcloud-vue version this app's LOCK pins, or None.

    The lock, not package.json: `npm ci` installs from the lock, so a caret
    range that would ACCEPT a new enough library says nothing about what the
    built bundle actually contains. Returns None when there is no lock or no
    entry — both are "cannot tell", which this gate treats as out of scope
    rather than as a pass.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(manifest_path)))
    lock = os.path.join(root, 'package-lock.json')
    try:
        with open(lock, encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    for key, entry in (data.get('packages') or {}).items():
        if key.endswith('node_modules/@conduction/nextcloud-vue'):
            raw = (entry or {}).get('version')
            if not isinstance(raw, str):
                return None
            parts = raw.split('-')[0].split('.')
            try:
                return tuple(int(x) for x in parts[:3])
            except ValueError:
                return None
    return None


def _settings_routes(manifest):
    """Routes whose menu entry sits in the SETTINGS section.

    `CnAppNav` renders main, child, footer and settings entries as four
    separate `v-for` loops. `data-cn-route` reached the settings one last
    (#811), so a stop targeting a settings entry is the case that silently
    resolved to nothing on older libraries.
    """
    routes = set()
    for item in (manifest.get('menu') or []):
        if not isinstance(item, dict):
            continue
        if item.get('section') == 'settings' and isinstance(item.get('route'), str):
            routes.add(item['route'])
    return routes

def check(path, findings):
    """Append findings for one manifest.

    :param path: Manifest path.
    :param findings: List to append to.
    :return: True when the manifest was actually inspected.
    """
    manifest = _load(path)
    if manifest is None:
        return False

    walkthrough = manifest.get('walkthrough') or {}
    tours = walkthrough.get('tours') or []
    page_ids = _flows_pages(manifest)

    # Not applicable: no flows surface to point at, or no tour to point with.
    # Deliberately NOT a finding — an app without flows has nothing to show,
    # and an app without a walkthrough is gate-scope for nobody here.
    if not page_ids or not tours or walkthrough.get('enabled') is False:
        return False

    for t_index, tour in enumerate(tours):
        if not isinstance(tour, dict):
            continue
        steps = [s for s in (tour.get('steps') or []) if isinstance(s, dict)]
        menu_ids = _menu_ids_for(manifest, page_ids)
        hits = [s for s in steps if _targets_flows(s, page_ids, menu_ids)]
        tour_id = tour.get('id', f'tours[{t_index}]')

        if not hits:
            # Name the near-miss when it is there: a step that references the
            # MENU id looks correct in review and resolves to nothing at
            # runtime, so "no step targets it" would read as a flat
            # contradiction to whoever authored one.
            near = [s for s in steps
                    if (s.get('target') or {}).get('ref') in menu_ids]
            hint = ''
            if near:
                ids = ', '.join(sorted({(s.get('target') or {})['ref'] for s in near}))
                hint = (f' NOTE: step(s) reference the MENU id ({ids}), which resolves to '
                        f'nothing — CnWalkthrough looks a nav-item ref up as '
                        f'[data-cn-route], set from the page ROUTE. Use one of '
                        f'{sorted(page_ids)}.')
            findings.append(
                f'{path}:walkthrough.tours[{t_index}] rule=missing-flows-stop '
                f'tour={tour_id} flows_pages={sorted(page_ids)} '
                'no step targets the flows surface — it is discoverable only to '
                'someone who already knows it is there. Add a view-only stop '
                '(optional + allowManualNext + a route-match advance).' + hint
            )
            continue

        settings_routes = _settings_routes(manifest)
        locked = _locked_nc_vue(path)

        for step in hits:
            # A stop that targets a SETTINGS entry on a library older than
            # 2.21.0 is not merely cosmetic: CnWalkthrough.armStep() SKIPS an
            # optional step whose target is absent, with no console error and
            # nothing on screen. `optional: true` is exactly what keeps this
            # stop from forcing authorship, so the friendly authoring choice is
            # also the one that fails silently — and the step counter cannot
            # catch it either, because skip() advances and the declared total
            # is unchanged.
            #
            # This is the difference between a gate that reads the manifest and
            # one that measures what a user gets: without it, all seven fleet
            # apps would have passed this gate while shipping a stop nobody
            # could ever see.
            ref = (step.get('target') or {}).get('ref')
            if (ref in settings_routes
                    and locked is not None
                    and locked < MIN_NC_VUE):
                findings.append(
                    f'{path}:walkthrough.tours[{t_index}].steps[{step.get("id", "?")}] '
                    f'rule=unanchorable-flows-stop the stop targets "{ref}", a '
                    f'SETTINGS-section entry, but package-lock.json pins '
                    f'@conduction/nextcloud-vue '
                    f'{".".join(str(x) for x in locked)} — CnAppNav did not emit '
                    f'data-cn-route on its settings loop until '
                    f'{".".join(str(x) for x in MIN_NC_VUE)} (#811), so the step '
                    'resolves nothing and is SKIPPED for every user. Bump the '
                    'LOCK, not just the caret range: npm ci installs from the lock.'
                )
            if _is_forcing(step):
                findings.append(
                    f'{path}:walkthrough.tours[{t_index}].steps[{step.get("id", "?")}] '
                    'rule=forcing-flows-stop the step pointing at flows advances only '
                    'on object-created and sets no allowManualNext, so the tour cannot '
                    'be finished without authoring a flow. Showing where flows live '
                    'must not require building one.'
                )
    return True


def main(argv):
    """Entry point.

    :param argv: `[log_path, manifest...]`.
    :return: Exit status (0 unless the checker itself could not run).
    """
    if len(argv) < 2:
        sys.stderr.write('usage: check_walkthrough_flows_stop.py <log> <manifest>...\n')
        return 2

    log_path, manifests = argv[0], argv[1:]
    findings = []
    applicable = 0
    for path in manifests:
        if os.path.isfile(path) and check(path, findings):
            applicable += 1

    with open(log_path, 'a', encoding='utf-8') as handle:
        for line in findings:
            handle.write(line + '\n')

    # How many manifests this gate's subject matter actually EXISTS in. The
    # caller needs it to tell "a flows page, and the tour points at it" from
    # "no flows page, so nothing was judged" — both of which produce zero
    # findings, and only the first of which is a pass. Without this the gate
    # reports PASS for an app that has nothing to check, and an app that later
    # drops its flows page keeps a green gate for ever.
    with open(log_path + '.applicable', 'w', encoding='utf-8') as handle:
        handle.write(str(applicable) + '\n')

    sys.stderr.write(
        f'[check_walkthrough_flows_stop] {applicable} applicable manifest(s), '
        f'{len(findings)} finding(s)\n'
    )
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
