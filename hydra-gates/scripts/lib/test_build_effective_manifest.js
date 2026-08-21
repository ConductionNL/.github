#!/usr/bin/env node
// SPDX-License-Identifier: EUPL-1.2
//
// test_build_effective_manifest.js — merge-semantics self-test for the
// gate-30 vendored effective-manifest builder (build_effective_manifest.js).
//
// These assertions PIN the observable buildManifest behaviour ported from
// nextcloud-vue/src/utils/buildManifest.js (see the sync note there). If the
// lib's merge semantics change, this file is where the vendored port catches
// up. Covers: fragment filename order, page replace-by-id, keyed menu merge
// (first scalar wins, children unioned), relocations, removals,
// settingsSection — plus assembly from the good fixture directory.
//
// Run: node scripts/lib/test_build_effective_manifest.js   (exit 0 = pass)

'use strict'

const fs = require('fs')
const os = require('os')
const path = require('path')
const { spawnSync } = require('child_process')
const {
	buildManifest,
	mergeMenuItems,
	mergePages,
	applyMenuRelocations,
	applyMenuRemovals,
	applySettingsSection,
	expandPageTemplates,
	assembleFromDir,
	assembleAtRef,
} = require('./build_effective_manifest.js')

// --- guard the guard --------------------------------------------------------
// The last block of this file assembles from
// scripts/test-fixtures/effective-manifest/good/. Until 2026-08-04 that
// directory did not exist and nothing in CI ran this file, so the in-memory
// assertions above it reported PASS and the run then died on an uncaught
// ENOBASE stack trace. Fail with a cause instead — and before, not after, the
// misleading passes.
{
	const goodDir = path.resolve(__dirname, '..', 'test-fixtures', 'effective-manifest', 'good')
	const required = [
		'src/manifest.json',
		'src/manifest.d/10-archive.json',
		'src/manifest.d/20-settings.json',
		'src/menu-layout.json',
	]
	// The templating leg (manifest-entity-scaffold-templating) has its own
	// fixture directory — guard it the same way, for the same reason.
	const templatedDir = path.resolve(__dirname, '..', 'test-fixtures', 'effective-manifest', 'templated')
	const requiredTemplated = [
		'src/manifest.json',
		'src/manifest.d/00-templates.json',
		'src/manifest.d/10-entities.json',
	]
	const missing = required.filter((rel) => !fs.existsSync(path.join(goodDir, rel)))
		.concat(requiredTemplated.filter((rel) => !fs.existsSync(path.join(templatedDir, rel))).map((rel) => `templated/${rel}`))
	if (missing.length > 0) {
		console.log(`FAIL — ${missing.length} fixture file(s) MISSING under ${goodDir}; this suite cannot assert anything:`)
		for (const rel of missing) console.log(`    ${rel}`)
		console.log('')
		console.log('Refusing to run. The assembly assertions at the end of this file need them,')
		console.log('and reporting the in-memory passes above without them would announce a green')
		console.log('for a suite that never reached its integration leg.')
		process.exit(1)
	}
}

let fails = 0
function assert(cond, label) {
	if (cond) {
		console.log(`PASS — ${label}`)
	} else {
		console.log(`FAIL — ${label}`)
		fails++
	}
}

// --- pages: replace-by-id, later fragment wins -------------------------------
{
	const target = [{ id: 'a', title: 'base-a' }, { id: 'b', title: 'base-b' }]
	mergePages(target, [{ id: 'b', title: 'frag-b' }, { id: 'c', title: 'frag-c' }])
	assert(target.length === 3, 'mergePages: new page appended')
	assert(target.find((p) => p.id === 'b').title === 'frag-b', 'mergePages: fragment page REPLACES base page by id (wholesale)')
	assert(target[1].id === 'b', 'mergePages: replaced page keeps its position')
}

