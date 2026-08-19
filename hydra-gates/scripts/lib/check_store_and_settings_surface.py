#!/usr/bin/env python3
"""Gates 62 (store-plane, ADR-080) and 63 (settings-surface, ADR-079).

Both gates read the app's manifests plus ``src/menu-layout.json`` and enforce
naming/placement rules that JSON Schema cannot express.

Gate 62 exists because gate 60 (icon-vocabulary) validates icon NAMES but
cannot recover a CONCEPT from an arbitrary label — ADR-077 says so explicitly,
since a label-count heuristic flags correct manifests. Once ADR-080 fixes the
naming, the concept becomes legible and Tier A can be enforced on it.

Usage:
    check_store_and_settings_surface.py <app-root> --gate store|settings
                                        [--base <ref>]

Exit code 0 = pass, 1 = at least one HARD FAIL. WARN lines never fail the gate.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from source_scope import php_mask  # noqa: E402

# ---------------------------------------------------------------------------
# AN EXIT CODE IS A STATUS (.github#240 / #242)
# ---------------------------------------------------------------------------
# "I checked and it was fine", "there was nothing here to check", and "I was
# handed an empty scope and checked nothing" were all the same 0. The runner
# printed PASS for all three, and the log line beside the PASS literally read
# "gate skipped". Only `na` is allowed not to count against coverage; the other
# two must be visible to --require-full-coverage, so they get their own codes.
EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_ERROR = 2
EXIT_EMPTY_SCOPE = 3      # scope resolved, selected nothing -> runner _skip `na` (.github#268)
EXIT_NOT_APPLICABLE = 4   # subject matter absent entirely   -> runner _skip na

# ADR-077 vocabulary: the canonical glyph for each concept this gate names.
STORE_ICON = "StoreOutline"
TEMPLATE_ICON = "FileReplaceOutline"
CATALOGUE_ICON = "Bookshelf"
APPS_ICON = "ViewGridOutline"

# Labels that CLAIM the store concept. Matching is case-insensitive and exact
# on the stripped label — substring matching would flag "Data store settings".
STORE_LABELS = {"store", "app store", "marketplace", "app marketplace"}
# Labels that name the DIFFERENT outward-facing-catalogue concept.
CATALOGUE_LABELS = {"catalog", "catalogue", "catalogs", "catalogues"}
TEMPLATE_LABELS = {"templates", "template"}

# ADR-079: a settings page id/title that claims the platform meaning.
RESERVED_SETTINGS_NAMES = {"settings", "appsettings", "app settings"}


def _changed_files(root: Path, base: str | None) -> set[str] | None:
    """Return repo-relative changed paths, or None when unscoped (ADR-020)."""
    if not base:
        return None
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", f"{base}...HEAD"],
            cwd=root, capture_output=True, text=True, check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fail OPEN on scoping only: an unavailable base ref must not silently
        # skip the gate, so fall back to checking everything.
        return None
    return {line.strip() for line in out.splitlines() if line.strip()}


def _manifest_paths(root: Path) -> list[Path]:
    paths = []
    base = root / "src" / "manifest.json"
    if base.is_file():
        paths.append(base)
    frag_dir = root / "src" / "manifest.d"
    if frag_dir.is_dir():
        paths.extend(sorted(p for p in frag_dir.glob("*.json")))
    return paths


def _load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _walk_menu(items, out, skip_captions: bool = False):
    """Flatten a menu tree into *out*.

    ``skip_captions`` drops ``type: "caption"`` nodes AND their subtrees. See
    :func:`check_store` for the decision and its evidence; gate 63 keeps
    walking them, because the rule it applies to a caption (its LABEL) is a
    property the renderer does honour.
    """
    for item in items or []:
        if isinstance(item, dict):
            if skip_captions and item.get("type") == "caption":
                continue
            out.append(item)
            _walk_menu(item.get("children"), out, skip_captions)


def _pages_by_id(manifests: list[tuple[Path, dict]]) -> dict[str, dict]:
    pages = {}
    for _, data in manifests:
        for page in data.get("pages") or []:
            if isinstance(page, dict) and page.get("id"):
                pages[page["id"]] = page
    return pages


def check_store(root: Path, manifests, findings, changed: set[str] | None = None) -> None:
    """ADR-080: store / templates / catalogue are three distinct concepts.

    A ``type: "caption"`` entry is NOT a menu entry for this gate's purposes.
    -----------------------------------------------------------------------
    Until 2026-08-12 this gate and gate 60 (icon-vocabulary) DISAGREED about
    that node, in the same package, on the same three lines of JSON: gate 60
    exempted it, and this gate failed it TWICE — once for "names the STORE
    concept but renders X", once for "one glyph, two meanings". Reproduced on
    a fixture carrying `{"type":"caption","label":"Store","icon":
    "ViewGridOutline"}`: gate-60 → 0 findings, gate-62 → 2 FAILs.

    The disagreement was decided against the RENDERER, not by aligning
    whichever gate was easier to edit. ``CnAppNav.vue`` renders a caption as

        <NcAppNavigationCaption v-if="isCaption(item)"
            :name="resolveLabel(item)"
            :data-testid="`cn-nav-caption-${item.id}`" />

    — the label and a test id, and nothing else. No ``#icon`` slot, no ``:to``,
    no children loop. Its own docblock states the contract ("Caption entries
    ignore `route`, `href`, `action`, `icon`, `count`, `children`, and
    `pinned`"), and the manifest schema states it independently ("'caption'
    renders an NcAppNavigationCaption section divider — only label, id, order,
    and section are honoured").

    EVERY rule below is a claim about a rendered ICON or a resolved ROUTE, and
    a caption has neither. So gate 60 was right and this gate was wrong: it was
    emitting unclosable findings about dead metadata, whose only "fix" changes
    no pixel. This gate is therefore aligned to gate 60, and gate 60 now emits
    a WARN naming the dead keys so the information is not merely dropped.

    ⚠️ SCOPE OF THE DECISION. It covers the ICON and ROUTE rules only. A
    caption's LABEL *is* honoured by the renderer, so a label rule on a caption
    would still be legitimate — gate 63 (settings-surface) keeps walking
    captions for exactly that reason, and its ADR-079 D4 rule is about the
    label. Nothing here exempts a caption from a future naming rule.

    Fleet exposure, measured before the change across 14 repos and 145
    manifests: **1** caption node exists and **0** carry any dead key, so this
    corrects a latent contradiction, not a live count. The census was
    positive-controlled (it found the 1 caption, so a 0 is a result).
    """
    pages = _pages_by_id(manifests)

    for path, data in manifests:
        entries: list[dict] = []
        _walk_menu(data.get("menu"), entries, skip_captions=True)
        rel = path.relative_to(root)

        for entry in entries:
            label = str(entry.get("label") or "").strip().lower()
            icon = str(entry.get("icon") or "")

            if label in STORE_LABELS:
                if icon != STORE_ICON:
                    findings.append(
                        f"FAIL {rel}: menu entry '{entry.get('label')}' names the STORE concept but "
                        f"renders '{icon}' — Tier A requires '{STORE_ICON}' (ADR-080 D1 / ADR-077)."
                    )
                if icon == APPS_ICON:
                    findings.append(
                        f"FAIL {rel}: menu entry '{entry.get('label')}' uses '{APPS_ICON}', which the "
                        f"vocabulary assigns to the 'apps' concept — one glyph, two meanings "
                        f"(ADR-077 rule 5)."
                    )

                # Decision 4: a store surface must be registry-backed.
                page = pages.get(entry.get("route") or "")
                if page is not None:
                    cfg = page.get("config") or {}
                    note = json.dumps(page.get("_note") or "")
                    registry_backed = (
                        "registry" in note.lower()
                        or "store" in str(cfg.get("cardComponent") or "").lower()
                        or bool(cfg.get("storeRegistry"))
                    )
                    if not registry_backed:
                        findings.append(
                            f"WARN {rel}: page '{page.get('id')}' is labelled 'Store' but shows no sign "
                            f"of the ADR-080 registry contract (GenericStoreService). A local-only card "
                            f"grid is a Templates page, not a Store (Decision 4)."
                        )

            elif label in CATALOGUE_LABELS:
                route = entry.get("route") or ""
                page = pages.get(route)
                schema = str(((page or {}).get("config") or {}).get("schema") or "")
                # A "Catalog" over an install-y schema is a mislabelled store.
                if any(k in schema.lower() for k in ("catalog_item", "template", "adapter")):
                    findings.append(
                        f"FAIL {rel}: menu entry '{entry.get('label')}' backs schema '{schema}', which is "
                        f"installable content — that is the STORE concept, not a published catalogue. "
                        f"Rename to 'Store' with '{STORE_ICON}' (ADR-080 D1)."
                    )
                elif entry.get("icon", "").startswith("icon-"):
                    findings.append(
                        f"WARN {rel}: catalogue entry '{entry.get('label')}' uses legacy CSS icon "
                        f"'{entry.get('icon')}' — migrate to '{CATALOGUE_ICON}' (NC34 invisible-glyph hazard)."
                    )

            elif label in TEMPLATE_LABELS and icon and icon != TEMPLATE_ICON:
                findings.append(
                    f"WARN {rel}: 'Templates' entry renders '{icon}' rather than '{TEMPLATE_ICON}'."
                )

    # Decision 3: no app-local re-implementation of store discovery.
    #
    # DIFF-SCOPED, like every other half of this gate.
    #
    # This scan used to walk the whole lib/ tree unconditionally while the
    # manifest half above honoured ADR-020. The combination is the worst of
    # both: the gate only RUNS when a manifest changed, and then judges code
    # the PR never touched. One pre-existing violation in pipelinq therefore
    # blocked EVERY manifest-touching PR in that repo, permanently, with a
    # finding naming a file outside the diff — and there is no action the
    # PR's author can take that is about their own change.
    #
    # Inherited debt in an untouched file is not this PR's to answer for
    # (ADR-020). It is still real; it surfaces on a full-tree run and on the
    # first PR that touches the file.
    lib = root / "lib"
    if lib.is_dir():
        for php in lib.rglob("*.php"):
            if php.name in {"GenericStoreService.php", "GenericStoreControllerBase.php"}:
                continue
            if changed is not None and str(php.relative_to(root)) not in changed:
                continue
            try:
                text = php.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            # A COMMENT MUST NOT MANUFACTURE A FINDING (#415/#423).
            #
            # This was a substring test over the RAW file, so the docblock
            #
            #     We deliberately do NOT hit /apps/openregister/api/objects/
            #     with an IClientService here — GenericStoreService owns
            #     store discovery (ADR-080 D2/D3).
            #
            # produced a finding IDENTICAL to the real violation's, naming a
            # file that does exactly what the gate wants. The author's
            # cheapest fix is to delete the paragraph recording the decision
            # — which is the same shape gate-64 was already repaired for
            # (doriath's `loadApp`), one gate over.
            #
            # STRING CONTENTS ARE KEPT (`blank_strings` at its default): the
            # URL this rule exists to find is a string literal in every real
            # violation, so blanking literals would delete the evidence and
            # turn the false positive into a false negative.
            code = php_mask(text)
            if "/apps/openregister/api/objects/" in code and (
                "IClientService" in code or "newClient()" in code
            ):
                findings.append(
                    f"FAIL {php.relative_to(root)}: builds and fetches an OpenRegister objects-API URL "
                    f"outside GenericStoreService — store discovery is OpenRegister's (ADR-080 D2/D3)."
                )


def check_settings(root: Path, manifests, findings) -> None:
    """ADR-079: app config lives in the NC settings framework."""
    for path, data in manifests:
        rel = path.relative_to(root)

        if isinstance(data.get("adminSettings"), list) and data["adminSettings"]:
            findings.append(
                f"FAIL {rel}: manifest declares adminSettings[] — the generic admin-settings modal is "
                f"removed; app configuration belongs in lib/Settings/*Admin.php (ADR-079 D2)."
            )

        for page in data.get("pages") or []:
            if not isinstance(page, dict) or page.get("type") != "settings":
                continue
            pid = str(page.get("id") or "").strip().lower()
            title = str(page.get("title") or "").strip().lower()
            if pid in RESERVED_SETTINGS_NAMES or title in RESERVED_SETTINGS_NAMES:
                findings.append(
                    f"FAIL {rel}: page '{page.get('id')}' is a type:settings page claiming the platform "
                    f"meaning of 'Settings'. App configuration lives at /settings/admin/<app>; a domain "
                    f"page that happens to be called settings must be renamed (ADR-079 D1)."
                )

        entries: list[dict] = []
        _walk_menu(data.get("menu"), entries)
        for entry in entries:
            if entry.get("section") == "settings":
                label = str(entry.get("label") or "").strip().lower()
                if label in RESERVED_SETTINGS_NAMES:
                    findings.append(
                        f"FAIL {rel}: settings-foldout entry is labelled '{entry.get('label')}' — the "
                        f"foldout button is already called Settings, so this renders Settings > Settings "
                        f"(ADR-079 D4)."
                    )

    layout = root / "src" / "menu-layout.json"
    data = _load(layout) if layout.is_file() else None
    if isinstance(data, dict):
        for entry_id in data.get("settingsSection") or []:
            if str(entry_id).strip().lower() in RESERVED_SETTINGS_NAMES:
                findings.append(
                    f"FAIL src/menu-layout.json: settingsSection lifts '{entry_id}' into the gear "
                    f"foldout, whose button is also called Settings (ADR-079 D4)."
                )

    # The duplicate-home WARN: an in-app settings page next to a real NC section.
    has_nc_section = any((root / "lib" / "Settings").glob("*.php")) if (root / "lib" / "Settings").is_dir() else False
    has_inapp = any(
        isinstance(p, dict) and p.get("type") == "settings"
        for _, d in manifests for p in (d.get("pages") or [])
    )
    if has_inapp and has_nc_section:
        findings.append(
            "WARN src/manifest.json: app ships an in-app type:settings page AND a lib/Settings/*Admin.php "
            "section — two homes for one concern; delete the in-app page (ADR-079 D1)."
        )
    if not has_nc_section and (root / "appinfo" / "info.xml").is_file():
        findings.append(
            "WARN lib/Settings: app registers no Nextcloud admin settings section, so it has no "
            "platform-authorized home for configuration (ADR-079 D1)."
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--gate", choices=("store", "settings"), required=True)
    ap.add_argument("--base", default=None)
    args = ap.parse_args()

    root = Path(args.root).resolve()
    manifest_paths = _manifest_paths(root)
    if not manifest_paths:
        print("No manifest — gate not applicable (Tier 0 app).")
        return EXIT_NOT_APPLICABLE

    changed = _changed_files(root, args.base)
    if changed is not None:
        scoped = [
            p for p in manifest_paths
            if str(p.relative_to(root)) in changed
        ]
        layout_changed = "src/menu-layout.json" in changed
        if not scoped and not layout_changed:
            # THIS BRANCH USED TO `return 0`, and the runner printed PASS. The
            # log line said "gate skipped" and the verdict line next to it said
            # PASS — the two contradicted each other on the same screen, and the
            # PASS is what every consumer counted. (.github#240)
            #
            # A full-tree audit was the one mode this gate could never reach:
            # the runner passed --base unconditionally, so even an unscoped run
            # landed here and reported a green over an unopened manifest.
            print(
                f"No changed manifest / menu-layout — EMPTY SCOPE (ADR-020 diff "
                f"scoping against '{args.base}'). {len(manifest_paths)} manifest(s) "
                f"exist here and NONE were inspected; this gate's placement rules "
                f"are UNVERIFIED by this run. This is not a pass. Omit --base to "
                f"audit the whole tree."
            )
            return EXIT_EMPTY_SCOPE
        manifest_paths = scoped or manifest_paths

    manifests = []
    for path in manifest_paths:
        data = _load(path)
        if data is None:
            print(f"FAIL {path.relative_to(root)}: unparseable JSON.")
            return 1
        manifests.append((path, data))

    findings: list[str] = []
    if args.gate == "store":
        check_store(root, manifests, findings, changed)
    else:
        check_settings(root, manifests, findings)

    for line in findings:
        print(line)

    hard = [f for f in findings if f.startswith("FAIL")]
    warn = [f for f in findings if f.startswith("WARN")]
    print(f"\nchecked {len(manifests)} manifest(s): {len(hard)} failure(s), {len(warn)} warning(s).")
    return EXIT_FAIL if hard else EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
