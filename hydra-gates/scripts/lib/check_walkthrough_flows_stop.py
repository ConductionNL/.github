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
    """Page ids of every `type:"flows"` page.

    :param manifest: Parsed manifest.
    :return: Set of page ids.
    """
    out = set()
    for page in manifest.get('pages') or []:
        if isinstance(page, dict) and page.get('type') == 'flows' and page.get('id'):
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
    nothing and falls back to a centred, anchorless coachmark — it still
    appears and still advances, it just stops pointing at anything.

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

        for step in hits:
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
