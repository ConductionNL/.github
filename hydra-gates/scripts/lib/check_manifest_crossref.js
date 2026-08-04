#!/usr/bin/env node
// SPDX-License-Identifier: EUPL-1.2
//
// check_manifest_crossref.js — Gate-30 cross-reference checker.
//
// Runs the joins JSON Schema cannot express against an app's EFFECTIVE
// manifest (assembled by scripts/lib/build_effective_manifest.js):
//
//   (a) menu-route     — every menu[].route / children[].route resolves to an
//                        existing pages[].id or pages[].route. FAIL on miss.
//   (b) action-target  — type:"open-page" actions target an existing page id
//                        (FAIL on miss); type:"open-modal" targets live in the
//                        app's component registry (app code the gate cannot
//                        statically parse) → WARN, never a false FAIL.
//   (c) slug-resolution— every (register, schema) pair referenced by the
//                        manifest (page config.register/config.schema, widget
//                        source/dataSource blocks — incl. the detail-widget
//                        content.{register,schema} shape — and
//                        deepLinks[].registerSlug/schemaSlug) resolves against
//                        the schema slugs the app declares in
//                        lib/Settings/*register*.json (+ lib/Settings/
//                        register.d/*.json). FAIL when a register JSON exists
//                        in-repo and the reference is unresolved (the
//                        zaakafhandelapp besluit/resultaat failure class);
//                        WARN when no register JSON is present (runtime-bound
//                        registers).
//   (d) deeplink-route — each deepLinks[].urlTemplate path prefix corresponds
//                        to a routable page: some pages[].route, after
//                        stripping :param segments, is a path-prefix of the
//                        urlTemplate after stripping {param} segments.
//                        FAIL on miss.
//   (e) removals-invariant (ADR-044 no-functionality-loss) — every id in
//                        menu-layout.json#removals must, after assembly, leave
//                        its route reachable via another surviving menu entry.
//                        FAIL on an orphaned route.
//
// Report shape (mirrors gate-22 / check_manifest.js): on findings, ONE
// machine-parseable per-file JSON line, then always the JSON summary line —
// both on stdout (every stdout line valid JSON). Human diagnostics go to
// stderr as `at <path>: <message>` (FAIL) / `at <path>: WARN <message>`
// (warn). WARN findings never set the failure exit code.
//
// Usage:
//   node scripts/lib/check_manifest_crossref.js [--app-dir DIR] [--manifest FILE]
//     --app-dir DIR    app repo root (default: CWD). Used for register-JSON
//                      discovery and for the removals-invariant pre-removal
//                      menu state.
//     --manifest FILE  a pre-assembled effective manifest to check (e.g. the
//                      temp file gate-30 already validated structurally).
//                      When omitted, the checker assembles it itself via
//                      build_effective_manifest.js.
//
// Exit codes:
//   0 — no error-severity findings (warnings allowed)
//   1 — at least one error-severity finding (or unusable manifest input)
//   2 — checker misconfiguration (builder module missing, app dir unreadable)

'use strict'

const fs = require('fs')
const path = require('path')

let builder
try {
	builder = require('./build_effective_manifest.js')
} catch (e) {
	console.error(`[check_manifest_crossref] vendored builder missing next to this helper (${e.message}) — gate misconfiguration`)
	process.exit(2)
}

// --- argument parsing --------------------------------------------------------

let APP_DIR = process.cwd()
let MANIFEST_FILE = null
// `--scope-ids FILE` (ADR-020) — see manifest_scope_filter.js. The joins are
// still answered against the WHOLE assembled manifest; the flag only decides
// which of the answers block this PR.
let SCOPE_IDS_FILE = null
{
	const argv = process.argv.slice(2)
	for (let i = 0; i < argv.length; i++) {
		if (argv[i] === '--app-dir' && argv[i + 1]) { APP_DIR = path.resolve(argv[++i]); continue }
		if (argv[i] === '--manifest' && argv[i + 1]) { MANIFEST_FILE = path.resolve(argv[++i]); continue }
		if (argv[i] === '--scope-ids' && argv[i + 1]) { SCOPE_IDS_FILE = argv[++i]; continue }
		console.error(`[check_manifest_crossref] unknown argument: ${argv[i]}`)
		process.exit(2)
	}
}

