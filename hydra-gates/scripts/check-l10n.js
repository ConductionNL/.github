#!/usr/bin/env node
/* SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl> */
/* SPDX-License-Identifier: EUPL-1.2 */
/**
 * check-l10n.js — one shared translation-coverage checker for the fleet.
 *
 * WHAT IT IS FOR
 * --------------
 * Every user-visible string an app ships should reach the English catalogue
 * (l10n/en.json) and, for a Dutch audience, the Dutch one (l10n/nl.json). A
 * string that reaches neither renders its source text, silently, in every
 * locale. Nothing else in the pipeline notices: `check:l10n-js` compares
 * nl.json to the generated nl.js, and a string absent from BOTH is perfectly
 * in sync.
 *
 * THE DEFECT THIS EXISTS TO FIX
 * -----------------------------
 * Twenty-one apps vendored a copy of this script, and every one of them
 * computed `missing` from `src/` t() calls alone:
 *
 *     const missing = [...usedKeys].filter((k) => !keys.has(k))
 *
 * where `usedKeys` came only from walking .vue/.js/.ts. PHP and schema JSON
 * were, at best, added to the list of things that SUPPRESS an "unused"
 * warning. So a `->t('…')` in a controller could never produce a "missing"
 * finding, and a schema `title` could not either. No app in the fleet could
 * see a server-side or schema string that had reached no catalogue at all.
 *
 * Measured on opencatalogi at development@4af8e55a: 49 strings passed to a PHP
 * translate call and 319 register/schema strings have no key in en.json. Its
 * own vendored copy reports zero, and the src/ leg really is clean, so the 368
 * are not a stricter reading of the old scope. They are the new sources.
 *
 * Here `missing` is computed from ALL FOUR sources, and each finding carries
 * the origin that produced it.
 *
 * FOUR SOURCES
 * ------------
 *   SRC       src/ *.vue, *.js, *.ts — t(), n(), $t(), $n() literal calls
 *   PHP       lib/, templates/, appinfo/ — ->t('…') and ->n('…')
 *   MANIFEST  src/manifest.json and src/manifest.d/*.json — the fields a
 *             renderer walks (CnAppNav labels, page titles, walkthrough copy)
 *   SCHEMA    lib/Settings/**\/*.json — register and schema title/description,
 *             including per-property, which OpenRegister renders in forms and
 *             detail pages
 *
 * All four feed MISSING, and all four suppress UNUSED.
 *
 * ONE DELIBERATE EXCEPTION. A PHP array value under a rendered field name
 * (`'description' => '…'`) suppresses UNUSED but does NOT create MISSING.
 * `->t('Approve')` is an unambiguous claim that a string is user-facing; a
 * `description` key in an array is not. Measured on opencatalogi 2026-09-19:
 * treating array values as missing-creating added 63 findings, and the sample
 * was dominated by MCP tool descriptions an agent reads and no person sees.
 * Precision here is worth more than reach, because a gate whose first run is
 * mostly noise gets excluded rather than fixed.
 *
 * WARNING FIRST
 * -------------
 * `--warn-only` makes the script exit 0 whatever it finds. Gate 117 passes it,
 * because fourteen of twenty-one repos carry inherited findings and a blocking
 * launch reddens them the minute it merges. The findings are printed either
 * way; only the exit code is held back.
 *
 * USAGE
 *   node check-l10n.js [app-root] [--warn-only] [--json] [--source=SRC,PHP,...]
 *
 * EXIT CODES
 *   0  no findings, or --warn-only
 *   1  findings
 *   4  empty scope: no catalogue, or no source string anywhere
 *   9  could not read something it needed (a crash is not a finding)
 */

'use strict'

const fs = require('fs')
const path = require('path')

const ALL_SOURCES = ['SRC', 'PHP', 'MANIFEST', 'SCHEMA']

// Fields a renderer walks and translates by literal lookup. Shared by the
// manifest collector and the PHP-array collector, because a PHP array using
// `label` / `description` is the same kind of thing: data, not code.
const RENDERED_FIELDS = [
	'title',
	'body',
	'task',
	'label',
	'description',
	'emptyText',
	'placeholder',
	'subtitle',
	'helpText',
	'allLabel',
]

