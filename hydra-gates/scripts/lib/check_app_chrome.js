#!/usr/bin/env node
// SPDX-License-Identifier: EUPL-1.2
//
// check_app_chrome.js — gate-107 (app-chrome) checker.
//
// Implements ADR-114: "The app chrome is seven items, and one gate says so."
//
// Seven things belong at the bottom-left of every Conduction app. CnAppNav
// draws two of them itself (Personal settings, Admin settings, ADR-079 /
// ADR-110 D2) and no app declares those. The other five are the app's own
// manifest declarations:
//
//   footer   Documentation        order  90   href to the app's docs site
//   footer   Store                order  92   type: "store"
//   footer   Reports              order  95   type: "reports"
//   footer   Features & roadmap   order 100   type: "roadmap"
//   settings Flows                             type: "flows"
//
// Measured 2026-09-03 across the 21 core apps: ONE carries all seven, and it
// is dossiq. Reports is in 3 of 19, Store in 4 of 19.
//
// WHY A NEW GATE, WHEN FOUR ALREADY READ THIS MENU.
// -------------------------------------------------
// Because every one of them is presence-blind. gate-60 validates the ICON on
// an entry that exists. gate-62 and gate-63 judge the NAMES of entries that
// exist. gate-104 states in its own header that it "does NOT require an app to
// HAVE a reports page" and answers NOT APPLICABLE when there is none. gate-53
// checks a declared entry RESOLVES, which cannot ask why an entry was never
// declared. Fifteen apps ship no Store and every gate is green.
//
// DETECTION IS BY PAGE TYPE, NOT BY LABEL.
// ----------------------------------------
// A label is not a reliable key. launchpad and humaniq ship i18n KEYS as
// labels ("launchpad.menu.dashboards"), dossiq's Reports entry has the id
// "AnalyticsGroup", and any of them may be translated. So four of the five
// items are resolved by following `entry.route` to a page and reading that
// page's `type`. Only Documentation has no page behind it (it is an href to a
// docs site), and it is matched on id/label as a documented exception.
//
// THE MENU WALK DESCENDS INTO children[].
// ---------------------------------------
// ADR-110's own fleet audit walked only top-level `menu[]` entries, read
// integriq's nested `Flows` as absent, and published a claim it then had to
// withdraw in the ADR itself. A nested entry renders; this gate sees it.
//
// THE RATCHET (ADR-114 Decision 8).
// ---------------------------------
// A hard gate on all five items would red every app on the day it ships, and a
// gate that blocks everything gets suppressed. So Documentation, Features &
// roadmap and Flows are blocking from day one (three apps short between them),
// while Store and Reports WARN until their rollouts land. Flip the two
// constants below to promote them; ADR-114 D8 commits to that edit.
//
// Usage:
//   node scripts/lib/check_app_chrome.js [--app-dir DIR]
//     --app-dir DIR    app repo root (default: CWD).
//
// Output: human diagnostics to stderr as `at <path>: <message>`; a JSON
// findings line and a JSON summary line to stdout; a terminal
// `[app-chrome] findings=N` marker on every completed run, so the wrapper can
// tell "ran and found N" from "did not finish".
//
// Exit codes:
//   0 — no blocking findings, or the app renders no manifest-driven UI
//   1 — at least one blocking finding
//   2 — checker misconfiguration (vendored builder missing)

'use strict'

const fs = require('fs')
const path = require('path')

let builder
try {
	builder = require('./build_effective_manifest.js')
} catch (e) {
	console.error(`[check_app_chrome] vendored builder missing next to this helper (${e.message}) — gate misconfiguration`)
	process.exit(2)
}

// --- the ratchet -------------------------------------------------------------
// ADR-114 Decision 8. Each of these is the one-line promotion the ADR commits
// to, taken once that item's fleet rollout has landed. Promoting an item makes
// BOTH its absence and its misplacement blocking, so an app is never hard-
// failed for putting a Store in the wrong place while fifteen others are
// merely warned for having none at all.
const STORE_IS_BLOCKING = false
const REPORTS_IS_BLOCKING = false