const scopeFilter = require('./manifest_scope_filter.js')

// --- findings accumulator ----------------------------------------------------

const findings = []
function fail(check, ptr, message) {
	findings.push({ path: ptr, check, severity: 'error', message })
}
function warn(check, ptr, message) {
	findings.push({ path: ptr, check, severity: 'warn', message })
}

// --- register/schema discovery (Decision 3) ----------------------------------

// Slugify fallback when a schema/register object carries no explicit slug.
function slugify(s) {
	return String(s || '').toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')
}

// Union register + schema slugs across lib/Settings/*register*.json and
// lib/Settings/register.d/*.json. Tolerant of the OpenAPI-ish seed shape
// (components.registers / components.schemas as keyed maps) and of plain
// top-level registers/schemas maps or arrays.
function discoverDeclaredSlugs(appDir) {
	const settingsDir = path.join(appDir, 'lib', 'Settings')
	const files = []
	if (fs.existsSync(settingsDir) && fs.statSync(settingsDir).isDirectory()) {
		for (const f of fs.readdirSync(settingsDir).sort()) {
			if (/register/i.test(f) && f.endsWith('.json')) files.push(path.join(settingsDir, f))
		}
		const fragDir = path.join(settingsDir, 'register.d')
		if (fs.existsSync(fragDir) && fs.statSync(fragDir).isDirectory()) {
			for (const f of fs.readdirSync(fragDir).sort()) {
				if (f.endsWith('.json')) files.push(path.join(fragDir, f))
			}
		}
	}
	const registers = new Set()
	const schemas = new Set()
	const collect = (container, kind) => {
		if (!container) return
		const entries = Array.isArray(container)
			? container.map((v) => [null, v])
			: (typeof container === 'object' ? Object.entries(container) : [])
		for (const [key, obj] of entries) {
			if (!obj || typeof obj !== 'object') continue
			const slug = (typeof obj.slug === 'string' && obj.slug !== '')
				? obj.slug
				: (key || slugify(obj.title))
			if (!slug) continue
			const target = kind === 'register' ? registers : schemas
			target.add(String(slug).toLowerCase())
			// A register object may list its schema slugs inline.
			if (kind === 'register' && Array.isArray(obj.schemas)) {
				for (const s of obj.schemas) {
					if (typeof s === 'string') schemas.add(s.toLowerCase())
				}
			}
		}
	}
	for (const file of files) {
		let doc
		try {
			doc = JSON.parse(fs.readFileSync(file, 'utf8'))
		} catch (e) {
			// A corrupt register JSON is itself a finding: the declared set is
			// unknowable, so slug resolution against it would be fiction.
			fail('slug-resolution', '/', `register JSON ${path.relative(appDir, file)} is not valid JSON (${e.message})`)
			continue
		}
		collect(doc.components && doc.components.registers, 'register')
		collect(doc.components && doc.components.schemas, 'schema')
		collect(doc.registers, 'register')
		collect(doc.schemas, 'schema')
	}
	return { files, registers, schemas }
}

// --- manifest walkers ----------------------------------------------------------

// True when a slug value is a literal (checkable) string — runtime sentinels
// (@resolve:*, @workspace.*, {tokens}) are resolved by the host loader and
// are deliberately not statically checked.
function isLiteralSlug(v) {
	return typeof v === 'string' && v !== '' && !v.includes('@') && !v.includes('{') && !v.includes('$')
}

// Recursively collect every object carrying BOTH a literal `register` and
// `schema` string — covers page config, widget dataSource/source blocks, the
// detail-widget content.{register,schema} shape, and summaryAggregates.
// Returns [{ ptr, register, schema, context }].
function collectSlugPairs(node, ptr, nearestId, out) {
	if (Array.isArray(node)) {
		node.forEach((v, i) => collectSlugPairs(v, `${ptr}/${i}`, nearestId, out))
		return
	}
	if (!node || typeof node !== 'object') return
	const ownId = (typeof node.id === 'string' && node.id !== '') ? node.id : nearestId
	if (isLiteralSlug(node.register) && isLiteralSlug(node.schema)) {
		out.push({ ptr, register: node.register, schema: node.schema, context: ownId })
	}
	for (const [k, v] of Object.entries(node)) {
		if (k === '_note' || k === '_meta') continue
		collectSlugPairs(v, `${ptr}/${k}`, ownId, out)
	}
}

