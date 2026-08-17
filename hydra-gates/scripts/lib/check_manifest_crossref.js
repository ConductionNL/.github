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
//                        its page reachable. Reachability is the transitive
//                        closure of the manifest's DECLARATIVE navigation
//                        edges (open-page action targets, handler:'navigate'
//                        routes, viewAllRoute / rowRoute / clickRoute /
//                        onSuccessRoute / drilldown.route), seeded by the
//                        surviving menu — not the surviving menu alone.
//                        FAIL on an orphaned page. When the replacement
//                        surface names the retired page NOWHERE (its
//                        functionality moved rather than its link), the app
//                        may name that surface in
//                        menu-layout.json#removalsReplacedBy; the gate
//                        verifies the named page exists and is ITSELF
//                        reachable, then downgrades to WARN. Never a
//                        free-text reason — see the block comment at (e).
//                        A replacement in ANOTHER app is spelled
//                        '<appId>:<PageId>' and gets a STRICTLY WEAKER check
//                        (syntax + known fleet app id + not this app), because
//                        the gate cannot read another app's manifest; the WARN
//                        says so explicitly. See CROSS_APP_APP_RE.
//   (f) registry-crossref— the manifest and src/registry.js must agree about
//                        which components exist. A manifest `component` /
//                        slot-override naming no registry export renders
//                        NOTHING at runtime (FAIL); a registry export of kind
//                        section/page/widget that no manifest position names
//                        is unreachable UI (WARN — an orphan is either wired
//                        or deleted and the gate cannot know which).
//                        Cn* names resolve from the nextcloud-vue library, not
//                        the app registry, and are exempt. Skipped entirely
//                        when the app ships no src/registry.js.
//                        Closes #238 / larpingapp#286.
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

// --- (f) component-registry cross-reference ----------------------------------
//
// WHY THIS IS STATICALLY CHECKABLE AFTER ALL
//
// The gate used to decline the component registry wholesale — "src/registry.js
// is app code, not statically checkable" — and that blind spot shipped
// larpingapp#286: `EventRoster` was registered, resolvable, and named by no
// manifest position, so the event check-in surface had no entry point. It was
// unreachable UI long enough for its openspec task to be ticked over it, and
// BOTH gates that exist to catch manifest cross-reference defects were silent,
// in both directions.
//
// src/registry.js is app code but it is not opaque. It is a fixed-shape ES
// module whose top-level `export default { … }` keys are the registry's public
// surface. We cannot `import` it — it pulls in `.vue` SFCs — but the keys are
// extractable with brace-depth tracking, which is exactly how the app-local
// test in larpingapp#288 does it.
//
// DIRECTIONS, AND WHY THEY HAVE DIFFERENT SEVERITIES
//
//   2 → FAIL. A manifest `component` naming no registry key renders NOTHING.
//       CnObjectSidebar.resolveTabComponent() logs `component "…" not found in
//       registry or customComponents` and the tab comes up blank. This is
//       gate-14 route-reachability one layer up: unambiguously broken.
//   1 → WARN. A registered component no manifest position names is either a
//       component that should be wired or one that should be deleted, and the
//       gate cannot know which — the same "zero callers has two opposite
//       fixes" property that made this worth reporting rather than prescribing.
const REGISTRY_KINDS_REQUIRING_A_POSITION = new Set(['section', 'page', 'widget'])

// `Cn[A-Z]…` names resolve from the nextcloud-vue library, not the app
// registry. Treating them as unresolved would fail every well-formed manifest
// in the fleet — the widening that would make this check useless on arrival.
const LIB_COMPONENT = /^Cn[A-Z]\w*$/

// Blank line and block comments so a commented-out entry is NOT counted as a
// registration. A commented-out prelude counting as a prelude was a real
// false-GREEN in gate-64; the same mistake here would let a deleted component
// vouch for a manifest reference that resolves to nothing at runtime.
//
// THE PRIVATE TWO-LINE REGEX IS GONE (#424). It was not string-aware, so the
// `/*` inside `glob: '/*.vue'` opened a block comment that ran to the next
// real `*/` — swallowing whole registry entries, and (when the swallowed span
// was brace-unbalanced) making `parsed: false` skip the cross-reference check
// altogether. See scripts/lib/js_scope.js for the measured shapes; it is the
// node port of `source_scope.js_comment_mask` and is asserted byte-identical
// to it. String CONTENTS survive, because the quoted registry key and
// `kind: 'page'` are this parser's evidence.
const { jsCommentMask } = require('./js_scope.js')

