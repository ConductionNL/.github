#!/usr/bin/env node
// SPDX-License-Identifier: EUPL-1.2
//
// check_connections_declaration.js: the checker behind gate-116
// (connections-declaration).
//
// An app lists its outside connections in lib/Settings/connections.json
// (hydra openspec/changes/connection-registry, design D2). Integriq reads the
// file at runtime and turns each entry into one row on the connections page.
// Integriq refuses a file it cannot trust, and it refuses it quietly: the app
// simply has no rows. This checker finds the same problems at review time.
//
// FOUR RULES, one file:
//   1. the file validates against scripts/schemas/connections.schema.json, a
//      vendored copy of integriq's own schema (its source commit is in the
//      schema's $comment and in SOURCE_COMMIT below);
//   2. `app` equals <id> in appinfo/info.xml;
//   3. every connection `key` is unique in the file;
//   4. every `settingsUrl` carrying a `#section-<x>` anchor names an anchor
//      that exists under src/ or templates/. A link to a section that is not
//      rendered anywhere opens the settings page at the top.
//
// SCOPE. With --only-changed the changed paths arrive on stdin, one per line,
// and the file is judged only when the change touched one side of a rule:
// the declaration itself, appinfo/info.xml (rule 2), or anything under src/
// or templates/ (rule 4, an anchor can disappear without the declaration
// changing). Without the flag the file is judged whenever it exists.
//
// OUTPUT, one line each:
//   FAIL <path>: <what is wrong>
//   NA: <why nothing was judged>
//   [connections-declaration] checked <n> declaration file(s), <m> finding(s)
// The terminal `checked` line is printed only when the checker finished, so
// the runner can tell a crash from a verdict.
//
// EXIT: 0 clean, 1 findings, 2 the vendored schema is unreadable,
//       3 Ajv is not resolvable so schema validation did not happen,
//       4 nothing in scope.

'use strict'

const fs = require('fs')
const path = require('path')
const { spawnSync } = require('child_process')

const DECLARATION = 'lib/Settings/connections.json'
const SCHEMA_PATH = path.resolve(__dirname, '..', 'schemas', 'connections.schema.json')
const SOURCE_COMMIT = '605a87792a062ebbd38e05e8f598597fcf8a94c4'
const ANCHOR_DIRS = ['src', 'templates']
const SKIP_DIRS = new Set(['node_modules', 'vendor', 'dist', 'build', 'custom_apps', '.git'])
const TEXT_FILE = /\.(vue|js|mjs|cjs|ts|tsx|jsx|php|html|json|md|twig)$/

/**
 * Parse the command line.
 *
 * @param {string[]} argv Process arguments after the script name.
 * @return {{root: string, onlyChanged: boolean}} The options.
 */
function parseArgs(argv) {
	let root = '.'
	let onlyChanged = false
	for (const arg of argv) {
		if (arg === '--only-changed') {
			onlyChanged = true
		} else {
			root = arg
		}
	}
	return { root: path.resolve(root), onlyChanged }
}

/**
 * Whether a changed path can change the verdict on the declaration.
 *
 * @param {string} file A repo-relative path.
 * @return {boolean} True when the path is one side of a rule.
 */
function touchesARule(file) {
	return file === DECLARATION
		|| file === 'appinfo/info.xml'
		|| ANCHOR_DIRS.some((dir) => file.startsWith(dir + '/'))
}

/**
 * Node module search paths, anchored on the app under judgement first and the
 * gate package last, the way check_manifest.js resolves Ajv (.github#271).
 *
 * @param {string} root The app root.
 * @return {string[]} node_modules directories to try.
 */
function ajvSearchPaths(root) {
	const out = []
	const seen = new Set()
	for (const start of [root, process.cwd(), __dirname]) {
		let dir = start
		for (;;) {
			const nm = path.join(dir, 'node_modules')
			if (!seen.has(nm)) {
				seen.add(nm)
				out.push(nm)
			}
			const parent = path.dirname(dir)
			if (parent === dir) {
				break
			}
			dir = parent
		}
	}
	return out
}