// --- menu: keyed merge, first scalar wins, children unioned ------------------
{
	const target = []
	mergeMenuItems(target, [{ id: 'g', label: 'base-label', order: 10, children: [{ id: 'c1', label: 'c1' }] }])
	mergeMenuItems(target, [{ id: 'g', label: 'frag-label', icon: 'frag-icon', order: 99, children: [{ id: 'c2', label: 'c2' }, { id: 'c1', label: 'c1-dup' }] }])
	const g = target.find((t) => t.id === 'g')
	assert(g.label === 'base-label' && g.order === 10, 'mergeMenuItems: first definition of a scalar key wins')
	assert(g.icon === 'frag-icon', 'mergeMenuItems: fragment fills a key the base left undefined')
	assert(g.children.length === 2 && g.children[0].label === 'c1', 'mergeMenuItems: children unioned by id (no dup, first def wins)')
}

// --- buildManifest: fragment order end-to-end --------------------------------
{
	const base = { version: '1.0.0', pages: [{ id: 'p1', title: 'base' }], menu: [{ id: 'm1', label: 'one' }] }
	const frag10 = { pages: [{ id: 'p2', title: 'from-10' }] }
	const frag20 = { pages: [{ id: 'p2', title: 'from-20' }], menu: [{ id: 'm2', label: 'two' }] }
	const out = buildManifest(base, [frag10, frag20], {})
	assert(out.pages.length === 2 && out.pages.find((p) => p.id === 'p2').title === 'from-20', 'buildManifest: later fragment (ascending filename order) wins replace-by-id')
	assert(out.menu.length === 2, 'buildManifest: base + fragment menus merged')
	assert(base.pages.length === 1 && base.menu.length === 1, 'buildManifest: base object not mutated')
}

// --- relocations ---------------------------------------------------------------
{
	// Leaf moves under target group; group dissolves into target; missing
	// target keeps the entry at top level; empty shells dropped.
	const menu = [
		{ id: 'group-a', label: 'A', children: [{ id: 'leaf-1', label: 'L1', route: 'r1' }] },
		{ id: 'group-b', label: 'B', children: [{ id: 'leaf-2', label: 'L2', route: 'r2' }] },
		{ id: 'leaf-3', label: 'L3', route: 'r3' },
	]
	const out = applyMenuRelocations(menu, { 'leaf-3': 'group-a', 'group-b': 'group-a', 'leaf-9': 'nowhere' })
	const a = out.find((m) => m.id === 'group-a')
	assert(a && a.children.some((c) => c.id === 'leaf-3'), 'relocations: leaf moves under the target group')
	assert(a && a.children.some((c) => c.id === 'leaf-2'), 'relocations: relocated GROUP dissolves — its children merge into the target')
	assert(!out.some((m) => m.id === 'group-b'), 'relocations: dissolved group shell dropped')
}
{
	const menu = [{ id: 'lonely', label: 'L', route: 'r' }]
	const out = applyMenuRelocations(menu, { lonely: 'ghost-group' })
	assert(out.length === 1 && out[0].id === 'lonely', 'relocations: missing target keeps the entry at top level (nothing silently disappears)')
}

// --- removals -------------------------------------------------------------------
{
	const menu = [
		{ id: 'group', label: 'G', children: [{ id: 'dup', label: 'D', route: 'r1' }, { id: 'keep', label: 'K', route: 'r1' }] },
		{ id: 'clickable-group', label: 'CG', route: 'rg', children: [{ id: 'only-child', label: 'OC', route: 'r2' }] },
	]
	const out = applyMenuRemovals(menu, ['dup', 'only-child'])
	const g = out.find((m) => m.id === 'group')
	assert(g && g.children.length === 1 && g.children[0].id === 'keep', 'removals: leaf entry dropped, sibling with same route survives')
	assert(out.some((m) => m.id === 'clickable-group'), 'removals: a clickable group survives even when all children removed')
}

