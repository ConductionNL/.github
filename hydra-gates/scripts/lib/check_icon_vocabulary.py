#!/usr/bin/env python3
"""Gate 60 — icon-vocabulary (ADR-077).

Validates the `icon` field of every menu entry in an app's manifests against the
canonical semantic icon vocabulary, so a glyph means the same thing in every
Conduction app.

Checked, in severity order:

  FAIL  unresolvable   an MDI-style name that exists in neither the vocabulary
                       nor the installed vue-material-design-icons package.
                       This is what shipped as `LedgerOutline` / `FileSignOutline`
                       in shillinq: names that do not exist upstream at all and
                       render blank anywhere they are copied.
  FAIL  unregistered   a name the manifests use that the app never registers via
                       registerIcons(). CnAppNav resolves MDI names ONLY through
                       that registry, with no fallback, so the entry renders with
                       NO icon — 51 entries fleet-wide before ADR-077.
  FAIL  no-registry    src/main.js never calls registerIcons(), or calls it with
                       NO arguments. Eleven apps did the latter and looked fine
                       only because every icon was still a bridged `icon-*`.
  FAIL  tier-a-drift   a Tier A concept using a non-canonical icon. Tier A is the
                       universal chrome (Dashboard, Store, Settings, ...) whose
                       whole point is cross-app recognisability.
  FAIL  unbridged-css  a legacy `icon-*` name with no CSS_ICON_TO_MDI entry. It
                       falls through to the raw Nextcloud CSS class, which on
                       NC34+ light themes can render an invisible white glyph.
  FAIL  legacy-css     any remaining (bridged) `icon-*` name. This was a warning
                       while the fleet carried ~350 of them; every app is now at
                       zero, so one reappearing is a regression, not debt.
  FAIL  bad-lowercase  a lowercase value outside the declared ContentBlocks set.
                       Blanket-skipping lowercase values hid shillinq's
                       `calendar-sync` — a kebab-cased MDI name resolving to
                       nothing.
  WARN  tier-b-drift   a Tier B concept using a non-canonical icon.

Two dialects are legal, and both are governed:

  * MDI PascalCase — the ADR-077 vocabulary, rendered by CnIcon / CnAppNav.
  * The ContentBlocks set — 13 lowercase names owned by opencatalogi's page
    editor, stored in page/register data and drawn by the PUBLIC Softwarecatalogus
    website with its own glyphs. They are documented for end users, so they are a
    published contract and are NOT migrated to MDI; they are validated against the
    declared list instead.

Scanned: src/manifest.json, src/manifest.d/*.json, and the OpenRegister register
files under lib/Settings — a schema `icon` is drawn by CnIcon in index/detail
headers exactly like a manifest one.

Scope: per ADR-020, only manifests touched by the PR when --scope-to-diff is
given. Concept detection is label-driven and deliberately conservative: an entry
is only held to a concept when its label unambiguously names that concept, so an
app's domain-specific entries are never guessed at.

Exit 0 when there are no FAIL findings (warnings do not fail the gate).

Usage:
    check_icon_vocabulary.py <repo-root> [--changed-file PATH ...]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from source_scope import js_comment_mask  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
VOCAB_PATH = os.path.join(HERE, '..', 'schemas', 'semantic-icons.json')

# The rules this gate can enforce without node_modules are not all of them. When
# vue-material-design-icons is absent the "does this icon name exist upstream?"
# rule cannot run, and neither a FAIL nor a PASS is honest about that — the gate
# has shipped both errors in turn (.github#233). This status says the third
# thing, and the runner maps it to SKIPPED (wiring).
EXIT_TOOLING_MISSING = 5

# A manifest icon value that is NOT an MDI name: an image URL, a data URI, or a
# raw SVG path. All three stay legal per ADR-077 rule 1.
_URLISH = ('/', 'http://', 'https://', 'data:')

# Sentinel in the label slot of a _menu_entries() tuple, marking a caption that
# carries keys the renderer ignores. Not a label any manifest can produce.
_CAPTION_DEAD_KEYS = '\x00caption-dead-keys'


def _is_svg_path(value: str) -> bool:
    """Whether the value looks like a raw SVG path payload rather than a name."""
    return bool(re.match(r'^[Mm]\s*[-\d.]', value))


def _load_vocab() -> dict:
    with open(VOCAB_PATH, encoding='utf-8') as fh:
        return json.load(fh)


def _available_mdi_names(repo: str) -> set[str] | None:
    """Names in the app's installed vue-material-design-icons, or None.

    Returns None when the package is not installed — the gate then cannot tell an
    invented name from a real one and says so rather than passing silently.
    """
    for base in (
        os.path.join(repo, 'node_modules', 'vue-material-design-icons'),
        os.path.join(repo, '..', 'node_modules', 'vue-material-design-icons'),
    ):
        if os.path.isdir(base):
            return {f[:-4] for f in os.listdir(base) if f.endswith('.vue')}
    return None


def _manifest_paths(repo: str) -> list[str]:
    """Every file that can carry a renderable `icon`.

    OpenRegister register files are included, not just manifests: a schema's
    `icon` is drawn by CnIcon in index/detail headers exactly like a manifest
    one. Leaving them out is how shillinq's `calendar-sync` survived — it sits
    on the AppointmentSeries schema in lib/Settings/register.d/, which the gate
    never opened.
    """
    paths = []
    base = os.path.join(repo, 'src', 'manifest.json')
    if os.path.isfile(base):
        paths.append(base)
    paths += sorted(glob.glob(os.path.join(repo, 'src', 'manifest.d', '*.json')))
    paths += sorted(glob.glob(os.path.join(repo, 'lib', 'Settings', '*register*.json')))
    paths += sorted(glob.glob(os.path.join(repo, 'lib', 'Settings', 'register.d', '*.json')))
    return paths


def _js_code(text: str) -> str:
    """*text* with JS comments blanked and STRING LITERALS KEPT.

    A COMMENTED-OUT IMPORT VOUCHES FOR AN ICON THAT RENDERS BLANK (#422).
    --------------------------------------------------------------------
    `_registered_icon_names` used to extract names from the RAW bytes of
    `src/icons.js` and `src/main.js`, so a commented-out import registered an
    icon. Measured on this checker, one fixture, one variable:

        manifest uses ViewDashboardOutline,       FAIL — 1 icon name(s) used by
        icons.js registers only Cog                      the manifests are NOT
                                                         registered
        + icons.js gains the two lines            PASS               <- the defect
          "// TODO: the dashboard nav row still
          //  needs this — not wired up yet.
          // import ViewDashboardOutline from
          //  'vue-material-design-icons/ViewDashboardOutline.vue'"

    This gate exists for exactly one failure: `CnAppNav` resolves an MDI icon
    only through the registry `registerIcons()` populates, WITH NO FALLBACK, so
    an unregistered name renders nothing at all — no glyph, no console error.
    The comment saying the import is "not wired up yet" was the whole evidence
    that it was.

    ⚠️ `js_comment_mask`, NOT `js_mask(blank_strings=True)`. THE EVIDENCE HERE
    IS A STRING: the module specifier
    `'vue-material-design-icons/ViewDashboardOutline.vue'` is the only place
    the icon name appears in an import, so blanking literals would delete every
    registration and report every icon in the fleet unregistered. This is the
    gate where the mask that closes the false negative would, one keyword
    argument further, close the gate itself.

    The two `registerIcons(` probes above had a line-prefix filter
    (`startswith(('//', '*', '/*'))`) which recognises the three ways a comment
    line can BEGIN and misses every way it can continue — a trailing comment,
    and any unprefixed interior line of a block. Both now go through the same
    tokeniser.
    """
    return js_comment_mask(text)


def _registered_icon_names(repo: str) -> tuple[set[str] | None, str | None]:
    """(names the app registers, problem) from src/icons.js + src/main.js.

    Returns (None, None) when the app has no bootstrap to inspect.

    This is what closes the defect the ADR exists for: CnAppNav resolves an MDI
    menu icon only through the registry `registerIcons()` populates, with no
    fallback, so a name the app never registered renders NOTHING — 51 entries
    fleet-wide, 29 of hrmq's 72 nav rows. Eleven apps were calling
    `registerIcons()` with no arguments at all and looked fine only because
    every icon was still a bridged `icon-*` class.
    """
    main_js = os.path.join(repo, 'src', 'main.js')
    icons_js = os.path.join(repo, 'src', 'icons.js')
    if not os.path.isfile(main_js):
        return None, None

    with open(main_js, encoding='utf-8') as fh:
        src_main = fh.read()
    # Ignore comments so a `registerIcons()` mentioned in prose is not read as
    # a call. THE LINE-PREFIX FILTER THIS REPLACES ONLY KNEW HOW A COMMENT
    # BEGINS — see `_js_code` — so a trailing comment and every interior line
    # of a `/* … */` block sailed through it.
    code = _js_code(src_main)

    calls = re.findall(r'registerIcons\(([^)]*)\)', code)
    if not calls:
        return set(), 'src/main.js never calls registerIcons()'
    if all(c.strip() == '' for c in calls):
        return set(), ('src/main.js calls registerIcons() with NO arguments — it '
                       'registers nothing, so every MDI icon name renders blank')

    names: set[str] = set()
    for f in (icons_js, main_js):
        if not os.path.isfile(f):
            continue
        with open(f, encoding='utf-8') as fh:
            text = _js_code(fh.read())
        for m in re.finditer(r"import\s+(\w+)\s+from\s+'vue-material-design-icons/([\w-]+)\.vue'", text):
            names.add(m.group(1))
            names.add(m.group(2))
        # aliased or shorthand entries in the exported map / inline object
        for m in re.finditer(r'^\s*([A-Za-z][A-Za-z0-9_]*)\s*(?::\s*[A-Za-z][A-Za-z0-9_]*)?\s*,\s*$',
                             text, re.M):
            names.add(m.group(1))
    return names, None


def _menu_entries(path: str):
    """Yield (label, icon, entry_id) for EVERY icon field in the document.

    Originally menu-only. Menus are the cross-app chrome and were migrated
    first, but page/tab/widget icons and `actions[]` / `headerActions[]` entries
    render through the same CnIcon registry and hit exactly the same failure
    modes — an unbridged `icon-*` renders an invisible white glyph on NC34+
    light themes wherever it appears, not just in the nav. So the gate now walks
    the whole tree.
    """
    try:
        with open(path, encoding='utf-8') as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return

    def walk(node, label_ctx, in_widget=False):
        if isinstance(node, dict):
            if node.get('type') == 'caption':
                # THE CAPTION EXEMPTION, AND WHY IT IS THE CORRECT ONE.
                #
                # gate-60 and gate-62 DISAGREED about this node until
                # 2026-08-12: gate-60 skipped it, gate-62 failed it twice (once
                # for "names the STORE concept but renders X", once for "one
                # glyph, two meanings"). Two gates in one package, opposite
                # verdicts on the same three lines of JSON. Somebody had to
                # decide, so it was decided against the RENDERER rather than by
                # aligning whichever was easier to change.
                #
                # `CnAppNav.vue` renders a caption as
                #
                #     <NcAppNavigationCaption v-if="isCaption(item)"
                #         :name="resolveLabel(item)"
                #         :data-testid="`cn-nav-caption-${item.id}`" />
                #
                # — `:name` and a test id, and NOTHING ELSE. No `#icon` slot is
                # passed, no `:to`, no children loop. Its own docblock states
                # the contract: "Caption entries ignore `route`, `href`,
                # `action`, `icon`, `count`, `children`, and `pinned`." The
                # manifest schema says the same thing independently:
                # "'caption' renders an NcAppNavigationCaption section divider —
                # only label, id, order, and section are honoured."
                #
                # So a caption's `icon` DRAWS NOTHING. Every rule this gate
                # enforces is a claim about a rendered glyph, and there is no
                # glyph. Failing it — as gate-62 did — is an unclosable finding
                # about dead metadata, and the "fix" it demands changes no
                # pixel. gate-62 has been aligned to this decision, not the
                # other way round. See check_store_and_settings_surface.py.
                #
                # The `return` (rather than `continue`) is deliberate and is
                # part of the same decision: the renderer does not walk a
                # caption's `children` either, so nothing under it is drawn.
                #
                # WHAT IS *NOT* EXEMPT: the keys themselves. Dead metadata on a
                # caption is a mistake worth telling the author about — it
                # usually means they expected an icon and got none — so it is
                # reported as a WARN below, which does not fail the gate. An
                # exemption that produces silence is how a gate's quiet gets
                # believed; this one produces a sentence.
                dead = sorted(k for k in ('icon', 'route', 'children', 'href',
                                          'action', 'count', 'pinned')
                              if node.get(k))
                if dead:
                    label = str(node.get('label') or node.get('id') or '?')
                    yield (_CAPTION_DEAD_KEYS, ', '.join(dead), label, False)
                return
            label = (node.get('title') or node.get('label') or node.get('name')
                     or node.get('id') or label_ctx)
            icon = node.get('icon')
            if isinstance(icon, str) and icon:
                yield (str(label or ''), icon, str(node.get('id') or ''), in_widget)
            for key, value in node.items():
                if key != 'icon':
                    # Once inside a `widgets` array, everything below it is a
                    # widget icon and stays flagged as one. See the Tier A
                    # concept check for why that distinction matters.
                    yield from walk(value, label, in_widget or key == 'widgets')
        elif isinstance(node, list):
            for item in node:
                yield from walk(item, label_ctx, in_widget)

    yield from walk(data, '')


# Label -> concept. Only unambiguous namings; an app's own domain wording is
# never guessed at. Matched against the lowercased, stripped label.
#
# THIS MAP IS THE *SYNONYM* LAYER, NOT THE VOCABULARY.
# ---------------------------------------------------
# It holds the spellings that are NOT recoverable from a concept's own name:
# Dutch synonyms, plurals, and abbreviations. The concept names themselves are
# derived from semantic-icons.json by `_concept_labels()` below, so adding a
# concept to the vocabulary makes it enforceable without editing this file.
#
# WHY THAT MATTERS (.github, 2026-08-12). Every value in this map is a **Tier
# A** key, and the vocabulary ships **140 Tier B concepts**. So the
# `warns.append(... Tier B — SHOULD)` branch below was UNREACHABLE CODE: no
# label could ever resolve to a Tier B concept, and a green gate-60 said
# nothing whatsoever about 140 of the 153 concepts it claims to govern.
# Measured before the fix, with node_modules installed, across 14 fleet repos
# and 417 manifests: **0 warnings, everywhere, always.** A planted
# `{"label": "Invoice", "icon": "FileDocumentOutline"}` — an exact Tier B
# concept name carrying the wrong glyph — produced nothing at all.
#
# Three TIER A concepts were unreachable too — `activity`, `admin`,
# `tutorial` — and those are MUSTs, not SHOULDs.
CONCEPT_LABELS = {
    'docs': 'documentation',
    'features & roadmap': 'features-roadmap',
    'features and roadmap': 'features-roadmap',
    'instellingen': 'settings',
    'configuratie': 'settings',
    'configuration': 'settings',
    'zoeken': 'search',
    'notificaties': 'notifications',
    'audit log': 'audit-trail',
    'mijn werk': 'my-work',
    'beheer': 'admin',
    'activiteit': 'activity',
}


def _concept_labels(all_concepts: dict) -> dict:
    """Label -> concept, derived from the vocabulary plus the synonym map.

    A concept's own NAME is an exact, unambiguous label for it — `Invoice`
    means the `invoice` concept in any app, in the same way `Dashboard` means
    `dashboard`. This is NOT the label-count heuristic ADR-077 rule 5 forbids:
    nothing is inferred from how many entries share a glyph, and nothing is
    matched as a substring. The comparison is equality against the concept's
    own name, which is exactly the strength the hand-written map already had —
    the map was simply missing 143 of the 153 concepts.

    Hyphenated concepts (`audit-trail`, `bank-transaction`, `open-external`)
    additionally accept the space-separated spelling, because that is how a
    menu label is written.

    The synonym map WINS on a collision, so `configuration` keeps resolving to
    `settings` rather than being shadowed.
    """
    labels: dict[str, str] = {}
    for concept in all_concepts:
        labels[concept] = concept
        if '-' in concept:
            labels[concept.replace('-', ' ')] = concept
    labels.update(CONCEPT_LABELS)
    return labels


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('repo')
    ap.add_argument('--changed-file', action='append', default=None,
                    help='restrict to these manifest paths (ADR-020 diff scope)')
    args = ap.parse_args()

    repo = os.path.abspath(args.repo)
    vocab = _load_vocab()
    tier_a: dict = vocab['tierA']
    tier_b: dict = vocab['tierB']
    all_concepts = {**tier_a, **tier_b}
    concept_labels = _concept_labels(all_concepts)
    canonical_icons = set(all_concepts.values())
    bridged = set(vocab['bridgedCssIcons'])
    content_block_icons = set((vocab.get('contentBlockIcons') or {}).get('names') or [])

    available = _available_mdi_names(repo)

    paths = _manifest_paths(repo)
    if args.changed_file:
        wanted = {os.path.abspath(os.path.join(repo, p)) for p in args.changed_file}
        paths = [p for p in paths if os.path.abspath(p) in wanted]

    if not paths:
        print('no manifest in scope — nothing to check')
        return 0

    fails: list[str] = []
    warns: list[str] = []
    used_mdi: set[str] = set()
    # Non-vocabulary icon names this run could not check for existence because
    # vue-material-design-icons is not installed. EMPTY means the run is fully
    # verified and the missing library changed no answer.
    unverifiable: set[str] = set()

    for path in paths:
        rel = os.path.relpath(path, repo)
        for label, icon, entry_id, in_widget in _menu_entries(path):
            if label == _CAPTION_DEAD_KEYS:
                # Not a rendered icon — dead metadata on a section divider.
                # WARN, never FAIL: there is no glyph to be wrong about, so
                # this cannot block a PR, but it is not silent either.
                warns.append(
                    f'{rel}: caption entry "{entry_id}" declares {icon} — a '
                    f'type:"caption" renders NcAppNavigationCaption, which '
                    f'honours only label/id/order/section. These keys draw '
                    f'nothing; drop them, or drop type:"caption" if the entry '
                    f'was meant to be clickable.')
                continue
            where = f'{rel}: {label or entry_id or "?"}'
            if not icon:
                continue
            if icon.startswith(_URLISH) or _is_svg_path(icon):
                continue

            # A bare lowercase value belongs to the ContentBlocks dialect — a
            # SECOND, deliberately separate set owned by opencatalogi's page
            # editor and rendered by the public Softwarecatalogus website.
            # It is GOVERNED, not exempted: an earlier revision skipped every
            # lowercase value and that blanket exemption hid a real defect —
            # shillinq's AppointmentSeries schema carried `calendar-sync`, a
            # kebab-cased MDI name that resolves to nothing. Anything lowercase
            # that is not in the declared set is now a failure.
            if not icon.startswith('icon-') and not icon[:1].isupper():
                if icon not in content_block_icons:
                    fails.append(
                        f'{where}: icon "{icon}" is neither an MDI PascalCase name '
                        f'nor one of the ContentBlocks icons '
                        f'({", ".join(sorted(content_block_icons))}). A kebab-case or '
                        f'lowercase spelling of an MDI name resolves to nothing '
                        f'(ADR-077 rule 1).')
                continue

            if icon.startswith('icon-'):
                stem = re.sub(r'-(dark|white)$', '', icon)
                if icon not in bridged and stem not in bridged:
                    fails.append(
                        f'{where}: unbridged legacy icon "{icon}" — falls through to '
                        f'the raw NC CSS class, which can render invisible on NC34+ '
                        f'light themes. Use the canonical MDI name (ADR-077 rule 1).')
                else:
                    # Was a warning while the fleet still carried ~350 of these.
                    # Every app is now at zero, so a bridged legacy name is a
                    # REGRESSION, not debt — fail it.
                    fails.append(
                        f'{where}: legacy icon "{icon}" is deprecated and the fleet '
                        f'is fully migrated — use the canonical MDI name '
                        f'(ADR-077 rule 1).')
                continue

            # An MDI-style name from here on.
            if icon not in canonical_icons:
                if available is None:
                    # UNVERIFIABLE, AND ONLY THIS NAME IS.
                    #
                    # The existence rule used to be switched off wholesale the
                    # moment node_modules was absent, and the whole RUN then
                    # reported SKIPPED — including runs where every icon in the
                    # app came straight out of the vocabulary and nothing
                    # needed the library at all. That is why this gate "went
                    # unrun" in apps whose manifests were in fact clean: one
                    # missing `npm ci` erased a verdict the gate already had.
                    #
                    # A vocabulary icon needs no library to be verified. The
                    # vocabulary is curated, and nextcloud-vue's own
                    # tests/components/semanticIcons.spec.js asserts every name
                    # in it resolves. So the library is needed for exactly one
                    # question — "is this NON-vocabulary name real?" — and only
                    # a manifest that asks that question is unverifiable.
                    unverifiable.add(icon)
                elif icon not in available:
                    fails.append(
                        f'{where}: icon "{icon}" does not exist in '
                        f'vue-material-design-icons and is not a vocabulary icon — '
                        f'it renders blank wherever it is not aliased locally.')
                    continue

            used_mdi.add(icon)

            # WIDGET icons are exempt from the concept MUST, and only from that.
            #
            # A widget icon renders through CnWidgetGrid's own `widgetIcons.js`
            # registry, which is a strict SUBSET of the CnIcon vocabulary this
            # gate governs. Where the two disagree the concept rule becomes
            # unsatisfiable: ADR-077 Tier A requires "CogOutline" for the
            # `settings` concept, `widgetIcons.js` ships "Cog" and NOT
            # "CogOutline", and gate-55 fails any widget icon outside that
            # registry. Verified against the installed library, not inferred:
            #
            #   grep -c CogOutline widgetIcons.js -> 0
            #   grep -c '\bCog\b'   widgetIcons.js -> 2
            #
            # So obeying this rule on a widget renders the "?" fallback, and
            # obeying gate-55 fails this one. Hit on hermiq#162, blocking a PR
            # on a contradiction it could not resolve.
            #
            # Everything ABOVE still applies to widgets — a nonexistent icon or
            # an unbridged `icon-*` is still a failure wherever it appears. Only
            # the "this concept must use exactly that glyph" rule steps aside,
            # because gate-55 already governs widget icons against the registry
            # that actually draws them.
            #
            # The better end state is reconciling the two registries (add the
            # Tier A glyphs to widgetIcons.js), after which this exemption can
            # go. Until then it is the difference between a gate that is strict
            # and one that is impossible.
            concept = concept_labels.get(label.strip().lower())
            if concept and in_widget is True:
                concept = None

            if concept:
                expected = all_concepts.get(concept)
                if expected and icon != expected:
                    # Name the ENTRY ID as well as the label. One manifest can
                    # carry the same label at several ids, and without the id
                    # the findings are byte-identical — 14 warnings collapsing
                    # to 8 distinct strings in pipelinq, none of them telling
                    # you WHICH entry to edit. A count you cannot act on is not
                    # a finished measurement.
                    ident = f' [id={entry_id}]' if entry_id else ''
                    msg = (f'{where}{ident}: concept "{concept}" must use '
                           f'"{expected}", found "{icon}"')
                    if concept in tier_a:
                        fails.append(msg + ' (ADR-077 Tier A — MUST).')
                    else:
                        warns.append(msg + ' (ADR-077 Tier B — SHOULD).')

    # Deliberately NOT checked here: "one icon used for N labels". ADR-077 rule 5
    # explicitly allows the same concept at different scopes to share a glyph
    # ("Mijn uren" / "Uren" / "Urenregistratie" are all `hours`), and concept is
    # not recoverable from arbitrary labels — so a label-count heuristic flags
    # correct manifests. The one-icon-one-concept invariant is enforced where it
    # is actually decidable: the vocabulary itself is a bijection, asserted by
    # nextcloud-vue's tests/components/semanticIcons.spec.js.

    # --- registry completeness -------------------------------------------
    # The gate's whole reason for existing: a name the app never registered
    # renders NOTHING in the navigation — no fallback glyph, no console error.
    registered, bootstrap_problem = _registered_icon_names(repo)
    if bootstrap_problem:
        fails.append(f'src/main.js: {bootstrap_problem} (ADR-077 rule 3).')
    elif registered is not None and used_mdi:
        unregistered = sorted(n for n in used_mdi if n not in registered)
        if unregistered:
            shown = ', '.join(unregistered[:8])
            more = f' (+{len(unregistered) - 8} more)' if len(unregistered) > 8 else ''
            fails.append(
                f'src/icons.js: {len(unregistered)} icon name(s) used by the '
                f'manifests are NOT registered — they render with no icon at all, '
                f'not a fallback: {shown}{more} (ADR-077 rule 3).')

    if available is None and unverifiable:
        # No silent caps: say what could not be checked, and NAME it. A NOTE
        # that lists the actual names is auditable; "could not verify" is not.
        print('NOTE: vue-material-design-icons is not installed and this app uses '
              f'{len(unverifiable)} icon name(s) from OUTSIDE the ADR-077 vocabulary, '
              'whose existence therefore could not be verified: '
              f'{", ".join(sorted(unverifiable))}. Install dependencies for full coverage.')
        # ...and do not let the caller read that NOTE as a clean bill of health.
        #
        # This gate once reported 43 confident FAILs when node_modules was
        # absent ("Calendar does not exist"), turning an environment failure
        # into findings. That was fixed by guarding the existence check on
        # `available is not None` — which swapped it for the OPPOSITE error: the
        # check silently stops happening and the gate returns 0, so the runner
        # prints PASS over an invented-icon-name rule that never ran.
        #
        # Neither reading is honest. A missing dependency is a THIRD state:
        # not a finding, and not a pass. (.github#233)

    for w in warns:
        print(f'WARN  {w}')
    for f in fails:
        print(f'FAIL  {f}')

    print(f'\nchecked {len(paths)} manifest(s): {len(fails)} failure(s), '
          f'{len(warns)} warning(s)')
    if fails:
        return 1
    if available is None and unverifiable:
        # Clean on every rule that COULD run, but the invented-name rule could
        # not be answered FOR THESE NAMES. The runner reports this as SKIPPED
        # (wiring), which is visible to --require-full-coverage. Returning 0
        # here would claim those names were verified against the library when
        # the library was not there.
        #
        # Note the condition is `unverifiable`, not `available is None`: an app
        # whose every icon comes from the vocabulary has nothing left to ask
        # the library, so it gets a real PASS with no toolchain. That is not a
        # loosening — it is the difference between "I could not check" and "I
        # did not need to".
        return EXIT_TOOLING_MISSING
    return 0


if __name__ == '__main__':
    sys.exit(main())