// Top-level keys of the `export default { … }` object, with their `kind`.
// Brace-depth tracking keeps nested object keys (`component:`, `props:`) out.
function parseRegistry(appDir, rel) {
	const file = path.join(appDir, 'src', rel || 'registry.js')
	let raw
	try {
		raw = fs.readFileSync(file, 'utf8')
	} catch (e) {
		return null // absent — nothing to add from this source
	}
	const src = jsCommentMask(raw)
	const start = src.search(/export\s+default\s*\{/)
	if (start === -1) return { file, entries: new Map(), parsed: false }

	const open = src.indexOf('{', start)
	const entries = new Map()
	let depth = 0
	let i = open
	let bodyStart = -1
	for (; i < src.length; i++) {
		const c = src[i]
		if (c === '{') { depth++; if (depth === 1) bodyStart = i + 1 } else if (c === '}') {
			depth--
			if (depth === 0) break
		}
	}
	if (depth !== 0 || bodyStart === -1) return { file, entries: new Map(), parsed: false }
	const body = src.slice(bodyStart, i)

	// Walk the body, recording `Name:` / `'Name':` / `"Name":` at depth 0 only.
	//
	// A QUOTED key may contain characters a bare identifier cannot — hermiq
	// registers `'agent-form'`, `'agent-skills'`, `'agent-run-history'`. The
	// first version of this matcher shared one character class with the bare
	// form, so it captured `agent` and stopped at the hyphen: every hyphenated
	// registration was invisible and every manifest reference to one was
	// reported unresolved. 25 false FAILs on hermiq alone. Quoted and bare keys
	// are therefore matched by SEPARATE alternatives with different classes.
	depth = 0
	const KEY = /(?:^|[,{\s])(?:'([^']+)'|"([^"]+)"|([A-Za-z_$][\w$]*))\s*:/g
	// Depth map: for each index, how deep we are. Cheap enough for these files.
	const depthAt = new Array(body.length).fill(0)
	for (let j = 0; j < body.length; j++) {
		const c = body[j]
		if (c === '{' || c === '[') depth++
		depthAt[j] = depth
		if (c === '}' || c === ']') depth--
	}
	let m
	while ((m = KEY.exec(body)) !== null) {
		const name = m[1] || m[2] || m[3]
		const at = m.index + m[0].indexOf(name)
		if (depthAt[at] !== 0) continue
		// `kind: 'section'` inside this entry's own braces.
		const tail = body.slice(m.index, m.index + 400)
		const km = /\bkind\s*:\s*['"]([a-z-]+)['"]/.exec(tail)
		entries.set(name, { kind: km ? km[1] : null })
	}
	// Shorthand `Name,` entries (no colon) — a registration all the same.
	const SHORT = /(?:^|[,{])\s*([A-Za-z_$][\w$]*)\s*(?=[,}])/g
	while ((m = SHORT.exec(body)) !== null) {
		const at = m.index + m[0].indexOf(m[1])
		if (depthAt[at] !== 0) continue
		if (!entries.has(m[1])) entries.set(m[1], { kind: null })
	}
	return { file, entries, parsed: true }
}

// Every manifest position that names a component by string. Covers
// pages[].component, config.sections[].component, config.sidebar.tabs[].
// component, widget component fields and `slots` overrides, at any depth.
function collectComponentRefs(node, ptr, out) {
	if (Array.isArray(node)) {
		node.forEach((v, i) => collectComponentRefs(v, `${ptr}/${i}`, out))
		return
	}
	if (!node || typeof node !== 'object') return
	for (const [k, v] of Object.entries(node)) {
		if (k === '_note' || k === '_meta') continue
		if (k === 'component' && typeof v === 'string' && v !== '') {
			out.push({ ptr: `${ptr}/component`, name: v })
			continue
		}
		// `slots: { 'photos-leaf': 'ObjectDetail' }` — slot-override map whose
		// VALUES are registry names.
		if (k === 'slots' && v && typeof v === 'object' && !Array.isArray(v)) {
			for (const [slot, target] of Object.entries(v)) {
				if (typeof target === 'string' && target !== '') {
					out.push({ ptr: `${ptr}/slots/${slot}`, name: target })
				}
			}
			continue
		}
		collectComponentRefs(v, `${ptr}/${k}`, out)
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

// --- (e) declarative navigation edges ----------------------------------------
//
// THE MENU IS NOT THE ONLY WAY TO REACH A PAGE, AND PRETENDING IT IS PRODUCES
// FALSE ORPHANS.
//
// The removals-invariant used to ask "does a surviving MENU entry still point
// at this route". A page reached by a dashboard tile's click-through, a
// widget's "view all" link, a header action or a chart drilldown is reachable
// by any honest reading of ADR-044 no-functionality-loss, and every one of
// those is a first-class, statically checkable field of the manifest schema —
// gate-32 (check_detail_page_discipline.py (f)/(f2)) already resolves
// `viewAllRoute` / `rowRoute` and the object `{name}` route form against the
// page-id set for exactly this reason. Measured on procest `development`
// @78c96081: `Voorstellen` is named by
// `CaseDetail.config.widgets[12].content.viewAllRoute` and was still reported
// an orphan by this invariant.
//
// THE KEYS BELOW ARE THE SCHEMA'S, NOT A GUESS. Each is a documented
// destination field in scripts/schemas/app-manifest-v2.schema.json:
//   route           $defs/action ("Destination route name for handler:
//                   'navigate'"), $defs/primaryAction, the stat/banner tile
//                   click-through, and drilldown.route — the last is a `route`
//                   key inside the drilldown object, so it needs no entry of
//                   its own.
//   viewAllRoute    widget "view all" link       (gate-32 (f) resolves it too)
//   rowRoute        widget row click-through     (gate-32 (f) resolves it too)
//   clickRoute      whole-tile click-through ("Alias of content.route")
//   onSuccessRoute  open-form action navigates here after a successful save
// `target` is handled separately because the schema OVERLOADS it: it is a
// modal id for open-modal and a URL for navigate — only the open-page form
// names a page, and crediting the other two would let a modal id vouch for a
// page that happens to share its name.
//
// `href` is deliberately absent: an external URL is not a page. deepLinks are
// deliberately absent too — they are matched by PATH PREFIX (check (d)), so a
// deepLink at `/` would vouch for every page in the app, and they declare an
// entry point from ANOTHER app rather than a navigation edge within this one.
const ROUTE_REF_KEYS = new Set([
	'route',
	'viewAllRoute',
	'rowRoute',
	'clickRoute',
	'onSuccessRoute',
])

// Collect every destination reference beneath `node`. Accepts the string form
// ("CaseDetail" / "/cases") and the OBJECT form ({ name, query }) that
// stats-block entries use — openconnector shipped a dangling one of those and
// a string-only scan reported "no unresolvable route refs" while the page threw
// on mount (see check_detail_page_discipline.py (f2)).
function collectRouteRefs(node, out) {
	if (Array.isArray(node)) {
		node.forEach((v) => collectRouteRefs(v, out))
		return
	}
	if (!node || typeof node !== 'object') return
	const push = (v) => {
		if (typeof v === 'string' && v !== '') out.push(v)
		else if (v && typeof v === 'object' && typeof v.name === 'string' && v.name !== '') out.push(v.name)
	}
	if (node.type === 'open-page') push(node.target)
	for (const [k, v] of Object.entries(node)) {
		if (k === '_note' || k === '_meta') continue
		if (ROUTE_REF_KEYS.has(k)) push(v)
		collectRouteRefs(v, out)
	}
}

// --- (e) CROSS-APP replacement targets ---------------------------------------
//
// SOME FUNCTIONALITY DOES NOT MOVE TO ANOTHER PAGE — IT MOVES TO ANOTHER APP,
// AND THE SAME-APP WAIVER CANNOT SAY SO.
//
// Measured on procest: seven of its eight retired pages are superseded by a
// surface in procest itself and `removalsReplacedBy: {"<id>": "<pageId>"}`
// states that, checkably. The eighth — `BesluitvormingAgenda`, a CROSS-CASE
// meeting-agenda compiler — moved to **decidesk**. With only the same-app form
// available, procest's honest options were (i) leave a true FAIL standing or
// (ii) name a local page that does exist and is reachable. 🔑 THE GATE WOULD
// HAVE ACCEPTED `CaseDetail`: existence + reachability is the whole of what it
// checks, so the false claim would have passed and NOTHING downstream could
// have caught it. A form that cannot state the truth does not prevent lies; it
// selects for them. Hence `<appId>:<PageId>`.
//
// 🔴 WHAT A CROSS-APP TARGET CAN AND CANNOT BE CHECKED — STATED, NOT IMPLIED.
//
// The gate reads THIS app's manifest. It has no access to decidesk's manifest,
// its menu, or its pages, and it is not going to acquire one: the runner is
// offline, one repo deep, and a gate that reached across repositories would
// fail for reasons its own PR cannot fix. So a cross-app waiver gets a
// STRICTLY WEAKER check than a same-app one, and both the code and the WARN
// say so out loud rather than letting the two look alike in a report.
//
//   CAN check   syntax (`<appId>:<PageId>`, one colon, NC app-id charset)
//               the named app is NOT this app (see below — that is the
//                 same-app case in disguise and must take the strict path)
//               the named app is a known Conduction fleet app id
//   CANNOT check that `<PageId>` exists in that app
//               that it is reachable there
//               that the app is even installed on the instance
//               that it carries the retired functionality
//
// 🔑 AND THE PROPERTY #490 PRIZED IS THE ONE THAT IS LOST: a same-app waiver
// ROTS LOUDLY — the day the named page leaves the menu, every waiver pointing
// at it FAILs. A cross-app waiver CANNOT rot, because there is nothing local
// left to rot against. decidesk can delete `BesluitvormingAgenda` tomorrow and
// procest's gate stays green. That is the price of being able to state the
// truth at all, it is not hidden, and the WARN prints it on every run.
//
// THE LOCAL PATH IS UNTOUCHED AND UNREACHABLE FROM HERE. A value that resolves
// to a local pages[].id or pages[].route NEVER enters this branch (see the call
// site), so the cross-app form cannot be used to skip the exists / reachable /
// not-itself checks on a local page. Naming this app's OWN id with a colon
// FAILs for exactly that reason.
const CROSS_APP_APP_RE = /^[a-z][a-z0-9_-]*$/
const CROSS_APP_PAGE_RE = /^[A-Za-z][A-Za-z0-9_-]*$/
// A value is treated as a cross-app ATTEMPT (and validated strictly, with
// cross-app diagnostics) when it carries a colon whose left side contains no
// `/`. The `/` exclusion is what keeps a LOCAL ROUTE out of this branch:
// `/cases/:uuid` and `cases/:uuid` are parameterised page routes, not app
// references, and misreading one as an app id would replace a precise
// "resolves to no page" FAIL with a confusing "unknown app" FAIL.
const CROSS_APP_ATTEMPT_RE = /^([^:/\s]+):(.*)$/

// KNOWN CONDUCTION FLEET APP IDS — 18 core apps + the ExApp sidecar wrappers.
//
// ⚠️ THIS LIST DRIFTS, AND IT FAILS CLOSED WHEN IT DOES: a NEW fleet app cannot
// be named as a cross-app replacement until it is added here, and the FAIL
// message says so and names this constant. That is the intended direction —
// the realistic defect is a TYPO (`decidsk:`, `decidesk-old:`), which a free
// syntax check would bless forever, and an unknown app id would then read as a
// verified waiver. Verified 2026-08-17 against `gh repo list ConductionNL`
// (non-archived); ids are the appinfo/info.xml <id>, not the repo name — hence
// `n8n` for the `n8n-nextcloud` repo. `mydash` is deliberately ABSENT: the app
// is `launchpad` and the mydash repo is archived.
//
// A second copy of a fleet-app list lives in
// check_phantom_cross_app_rpc.py#FLEET_APP_IDS (12 ids, a different and
// narrower purpose — quoted app ids in `->call()`). They are NOT merged here on
// purpose: this is shared infrastructure consumed live at @main by every fleet
// app, and a refactor touching a second gate's inputs is a wider blast radius
// than this change is worth. Recorded so the next reader knows both exist.
const FLEET_APP_IDS = new Set([
	// 18 core apps
	'openregister', 'opencatalogi', 'openconnector', 'docudesk', 'nldesign',
	'launchpad', 'softwarecatalog', 'larpingapp', 'zaakafhandelapp', 'procest',
	'pipelinq', 'shillinq', 'scholiq', 'portaliq', 'decidesk', 'openbuild',
	'doriath', 'hermiq',
	// ExApp sidecar wrappers
	'openklant', 'opentalk', 'openzaak', 'valtimo', 'n8n',
])

// This app's OWN id, for the "same-app case wearing a cross-app disguise"
// refusal. TWO sources, unioned, because either can be absent or wrong and
// neither failure may open the bypass:
//   appinfo/info.xml <id>  — authoritative for a Nextcloud app, present in
//                            every fleet repo.
//   basename(APP_DIR)      — what CI actually gives us
//                            (/home/runner/work/procest/procest), and the only
//                            source when the checker runs over a fixture or a
//                            partial checkout.
// A union can only ever REFUSE more, never accept more, so a false positive
// here costs an app one honest error message ("use the bare form") while a
// false negative would cost the strict path entirely.
function declaringAppIds(appDir) {
	const ids = new Set()
	const base = path.basename(appDir)
	if (base) ids.add(base.toLowerCase())
	try {
		const xml = fs.readFileSync(path.join(appDir, 'appinfo', 'info.xml'), 'utf8')
		const m = /<id>\s*([^<\s]+)\s*<\/id>/.exec(xml)
		if (m) ids.add(m[1].toLowerCase())
	} catch (e) { /* no appinfo/info.xml — the basename still guards */ }
	return ids
}

// Does this app DECLARE a dependency on `appId`? Informational only — it is
// reported in the WARN and never decides the verdict.
//
// Deliberately NOT a requirement, and the reasoning matters: manifest
// `dependencies` is RUNTIME-LOAD-BEARING (CnAppRoot resolves each id via
// useAppStatus — a HARD entry blocks the shell behind CnDependencyMissing, a
// SOFT one raises a dismissible banner). Making the waiver require one would
// mean adopting it CHANGES WHAT USERS SEE, which the "runtime-inert" property
// of menu-layout.json exists to avoid, and would push a product decision into
// a gate. So the gate REPORTS the answer and lets the reviewer weigh it: an
// app claiming its functionality moved to an app it does not depend on is a
// coherent thing to notice and an incoherent thing to auto-enforce.
function declaresDependencyOn(manifest, appId) {
	const deps = Array.isArray(manifest && manifest.dependencies) ? manifest.dependencies : []
	return deps.some((d) => (typeof d === 'string' && d === appId)
		|| (d && typeof d === 'object' && d.id === appId))
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
			// COMPARE PAGE IDENTITY, NOT THE ROUTE SPELLING (.github#340).
			//
			// A `menu[].route` may hold EITHER a pages[].id or a pages[].route —
			// check (a) above accepts both and every app uses both spellings.
			// This invariant used to compare the raw strings, so two menu
			// entries reaching the SAME page by different spellings did not
			// count as reaching each other. Retiring one of them is precisely
			// the "duplicate navigation entry whose page is still reachable"
			// that ADR-044 §5 sanctions, and it was reported as an orphan.
			//
			// Measured on a two-entry manifest (`route: "ItemsPage"` and
			// `route: "/items"`, one page `{id: ItemsPage, route: /items}`):
			// removing the path-spelled entry FAILED removals-invariant.
			//
			// Resolve both sides to the page id before comparing. A reference
			// that resolves to no page is left as-is: check (a) already fails
			// it, and collapsing unresolvable references onto one another here
			// would let two broken entries vouch for each other.
			const pageIdByRoute = new Map()
			for (const p of pages) {
				if (!p || typeof p.route !== 'string' || typeof p.id !== 'string') continue
				if (!pageIdByRoute.has(p.route)) pageIdByRoute.set(p.route, p.id)
			}
			const pageKey = (ref) => (pageIds.has(ref) ? ref : (pageIdByRoute.get(ref) || ref))
			const effectiveRoutes = []
			collectMenuRoutes(manifest.menu, '/menu', effectiveRoutes)
			const effectiveKeys = new Set(effectiveRoutes.map((m) => pageKey(m.route)))

			// REACHABILITY IS A CLOSURE, NOT A ONE-HOP MENU LOOKUP.
			//
			// Seeded by the surviving menu, then expanded along the declarative
			// navigation edges each reachable page declares (ROUTE_REF_KEYS
			// above). TRANSITIVE ON PURPOSE: an edge is credited only when it
			// is declared BY A PAGE THAT IS ITSELF REACHABLE, so two orphaned
			// pages linking to each other cannot vouch for one another — the
			// same trap the pageKey normalisation above is careful not to fall
			// into with unresolvable references.
			//
			// UNIONED WITH `effectiveKeys`, NEVER SUBSTITUTED FOR IT. The
			// closure only credits keys that resolve to a real page, while
			// `effectiveKeys` also carries menu routes that resolve to nothing
			// (check (a) fails those separately, and this invariant must not
			// fail them a second time). Taking the union makes this change
			// strictly ADDITIVE: no removal that passed this invariant before
			// can fail it now.
			const edgesByPage = new Map()
			for (const p of pages) {
				if (!p || typeof p.id !== 'string') continue
				const refs = []
				collectRouteRefs(p, refs)
				edgesByPage.set(p.id, refs)
			}
			const reachable = new Set(effectiveKeys)
			const seen = new Set()
			const queue = []
			const visit = (key) => {
				if (!pageIds.has(key)) return
				reachable.add(key)
				if (seen.has(key)) return
				seen.add(key)
				queue.push(key)
			}
			for (const k of effectiveKeys) visit(k)
			while (queue.length > 0) {
				const from = queue.shift()
				for (const ref of (edgesByPage.get(from) || [])) visit(pageKey(ref))
			}

			// menu-layout.json#removalsReplacedBy — THE ONE THING THE GATE
			// CANNOT DERIVE, DECLARED BY THE APP AND VERIFIED BY THE GATE.
			//
			// A navigation surface is sometimes retired because the
			// FUNCTIONALITY moved to a surface that does not — and should not —
			// name the old page anywhere: an index page superseded by a
			// `folderSidebar` filter on another index, a standalone map page
			// superseded by `viewModes: ["map"]` on the index it duplicated,
			// three decision pages superseded by one sidebar tab on a detail
			// page. All three shipped on procest, and NONE of them references
			// the retired page in the manifest — measured, not assumed: a full
			// string walk of procest's assembled manifest finds seven of its
			// eight retired pages named by NOTHING but their own `pages[]`
			// entry. There is no edge to widen toward, and inferring one from a
			// page TYPE (`viewModes` contains "map", so any map page may go)
			// would bless deleting a map page in every app that owns a map
			// viewMode — the widening that retires the check.
			//
			// So the gate is RIGHT that the page has no entry point, and WRONG
			// that this is a functionality loss. That is exactly the ambiguity
			// check (f) direction 1 already answers with a WARN — "an orphan is
			// either wired or deleted and the gate cannot know which". Here the
			// app CAN say, and the claim is CHECKABLE rather than prose: it
			// names the page carrying the functionality now, and the gate
			// refuses it unless that page exists AND is itself reachable. It
			// therefore ROTS LOUDLY — the day the named page leaves the menu,
			// every waiver pointing at it FAILs. That is the property a
			// free-text reason does not have, and the reason this is not
			// `@removals-invariant exclude <reason>`.
			const replacedBy = (inputs.menuLayout
				&& typeof inputs.menuLayout.removalsReplacedBy === 'object'
				&& inputs.menuLayout.removalsReplacedBy !== null
				&& !Array.isArray(inputs.menuLayout.removalsReplacedBy))
				? inputs.menuLayout.removalsReplacedBy
				: {}
			const selfAppIds = declaringAppIds(APP_DIR)
			removals.forEach((id, i) => {
				const entry = findEntry(preRemoval, id)
				if (!entry) {
					warn('removals-invariant', `/menu-layout/removals/${i}`, `removal '${id}' matches no merged menu entry (stale removal)`)
					return
				}
				if (typeof entry.route !== 'string' || entry.route === '') return // nothing routable retired
				if (!reachable.has(pageKey(entry.route))) {
					const ptr = `/menu-layout/removals/${i}`
					const key = pageKey(entry.route)
					const declared = replacedBy[id]
					if (declared === undefined) {
						fail('removals-invariant', ptr, `removal '${id}' orphans route '${entry.route}' — no surviving menu entry, and no declarative navigation edge (open-page action target, handler:'navigate' route, viewAllRoute / rowRoute / clickRoute / onSuccessRoute / drilldown.route) on any REACHABLE page names it (ADR-044 no-functionality-loss). If the FUNCTIONALITY moved to another surface rather than the link, name that surface's page in menu-layout.json#removalsReplacedBy['${id}'] — the gate then verifies that page exists and is itself reachable. If the functionality moved to ANOTHER app, spell it '<appId>:<PageId>' (e.g. 'decidesk:SomePage'), which the gate can only check syntactically`)
					} else if (typeof declared !== 'string' || declared === '') {
						fail('removals-invariant', ptr, `removal '${id}' orphans route '${entry.route}' and its menu-layout.json#removalsReplacedBy entry is not a non-empty page reference — the waiver names nothing the gate can check (ADR-044 no-functionality-loss)`)
					} else if (!pageIds.has(pageKey(declared)) && CROSS_APP_ATTEMPT_RE.test(declared)) {
						// CROSS-APP FORM `<appId>:<PageId>` — a STRICTLY WEAKER
						// check, entered only when the value resolves to NO local
						// page, so the same-app path above and the exists /
						// not-itself / reachable path below are never skippable
						// through this branch. See the block comment at
						// CROSS_APP_APP_RE for what this can and cannot verify.
						const [, otherApp, otherPage] = CROSS_APP_ATTEMPT_RE.exec(declared)
						if (!CROSS_APP_APP_RE.test(otherApp)) {
							fail('removals-invariant', ptr, `removal '${id}' orphans route '${entry.route}' and its declared replacement '${declared}' is not a usable reference: the part before ':' ('${otherApp}') is not a Nextcloud app id (lowercase, starting with a letter, then letters/digits/_/-). A cross-app replacement is spelled '<appId>:<PageId>' (ADR-044 no-functionality-loss)`)
						} else if (!CROSS_APP_PAGE_RE.test(otherPage)) {
							fail('removals-invariant', ptr, `removal '${id}' orphans route '${entry.route}' and its declared replacement '${declared}' is not a usable reference: the part after ':' ('${otherPage}') is not a page id (a bare identifier — not a path, not empty, no second ':'). A cross-app replacement names a PAGE in the other app, not a URL (ADR-044 no-functionality-loss)`)
						} else if (selfAppIds.has(otherApp.toLowerCase())) {
							fail('removals-invariant', ptr, `removal '${id}' orphans route '${entry.route}' and its declared replacement '${declared}' names THIS app ('${otherApp}') — that is the same-app case wearing a cross-app disguise, and the cross-app form is checked strictly less. Write the bare page reference ('${otherPage}') so the gate can verify it exists, is not the retired page, and is itself reachable (ADR-044 no-functionality-loss)`)
						} else if (!FLEET_APP_IDS.has(otherApp)) {
							fail('removals-invariant', ptr, `removal '${id}' orphans route '${entry.route}' and its declared replacement '${declared}' names '${otherApp}', which is not a known Conduction fleet app id — the gate cannot distinguish an app it has never heard of from a typo, and an unrecognised id would otherwise read as a verified waiver. If '${otherApp}' is a real fleet app, add it to FLEET_APP_IDS in scripts/lib/check_manifest_crossref.js (ADR-044 no-functionality-loss)`)
						} else {
							const dep = declaresDependencyOn(manifest, otherApp)
							warn('removals-invariant', ptr, `removal '${id}' leaves route '${entry.route}' with no navigation entry point of its own; menu-layout.json declares its functionality moved to page '${otherPage}' in ANOTHER app, '${otherApp}'. REDUCED GUARANTEE — THIS WAIVER WAS NOT VERIFIED THE WAY A SAME-APP ONE IS. The gate checked only that '${otherApp}' is a known fleet app id and is not this app; it CANNOT check that page '${otherPage}' exists in '${otherApp}', that it is reachable there, that '${otherApp}' is installed, or that it carries this functionality — it does not read another app's manifest. It also does NOT rot: a same-app waiver FAILs the day its target leaves the menu, this one cannot. ${dep ? `This app does declare a manifest dependency on '${otherApp}'.` : `This app declares NO manifest dependency on '${otherApp}', so nothing in this repo corroborates the claim.`} Verifying it is a review judgement (ADR-044 no-functionality-loss)`)
						}
					} else if (!pageIds.has(pageKey(declared))) {
						fail('removals-invariant', ptr, `removal '${id}' orphans route '${entry.route}' and its declared replacement '${declared}' resolves to no pages[].id or pages[].route — a waiver pointing at a page that does not exist is not a replacement (ADR-044 no-functionality-loss)`)
					} else if (pageKey(declared) === key) {
						fail('removals-invariant', ptr, `removal '${id}' orphans route '${entry.route}' and declares ITSELF as its replacement — a page cannot vouch for its own reachability (ADR-044 no-functionality-loss)`)
					} else if (!reachable.has(pageKey(declared))) {
						fail('removals-invariant', ptr, `removal '${id}' orphans route '${entry.route}' and its declared replacement '${declared}' is ITSELF unreachable — the waiver moves the orphan, it does not close it (ADR-044 no-functionality-loss)`)
					} else {
						warn('removals-invariant', ptr, `removal '${id}' leaves route '${entry.route}' with no navigation entry point of its own; menu-layout.json declares its functionality moved to '${declared}', which exists and is reachable. The page stays routable for deep links. The gate can only check that '${declared}' IS reachable — whether it genuinely carries this functionality is a review judgement`)
					}
				}
			})
		}
	}

	// (f) component-registry cross-reference — larpingapp#286, both directions.
	const registry = parseRegistry(APP_DIR)
	// THE SECOND REGISTRATION SOURCE.
	//
	// The runtime resolution order is documented in every app's own
	// customComponents.js, and the console error this gate quotes says it out
	// loud: "not found in registry OR customComponents". The first version of
	// this check read only registry.js and therefore reported 9 false FAILs on
	// softwarecatalog and 1 on hermiq for components that are registered — just
	// in the other file. A component resolvable by EITHER route resolves.
	const legacy = parseRegistry(APP_DIR, 'customComponents.js')
	if (registry && registry.parsed) {
		const refs = []
		collectComponentRefs({ pages: manifest.pages }, '', refs)
		const named = new Set(refs.map((r) => r.name))
		const registered = new Set(registry.entries.keys())
		if (legacy && legacy.parsed) for (const k of legacy.entries.keys()) registered.add(k)

		// Direction 2 — a manifest position naming a component nobody registers.
		// Renders nothing at runtime, so this FAILS.
		for (const { ptr, name } of refs) {
			if (LIB_COMPONENT.test(name)) continue
			if (registered.has(name)) continue
			fail('registry-crossref', ptr,
				`component '${name}' is named by the manifest but is registered in neither src/registry.js nor src/customComponents.js — resolution falls through and renders NOTHING`)
		}

		// Direction 1 — a registered component no manifest position names.
		// Either wire it or delete it; the gate cannot know which, so WARN.
		for (const [name, meta] of registry.entries) {
			if (named.has(name)) continue
			if (!REGISTRY_KINDS_REQUIRING_A_POSITION.has(meta.kind)) continue
			warn('registry-crossref', '/pages',
				`src/registry.js exports '${name}' (kind '${meta.kind}') but no manifest tabs[]/sections[]/page entry names it — the surface it renders has no entry point. Wire it, or delete it`)
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