// --- settingsSection -------------------------------------------------------------
{
	const menu = [
		{ id: 'group', label: 'G', children: [{ id: 'cfg', label: 'Config', route: 'settings-page' }, { id: 'other', label: 'O', route: 'r' }] },
	]
	const out = applySettingsSection(menu, ['cfg'])
	const lifted = out.find((m) => m.id === 'cfg')
	assert(lifted && lifted.section === 'settings', 'settingsSection: listed entry lifted to top level with section:"settings"')
	assert(out[out.length - 1].id === 'cfg', 'settingsSection: lifted entry appended after remaining entries')
	assert(out.find((m) => m.id === 'group').children.length === 1, 'settingsSection: entry stripped from its original group')
}

// --- absent inputs: effective == base --------------------------------------------
{
	const base = { version: '1.0.0', pages: [{ id: 'p' }], menu: [{ id: 'm', label: 'M', route: 'p' }] }
	const out = buildManifest(base, [], {})
	assert(JSON.stringify(out.pages) === JSON.stringify(base.pages)
		&& JSON.stringify(out.menu) === JSON.stringify([{ id: 'm', label: 'M', route: 'p' }]),
	'buildManifest: no fragments + no menu-layout → effective equals base')
}

// --- assembly from the good fixture dir (file ordering + full pipeline) -----------
{
	const goodDir = path.resolve(__dirname, '..', 'test-fixtures', 'effective-manifest', 'good')
	const { manifest, inputs } = assembleFromDir(goodDir)
	assert(inputs.fragmentFiles.length === 2
		&& path.basename(inputs.fragmentFiles[0]) === '10-archive.json'
		&& path.basename(inputs.fragmentFiles[1]) === '20-settings.json',
	'assembleFromDir: fragments gathered in ascending filename order')
	const settings = manifest.pages.find((p) => p.id === 'settings-page')
	assert(settings && settings.component === 'SettingsPage', 'assembleFromDir: 20-settings.json replaces the 10-archive.json page (later fragment wins)')
	assert(!manifest.menu.some(function walk(m) { return m.id === 'items-index-duplicate' || (m.children || []).some(walk) }),
		'assembleFromDir: menu-layout removals applied (duplicate entry gone)')
	const settingsEntry = manifest.menu.find((m) => m.id === 'app-settings-entry')
	assert(settingsEntry && settingsEntry.section === 'settings', 'assembleFromDir: settingsSection applied')
	const itemsGroup = manifest.menu.find((m) => m.id === 'items-group')
	assert(itemsGroup && itemsGroup.children.some((c) => c.id === 'reports-entry'), 'assembleFromDir: relocations applied (reports-entry under items-group)')
	assert(itemsGroup.children.find((c) => c.id === 'reports-entry').order === 20, 'assembleFromDir: keyed menu merge — base scalar (order 20) beat the fragment re-declaration (25)')
}

