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

// --- role-resolvable / group-declared discovery (fix-dead-role-gates) --------
//
// Closes the defect class fix-dead-role-gates exists for: a manifest
// `visibleIf.user.primaryRole` literal that the app's own role resolver can
// never emit (silent, permanent menu-item lockout), and the mirror-image
// defect — an `IGroupManager::isInGroup()` call naming a group id nothing in
// the app declares (a role that can never be granted). Both are silent at
// runtime: a `visibleIf` mismatch just hides a menu entry, and an undeclared
// group returns `false` from `isInGroup()` forever. See
// openspec/changes/fix-dead-role-gates/design.md "CI Gate Extension".

// Blank out PHP comments (`//`, `#` except `#[Attribute]`, `/* */`) while
// keeping string literal CONTENTS, all other code, and every newline —
// same-length output so an index into the mask addresses the original text.
//
// WHY THIS EXISTS: a PHPDoc block is free to contain example code (this very
// file's fixtures do — "a `provideInitialState('primaryRole', ...)` call
// site" is prose, not a call site). Scanning raw source found that sentence
// before the real call and mis-resolved the method name from it. Masking
// comments first is the same fix js_scope.js applies for JS registries (#424)
// — a two-line unescaped regex swallowed real registrations there; scanning
// unmasked PHP source here would misattribute resolver discovery to prose.
function phpCommentMask(text) {
	let out = ''
	let i = 0
	const n = text.length
	while (i < n) {
		const c = text[i]
		if (c === "'" || c === '"') {
			const quote = c
			out += c
			i++
			while (i < n) {
				const ch = text[i]
				out += ch
				if (ch === '\\' && i + 1 < n) { out += text[i + 1]; i += 2; continue }
				i++
				if (ch === quote) break
			}
			continue
		}
		if (c === '/' && text[i + 1] === '/') {
			while (i < n && text[i] !== '\n') { out += ' '; i++ }
			continue
		}
		if (c === '#' && text[i + 1] !== '[') {
			while (i < n && text[i] !== '\n') { out += ' '; i++ }
			continue
		}
		if (c === '/' && text[i + 1] === '*') {
			out += '  '
			i += 2
			while (i < n && !(text[i] === '*' && text[i + 1] === '/')) {
				out += (text[i] === '\n') ? '\n' : ' '
				i++
			}
			if (i < n) { out += '  '; i += 2 }
			continue
		}
		out += c
		i++
	}
	return out
}

// Recursively list every `.php` file under `<appDir>/lib` (skip vendor/
// node_modules defensively — neither should exist under lib/, but a
// misplaced vendored copy must not be scanned as first-party code).
function listPhpFiles(appDir) {
	const root = path.join(appDir, 'lib')
	const out = []
	function walk(dir) {
		let entries
		try {
			entries = fs.readdirSync(dir, { withFileTypes: true })
		} catch (e) {
			return
		}
		for (const entry of entries) {
			if (entry.name === 'vendor' || entry.name === 'node_modules') continue
			const full = path.join(dir, entry.name)
			if (entry.isDirectory()) {
				walk(full)
			} else if (entry.isFile() && entry.name.endsWith('.php')) {
				out.push(full)
			}
		}
	}
	walk(root)
	return out
}