// ADR-110 Decision 4's three documented placement exceptions: these keep Flows
// in `main`. openregister owns the engine and its /flows is the unscoped
// fleet-wide view; hermiq authors flows as a core activity; integriq's Flows is
// a leaf of an Automation group whose other members are the same concern.
const FLOWS_IN_MAIN_ALLOWED = new Set(['openregister', 'hermiq', 'integriq'])

// --- argument parsing --------------------------------------------------------

let APP_DIR = process.cwd()
{
	const argv = process.argv.slice(2)
	for (let i = 0; i < argv.length; i++) {
		if (argv[i] === '--app-dir' && argv[i + 1]) { APP_DIR = path.resolve(argv[++i]); continue }
	}
}

const rel = path.relative(process.cwd(), APP_DIR) || '.'

/**
 * The app id from appinfo/info.xml, which is the only authority for it.
 *
 * Needed for two things: the Flows placement exceptions above, and the
 * hand-rolled Admin settings link, whose href is `/settings/admin/<appId>`.
 * An unreadable info.xml yields null, and both checks then decline to fire
 * rather than guessing an id.
 *
 * @param {string} root The app repo root.
 * @return {string|null} The declared app id, or null.
 */
function readAppId(root) {
	try {
		const xml = fs.readFileSync(path.join(root, 'appinfo', 'info.xml'), 'utf8')
		const m = xml.match(/<id>\s*([^<\s]+)\s*<\/id>/)
		return m ? m[1] : null
	} catch (e) {
		return null
	}
}

// --- assemble ----------------------------------------------------------------

let manifest
try {
	// assembleFromDir returns { manifest, inputs, expansion } — the assembled
	// manifest is NESTED. Reading .pages off the wrapper yields undefined, and
	// this gate would then call every app NOT APPLICABLE, which is a pass.
	// That defect shipped once already, in gate-104's first version.
	const assembled = builder.assembleFromDir(APP_DIR)
	manifest = (assembled && assembled.manifest) ? assembled.manifest : assembled
} catch (e) {
	console.error(`at ${rel}: could not assemble the effective manifest (${e.message})`)
	console.log(JSON.stringify({ status: 'failed', checked: 0, failed: 1 }))
	console.log('[app-chrome] findings=1')
	process.exit(1)
}

const pages = Array.isArray(manifest && manifest.pages) ? manifest.pages : []
const menu = Array.isArray(manifest && manifest.menu) ? manifest.menu : []
const appId = readAppId(APP_DIR)

// --- Decision 7: the exemption is measured, never listed ---------------------
//
// An app is out of scope when it renders no manifest-driven UI. The test is
// `pages.length === 0` on the EFFECTIVE manifest (the runner has already
// established that src/manifest.json exists, which is the other half).
//
// It is stated as a measurement rather than a list of app names because the
// list went stale and nobody noticed: ADR-110 named planninq a Tier-0 adopter
// while it shipped pages:[], it now ships nine pages, and its exemption had
// quietly lapsed. Naming the app instead of the property is what let that sit.
if (pages.length === 0) {
	console.error(`at ${rel}: NOT APPLICABLE — the effective manifest declares no pages, so this app renders no manifest-driven UI (ADR-040 Tier-0, ADR-114 Decision 7) and has no navigation for the chrome to sit in. Nothing was inspected. This is NOT evidence that the app's navigation is right.`)
	console.log(JSON.stringify({ status: 'passed', checked: 0, failed: 0 }))
	console.log('[app-chrome] findings=0')
	process.exit(0)
}

/**
 * Every menu entry, flattened, children included.
 *
 * @param {Array<object>} nodes The menu nodes.
 * @param {object|null} parent The parent node, if any.
 * @return {Array<object>} Flattened entries, each carrying its parent.
 */
function flatten(nodes, parent = null) {
	const out = []
	for (const node of nodes) {
		if (!node || typeof node !== 'object') { continue }
		out.push({ node, parent })
		for (const key of ['children', 'items']) {
			if (Array.isArray(node[key])) { out.push(...flatten(node[key], node)) }
		}
	}
	return out
}

