#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""
Gate 104 — duplicate-page-refresh.

Every page surface built on `CnDashboardPage` / `CnDetailPage` already ships a
Refresh. `CnActionsMenu` renders it as the FIRST item of the page-level ...
Actions overflow menu, ahead of the mandatory trio (Request a feature / Report
a bug / Documentation), and the page passes `show-refresh="showRefresh"` with
`showRefresh` defaulting to TRUE. So a surface that also declares a Refresh of
its own ships two Refreshes, side by side, doing the same thing.

MEASURED 2026-08-31, after a user reported the dossiq dashboard showing
"Refresh" as a toolbar button AND "Refresh" as the first Actions-menu item.
Five surfaces across the fleet had it:

    dossiq (procest)   Dashboard  manifest headerActions `dashboard-refresh`
    hermiq             Dashboard  manifest headerActions `dashboard-refresh`
    larpinq            Dashboard  manifest headerActions `refresh-dashboard`
    opencatalogi       Dashboard  Vue `#actions` slot button
    shillinq           BBV        Vue `#header-actions` slot button

openregister's dashboard was the one clean case, and it shows the supported
way out: it keeps its own prominent button and passes `:showRefresh="false"`
so the menu item stands down. Either shape is fine. Shipping BOTH is not.

THE MANIFEST CASE IS A PURE DUPLICATE. A `"type": "refresh"` headerAction is
dispatched by `actionsDispatcher.js` as `emit(PAGE_REFRESH_CHANNEL, {})` — the
exact signal `CnActionsMenu` broadcasts on `refresh-channel="cn:page:refresh"`.
Same channel, same subscribers, same effect. Nothing is lost by removing it.

THE VUE CASE IS USUALLY WORSE THAN A DUPLICATE. On both apps found, the
hand-written button called a host method (`loadDashboardData`, `loadProgrammes`)
that was NOT subscribed to `cn:page:refresh`. So the two Refreshes were not
even equivalent: the app's button worked and the menu's did nothing at all.
Removing the button without wiring `@refresh` would have left only the dead
one, which is why this gate names the `@refresh` listener in its remedy.

WHY A GATE. Nothing downstream reads a page's action list for redundancy.
`check:manifest` validates against a JSON Schema, and a schema cannot know
that the component rendering the page contributes an item of its own. The only
detector was a person looking at the screen and counting.

WHAT IS CHECKED.

  * Manifest — `src/manifest.json` and `src/manifest.d/*.json`. Any object
    carrying a `headerActions` / `pageActions` list is a page surface. It
    fails when one of those actions has `"type": "refresh"` while the same
    object does not set `"showRefresh": false`.

  * Vue — `src/**/*.vue`. A file mounting `<CnDashboardPage>` / `<CnDetailPage>`
    without a false `show-refresh` fails when its `#actions` / `#header-actions`
    slot contains a Refresh control (a `<Refresh>` icon, or a `Refresh` label).

WHAT IS NOT CHECKED. Per-WIDGET Refresh items (`CnWidgetWrapper`, and the
`widgetShowRefresh` tri-state) — a widget's own Refresh is a different scope
from the page's, and a page-level button beside per-widget menus is not a
duplicate. Actions that merely use `"icon": "Refresh"` for something else are
untouched: shillinq's `renew-consent` action is a legitimate use of the icon.
HTML comments are stripped before the Vue scan, so prose about Refresh in a
comment cannot produce a finding.