// --- assembleAtRef (gate-68) — base-ref assembly reproduces assembleFromDir ------
{
	const goodDir = path.resolve(__dirname, '..', 'test-fixtures', 'effective-manifest', 'good')
	const tmpRepo = fs.mkdtempSync(path.join(os.tmpdir(), 'hydra-gate68-selftest-'))
	const git = (args) => spawnSync('git', ['-C', tmpRepo, ...args], { encoding: 'utf8' })
	try {
		git(['init', '-q', '.'])
		git(['config', 'user.email', 'test@example.invalid'])
		git(['config', 'user.name', 'Gate Test'])

		// Commit 1: base manifest ONLY — predates manifest.d/ and menu-layout.json,
		// mirroring an app before it adopted ADR-037 fragments.
		fs.mkdirSync(path.join(tmpRepo, 'src'), { recursive: true })
		fs.copyFileSync(path.join(goodDir, 'src', 'manifest.json'), path.join(tmpRepo, 'src', 'manifest.json'))
		git(['add', '-A'])
		git(['commit', '-q', '-m', 'base manifest only'])
		const baseSha = git(['rev-parse', 'HEAD']).stdout.trim()

		// Commit 2: the full "good" fixture tree (manifest.d/ + menu-layout.json).
		fs.mkdirSync(path.join(tmpRepo, 'src', 'manifest.d'), { recursive: true })
		for (const f of ['10-archive.json', '20-settings.json']) {
			fs.copyFileSync(path.join(goodDir, 'src', 'manifest.d', f), path.join(tmpRepo, 'src', 'manifest.d', f))
		}
		fs.copyFileSync(path.join(goodDir, 'src', 'menu-layout.json'), path.join(tmpRepo, 'src', 'menu-layout.json'))
		git(['add', '-A'])
		git(['commit', '-q', '-m', 'add manifest.d + menu-layout.json'])
		const headSha = git(['rev-parse', 'HEAD']).stdout.trim()

		const atHead = assembleAtRef(tmpRepo, headSha, '.')
		const fromDir = assembleFromDir(goodDir)
		assert(JSON.stringify(atHead.manifest) === JSON.stringify(fromDir.manifest),
			'assembleAtRef: output at a ref whose tree equals the live fixture directory equals assembleFromDir\'s output')

		const atBase = assembleAtRef(tmpRepo, baseSha, '.')
		assert(atBase.inputs.fragmentFiles.length === 0,
			'assembleAtRef: correctly omits manifest.d/ when assembling a ref that predates it')
		assert(atBase.inputs.menuLayoutPath === null,
			'assembleAtRef: correctly omits menu-layout.json when assembling a ref that predates it')
		assert(JSON.stringify(atBase.manifest.pages) === JSON.stringify(fromDir.inputs.base.pages),
			'assembleAtRef: base-only ref assembles to exactly the base manifest\'s pages (no fragment merge to omit)')

		let badRefThrew = null
		try {
			assembleAtRef(tmpRepo, 'no-such-ref-exists', '.')
		} catch (e) {
			badRefThrew = e
		}
		assert(badRefThrew && badRefThrew.code === 'EBADREF',
			'assembleAtRef: an unresolvable ref throws .code === \'EBADREF\', not a silent empty result')

		const emptyRepo = fs.mkdtempSync(path.join(os.tmpdir(), 'hydra-gate68-selftest-empty-'))
		try {
			const gitEmpty = (args) => spawnSync('git', ['-C', emptyRepo, ...args], { encoding: 'utf8' })
			gitEmpty(['init', '-q', '.'])
			gitEmpty(['config', 'user.email', 'test@example.invalid'])
			gitEmpty(['config', 'user.name', 'Gate Test'])
			fs.writeFileSync(path.join(emptyRepo, 'README.md'), 'no manifest here\n')
			gitEmpty(['add', '-A'])
			gitEmpty(['commit', '-q', '-m', 'no manifest yet'])
			const emptySha = gitEmpty(['rev-parse', 'HEAD']).stdout.trim()
			let noBaseThrew = null
			try {
				assembleAtRef(emptyRepo, emptySha, '.')
			} catch (e) {
				noBaseThrew = e
			}
			assert(noBaseThrew && noBaseThrew.code === 'ENOBASE',
				'assembleAtRef: a ref that predates src/manifest.json itself throws .code === \'ENOBASE\'')
		} finally {
			fs.rmSync(emptyRepo, { recursive: true, force: true })
		}
	} finally {
		fs.rmSync(tmpRepo, { recursive: true, force: true })
	}
}