// ---------------------------------------------------------------------------
// tiny helpers
// ---------------------------------------------------------------------------

function walk(dir, exts) {
	const out = []
	if (!fs.existsSync(dir)) {
		return out
	}
	for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
		if (entry.name === 'node_modules' || entry.name === 'vendor' || entry.name.startsWith('.')) {
			continue
		}
		const full = path.join(dir, entry.name)
		if (entry.isDirectory()) {
			out.push(...walk(full, exts))
		} else if (exts.some((e) => entry.name.endsWith(e))) {
			out.push(full)
		}
	}
	return out
}

function readJson(file) {
	return JSON.parse(fs.readFileSync(file, 'utf8'))
}

/**
 * Keys of a Nextcloud catalogue file.
 *
 * `{ "translations": { key: value } }` is the shape these apps ship. A plain
 * flat map is accepted too, because a few older apps still write one.
 *
 * @param {string} file path to en.json / nl.json
 * @return {Map<string,string>} key to translated value
 */
function loadCatalogue(file) {
	const out = new Map()
	if (!fs.existsSync(file)) {
		return out
	}
	const raw = readJson(file)
	const body = raw && typeof raw === 'object' && raw.translations ? raw.translations : raw
	if (!body || typeof body !== 'object') {
		return out
	}
	for (const [k, v] of Object.entries(body)) {
		if (typeof v === 'string') {
			out.set(k, v)
		} else if (Array.isArray(v)) {
			// Plural form: `["one", "other"]`. The key is still the key.
			out.set(k, v[0] ?? '')
		}
	}
	return out
}

// ---------------------------------------------------------------------------
// SRC — t() / n() in .vue, .js, .ts
// ---------------------------------------------------------------------------

/**
 * Read a quoted literal starting at the opening quote. Returns null when the
 * literal is unterminated, spans a newline, or is a template literal with an
 * interpolation — none of those is a static key this checker can trust.
 *
 * @param {string} text source
 * @param {number} start index of the opening quote
 * @return {{value: string, end: number}|null} the literal and its closing index
 */
function readLiteral(text, start) {
	const quote = text[start]
	if (quote !== "'" && quote !== '"' && quote !== '`') {
		return null
	}
	let i = start + 1
	let value = ''
	while (i < text.length) {
		const c = text[i]
		if (c === '\\' && i + 1 < text.length) {
			const n = text[i + 1]
			if (n === 'u' && /^[0-9a-fA-F]{4}$/.test(text.slice(i + 2, i + 6))) {
				value += String.fromCharCode(parseInt(text.slice(i + 2, i + 6), 16))
				i += 6
				continue
			}
			const simple = { n: '\n', t: '\t', r: '\r' }
			value += simple[n] ?? n
			i += 2
			continue
		}
		if (c === quote) {
			return { value, end: i }
		}
		if (quote !== '`' && c === '\n') {
			return null
		}
		if (quote === '`' && c === '$' && text[i + 1] === '{') {
			return null
		}
		value += c
		i += 1
	}
	return null
}

/**
 * Every string the frontend passes to t() or n().
 *
 * `n()` matters as much as `t()`: an extractor that matched only `t(` reported
 * every plural key as unused, which is how a clean-up script came to be armed
 * to delete live keys from all 37 locale files.
 *
 * @param {string} root app root
 * @param {string} appId the app id used as the first argument
 * @return {Set<string>} strings the frontend translates
 */
function collectSrcStrings(root, appId) {
	const used = new Set()
	const srcDir = path.join(root, 'src')
	// `(?<![\w$])` rejects identifiers that merely END in t or n — format(,
	// fn(, min( — which a bare \b lets through.
	const re = new RegExp(
		`(?<![\\w$])\\$?([tn])\\s*\\(\\s*(['"\`])${appId.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\2\\s*,\\s*`,
		'g',
	)
	for (const file of walk(srcDir, ['.vue', '.js', '.ts'])) {
		const source = fs.readFileSync(file, 'utf8')
		let m
		while ((m = re.exec(source)) !== null) {
			const fn = m[1]
			const first = readLiteral(source, re.lastIndex)
			if (!first) {
				continue
			}
			used.add(first.value)
			if (fn !== 'n') {
				continue
			}
			// n(app, singular, plural, count) — the plural form is a key too.
			let j = first.end + 1
			while (j < source.length && /[\s,]/.test(source[j])) {
				j += 1
			}
			const second = readLiteral(source, j)
			if (second) {
				used.add(second.value)
			}
		}
	}
	return used
}