const entries = flatten(menu)
const pageById = new Map()
for (const p of pages) {
	if (p && p.id) { pageById.set(p.id, p) }
}

/**
 * The page an entry routes to, if any.
 *
 * `route` names a page ID, not a path. An entry with an `href`, an `action`,
 * or nothing at all resolves to null and is classified by id/label instead.
 *
 * @param {object} node A menu entry.
 * @return {object|null} The page, or null.
 */
function pageOf(node) {
	return (node && node.route && pageById.get(node.route)) || null
}

/**
 * The section an entry renders in. An entry with no `section` renders in the
 * main navigation, so the default is not "unknown", it is "main".
 *
 * @param {object} node A menu entry.
 * @return {string} The section name.
 */
function sectionOf(node) {
	return typeof node.section === 'string' && node.section ? node.section : 'main'
}

/**
 * True when an entry looks like the Documentation link.
 *
 * Documentation is the one chrome item with no page behind it: it is an href
 * to the app's own docs site, so there is no `type` to read and it must be
 * matched on identity. Both an id and a label are accepted because an app may
 * translate the label, and launchpad and humaniq ship i18n keys as labels.
 *
 * @param {object} node A menu entry.
 * @return {boolean} Whether this is the Documentation entry.
 */
function isDocumentation(node) {
	const id = String(node.id || '')
	const label = String(node.label || '')
	if (/^documentation$/i.test(id)) { return true }
	if (/^(documentation|docs|documentatie)$/i.test(label.trim())) { return true }
	// An i18n-keyed label such as "launchpad.menu.documentation".
	if (/\.(documentation|docs)$/i.test(label.trim())) { return true }
	return Boolean(node.href) && /doc/i.test(id)
}

/**
 * True when a page is the app's flow index.
 *
 * Three shapes are live in the fleet and all three render the same surface:
 * `type: "flows"` (the dedicated type), and `type: "index"` over the named
 * `flows` entity source, which is what most apps adopted before the type
 * existed. Both are correct; ADR-110 Decision 4 is about the components and
 * the `app` scoping, not the spelling.
 *
 * @param {object} page A manifest page.
 * @return {boolean} Whether this page is a flow index.
 */
function isFlowsPage(page) {
	if (!page) { return false }
	if (page.type === 'flows') { return true }
	const src = page.config && page.config.entitySource
	return page.type === 'index' && src === 'flows'
}

const findings = []

/**
 * Record one finding.
 *
 * @param {string} severity Either "error" or "warning".
 * @param {string} item The chrome item this is about.
 * @param {string} message The diagnostic.
 * @return {void}
 */
function report(severity, item, message) {
	findings.push({ severity, path: rel, item, message })
}

// --- the five declared items -------------------------------------------------

const CHROME = [
	{
		item: 'Documentation',
		section: 'footer',
		blocking: true,
		find: () => entries.find(({ node }) => isDocumentation(node)),
		absent: 'no Documentation entry. ADR-114 Decision 1: an href to the app\'s own docs site, section:"footer", order 90. It is the one chrome item that leaves the app without being an Integrations link (ADR-110), because it does not leave for another app.',
	},
	{
		item: 'Store',
		section: 'footer',
		blocking: STORE_IS_BLOCKING,
		find: () => entries.find(({ node }) => {
			const p = pageOf(node)
			return (p && p.type === 'store') || /^(store|app store|marketplace)$/i.test(String(node.label || '').trim())
		}),
		absent: 'no Store entry. ADR-114 Decision 4: section:"footer", order 92, over a type:"store" page. ADR-080 Decision 4 still governs what may carry the word: registry-backed via GenericStoreService, and with no registry configured it renders the app\'s built-in items and makes no network call.',
	},
	{
		item: 'Reports',
		section: 'footer',
		blocking: REPORTS_IS_BLOCKING,
		find: () => entries.find(({ node }) => {
			const p = pageOf(node)
			return Boolean(p) && p.type === 'reports'
		}),
		absent: 'no Reports entry. ADR-114 Decision 3 amends ADR-112 Decision 4: the title of that ADR wins, and every app in scope declares one type:"reports" page in section:"footer" at order 95. An empty Reports page is still forbidden, so an app with nothing to report fills the page rather than skipping it.',
	},
	{
		item: 'Features & roadmap',
		section: 'footer',
		blocking: true,
		find: () => entries.find(({ node }) => {
			const p = pageOf(node)
			return Boolean(p) && p.type === 'roadmap'
		}),
		absent: 'no Features & roadmap entry. ADR-018 requires it in every app and ADR-114 Decision 5 repeals the clause that forbade gates from enforcing that.',
	},
	{
		item: 'Flows',
		section: 'settings',
		blocking: true,
		find: () => entries.find(({ node }) => isFlowsPage(pageOf(node))),
		absent: 'no Flows entry. ADR-110 Decision 4: every app with a manifest-driven UI hosts its own /flows and /flows/:id on the shared CnFlowIndexPage and CnFlowDetail, scoped app:"<appId>", with the entry in the settings foldout. A flow is app-specific, so the authoring surface belongs in the app whose objects it drives.',
	},
]

