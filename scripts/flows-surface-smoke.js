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

/**
 * Vault apps (keepiq) gate every route behind a master password. `isLocked` is
 * purely `cryptoKey === null` in the browser and the password never reaches the
 * server, so no config key or occ command can wave this through: the only way
 * past it is to type the password.
 *
 * Two screens, because the vault may not exist yet:
 *   "Set up your master password" -> two fields, creates the vault (12 char min)
 *   "Unlock Keepiq"               -> one field, unlocks the session
 *
 * The lock ROUTE resolves before the lock FORM mounts, so this waits for the
 * field rather than the URL. Waiting on the URL alone found zero password
 * inputs, filled nothing, and left the app reported LOCKED with the unlock
 * never actually attempted.
 *
 * NC_VAULT_PASS is a dev-instance credential and nothing else. It exists so a
 * vault app's flows surface is asserted rather than skipped, which is the
 * difference between a report covering 14 apps and one quietly covering 13.
 *
 * @param {import('playwright').Page} page The logged-in page sitting on a lock screen.
 * @return {Promise<boolean>} True if an unlock was attempted.
 */
async function unlockVaultIfPrompted(page) {
	const pass = process.env.NC_VAULT_PASS || 'admin-admin-keepiq'
	const first = page.locator('input[type=password]').first()
	await first.waitFor({ state: 'visible', timeout: 15000 }).catch(() => {})
	if (!(await first.isVisible().catch(() => false))) return false

	await first.fill(pass).catch(() => {})
	// A second password field means this is the create-the-vault screen.
	const confirm = page.locator('input[type=password]').nth(1)
	if (await confirm.count().catch(() => 0)) {
		await confirm.fill(pass).catch(() => {})
	}

	// Match the submit by SHAPE, not by its label. An earlier version looked for
	// /^(Unlock|Set up vault)$/, which silently found nothing on a Dutch instance
	// rendering "Kluis instellen": the click never fired and keepiq was reported
	// LOCKED, which reads as "app gated its own surface" rather than "the test
	// could not press the button". A label match is a language assertion, and
	// this suite has no business asserting the instance's language.
	//
	// The submit is the one button in the lock panel that starts disabled and
	// becomes enabled once the password validates; the only other buttons there
	// are the password-visibility toggles, which are never disabled.
	await page.waitForFunction(() => {
		const inPanel = [...document.querySelectorAll('main button, [role=main] button')]
		const b = inPanel.filter(x => !x.closest('[class*=visibility], [class*=toggle]')).pop()
		return b && !b.disabled
	}, { timeout: 10000 }).catch(() => {})

	await page.evaluate(() => {
		const inPanel = [...document.querySelectorAll('main button, [role=main] button')]
		const b = inPanel.filter(x => !x.closest('[class*=visibility], [class*=toggle]')).pop()
		if (b && !b.disabled) b.click()
	}).catch(() => {})
	await page.waitForFunction(
		() => !/[#/]lock(\?|$|\/)/.test(location.href),
		{ timeout: 15000 },
	).catch(() => {})
	return true
}

/** First-run overlays sit above the app and swallow everything behind them. */
async function dismissOverlays(page) {
	await page.evaluate(() => {
		document.querySelectorAll('.cn-walkthrough').forEach(n => n.remove())

		// The NON-GATING optional-setup wizard (REQ-SETUP-NV-012) auto-opens
		// once per manifest `setup.version` whenever a step marked optional is
		// still unmet, and records its dismissal in localStorage. Playwright
		// starts from a fresh profile every run, so that dismissal never
		// carries over and the wizard reopens on every navigation, covering
		// the canvas. opencatalogi reported INDEX yes / CANVAS no for exactly
		// this reason, with its own API answering `completed: true`.
		//
		// Only `__setup-optional` is removed. The GATING surface renders as
		// `cn-app-root__setup` and means a REQUIRED step is unmet — the app
		// genuinely is not set up, and removing that would fake a pass on an
		// app that cannot work.
		document.querySelectorAll('.cn-app-root__setup-optional').forEach(n => n.remove())

		document.querySelectorAll('[data-testid="cn-modal"] button[aria-label="Close"]')
			.forEach(b => b.click())
	}).catch(() => {})
}

/** Apps differ on hash vs path routing, so try both rather than assume. */
async function probe(page, id, route) {
	for (const url of [`${BASE}/apps/${id}/${route}`, `${BASE}/apps/${id}/#/${route}`]) {
		await page.goto(url, { waitUntil: 'domcontentloaded' }).catch(() => {})
		// A vault's crypto key lives in memory only, so every full page load
		// re-locks it. Unlocking once per app is not enough: it has to happen
		// after each navigation. The lock screen carries `?returnUrl=`, so the
		// app returns to the route we asked for once it opens.
		await page.waitForFunction(
			() => /[#/]lock(\?|$|\/)/.test(location.href)
				|| document.querySelector('main h1, main h2, .cn-flow-detail'),
			{ timeout: 10000 },
		).catch(() => {})
		if (/[#/]lock(\?|$|\/)/.test(page.url())) {
			await unlockVaultIfPrompted(page)
		}
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
		// Re-settle AFTER dismissing. The wait above can time out with the
		// overlay still up, and reading the verdict in that same frame reports
		// a canvas that simply had not been allowed to mount yet.
		await page.waitForFunction(() => {
			const canvas = document.querySelector('.cn-flow-detail')
			const sidebar = document.querySelector('#app-sidebar-vue, aside.app-sidebar')
			return (canvas && sidebar) || /[#/]lock(\?|$|\/)/.test(location.href)
		}, { timeout: 10000 }).catch(() => {})
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
		const row = {
			id,
			index: index.flowsHeading,
			canvas: detail.canvas,
			sidebar: detail.sidebar,
			locked: detail.locked || index.locked,
		}
		rows.push(row)
		// Print as we go. A run over 14 apps takes minutes, and a silent
		// process that only speaks at the end is indistinguishable from a hung
		// one — which is exactly how it looked the first time it ran long.
		process.stderr.write(`  ${row.id}: `
			+ `${row.locked ? 'locked' : (row.canvas && row.sidebar ? 'ok' : 'FAIL')}\n`)
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