// Recursively collect menu entries carrying a `route` (any nesting depth).
function collectMenuRoutes(items, ptr, out) {
	if (!Array.isArray(items)) return
	items.forEach((item, i) => {
		if (!item || typeof item !== 'object') return
		const here = `${ptr}/${i}`
		if (typeof item.route === 'string' && item.route !== '') {
			out.push({ ptr: here, id: item.id, route: item.route })
		}
		collectMenuRoutes(item.children, `${here}/children`, out)
	})
}

// Recursively collect action objects: any array under an `actions` key whose
// items carry a `label` (the $defs/action required key) — covers pages[].
// actions, object-table props.actions, and widget header actionItems.
function collectActions(node, ptr, out) {
	if (Array.isArray(node)) {
		node.forEach((v, i) => collectActions(v, `${ptr}/${i}`, out))
		return
	}
	if (!node || typeof node !== 'object') return
	for (const [k, v] of Object.entries(node)) {
		if (k === '_note' || k === '_meta') continue
		if ((k === 'actions' || k === 'actionItems') && Array.isArray(v)) {
			v.forEach((a, i) => {
				if (a && typeof a === 'object' && typeof a.label === 'string') {
					out.push({ ptr: `${ptr}/${k}/${i}`, action: a })
				}
			})
		}
		collectActions(v, `${ptr}/${k}`, out)
	}
}