for (const spec of CHROME) {
	const severity = spec.blocking ? 'error' : 'warning'
	const hit = spec.find()

	if (hit === undefined) {
		report(severity, spec.item, spec.absent)
		continue
	}

	const section = sectionOf(hit.node)
	if (section === spec.section) { continue }

	// ADR-110 Decision 4's three documented exceptions keep Flows in `main`.
	if (spec.item === 'Flows' && section === 'main' && appId && FLOWS_IN_MAIN_ALLOWED.has(appId)) {
		continue
	}

	report(severity, spec.item, `the ${spec.item} entry is section:${JSON.stringify(hit.node.section ?? null)}, not ${JSON.stringify(spec.section)}. ADR-114 Decision 1 fixes the sections so the bottom-left of the navigation reads the same in every app.`)
}

// --- Decision 2: the shell draws Admin settings, and no app declares it ------
//
// A hand-rolled copy renders twice for an instance admin, and once for a user
// who cannot use it: the app's own entry misses the isAdmin gating CnAppNav
// applies to the entry it prepends. This is live, not hypothetical. shillinq
// declares `GeneralSettings` at /index.php/settings/admin/shillinq.
if (appId) {
	const adminHref = new RegExp(`^(?:/index\\.php)?/settings/admin/${appId.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}/?$`)
	for (const { node } of entries) {
		if (typeof node.href !== 'string' || !adminHref.test(node.href.trim())) { continue }
		report('error', 'Admin settings', `menu entry ${JSON.stringify(node.id || node.label || node.href)} hand-rolls the Admin settings link (${node.href}). CnAppNav auto-prepends that link for instance admins, so this is a second copy of it, and the copy misses the shell's isAdmin gating: it renders for users who cannot open it. ADR-110 Decision 2 and ADR-114 Decision 2: delete the entry, the capability is already there.`)
	}
}

// --- output ------------------------------------------------------------------

for (const f of findings) {
	console.error(`at ${f.path}: [${f.severity}] ${f.item}: ${f.message}`)
}

const blocking = findings.filter((f) => f.severity === 'error')
const warned = findings.filter((f) => f.severity === 'warning')

if (findings.length > 0) {
	console.log(JSON.stringify({ file: rel, schemaVersion: 'v2-effective', findings }))
}

// THE COUNT IS PRINTED ON EVERY RUN, PASSING OR FAILING (ADR-114 D8). A gate
// that is silent when it passes cannot be shown to have run, and this one's
// whole value is the number it carries.
console.error(`at ${rel}: app-chrome: ${CHROME.length - findings.filter((f) => f.item !== 'Admin settings').length} of ${CHROME.length} declared chrome items present and correctly placed.`)

console.log(JSON.stringify({ status: blocking.length > 0 ? 'failed' : 'passed', checked: CHROME.length, failed: blocking.length, warned: warned.length }))
console.log(`[app-chrome] findings=${blocking.length} warnings=${warned.length}`)
process.exit(blocking.length > 0 ? 1 : 0)