// Find the app's role-resolution service and its producible-value set.
//
// Discovery mirrors how `hydra-gate-initial-state` already locates the
// `IInitialState::provideInitialState` call site: grep every lib/**/*.php
// file for a call keyed on the literal `'primaryRole'`, take the method
// invoked on its second argument (e.g. `$this->dashboardRoleSvc-
// >resolvePrimaryRole($user)` → `resolvePrimaryRole`), then find the file
// that DEFINES a method of that name — that file is the resolver.
//
// From the resolver file, the producible-value set is the union of:
//   - every literal string `return 'x';` / `return "x";` in the file
//   - every key (associative) or bare value (plain list) of a `const` array
//     whose name contains ROLE (case-insensitive) — covers both the
//     `GROUP_BACKED_ROLES` role => group-id map shape and a plain
//     positional role-name list shape (the pre-fix scholiq form).
//
// Returns `{ file, roles: Set<string> }`, or `null` when no call site is
// discoverable (most apps do not gate on `primaryRole` at all — the caller
// WARNs and skips, matching this gate's existing WARN-on-unknowable posture
// for slug-resolution).
function discoverRoleResolver(appDir) {
	const files = listPhpFiles(appDir)
	let methodName = null
	for (const file of files) {
		let src
		try {
			src = phpCommentMask(fs.readFileSync(file, 'utf8'))
		} catch (e) {
			continue
		}
		const m = /provideInitialState\s*\(\s*['"]primaryRole['"]\s*,\s*([^;]+?)\)\s*;/.exec(src)
		if (!m) continue
		const callExpr = m[1]
		const calls = callExpr.match(/->\s*(\w+)\s*\(/g)
		if (!calls || calls.length === 0) continue
		const last = calls[calls.length - 1]
		methodName = /->\s*(\w+)\s*\(/.exec(last)[1]
		break
	}
	if (!methodName) return null

	for (const file of files) {
		let src
		try {
			src = phpCommentMask(fs.readFileSync(file, 'utf8'))
		} catch (e) {
			continue
		}
		const defRe = new RegExp(`function\\s+${methodName}\\s*\\(`)
		if (!defRe.test(src)) continue

		const roles = new Set()
		const returnRe = /return\s+['"]([a-z][a-z0-9-]*)['"]\s*;/g
		let rm
		while ((rm = returnRe.exec(src)) !== null) roles.add(rm[1])

		const constRe = /(?:private|public|protected)\s+const\s+(\w*ROLE\w*)\s*=\s*\[([\s\S]*?)\];/gi
		let cm
		while ((cm = constRe.exec(src)) !== null) {
			const body = cm[2]
			// Associative `'key' => 'value'` — the key is the producible role.
			const assocRe = /['"]([a-z][a-z0-9-]*)['"]\s*=>/g
			let am
			let sawAssoc = false
			while ((am = assocRe.exec(body)) !== null) { roles.add(am[1]); sawAssoc = true }
			// Plain positional list `'role', 'role', ...` (no `=>` at all in
			// the array) — every quoted entry is itself a producible role.
			if (!sawAssoc) {
				const listRe = /['"]([a-z][a-z0-9-]*)['"]/g
				let lm
				while ((lm = listRe.exec(body)) !== null) roles.add(lm[1])
			}
		}
		return { file, roles }
	}
	return null
}

// Collect every `visibleIf.user.primaryRole.in[]` literal in the assembled
// manifest, at any nesting depth, with the nearest enclosing menu item id.
function collectRoleLiterals(node, ptr, nearestId, out) {
	if (Array.isArray(node)) {
		node.forEach((v, i) => collectRoleLiterals(v, `${ptr}/${i}`, nearestId, out))
		return
	}
	if (!node || typeof node !== 'object') return
	const ownId = (typeof node.id === 'string' && node.id !== '') ? node.id : nearestId
	if (node.visibleIf && typeof node.visibleIf === 'object') {
		const pr = node.visibleIf['user.primaryRole']
		if (pr && typeof pr === 'object' && Array.isArray(pr.in)) {
			pr.in.forEach((literal, i) => {
				if (typeof literal === 'string' && literal !== '') {
					out.push({ ptr: `${ptr}/visibleIf/user.primaryRole/in/${i}`, id: ownId, literal })
				}
			})
		}
	}
	for (const [k, v] of Object.entries(node)) {
		if (k === '_note' || k === '_meta') continue
		collectRoleLiterals(v, `${ptr}/${k}`, ownId, out)
	}
}

// Collect every group id referenced anywhere in an OAS-shaped register
// document — a JS port of OpenRegister's `RbacGroupCollector::fromDocument()`
// (openregister/lib/Service/Authorization/RbacGroupCollector.php): the
// DERIVED floor (register + schema + property `authorization` blocks) unioned
// with the AUTHORED scope map
// (`components.securitySchemes.oauth2.flows.authorizationCode.scopes` keys).
const RESERVED_PRINCIPALS = new Set(['admin', 'public'])

function groupsFromAuthorizationBlock(authorization, out) {
	if (!authorization || typeof authorization !== 'object') return
	for (const [key, value] of Object.entries(authorization)) {
		if (!value || typeof value !== 'object') continue // e.g. `public: true`
		if (key === 'roles') {
			// role-name => group(s) map; only the VALUES are group ids.
			for (const assigned of Object.values(value)) {
				const list = Array.isArray(assigned) ? assigned : [assigned]
				for (const g of list) if (typeof g === 'string') out.add(g)
			}
			continue
		}
		if (!Array.isArray(value)) continue
		for (const rule of value) {
			if (typeof rule === 'string') { out.add(rule); continue }
			if (rule && typeof rule === 'object' && typeof rule.group === 'string') out.add(rule.group)
		}
	}
}

function groupsFromSchemaDefinition(schemaDefinition, out) {
	groupsFromAuthorizationBlock(schemaDefinition && schemaDefinition.authorization, out)
	const properties = schemaDefinition && schemaDefinition.properties
	if (!properties || typeof properties !== 'object') return
	for (const propertyDefinition of Object.values(properties)) {
		groupsFromAuthorizationBlock(propertyDefinition && propertyDefinition.authorization, out)
	}
}

// Discover every group id declared anywhere in the app's register JSON: the
// derived-floor authorization blocks plus the authored OAS scope map. Reads
// the same `lib/Settings/*register*.json` (+ `register.d/*.json`) files
// `discoverDeclaredSlugs` already locates.
function discoverDeclaredGroups(appDir) {
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
	const groups = new Set()
	for (const file of files) {
		let doc
		try {
			doc = JSON.parse(fs.readFileSync(file, 'utf8'))
		} catch (e) {
			continue // corrupt register JSON is already reported by slug-resolution
		}
		const registers = (doc.components && doc.components.registers) || doc.registers
		if (registers && typeof registers === 'object') {
			for (const def of Object.values(registers)) {
				groupsFromAuthorizationBlock(def && def.authorization, groups)
			}
		}
		const schemas = (doc.components && doc.components.schemas) || doc.schemas
		if (schemas && typeof schemas === 'object') {
			for (const def of Object.values(schemas)) {
				groupsFromSchemaDefinition(def, groups)
			}
		}
		const scopes = doc.components && doc.components.securitySchemes
			&& doc.components.securitySchemes.oauth2
			&& doc.components.securitySchemes.oauth2.flows
			&& doc.components.securitySchemes.oauth2.flows.authorizationCode
			&& doc.components.securitySchemes.oauth2.flows.authorizationCode.scopes
		if (scopes && typeof scopes === 'object') {
			for (const key of Object.keys(scopes)) groups.add(key)
		}
	}
	for (const p of RESERVED_PRINCIPALS) groups.add(p)
	return { hasRegisterJson: files.length > 0, groups }
}

// Collect every `IGroupManager::isInGroup($uid, <arg>)` call site under
// lib/**/*.php. A LITERAL second argument (single- or double-quoted string)
// is checkable; anything else (variable, concatenation, method call) is
// dynamically-constructed and cannot be resolved statically.
function collectIsInGroupCallSites(appDir) {
	const out = []
	for (const file of listPhpFiles(appDir)) {
		let raw
		try {
			raw = fs.readFileSync(file, 'utf8')
		} catch (e) {
			continue
		}
		const src = phpCommentMask(raw) // same length/newlines as raw — a doc-comment example must not read as a real call site
		const lines = raw.split('\n')
		const callRe = /->\s*isInGroup\s*\(\s*[^,]+,\s*([^)]+)\)/g
		let m
		while ((m = callRe.exec(src)) !== null) {
			const arg = m[1].trim()
			const lineNo = src.slice(0, m.index).split('\n').length
			const literalMatch = /^['"]([^'"]*)['"]$/.exec(arg)
			out.push({
				file,
				line: lineNo,
				lineText: (lines[lineNo - 1] || '').trim(),
				literal: literalMatch ? literalMatch[1] : null,
			})
		}
	}
	return out
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
			removals.forEach((id, i) => {
				const entry = findEntry(preRemoval, id)
				if (!entry) {
					warn('removals-invariant', `/menu-layout/removals/${i}`, `removal '${id}' matches no merged menu entry (stale removal)`)
					return
				}
				if (typeof entry.route !== 'string' || entry.route === '') return // nothing routable retired
				if (!effectiveKeys.has(pageKey(entry.route))) {
					fail('removals-invariant', `/menu-layout/removals/${i}`, `removal '${id}' orphans route '${entry.route}' — no surviving menu entry reaches it (ADR-044 no-functionality-loss)`)
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

	// (g) role-resolvable (fix-dead-role-gates) — every visibleIf.user.
	// primaryRole literal must resolve to a value the app's role resolver can
	// actually emit. A mismatch is silent in the running app (the menu entry
	// just never appears), so this is the mechanical enforcement of that
	// invariant.
	const roleLiterals = []
	collectRoleLiterals(manifest, '', null, roleLiterals)
	if (roleLiterals.length > 0) {
		const resolver = discoverRoleResolver(APP_DIR)
		if (!resolver) {
			warn('role-resolvable', '/', `manifest gates on user.primaryRole but no role-resolution service is discoverable (no 'primaryRole' provideInitialState call site under lib/) — role-resolvable cannot be checked`)
		} else {
			for (const { ptr, id, literal } of roleLiterals) {
				if (!resolver.roles.has(literal)) {
					fail('role-resolvable', ptr, `menu item '${id || '(no id)'}' names role '${literal}' in visibleIf.user.primaryRole, which ${path.relative(APP_DIR, resolver.file)}'s resolver can never emit`)
				}
			}
		}
	}

	// (h) group-declared (fix-dead-role-gates) — every literal-string
	// IGroupManager::isInGroup() call site must name a group id declared
	// somewhere the app's RBAC group collector reads (register/schema
	// authorization blocks or the OAS scope map). An undeclared literal group
	// id can never be granted — isInGroup() against a non-existent group
	// always returns false, so the gated role is permanently unreachable.
	const groupCallSites = collectIsInGroupCallSites(APP_DIR)
	if (groupCallSites.length > 0) {
		const declaredGroups = discoverDeclaredGroups(APP_DIR)
		for (const site of groupCallSites) {
			const rel = path.relative(APP_DIR, site.file)
			if (site.literal === null) {
				warn('group-declared', `${rel}:${site.line}`, `isInGroup() call names a dynamically-constructed group id ('${site.lineText}') — not statically resolvable`)
				continue
			}
			if (!declaredGroups.hasRegisterJson) {
				warn('group-declared', `${rel}:${site.line}`, `isInGroup($uid, '${site.literal}') cannot be resolved — no lib/Settings/*register*.json in repo`)
				continue
			}
			if (!declaredGroups.groups.has(site.literal)) {
				fail('group-declared', `${rel}:${site.line}`, `isInGroup($uid, '${site.literal}') names a group id declared nowhere in this app's RBAC configuration (register/schema authorization blocks or the OAS scope map)`)
			}
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