// Normalize a deepLink urlTemplate to an app-relative route path before
// prefix matching (design.md Open Question — refined here after real apps
// tripped the provisional rule): strip an absolute scheme+host, a leading
// `/apps/<appid>` mount, and a hash-router `#/` marker, so both the bare
// form (`/besluiten/{id}`) and the full form
// (`/apps/decidesk/#/meetings/{uuid}`) resolve against pages[].route.
function normalizeDeepLinkTemplate(t) {
	let s = String(t || '')
	s = s.replace(/^https?:\/\/[^/]+/, '')
	s = s.replace(/^\/apps\/[^/#]+/, '')
	s = s.replace(/^\/?#\//, '/')
	if (s === '' || s === '#') s = '/'
	return s
}

// Strip parameter segments (":id" route params, "{id}" template params) from
// a path and return the static prefix up to the first parameter segment.
function staticPrefix(p) {
	const segs = String(p || '').split('/').filter((s) => s !== '')
	const kept = []
	for (const s of segs) {
		if (s.startsWith(':') || (s.includes('{') && s.includes('}'))) break
		kept.push(s)
	}
	return '/' + kept.join('/')
}

// True when prefix P covers path T on a segment boundary.
function isPathPrefix(p, t) {
	if (p === '/') return t === '/' // a bare root route only matches root
	return t === p || t.startsWith(p + '/')
}

// --- main ----------------------------------------------------------------------

function main() {
	// Assemble (or load) the effective manifest.
	let manifest
	let manifestLabel
	if (MANIFEST_FILE) {
		manifestLabel = MANIFEST_FILE
		try {
			manifest = JSON.parse(fs.readFileSync(MANIFEST_FILE, 'utf8'))
		} catch (e) {
			console.error(`at /: effective manifest ${MANIFEST_FILE} unreadable or invalid JSON (${e.message})`)
			console.log(JSON.stringify({ status: 'failed', checked: 1, failed: 1 }))
			process.exit(1)
		}
	} else {
		manifestLabel = path.join(APP_DIR, 'src', 'manifest.json') + ' (effective)'
		try {
			manifest = builder.assembleFromDir(APP_DIR).manifest
		} catch (e) {
			if (e.code === 'ENOBASE') {
				// Tier 0 — no manifest. Defensive: the gate skips before calling us.
				console.error('[check_manifest_crossref] no src/manifest.json — Tier 0, skipping')
				console.log(JSON.stringify({ status: 'passed', checked: 0, failed: 0 }))
				process.exit(0)
			}
			console.error(`at /: effective manifest could not be assembled (${e.message})`)
			console.log(JSON.stringify({ status: 'failed', checked: 1, failed: 1 }))
			process.exit(1)
		}
	}

	const pages = Array.isArray(manifest.pages) ? manifest.pages : []
	const pageIds = new Set(pages.map((p) => p && p.id).filter((v) => typeof v === 'string'))
	const pageRoutes = new Set(pages.map((p) => p && p.route).filter((v) => typeof v === 'string'))

	// (a) menu-route → page-id resolution.
	const menuRoutes = []
	collectMenuRoutes(manifest.menu, '/menu', menuRoutes)
	for (const m of menuRoutes) {
		if (!pageIds.has(m.route) && !pageRoutes.has(m.route)) {
			fail('menu-route', m.ptr, `menu entry '${m.id || '(no id)'}' route '${m.route}' resolves to no pages[].id or pages[].route`)
		}
	}

	// (b) action targets.
	const actions = []
	collectActions({ pages: manifest.pages }, '', actions)
	for (const { ptr, action } of actions) {
		if (action.type === 'open-page') {
			const target = typeof action.target === 'string' ? action.target : action.route
			if (typeof target !== 'string' || target === '') {
				fail('action-target', ptr, `open-page action '${action.id || action.label}' declares no target page`)
			} else if (!pageIds.has(target) && !pageRoutes.has(target)) {
				fail('action-target', ptr, `open-page action '${action.id || action.label}' targets page '${target}' which does not exist`)
			}
		} else if (action.type === 'open-modal') {
			// The modal registry is app code (src/registry.js et al.) the gate
			// cannot statically parse — degrade to WARN per the gate spec.
			warn('action-target', ptr, `open-modal action '${action.id || action.label}' targets '${action.target || '(unset)'}' — modal registry is app code, not statically checkable`)
		}
	}

	// (c) register/schema slug resolution.
	const declared = discoverDeclaredSlugs(APP_DIR)
	const hasRegisterJson = declared.files.length > 0
	const pairs = []
	collectSlugPairs({ pages: manifest.pages }, '', null, pairs)
	// deepLinks carry registerSlug/schemaSlug instead of register/schema.
	const deepLinks = Array.isArray(manifest.deepLinks) ? manifest.deepLinks : []
	deepLinks.forEach((d, i) => {
		if (d && typeof d === 'object' && isLiteralSlug(d.registerSlug) && isLiteralSlug(d.schemaSlug)) {
			pairs.push({ ptr: `/deepLinks/${i}`, register: d.registerSlug, schema: d.schemaSlug, context: d.displayName || null })
		}
	})
	for (const p of pairs) {
		const schemaOk = declared.schemas.has(p.schema.toLowerCase())
		if (schemaOk) continue
		const ctx = p.context ? ` (widget '${p.context}')` : ''
		if (!hasRegisterJson) {
			warn('slug-resolution', p.ptr, `(register '${p.register}', schema '${p.schema}') cannot be resolved — no lib/Settings/*register*.json in repo (runtime-bound registers)${ctx}`)
		} else if (declared.registers.size > 0 && !declared.registers.has(p.register.toLowerCase())) {
			// Reference targets a register this app does not declare (a
			// cross-app register) — its schema set is not statically knowable.
			warn('slug-resolution', p.ptr, `register '${p.register}' is not declared in this app's register JSON — schema '${p.schema}' not statically resolvable${ctx}`)
		} else {
			fail('slug-resolution', p.ptr, `schema '${p.schema}' (register '${p.register}') is not declared in lib/Settings/*register*.json${ctx}`)
		}
	}

	// (d) deepLink route correspondence.
	const routePrefixes = [...pageRoutes].map(staticPrefix)
	deepLinks.forEach((d, i) => {
		if (!d || typeof d !== 'object' || typeof d.urlTemplate !== 'string') return
		const t = staticPrefix(normalizeDeepLinkTemplate(d.urlTemplate))
		if (!routePrefixes.some((p) => isPathPrefix(p, t))) {
			fail('deeplink-route', `/deepLinks/${i}`, `urlTemplate '${d.urlTemplate}' corresponds to no routable page (no pages[].route prefix match)`)
		}
	})

	// (e) ADR-044 no-functionality-loss removals invariant. Needs the
	// PRE-removal menu state, so re-run the assembly stages from the raw
	// inputs (only meaningful when the app ships a menu-layout.json).
	if (!MANIFEST_FILE || fs.existsSync(path.join(APP_DIR, 'src', 'manifest.json'))) {
		let inputs = null
		try {
			inputs = builder.loadAppInputs(APP_DIR)
		} catch (e) {
			inputs = null // assembly errors already surfaced via the manifest path
		}
		const removals = inputs && inputs.menuLayout && Array.isArray(inputs.menuLayout.removals)
			? inputs.menuLayout.removals : []
		if (removals.length > 0) {
			// Merged menu after relocations, BEFORE removals (deep copies —
			// the pipeline steps mutate in place).
			const merged = builder.buildManifest(inputs.base, inputs.fragments, {})
			const preRemoval = builder.applyMenuRelocations(
				JSON.parse(JSON.stringify(merged.menu)), inputs.menuLayout.relocations)
			const findEntry = (nodes, id) => {
				for (const n of nodes || []) {
					if (n && n.id === id) return n
					const hit = findEntry(n && n.children, id)
					if (hit) return hit
				}
				return null
			}
			const effectiveRoutes = []
			collectMenuRoutes(manifest.menu, '/menu', effectiveRoutes)
			removals.forEach((id, i) => {
				const entry = findEntry(preRemoval, id)
				if (!entry) {
					warn('removals-invariant', `/menu-layout/removals/${i}`, `removal '${id}' matches no merged menu entry (stale removal)`)
					return
				}
				if (typeof entry.route !== 'string' || entry.route === '') return // nothing routable retired
				if (!effectiveRoutes.some((m) => m.route === entry.route)) {
					fail('removals-invariant', `/menu-layout/removals/${i}`, `removal '${id}' orphans route '${entry.route}' — no surviving menu entry reaches it (ADR-044 no-functionality-loss)`)
				}
			})
		}
	}

	report(manifestLabel, manifest)
}

// Emit the gate-22 report shape: per-file findings line (when any findings,
// error OR warn), then always the summary line — both valid JSON on stdout.
// Human diagnostics on stderr; WARNs never set the failure exit code.
function report(manifestLabel, manifest) {
	// ADR-020 diff scoping. WARNs are advisory already and are never scoped out
	// — they cost nothing and vanishing them would hide debt twice over. Only
	// error-severity findings are partitioned into blocking vs pre-existing.
	const scope = scopeFilter.loadScope(SCOPE_IDS_FILE)
	const errorFindings = findings.filter((f) => f.severity === 'error')
	const parts = scopeFilter.partition(errorFindings, manifest || {}, scope)
	const preexisting = new Set(parts.preexisting)
	const errors = parts.blocking
	const failed = errors.length > 0 ? 1 : 0
	for (const f of findings) {
		const first = String(f.message).split('\n')[0]
		if (f.severity === 'warn') {
			console.error(`at ${f.path || '/'}: WARN ${first}`)
		} else if (preexisting.has(f)) {
			console.error(`at ${f.path || '/'}: PRE-EXISTING ${first}`)
		} else {
			console.error(`at ${f.path || '/'}: ${first}`)
		}
	}
	if (parts.preexisting.length > 0) {
		console.error(`[check_manifest_crossref] diff-scope (ADR-020): ${parts.preexisting.length} cross-reference finding(s) sit on manifest entries this PR did not touch — reported above as PRE-EXISTING, not blocking.`)
	}
	if (parts.unscopable.length > 0) {
		console.error(`[check_manifest_crossref] ${parts.unscopable.length} finding(s) address the manifest as a WHOLE and block regardless of scope.`)
	}
	if (findings.length > 0) {
		console.log(JSON.stringify({
			file: path.relative(process.cwd(), manifestLabel.replace(' (effective)', '')),
			schemaVersion: 'v2-effective',
			findings,
		}))
	}
	console.log(JSON.stringify({ status: failed === 1 ? 'failed' : 'passed', checked: 1, failed }))
	process.exit(failed)
}

main()