/**
 * Load the draft 2020-12 build of Ajv.
 *
 * @param {string} root The app root.
 * @return {Function|null} The Ajv constructor, or null when not resolvable.
 */
function loadAjv(root) {
	const paths = ajvSearchPaths(root)
	for (const attempt of [
		() => require(require.resolve('ajv/dist/2020', { paths })),
		() => require('ajv/dist/2020'),
	]) {
		try {
			const mod = attempt()
			return mod.default || mod
		} catch (_) {
			// try the next resolution
		}
	}
	return null
}

/**
 * List the files under the anchor directories. Tracked files when the root is
 * a git work tree, so a nested vendored copy cannot supply an anchor.
 *
 * @param {string} root The app root.
 * @return {string[]} Repo-relative paths.
 */
function anchorFiles(root) {
	const git = spawnSync('git', ['-c', 'safe.directory=*', 'ls-files', '-z', '--', ...ANCHOR_DIRS], { cwd: root, encoding: 'utf8' })
	if (git.status === 0) {
		const tracked = git.stdout.split('\0').filter((f) => f && TEXT_FILE.test(f) && !f.split('/').some((p) => SKIP_DIRS.has(p)))
		// An empty answer from inside a work tree can mean the app sits
		// untracked in a parent repo. Walking the disk then is the safe side.
		if (tracked.length > 0) {
			return tracked
		}
	}
	const out = []
	const walk = (rel) => {
		let entries
		try {
			entries = fs.readdirSync(path.join(root, rel), { withFileTypes: true })
		} catch (_) {
			return
		}
		for (const entry of entries) {
			const child = rel + '/' + entry.name
			if (entry.isDirectory()) {
				if (!SKIP_DIRS.has(entry.name)) {
					walk(child)
				}
			} else if (TEXT_FILE.test(entry.name)) {
				out.push(child)
			}
		}
	}
	ANCHOR_DIRS.forEach(walk)
	return out
}

/**
 * Whether `section-<name>` appears as an anchor, not as a link to one. A match
 * preceded by `#` is a link (a copy of the settingsUrl in a manifest, say), so
 * it proves nothing about the section being rendered.
 *
 * @param {string} text File contents.
 * @param {string} anchor The anchor id, e.g. `section-zgw`.
 * @return {boolean} True when the anchor is defined in the text.
 */
function definesAnchor(text, anchor) {
	const escaped = anchor.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
	return new RegExp(`(^|[^#A-Za-z0-9_-])${escaped}(?![A-Za-z0-9_-])`).test(text)
}

/**
 * Read the app id from appinfo/info.xml.
 *
 * @param {string} root The app root.
 * @return {string|null} The id, or null when the file or element is missing.
 */
function appId(root) {
	let xml
	try {
		xml = fs.readFileSync(path.join(root, 'appinfo', 'info.xml'), 'utf8')
	} catch (_) {
		return null
	}
	const match = xml.replace(/<!--[\s\S]*?-->/g, '').match(/<id>\s*([^<\s]+)\s*<\/id>/)
	return match ? match[1] : null
}

/**
 * Judge one declaration.
 *
 * @param {string} root The app root.
 * @param {object} validate A compiled Ajv validator.
 * @return {string[]} Findings, each a sentence.
 */