FULL-TREE, not diff-scoped, for the reason gates 84 and 93 through 96 give: the
duplicates are already in the tree, and a diff-scoped version reports clean on
every PR that does not happen to touch that page.
"""

import glob
import json
import os
import re
import sys

# Page hosts that mount CnActionsMenu with a page-level `showRefresh` that
# defaults to true. CnWidgetWrapper and the widget renderers are deliberately
# absent: their Refresh is per-widget, a different scope from the page's.
PAGE_HOSTS = ("CnDashboardPage", "CnDetailPage")

# The two slots those hosts render beside the Actions menu. Both are real:
# CnDashboardPage declares `<slot name="header-actions" />` and
# `<slot name="actions" />` on adjacent lines.
ACTION_SLOTS = ("actions", "header-actions")

# Action lists that populate the page header. `actions` is deliberately NOT
# here: on a detail page that key holds OBJECT actions (approve, renew consent)
# which are not page-header controls.
ACTION_KEYS = ("headerActions", "pageActions")

# Manifest page types the shell renders through a host that mounts
# CnActionsMenu. These count as inspected surfaces even when they declare no
# action list at all: seven fleet apps ship dashboard pages with no
# headerActions, and counting only pages that HAVE an action list reported
# "checked 0" over them — indistinguishable from an app with no pages, which
# is the empty-scope defect .github#374 exists to stop.
PAGE_TYPES = ("dashboard", "detail")

SKIP_DIRS = {
    "node_modules", "vendor", ".git", "dist", "js", "build",
    "coverage", "test-results", "playwright-report",
}

_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_TEMPLATE_TAG_RE = re.compile(r"</?template\b")


def _is_false(value):
    """True when a manifest/Vue value explicitly says false."""
    return value is False or (isinstance(value, str) and value.strip().lower() == "false")


# --------------------------------------------------------------------------
# Manifest side
# --------------------------------------------------------------------------

def _walk_manifest(node, where, page_id, hits, counter, page_counted=False):
    """Recursively find page-surface objects and check their action lists.

    `page_counted` carries down from an enclosing typed page so one page is
    counted once. `type` sits on the page object and `headerActions` inside its
    `config` child, so without the flag every typed page with an action list
    would be counted twice.
    """
    if isinstance(node, list):
        for item in node:
            _walk_manifest(item, where, page_id, hits, counter, page_counted)
        return
    if not isinstance(node, dict):
        return

    # A page's `id` sits one level above its `config`, so carry it down for
    # a finding that names the page rather than just the file.
    here_id = node.get("id") if isinstance(node.get("id"), str) else page_id

    # A typed page is a surface whether or not it declares an action list.
    if not page_counted and node.get("type") in PAGE_TYPES and isinstance(node.get("route"), str):
        counter[0] += 1
        page_counted = True

    for key in ACTION_KEYS:
        actions = node.get(key)
        if not isinstance(actions, list):
            continue
        if not page_counted:
            counter[0] += 1
            page_counted = True
        if _is_false(node.get("showRefresh")):
            continue
        for action in actions:
            if not isinstance(action, dict):
                continue
            if action.get("type") != "refresh":
                continue
            hits.append((
                where,
                "page %s: %s[] declares a \"type\": \"refresh\" action (id %s) "
                "while showRefresh is not false" % (
                    here_id or "<unnamed>", key, action.get("id") or "<unnamed>",
                ),
            ))

    for value in node.values():
        _walk_manifest(value, where, here_id, hits, counter, page_counted)


def _manifest_files(root):
    files = []
    primary = os.path.join(root, "src", "manifest.json")
    if os.path.isfile(primary):
        files.append(primary)
    files.extend(sorted(glob.glob(os.path.join(root, "src", "manifest.d", "*.json"))))
    return files


# --------------------------------------------------------------------------
# Vue side
# --------------------------------------------------------------------------

def _opening_tag(text, start):
    """Return the text of the tag opened at `start`, quote-aware.

    A naive search for the next '>' stops inside `:options="{ a: '>' }"`, which
    is common in these templates. Track quoting so the attribute block that
    carries show-refresh is read in full.
    """
    quote = None
    i = start
    while i < len(text):
        char = text[i]
        if quote:
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif char == ">":
            return text[start:i]
        i += 1
    return text[start:]


def _slot_blocks(text, names):
    """Return the bodies of `<template #name>` blocks, nesting-aware.

    The slots hold NcButtons whose own `<template #icon>` closes with
    `</template>` first, so matching to the nearest close truncates the block
    before the control this gate is looking for. Count depth instead.
    """
    blocks = []
    pattern = re.compile(r"<template\s+#(?:%s)\b[^>]*>" % "|".join(
        re.escape(name) for name in names))
    for match in pattern.finditer(text):
        start = match.end()
        depth = 1
        pos = start
        while depth > 0:
            tag = _TEMPLATE_TAG_RE.search(text, pos)
            if tag is None:
                break
            if text[tag.start():tag.start() + 2] == "</":
                depth -= 1
                if depth == 0:
                    blocks.append(text[start:tag.start()])
                    break
            else:
                depth += 1
            pos = tag.end()
    return blocks


def _has_refresh_control(block):
    """True when a slot body renders something a user would read as Refresh."""
    if re.search(r"<Refresh\b", block):
        return True
    # A translated or literal label: t('app', 'Refresh'), >Refresh<, "Refresh…"
    if re.search(r"['\"]Refresh\b", block):
        return True
    if re.search(r">\s*Refresh\s*<", block):
        return True
    return False


def _vue_files(root):
    src = os.path.join(root, "src")
    found = []
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(".vue"):
                found.append(os.path.join(dirpath, name))
    return sorted(found)


def _check_vue(path, where, hits, counter):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = handle.read()
    except OSError as exc:
        print("SKIP %s: unreadable (%s)" % (where, exc))
        return

    if not any(("<%s" % host) in raw for host in PAGE_HOSTS):
        return

    text = _COMMENT_RE.sub("", raw)

    for host in PAGE_HOSTS:
        for match in re.finditer(r"<%s\b" % host, text):
            counter[0] += 1
            tag = _opening_tag(text, match.start())
            # `:showRefresh="false"`, `:show-refresh="false"`, `show-refresh="false"`
            if re.search(r":?show-?[Rr]efresh\s*=\s*[\"']\s*false\s*[\"']", tag):
                continue
            for block in _slot_blocks(text, ACTION_SLOTS):
                if _has_refresh_control(block):
                    hits.append((
                        where,
                        "<%s> renders a Refresh control in its %s slot while "
                        "showRefresh is not false" % (
                            host, " / ".join("#" + s for s in ACTION_SLOTS),
                        ),
                    ))
                    break


# --------------------------------------------------------------------------

def main(argv):
    root = argv[1] if len(argv) > 1 else "."
    root = os.path.abspath(root)

    hits = []
    counter = [0]

    for path in _manifest_files(root):
        where = os.path.relpath(path, root)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError) as exc:
            # A manifest that will not parse is gate-manifest-validation's
            # finding, not this gate's. Say so and keep going rather than
            # reporting a verdict over a file never read.
            print("SKIP %s: unreadable (%s)" % (where, exc))
            continue
        _walk_manifest(data, where, None, hits, counter)

    for path in _vue_files(root):
        _check_vue(path, os.path.relpath(path, root), hits, counter)

    if counter[0] == 0:
        print("checked 0 page surface(s)")
        return 4

    for where, reason in hits:
        print("FAIL %s: %s" % (where, reason))

    if hits:
        print("")
        print("CnActionsMenu already renders Refresh as the first item of the")
        print("page-level Actions menu, and showRefresh defaults to true.")
        print("Pick ONE:")
        print("  * drop the app's own Refresh (the manifest action, or the")
        print("    button in the #actions / #header-actions slot). For a Vue")
        print("    surface, wire @refresh on the page host to the method that")
        print("    button called, or the remaining Refresh does nothing.")
        print("  * keep the button and stand the menu item down with")
        print("    showRefresh: false (manifest config key, or the prop).")

    print("checked %d page surface(s)" % counter[0])
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