// --- page-template expansion (manifest-entity-scaffold-templating) ---------
// Pins the vendored expandPageTemplates port + buildManifest's collection of
// fragment-authored pageTemplates/pageInstances/sets — the runtime pipeline's
// FINAL step (nextcloud-vue buildManifest.js → expandPageTemplates.js).
{
	// Direct unit semantics: substitution modes + error strictness.
	const manifest = {
		pages: [{ id: 'Concrete' }],
		sets: { cols: ['a', 'b'] },
		pageTemplates: [{
			id: 'tpl',
			params: [
				{ name: 'id', required: true },
				{ name: 'title', required: true },
				{ name: 'icon', required: false },
			],
			page: {
				id: '{{id}}',
				title: 'Edit {{title}}',
				icon: '{{icon}}',
				config: { columns: '{{set:cols}}' },
			},
		}],
		pageInstances: [
			{ templateRef: 'tpl', params: { id: 'P1', title: 'Thing' } },
			{ templateRef: 'tpl', params: { id: 'P2', title: 'Other', icon: 'Cog' } },
			{ templateRef: 'missing-tpl', params: { id: 'P3', title: 'Ghost' } },
			{ templateRef: 'tpl', params: { id: 'P4' } }, // title missing (required)
		],
	}
	const res = expandPageTemplates(manifest, { throwOnError: false })
	assert(res.expandedCount === 2 && res.errors.length === 2,
		'expandPageTemplates: 2 of 4 instances expand; unknown templateRef + missing required param are NAMED errors, not silence')
	const p1 = res.manifest.pages.find((p) => p.id === 'P1')
	assert(p1 && p1.title === 'Edit Thing', 'expandPageTemplates: embedded {{param}} interpolates into the string')
	assert(p1 && !('icon' in p1), 'expandPageTemplates: absent OPTIONAL param on an exact-match placeholder DROPS the containing key')
	assert(p1 && JSON.stringify(p1.config.columns) === JSON.stringify(['a', 'b']),
		'expandPageTemplates: {{set:NAME}} resolves against the shared sets registry with the value\'s own JSON type')
	const p2 = res.manifest.pages.find((p) => p.id === 'P2')
	assert(p2 && p2.icon === 'Cog', 'expandPageTemplates: supplied optional param substitutes on the exact-match placeholder')
	assert(!('pageInstances' in res.manifest) && Array.isArray(res.manifest.pageTemplates),
		'expandPageTemplates: pageInstances removed after expansion, pageTemplates retained by default')
	assert(res.errors.every((e) => /pageInstances\[\d+\]/.test(e)),
		'expandPageTemplates: every expansion error names its instantiation (pageInstances[N])')
	assert(manifest.pages.length === 1 && Array.isArray(manifest.pageInstances),
		'expandPageTemplates: input manifest not mutated')
	let threw = null
	try {
		expandPageTemplates(manifest, { throwOnError: true })
	} catch (e) {
		threw = e
	}
	assert(threw && /Page-template expansion failed/.test(threw.message),
		'expandPageTemplates: throwOnError:true throws the concatenated named errors')
}

{
	// buildManifest collects templates/instances/sets FROM FRAGMENTS and runs
	// expansion as the FINAL step — meta reports what the runtime would skip.
	const base = { version: '1.0.0', pages: [{ id: 'Home' }], menu: [] }
	const fragTpl = {
		pageTemplates: [{
			id: 't',
			params: [{ name: 'id', required: true }],
			page: { id: '{{id}}', type: 'index' },
		}],
		sets: { s: [1] },
	}
	const fragInst = {
		pageInstances: [
			{ templateRef: 't', params: { id: 'FromFragment' } },
			{ templateRef: 'nope', params: { id: 'Bad' } },
		],
	}
	const meta = {}
	const out = buildManifest(base, [fragTpl, fragInst], {}, meta)
	assert(out.pages.some((p) => p.id === 'FromFragment'),
		'buildManifest: fragment-authored template + instance expand into concrete pages[]')
	assert(meta.expansion.expandedCount === 1 && meta.expansion.errors.length === 1
		&& /templateRef "nope"/.test(meta.expansion.errors[0]),
	'buildManifest: the skipped instantiation surfaces on meta.expansion.errors (runtime skips, the gate REPORTS)')
	assert(meta.expansion.expandedPages.length === 1 && meta.expansion.expandedPages[0].id === 'FromFragment',
		'buildManifest: meta.expansion.expandedPages carries exactly the materialised pages')
	assert(!('pageInstances' in out), 'buildManifest: no pageInstances key survives expansion')
}