function judge(root, validate) {
	const findings = []
	let doc
	try {
		doc = JSON.parse(fs.readFileSync(path.join(root, DECLARATION), 'utf8'))
	} catch (e) {
		return [`the file is not valid JSON (${e.message}), so integriq cannot read any connection from it.`]
	}

	// Rule 1: the schema.
	if (!validate(doc)) {
		for (const err of validate.errors) {
			const where = err.instancePath || '/'
			const extra = err.params && err.params.additionalProperty ? ` (${err.params.additionalProperty})` : ''
			findings.push(`schema: ${where} ${err.message}${extra}.`)
		}
	}

	// Rule 2: the app id.
	const id = appId(root)
	if (id === null) {
		findings.push('appinfo/info.xml has no <id>, so the declared app cannot be compared with the app that ships it.')
	} else if (typeof doc === 'object' && doc !== null && doc.app !== id) {
		findings.push(`app is "${doc.app}" and appinfo/info.xml says "${id}". Integriq refuses a file whose app differs from the app it was read from.`)
	}

	const connections = doc && Array.isArray(doc.connections) ? doc.connections : []

	// Rule 3: unique keys.
	const firstIndex = new Map()
	connections.forEach((conn, i) => {
		if (!conn || typeof conn.key !== 'string') {
			return
		}
		if (firstIndex.has(conn.key)) {
			findings.push(`key "${conn.key}" is used by connections[${firstIndex.get(conn.key)}] and connections[${i}]. A row is keyed by app and key, so the second one overwrites the first.`)
		} else {
			firstIndex.set(conn.key, i)
		}
	})

	// Rule 4: anchors exist.
	const wanted = []
	connections.forEach((conn, i) => {
		if (!conn || typeof conn.settingsUrl !== 'string') {
			return
		}
		const hash = conn.settingsUrl.indexOf('#')
		if (hash === -1) {
			return
		}
		const fragment = conn.settingsUrl.slice(hash + 1)
		if (/^section-[A-Za-z0-9_-]+$/.test(fragment)) {
			wanted.push({ i, anchor: fragment })
		}
	})
	if (wanted.length > 0) {
		const texts = anchorFiles(root).map((rel) => {
			try {
				return fs.readFileSync(path.join(root, rel), 'utf8')
			} catch (_) {
				return ''
			}
		})
		for (const { i, anchor } of wanted) {
			if (!texts.some((text) => definesAnchor(text, anchor))) {
				findings.push(`connections[${i}].settingsUrl links to #${anchor}, and no file under src/ or templates/ defines that anchor. The link would open the settings page at the top.`)
			}
		}
	}

	return findings
}

/**
 * Entry point.
 *
 * @return {number} The exit code.
 */
function main() {
	const { root, onlyChanged } = parseArgs(process.argv.slice(2))

	if (!fs.existsSync(path.join(root, DECLARATION))) {
		console.log(`NA: this app ships no ${DECLARATION}, so it declares no connections to check.`)
		return 4
	}
	if (onlyChanged) {
		let stdin = ''
		try {
			stdin = fs.readFileSync(0, 'utf8')
		} catch (_) {
			stdin = ''
		}
		const changed = stdin.split('\n').map((l) => l.trim()).filter(Boolean)
		if (!changed.some(touchesARule)) {
			console.log(`NA: this change touches neither ${DECLARATION}, appinfo/info.xml, src/ nor templates/, so nothing it did can change the declaration's verdict.`)
			return 4
		}
	}

	let schema
	try {
		schema = JSON.parse(fs.readFileSync(SCHEMA_PATH, 'utf8'))
	} catch (e) {
		console.log(`WIRING: the vendored schema at ${SCHEMA_PATH} could not be read (${e.message}). No declaration was judged.`)
		return 2
	}
	if (typeof schema.$comment !== 'string' || !schema.$comment.includes(SOURCE_COMMIT)) {
		console.log(`WIRING: the vendored schema does not record source commit ${SOURCE_COMMIT} in its $comment. Update both together, so the copy can be traced to the integriq commit it came from.`)
		return 2
	}

	const Ajv = loadAjv(root)
	if (!Ajv) {
		console.log('SCHEMA VALIDATION DID NOT HAPPEN: Ajv (ajv/dist/2020) is not resolvable from the app root, the working directory or the gate package. Run `npm ci` in the app, or install ajv next to the gates.')
		console.log(`searched: ${ajvSearchPaths(root).join(', ')}`)
		return 3
	}
	const validate = new Ajv({ allErrors: true, strict: false }).compile(schema)

	const findings = judge(root, validate)
	for (const finding of findings) {
		console.log(`FAIL ${DECLARATION}: ${finding}`)
	}
	console.log(`[connections-declaration] checked 1 declaration file(s), ${findings.length} finding(s)`)
	return findings.length > 0 ? 1 : 0
}

if (require.main === module) {
	process.exitCode = main()
}

module.exports = { definesAnchor, touchesARule, appId, SOURCE_COMMIT }