// ---------------------------------------------------------------------------
// PHP — ->t() / ->n(), and rendered array values
// ---------------------------------------------------------------------------

/**
 * Every string a server-side translate call passes.
 *
 * This is one of the two sources the vendored copies could only ever use to
 * suppress an "unused" warning. Here it also produces "missing", which is the
 * whole point: a `->t('Approve')` in a controller with no key in en.json is a
 * string that renders English to every reader and nothing reports it.
 *
 * @param {string} root app root
 * @return {Set<string>} strings passed to a server-side translate call
 */
function collectPhpTranslated(root) {
	const used = new Set()
	const patterns = [
		/->[tn]\(\s*'((?:\\.|[^'\\])*)'/g,
		/->[tn]\(\s*"((?:\\.|[^"\\])*)"/g,
	]
	for (const sub of ['lib', 'templates', 'appinfo']) {
		for (const file of walk(path.join(root, sub), ['.php'])) {
			const source = fs.readFileSync(file, 'utf8')
			for (const re of patterns) {
				let m
				while ((m = re.exec(source)) !== null) {
					used.add(m[1].replace(/\\(['"\\])/g, '$1'))
				}
			}
		}
	}
	return used
}

/**
 * Every user-visible string a PHP array DECLARES for the client to render.
 *
 * The setup wizard's card step forced this: a `choice` step with
 * `optionsSource` carries no options in the manifest, so every card's label
 * and description is a PHP array value the wizard translates client-side by
 * literal lookup. Adjacent literals joined by `.` are read as one value,
 * because PHP wraps long prose that way and a first-fragment-only match misses
 * the rest.
 *
 * @param {string} root app root
 * @return {Set<string>} strings a PHP array declares for the client
 */
function collectPhpDeclared(root) {
	const out = new Set()
	const PART = String.raw`'((?:\\.|[^'\\])*)'|"((?:\\.|[^"\\])*)"`
	for (const file of walk(path.join(root, 'lib'), ['.php'])) {
		const source = fs.readFileSync(file, 'utf8')
		for (const field of RENDERED_FIELDS) {
			const re = new RegExp(
				String.raw`['"]${field}['"]\s*=>\s*\(?\s*((?:(?:${PART})\s*\.?\s*)+)`,
				'g',
			)
			let m
			while ((m = re.exec(source)) !== null) {
				const parts = [...m[1].matchAll(new RegExp(PART, 'g'))].map((q) =>
					(q[1] ?? q[2] ?? '').replace(/\\(['"\\])/g, '$1'),
				)
				const joined = parts.join('')
				if (joined.trim()) {
					out.add(joined)
				}
			}
		}
	}
	return out
}

// ---------------------------------------------------------------------------
// MANIFEST
// ---------------------------------------------------------------------------

/**
 * Every user-visible string the manifest declares.
 *
 * `src/manifest.d/*.json` counts: the fragments are merged at runtime via
 * require.context, so a checker that opens only `src/manifest.json` is blind
 * to whatever they add. `_meta` is skipped, being per-fragment provenance that
 * is never rendered.
 *
 * @param {string} root app root
 * @return {Set<string>} the manifest's user-visible strings
 */
function collectManifestStrings(root) {
	const out = new Set()
	const files = []
	const main = path.join(root, 'src/manifest.json')
	if (fs.existsSync(main)) {
		files.push(main)
	}
	files.push(...walk(path.join(root, 'src/manifest.d'), ['.json']))

	const fields = new Set(RENDERED_FIELDS)
	const visit = (node) => {
		if (Array.isArray(node)) {
			node.forEach(visit)
			return
		}
		if (!node || typeof node !== 'object') {
			return
		}
		for (const [k, v] of Object.entries(node)) {
			if (k === '_meta') {
				continue
			}
			if (typeof v === 'string') {
				if (fields.has(k) && v.trim()) {
					out.add(v)
				}
			} else {
				visit(v)
			}
		}
	}
	for (const file of files) {
		try {
			visit(readJson(file))
		} catch (e) {
			throw new Error(`${path.relative(root, file)}: ${e.message}`)
		}
	}
	return out
}

// ---------------------------------------------------------------------------
// SCHEMA
// ---------------------------------------------------------------------------

/**
 * Every user-visible string an OpenRegister register or schema declares.
 *
 * The second source no vendored copy could turn into a "missing" finding, and
 * the larger one: 213 on opencatalogi alone. These are rendered by
 * OpenRegister — a schema's `title` heads its detail page, a property's
 * `title` labels its form field, a `description` becomes the help text under
 * it — so an untranslated one is English on screen in every locale.
 *
 * SCOPE IS DELIBERATELY NARROW. Only `components.registers` and
 * `components.schemas` are read, and only `title` and `description` within
 * them. `info.title`, `info.description` and everything under an `x-` key are
 * package metadata that no reader sees, and including them would have the
 * checker demand translations for a source URL's prose.
 *
 * @param {string} root app root
 * @return {Set<string>} register and schema strings rendered to a reader
 */
function collectSchemaStrings(root) {
	const out = new Set()
	const visit = (node) => {
		if (Array.isArray(node)) {
			node.forEach(visit)
			return
		}
		if (!node || typeof node !== 'object') {
			return
		}
		for (const [k, v] of Object.entries(node)) {
			if (k.startsWith('x-')) {
				continue
			}
			if (typeof v === 'string') {
				if ((k === 'title' || k === 'description') && v.trim()) {
					out.add(v)
				}
			} else {
				visit(v)
			}
		}
	}
	for (const file of walk(path.join(root, 'lib/Settings'), ['.json'])) {
		let doc
		try {
			doc = readJson(file)
		} catch (e) {
			throw new Error(`${path.relative(root, file)}: ${e.message}`)
		}
		const components = doc && doc.components
		if (!components || typeof components !== 'object') {
			continue
		}
		visit(components.registers)
		visit(components.schemas)
	}
	return out
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

/**
 * The app id, which is the first argument of every t() call and therefore the
 * thing the SRC extractor keys on. `appinfo/info.xml` is the only authority:
 * the fleet is mid-rename and the directory name is routinely the old one.
 *
 * @param {string} root app root
 * @return {string|null} the declared app id
 */
function readAppId(root) {
	const file = path.join(root, 'appinfo/info.xml')
	if (!fs.existsSync(file)) {
		return null
	}
	const m = /<id>\s*([^<\s]+)\s*<\/id>/.exec(fs.readFileSync(file, 'utf8'))
	return m ? m[1] : null
}

/**
 * Strings this app has declared it will not translate, one per entry.
 *
 * The migration path off a vendored copy needs somewhere to put the findings
 * an app is not fixing today, or the shared checker is unadoptable. A reason
 * is required, so the file cannot become a silent suppression list.
 *
 * @param {string} root app root
 * @return {Set<string>} strings excluded by the app, with a stated reason
 */
function loadIgnored(root) {
	const out = new Set()
	const file = path.join(root, 'l10n/.l10n-source-ignore.json')
	if (!fs.existsSync(file)) {
		return out
	}
	const raw = readJson(file)
	for (const [key, reason] of Object.entries(raw || {})) {
		if (typeof reason === 'string' && reason.trim()) {
			out.add(key)
		}
	}
	return out
}

function main(argv) {
	const args = argv.slice(2)
	const warnOnly = args.includes('--warn-only')
	const asJson = args.includes('--json')
	const sourceArg = args.find((a) => a.startsWith('--source='))
	const enabled = new Set(
		sourceArg ? sourceArg.slice('--source='.length).split(',').map((s) => s.trim().toUpperCase()) : ALL_SOURCES,
	)
	const root = path.resolve(args.find((a) => !a.startsWith('--')) || process.cwd())

	const appId = readAppId(root)
	if (!appId) {
		process.stderr.write(`no <id> in ${path.join(root, 'appinfo/info.xml')} — cannot tell which t() calls belong to this app\n`)
		return 9
	}

	const enPath = path.join(root, 'l10n/en.json')
	const nlPath = path.join(root, 'l10n/nl.json')
	const en = loadCatalogue(enPath)
	const nl = loadCatalogue(nlPath)

	/** @type {Map<string, Set<string>>} string to the origins that produced it */
	const origins = new Map()
	// Strings that prove a catalogue key is live without themselves demanding
	// one. See the note at the top about PHP array values.
	const suppressOnly = new Set()
	const record = (source, set) => {
		if (!enabled.has(source)) {
			return
		}
		for (const s of set) {
			if (!origins.has(s)) {
				origins.set(s, new Set())
			}
			origins.get(s).add(source)
		}
	}

	try {
		record('SRC', collectSrcStrings(root, appId))
		record('PHP', collectPhpTranslated(root))
		record('MANIFEST', collectManifestStrings(root))
		record('SCHEMA', collectSchemaStrings(root))
		if (enabled.has('PHP')) {
			for (const s of collectPhpDeclared(root)) {
				suppressOnly.add(s)
			}
		}
	} catch (e) {
		process.stderr.write(`could not read a source: ${e.message}\n`)
		return 9
	}

	const ignored = loadIgnored(root)
	for (const key of ignored) {
		origins.delete(key)
	}

	const total = origins.size
	if (total === 0 || en.size === 0) {
		process.stdout.write(`checked ${total} source string(s) against ${en.size} English key(s)\n`)
		return 4
	}

	const missingEn = []
	const missingNl = []
	for (const [key, from] of origins) {
		const label = [...from].sort().join('+')
		if (!en.has(key)) {
			missingEn.push({ key, source: label })
		}
		if (nl.size > 0 && !nl.has(key)) {
			missingNl.push({ key, source: label })
		}
	}
	const unused = [...en.keys()]
		.filter((k) => !origins.has(k) && !suppressOnly.has(k) && !ignored.has(k))
		.sort()

	missingEn.sort((a, b) => a.key.localeCompare(b.key))
	missingNl.sort((a, b) => a.key.localeCompare(b.key))

	if (asJson) {
		process.stdout.write(JSON.stringify({ appId, checked: total, missingEn, missingNl, unused }, null, 2) + '\n')
	} else {
		const byOrigin = (rows) => {
			const counts = {}
			for (const r of rows) {
				counts[r.source] = (counts[r.source] || 0) + 1
			}
			return Object.entries(counts).map(([k, v]) => `${k} ${v}`).join(', ') || 'none'
		}
		for (const row of missingEn) {
			process.stdout.write(`FAIL [${row.source}] no key in l10n/en.json: ${JSON.stringify(row.key)}\n`)
		}
		for (const row of missingNl) {
			process.stdout.write(`WARN [${row.source}] no key in l10n/nl.json: ${JSON.stringify(row.key)}\n`)
		}
		for (const key of unused) {
			process.stdout.write(`WARN [CATALOGUE] no source produces this key: ${JSON.stringify(key)}\n`)
		}
		process.stdout.write(`missing from en.json: ${missingEn.length} (${byOrigin(missingEn)})\n`)
		process.stdout.write(`missing from nl.json: ${missingNl.length} (${byOrigin(missingNl)})\n`)
		process.stdout.write(`unused in en.json: ${unused.length}\n`)
	}

	// The terminal marker. The gate runner requires it before it will read any
	// count off this log: a checker that crashed halfway prints findings too,
	// and a crash is not a finding.
	process.stdout.write(`checked ${total} source string(s) against ${en.size} English key(s)\n`)

	if (warnOnly) {
		return 0
	}
	return missingEn.length + missingNl.length + unused.length > 0 ? 1 : 0
}

if (require.main === module) {
	process.exit(main(process.argv))
}

module.exports = {
	collectSrcStrings,
	collectPhpTranslated,
	collectPhpDeclared,
	collectManifestStrings,
	collectSchemaStrings,
	loadCatalogue,
	main,
}