{
	// NO-TEMPLATE APPS ARE BYTE-IDENTICAL TO THE PRE-EXPANSION BUILDER — the
	// no-change control for the whole fleet, pinned as an assertion.
	const base = { version: '1.0.0', pages: [{ id: 'p' }], menu: [{ id: 'm', label: 'M', route: 'p' }] }
	const frag = { pages: [{ id: 'q' }] }
	const meta = {}
	const out = buildManifest(base, [frag], {}, meta)
	assert(!('pageTemplates' in out) && !('pageInstances' in out) && !('sets' in out),
		'buildManifest: an app without templates gains NO templating keys')
	assert(meta.expansion.expandedCount === 0 && meta.expansion.errors.length === 0,
		'buildManifest: an app without templates reports an all-zero expansion')
	assert(JSON.stringify(out) === JSON.stringify({ version: '1.0.0', pages: [{ id: 'p' }, { id: 'q' }], menu: [{ id: 'm', label: 'M', route: 'p' }] }),
		'buildManifest: no-template output shape unchanged (byte-identical serialisation)')
}

// --- assembly from the templated fixture dir (files → expansion, end to end) --
{
	const templatedDir = path.resolve(__dirname, '..', 'test-fixtures', 'effective-manifest', 'templated')
	const { manifest, expansion } = assembleFromDir(templatedDir)
	assert(expansion.expandedCount === 2 && expansion.errors.length === 1,
		'assembleFromDir(templated): 2 fixture instances expand, the broken templateRef is a named error')
	const items = manifest.pages.find((p) => p.id === 'Items')
	assert(items && items.title === 'Items overview' && items.route === '/items'
		&& JSON.stringify(items.config.columns) === JSON.stringify(['name', 'status'])
		&& items.config.toolbar && items.config.toolbar.search === true,
	'assembleFromDir(templated): substituted instance page materialised in pages[] (params + {{set:NAME}})')
	assert(items && !('icon' in items),
		'assembleFromDir(templated): optional icon param absent → key dropped from the expanded page')
	const orders = manifest.pages.find((p) => p.id === 'Orders')
	assert(orders && orders.title === 'Orders (overridden)' && orders.icon === 'TableColumn',
		'assembleFromDir(templated): instance override (base+delta merge) applied over the substituted page')
	assert(!manifest.pages.some((p) => p.id === 'BrokenDetail'),
		'assembleFromDir(templated): the failing instantiation\'s page is ABSENT (runtime skip semantics) — its error is the report')
	assert(/pageInstances\[2\].*doesNotExist/.test(expansion.errors[0]),
		'assembleFromDir(templated): the error names the instantiation and the unknown templateRef')
}

// --- CLI --expansion-out (the handoff the Python gate helpers consume) --------
{
	const templatedDir = path.resolve(__dirname, '..', 'test-fixtures', 'effective-manifest', 'templated')
	const expFile = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'hydra-expansion-out-')), 'expansion.json')
	try {
		const res = spawnSync(process.execPath, [
			path.join(__dirname, 'build_effective_manifest.js'),
			'--app-dir', templatedDir,
			'--out', path.join(path.dirname(expFile), 'effective.json'),
			'--expansion-out', expFile,
		], { encoding: 'utf8' })
		assert(res.status === 0, 'CLI --expansion-out: assembly exits 0 (runtime skip semantics — errors are REPORTED, not fatal)')
		const report = JSON.parse(fs.readFileSync(expFile, 'utf8'))
		assert(report.expandedCount === 2 && report.errors.length === 1
			&& report.expandedPages.length === 2
			&& report.expandedPages.some((p) => p.id === 'Items'),
		'CLI --expansion-out: report carries expandedCount + named errors + the expanded pages themselves')
		assert(/expansion error:.*doesNotExist/.test(res.stderr),
			'CLI: every expansion error is printed to stderr (lands in the gate-53 log)')
	} finally {
		fs.rmSync(path.dirname(expFile), { recursive: true, force: true })
	}
}

console.log('')
if (fails === 0) {
	console.log('ALL build_effective_manifest merge-semantics assertions PASSED')
	process.exit(0)
}
console.log(`${fails} build_effective_manifest assertion(s) FAILED`)
process.exit(1)
