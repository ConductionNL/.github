#!/usr/bin/env node
// SPDX-License-Identifier: EUPL-1.2
//
// check_reports_one_page.js — gate (reports-one-page) checker.
//
// Implements ADR-112: "Reports are one page of cards, in the footer, in every
// app." Reports arrive one at a time, each one is obviously a menu item, and
// the menu is where the last one went — so a Reports branch grows an entry per
// report and never loses one. shillinq reached 96 report types.
//
// Checks three structural things against the app's EFFECTIVE manifest (base
// src/manifest.json + src/manifest.d/*.json + src/menu-layout.json, assembled
// by build_effective_manifest.js):
//
//   1. AT MOST ONE `type: "reports"` page. Two reports pages is the submenu
//      problem again, one level down.
//   2. The menu entry pointing at it is `section: "footer"` (ADR-112 D3).
//   3. No OTHER menu entry points at a page that the reports page already
//      lists as a card. That is the duplication the ADR exists to remove: the
//      report is reachable twice, and the menu copy is the one that never
//      shrinks.
//
// WHAT IT DELIBERATELY DOES NOT CHECK.
//
// It does NOT require an app to HAVE a reports page. ADR-112 Decision 4 is
// explicit: the rule is "one page if you have reports", not "a Reports page in
// all twenty-one apps", because an empty Reports page is a promise the app
// does not keep. An app with no `type:"reports"` page is NOT APPLICABLE here,
// and this gate says so rather than passing silently — a gate that reports
// "passed" for an app it never inspected is how a fleet sweep learns nothing.
//
// It does NOT check that a card's route exists or is reachable. gate-53's
// reachability walk already does that, against the same effective manifest,
// and a second disagreeing implementation of the same question is worse than
// none.
//
// It does NOT judge whether a report is useful or its description accurate.
// Those are review judgements and the gate would only be guessing.
//
// Usage:
//   node scripts/lib/check_reports_one_page.js [--app-dir DIR]
//     --app-dir DIR    app repo root (default: CWD).
//
// Output: human diagnostics to stderr as `at <path>: <message>`; a JSON
// findings line and a JSON summary line to stdout; a terminal
// `[reports-one-page] findings=N` marker on every completed run, so the
// wrapper can tell "ran and found N" from "did not finish".
//
// Exit codes:
//   0 — no findings, or the app declares no reports page (not applicable)
//   1 — at least one finding
//   2 — checker misconfiguration (vendored builder missing)

'use strict'

const path = require('path')

let builder
try {
	builder = require('./build_effective_manifest.js')
} catch (e) {
	console.error(`[check_reports_one_page] vendored builder missing next to this helper (${e.message}) — gate misconfiguration`)
	process.exit(2)
}

// --- argument parsing --------------------------------------------------------

let APP_DIR = process.cwd()
{
	const argv = process.argv.slice(2)
	for (let i = 0; i < argv.length; i++) {
		if (argv[i] === '--app-dir' && argv[i + 1]) { APP_DIR = path.resolve(argv[++i]); continue }
	}
}

// --- assemble ----------------------------------------------------------------

let manifest
try {
	// assembleFromDir returns { manifest, inputs, expansion } — the assembled
	// manifest is NESTED. Reading .pages off the wrapper yields undefined, and
	// this gate then calls every app NOT APPLICABLE, which is a pass. That is
	// exactly the shape of failure the fixtures below exist to catch.
	const assembled = builder.assembleFromDir(APP_DIR)
	manifest = (assembled && assembled.manifest) ? assembled.manifest : assembled
} catch (e) {
	console.error(`at ${APP_DIR}: could not assemble the effective manifest (${e.message})`)
	console.log(JSON.stringify({ status: 'failed', checked: 0, failed: 1 }))
	console.log('[reports-one-page] findings=1')
	process.exit(1)
}

const pages = Array.isArray(manifest && manifest.pages) ? manifest.pages : []
const menu = Array.isArray(manifest && manifest.menu) ? manifest.menu : []

/**
 * Every menu entry, flattened — children included.
 *
 * A report entry nested under a Reports PARENT is exactly the shape ADR-112
 * retires, so a walk that only looked at top-level entries would miss the
 * case the gate exists for.
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
const reportsPages = pages.filter((p) => p && p.type === 'reports')

const findings = []
const rel = path.relative(process.cwd(), APP_DIR) || '.'

if (reportsPages.length === 0) {
	// NOT APPLICABLE, said out loud. ADR-112 Decision 4.
	console.error(`at ${rel}: NOT APPLICABLE — the app declares no type:"reports" page, and ADR-112 Decision 4 does not require one of an app with no reports.`)
	console.log(JSON.stringify({ status: 'passed', checked: 0, failed: 0 }))
	console.log('[reports-one-page] findings=0')
	process.exit(0)
}

if (reportsPages.length > 1) {
	findings.push({
		severity: 'error',
		path: rel,
		pageIds: reportsPages.map((p) => p.id),
		message: `${reportsPages.length} type:"reports" pages (${reportsPages.map((p) => p.id).join(', ')}); ADR-112 Decision 1 allows one. Two reports pages is the submenu problem one level down.`,
	})
}

const reportsPage = reportsPages[0]

// 2. Its menu entry sits in the footer group.
const reportsEntry = entries.find(({ node }) => node.route === reportsPage.id)
if (reportsEntry === undefined) {
	findings.push({
		severity: 'error',
		path: rel,
		pageIds: [reportsPage.id],
		message: `the type:"reports" page "${reportsPage.id}" has no menu entry, so nothing reaches it. ADR-112 Decision 3 puts one in the footer group.`,
	})
} else if (reportsEntry.node.section !== 'footer') {
	findings.push({
		severity: 'error',
		path: rel,
		pageIds: [reportsPage.id],
		message: `the Reports menu entry is section:${JSON.stringify(reportsEntry.node.section ?? null)}, not "footer". ADR-112 Decision 3: Reports is a place you go deliberately, not a place you work, so it belongs with Documentation and Features & roadmap rather than among the operational entries.`,
	})
}

// 3. No other menu entry points at a page the reports page already carries.
const cards = Array.isArray(reportsPage.config && reportsPage.config.cards) ? reportsPage.config.cards : []
const carded = new Set(cards.map((c) => c && c.route).filter(Boolean))

for (const { node } of entries) {
	if (!node.route || node.route === reportsPage.id) { continue }
	if (!carded.has(node.route)) { continue }

	findings.push({
		severity: 'error',
		path: rel,
		pageIds: [node.route],
		message: `menu entry ${JSON.stringify(node.label || node.route)} points at "${node.route}", which the Reports page already lists as a card. ADR-112 Decision 2: a report is a card OR a menu entry, not both — retire the menu entry in src/menu-layout.json under "removals"; the page stays routable.`,
	})
}

for (const f of findings) {
	console.error(`at ${f.path}: ${f.message}`)
}

const failed = findings.length > 0 ? 1 : 0
if (findings.length > 0) {
	console.log(JSON.stringify({ file: rel, schemaVersion: 'v2-effective', findings }))
}
console.log(JSON.stringify({ status: failed === 1 ? 'failed' : 'passed', checked: 1, failed }))
console.log(`[reports-one-page] findings=${findings.length}`)
process.exit(failed)
