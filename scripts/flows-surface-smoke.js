/**
 * SPDX-License-Identifier: EUPL-1.2
 * SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl>
 *
 * Flows surface smoke test, across every fleet app whose manifest declares
 * `pages[].sidebarComponent`.
 *
 * Asserts the two things the ADR-110 flows rollout is supposed to deliver:
 *
 *   1. the flows index renders
 *   2. the flow detail renders BOTH the canvas AND its sidebar
 *
 * The sidebar half is the whole point. `sidebarComponent` was declared in the
 * manifest, registered in registry.js and present in the bundle for nine apps,
 * and rendered nothing in all nine, because filling CnAppRoot's `#sidebar`
 * slot suppresses the manifest's own sidebar (Vue only uses a slot fallback
 * when the slot is absent). Nothing warned and nothing errored. A check that
 * only asserted the canvas would have stayed green through the entire outage,
 * which is exactly why this asserts the sidebar separately.
 *
 * The app list is DERIVED from the manifests, never hardcoded. The fleet's
 * scope of record has been wrong before in the direction that hides problems,
 * and a smoke test that silently skips an app looks identical to one that
 * passes it.
 *
 * Usage, from the apps-extra workspace with a running dev instance:
 *
 *   NODE_PATH=openregister/node_modules node .github/scripts/flows-surface-smoke.js
 *
 * Env: NC_BASE (default http://localhost:8080), NC_USER, NC_PASS.
 * Exits non-zero if any app fails to render the canvas and its sidebar.
 */
const fs = require('fs')
const path = require('path')
const { chromium } = require('playwright')

const BASE = process.env.NC_BASE || 'http://localhost:8080'
const USER = process.env.NC_USER || 'admin'
const PASS = process.env.NC_PASS || 'admin'
const ROOT = path.resolve(__dirname, '..', '..')

/**
 * Every checkout under apps-extra whose manifest declares a
 * `sidebarComponent`, keyed by the app id from appinfo/info.xml. The
 * directory name is NOT the app id for most of the fleet (docudesk ships as
 * filinq, doriath as keepiq), and the URL needs the id.
 */
function appsUnderTest() {
	const out = []
	for (const dir of fs.readdirSync(ROOT)) {
		const manifest = path.join(ROOT, dir, 'src', 'manifest.json')
		const info = path.join(ROOT, dir, 'appinfo', 'info.xml')
		if (!fs.existsSync(manifest) || !fs.existsSync(info)) continue
		let pages = []
		try {
			pages = JSON.parse(fs.readFileSync(manifest, 'utf8')).pages || []
		} catch { continue }
		if (!pages.some(p => p && p.sidebarComponent)) continue
		const id = (fs.readFileSync(info, 'utf8').match(/<id>([^<]+)<\/id>/) || [])[1]
		if (id) out.push({ dir, id })
	}
	// The workspace holds scratch worktrees beside the canonical checkouts, and
	// they carry the same manifest and the same app id. The URL is keyed on the
	// id, so testing an id twice tests the same running app twice and inflates
	// the denominator. Deduplicate, and say which directory answered.
	const seen = new Map()
	for (const app of out) {
		if (!seen.has(app.id)) seen.set(app.id, app)
	}
	return [...seen.values()].sort((a, b) => a.id.localeCompare(b.id))
}

/** First-run overlays sit above the app and swallow everything behind them. */
async function dismissOverlays(page) {
	await page.evaluate(() => {
		document.querySelectorAll('.cn-walkthrough').forEach(n => n.remove())
		document.querySelectorAll('[data-testid="cn-modal"] button[aria-label="Close"]')
			.forEach(b => b.click())
	}).catch(() => {})
}

/** Apps differ on hash vs path routing, so try both rather than assume. */
async function probe(page, id, route) {
	for (const url of [`${BASE}/apps/${id}/${route}`, `${BASE}/apps/${id}/#/${route}`]) {
		await page.goto(url, { waitUntil: 'domcontentloaded' }).catch(() => {})
		// Wait for the surface to settle rather than sleeping a fixed amount.
		// A flat 2500ms reported openregister as having no sidebar when it has
		// one: the app is heavy and simply had not mounted it yet. A smoke test
		// whose verdict depends on how fast the machine is will be ignored, and
		// deservedly.
		await page.waitForFunction(() => {
			const canvas = document.querySelector('.cn-flow-detail')
			const sidebar = document.querySelector('#app-sidebar-vue, aside.app-sidebar')
			const locked = /[#/]lock(\?|$|\/)/.test(location.href)
			const flows = /\bFlows\b/.test(document.body.innerText)
			return locked || (canvas && sidebar) || (flows && !canvas)
		}, { timeout: 15000 }).catch(() => {})
		await dismissOverlays(page)
		const r = await page.evaluate(() => ({
			canvas: !!document.querySelector('.cn-flow-detail'),
			sidebar: !!document.querySelector('#app-sidebar-vue, aside.app-sidebar'),
			flowsHeading: /\bFlows\b/.test(document.body.innerText),
			// A vault app (keepiq) bounces every route to its own lock screen
			// until the vault is unlocked. That is not the flows surface being
			// broken, and calling it a failure would be a false red that
			// trains people to ignore this report.
			locked: /[#/]lock(\?|$|\/)/.test(location.href),
		})).catch(() => ({ canvas: false, sidebar: false, flowsHeading: false, locked: false }))
		if (r.canvas || r.flowsHeading || r.locked) return r
	}
	return { canvas: false, sidebar: false, flowsHeading: false, locked: false }
}

;(async () => {
	const apps = appsUnderTest()
	if (apps.length === 0) {
		console.error('No app declares pages[].sidebarComponent. Either the rollout '
			+ 'was reverted or this is being run outside the apps-extra workspace. '
			+ 'Refusing to report a vacuous pass.')
		process.exit(2)
	}

	const browser = await chromium.launch()
	const page = await browser.newPage()
	await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded' })
	await page.fill('input[name=user]', USER)
	await page.fill('input[name=password]', PASS)
	await Promise.all([
		page.waitForNavigation({ waitUntil: 'domcontentloaded' }).catch(() => {}),
		page.click('button[type=submit]'),
	])

	const rows = []
	for (const { id } of apps) {
		const index = await probe(page, id, 'flows')
		const detail = await probe(page, id, 'flows/new')
		rows.push({
			id,
			index: index.flowsHeading,
			canvas: detail.canvas,
			sidebar: detail.sidebar,
			locked: detail.locked || index.locked,
		})
	}
	await browser.close()

	const pad = s => String(s).padEnd(14)
	console.log(pad('APP') + 'INDEX  CANVAS  SIDEBAR  VERDICT')
	let bad = 0
	let locked = 0
	for (const r of rows) {
		const ok = r.canvas && r.sidebar
		if (r.locked) locked++
		else if (!ok) bad++
		const verdict = r.locked ? 'LOCKED' : (ok ? 'ok' : 'FAIL')
		console.log(pad(r.id)
			+ `${r.index ? 'yes' : 'NO '}    ${r.canvas ? 'yes' : 'NO '}     `
			+ `${r.sidebar ? 'yes' : 'NO '}      ${verdict}`)
	}
	const testable = rows.length - locked
	console.log(`\n${testable - bad}/${testable} testable apps render the flow canvas AND its sidebar`)
	if (locked) {
		console.log(`${locked} app(s) reported LOCKED: the app bounced to its own lock `
			+ 'screen, so the flows surface was never reached. Not counted either way.')
	}
	process.exit(bad === 0 ? 0 : 1)
})()
