#!/usr/bin/env node
// SPDX-License-Identifier: EUPL-1.2
//
// test_check_connections_declaration.js: gate-116 (connections-declaration)
// checker self-test.
//
// Every app here is built in a tmpdir, so the fixtures cannot go missing.
//
// THE PLANTED ARMS CARRY ONE DEFECT EACH, and each is asserted by the rule it
// breaks, so a checker that notices only one kind of defect cannot pass the
// others for free. THE CLEAN ARM keeps the near misses a widened checker would
// turn red: a settingsUrl with no anchor, a connection with no settingsUrl, an
// anchor defined only in templates/, and a copy of a link in src/ next to the
// real anchor. The anchor arms keep the two near misses a narrowed checker
// would miss: a link to `#section-stuf` in a manifest is not a definition, and
// `section-zgw-extra` does not define `section-zgw`.
//
// The tooling arms copy the checker out of the package, so neither the gate
// package's own node_modules nor a vendored schema can rescue them.
//
// Run: node scripts/lib/test_check_connections_declaration.js   (exit 0 = pass)

'use strict'

const { spawnSync } = require('child_process')
const fs = require('fs')
const os = require('os')
const path = require('path')

const LIB = __dirname
const CHECKER = path.join(LIB, 'check_connections_declaration.js')
const SCHEMA = path.resolve(LIB, '..', 'schemas', 'connections.schema.json')

for (const p of [CHECKER, SCHEMA]) {
	if (!fs.existsSync(p)) {
		console.log(`FAIL: ${p} is missing; this suite cannot assert anything`)
		process.exit(1)
	}
}

let fails = 0
let asserts = 0
/**
 * Record one assertion.
 *
 * @param {boolean} cond The condition.
 * @param {string} label What it proves.
 */
function assert(cond, label) {
	asserts++
	if (cond) {
		console.log(`PASS: ${label}`)
	} else {
		console.log(`FAIL: ${label}`)
		fails++
	}
}

const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'gate116-test-'))
process.on('exit', () => fs.rmSync(TMP, { recursive: true, force: true }))

/**
 * Write a file, creating its directory.
 *
 * @param {string} file Absolute path.
 * @param {string} body Contents.
 */
function write(file, body) {
	fs.mkdirSync(path.dirname(file), { recursive: true })
	fs.writeFileSync(file, body)
}

const CLEAN = {
	app: 'fixture',
	connections: [
		{ key: 'zgw', title: 'ZGW APIs', order: 10, settingsUrl: '/settings/admin/fixture#section-zgw', requiredConfig: ['register'] },
		{ key: 'stuf', title: 'StUF-ZKN', order: 20, settingsUrl: '/settings/admin/fixture#section-stuf' },
		{ key: 'plain-link', title: 'No anchor', settingsUrl: '/settings/admin/fixture' },
		{ key: 'kvk', title: 'KvK', available: false, unavailableMessage: 'Not wired yet.', sourceTemplate: 'kvk' },
		{ key: 'berichtenbox', title: 'Berichtenbox', adapter: { configKey: 'berichtenbox_adapter', simulatedMessage: 'A mock answers.' } },
	],
}

/**
 * Build an app directory.
 *
 * @param {string} name Directory name under the tmpdir.
 * @param {object} opts What to put in it.
 * @return {string} The app root.
 */
function makeApp(name, { declaration = CLEAN, raw = null, id = 'fixture', srcAnchors = ['section-zgw'], templateAnchors = ['section-stuf'], srcLinks = [] } = {}) {
	const root = path.join(TMP, name)
	write(path.join(root, 'appinfo', 'info.xml'), `<?xml version="1.0"?>\n<info>\n    <!-- <id>commented-out</id> -->\n    <id>${id}</id>\n    <name>Fixture</name>\n</info>\n`)
	if (raw !== null || declaration !== null) {
		write(path.join(root, 'lib', 'Settings', 'connections.json'), raw !== null ? raw : JSON.stringify(declaration, null, 2))
	}
	write(path.join(root, 'src', 'views', 'settings', 'AdminSettings.vue'),
		`<template>\n\t<div>\n${srcAnchors.map((a) => `\t\t<NcSettingsSection id="${a}" name="x" />`).join('\n')}\n\t</div>\n</template>\n`)
	write(path.join(root, 'src', 'manifest.json'), JSON.stringify({ links: srcLinks }))
	write(path.join(root, 'templates', 'admin.php'), templateAnchors.map((a) => `<div id="${a}"></div>`).join('\n') + '\n')
	return root
}

/**
 * Run the checker.
 *
 * @param {string} root App root.
 * @param {object} opts Extra options.
 * @return {{status: number, stdout: string}} The result.
 */
function run(root, { onlyChanged = null, checker = CHECKER, env = process.env, cwd = root } = {}) {
	const args = [checker, root]
	if (onlyChanged !== null) {
		args.push('--only-changed')
	}
	const r = spawnSync(process.execPath, args, { encoding: 'utf8', input: onlyChanged === null ? '' : onlyChanged.join('\n') + '\n', env, cwd })
	return { status: r.status === null ? -1 : r.status, stdout: (r.stdout || '') + (r.stderr || '') }
}

const findings = (out) => out.split('\n').filter((l) => l.startsWith('FAIL '))

// --- the Ajv precondition -----------------------------------------------------
{
	const probe = run(makeApp('ajv-probe'))
	if (probe.status === 3) {
		console.log('FAIL: Ajv is not resolvable, so no schema arm below can assert anything. Install ajv (CI: npm install ajv at the repo root) or set NODE_PATH.')
		process.exit(1)
	}
}

// --- ARM 1: a clean declaration, with the near misses ---------------------------
{
	const r = run(makeApp('clean', { srcLinks: ['/settings/admin/fixture#section-zgw'] }))
	assert(r.status === 0, `clean: exit 0 (got ${r.status}: ${r.stdout.trim()})`)
	assert(findings(r.stdout).length === 0, 'clean: no FAIL line')
	assert(/^\[connections-declaration\] checked 1 declaration file\(s\), 0 finding\(s\)$/m.test(r.stdout), 'clean: the terminal checked line is printed')
}

// --- ARM 2: rule 1, the schema --------------------------------------------------
{
	const bad = JSON.parse(JSON.stringify(CLEAN))
	bad.connections[0].setingsUrl = bad.connections[0].settingsUrl
	delete bad.connections[0].settingsUrl
	bad.connections[1].key = 'StUF_ZKN'
	const r = run(makeApp('schema', { declaration: bad }))
	const f = findings(r.stdout)
	assert(r.status === 1, 'schema: exit 1')
	assert(f.some((l) => l.includes('schema: /connections/0 must NOT have additional properties (setingsUrl)')), 'schema: a misspelled property is named')
	assert(f.some((l) => l.includes('schema: /connections/1/key must match pattern')), 'schema: a key outside the pattern is named')
	assert(f.length === 2, `schema: exactly the two planted findings (got ${f.length})`)
}
{
	const r = run(makeApp('schema-missing-connections', { declaration: { app: 'fixture' } }))
	assert(r.status === 1 && findings(r.stdout).some((l) => l.includes("must have required property 'connections'")), 'schema: a missing connections array is a finding')
}

// --- ARM 3: rule 2, the app id --------------------------------------------------
{
	const r = run(makeApp('app-id', { id: 'otherapp' }))
	const f = findings(r.stdout)
	assert(r.status === 1, 'app id: exit 1')
	assert(f.length === 1 && f[0].includes('app is "fixture" and appinfo/info.xml says "otherapp"'), 'app id: the mismatch names both ids, and the commented-out <id> is ignored')
}

// --- ARM 4: rule 3, unique keys -------------------------------------------------
{
	const dup = JSON.parse(JSON.stringify(CLEAN))
	dup.connections.push({ key: 'zgw', title: 'ZGW again' })
	const r = run(makeApp('dup', { declaration: dup }))
	const f = findings(r.stdout)
	assert(r.status === 1, 'duplicate key: exit 1')
	assert(f.length === 1 && f[0].includes('key "zgw" is used by connections[0] and connections[5]'), 'duplicate key: names the key and both positions')
}

// --- ARM 5: rule 4, anchors -----------------------------------------------------
{
	// The stuf anchor is only LINKED from src/, never defined. A link is not a definition.
	const r = run(makeApp('anchor-link-only', { templateAnchors: [], srcLinks: ['/settings/admin/fixture#section-stuf'] }))
	const f = findings(r.stdout)
	assert(r.status === 1, 'anchor: exit 1 when the anchor is only linked')
	assert(f.length === 1 && f[0].includes('connections[1].settingsUrl links to #section-stuf'), 'anchor: a copy of the link in src/ does not count as the anchor')
}
{
	const r = run(makeApp('anchor-prefix', { srcAnchors: ['section-zgw-extra'] }))
	const f = findings(r.stdout)
	assert(r.status === 1 && f.length === 1 && f[0].includes('#section-zgw,'), 'anchor: section-zgw-extra does not define section-zgw')
}
{
	// A vendored copy under node_modules must not supply the anchor.
	const root = makeApp('anchor-vendored', { srcAnchors: [] })
	write(path.join(root, 'src', 'node_modules', 'pkg', 'index.js'), 'const id = "section-zgw"\n')
	const r = run(root)
	assert(r.status === 1 && findings(r.stdout).some((l) => l.includes('#section-zgw,')), 'anchor: node_modules under src/ does not supply the anchor')
}

// --- ARM 6: JSON that does not parse -------------------------------------------
{
	const r = run(makeApp('not-json', { raw: '{ "app": "fixture", ' }))
	assert(r.status === 1 && findings(r.stdout).length === 1 && r.stdout.includes('is not valid JSON'), 'invalid JSON: one finding, not a crash')
}

// --- ARM 7: scope ---------------------------------------------------------------
{
	const r = run(makeApp('no-file', { declaration: null }))
	assert(r.status === 4 && r.stdout.startsWith('NA: '), 'scope: no declaration is NOT APPLICABLE (exit 4)')
}
{
	const root = makeApp('scope', { id: 'otherapp' })
	const unrelated = run(root, { onlyChanged: ['README.md', 'lib/Service/Thing.php'] })
	assert(unrelated.status === 4, `scope: a change touching no rule's side is not judged, even over a defective file (got ${unrelated.status})`)
	assert(run(root, { onlyChanged: ['lib/Settings/connections.json'] }).status === 1, 'scope: a change to the declaration is judged')
	assert(run(root, { onlyChanged: ['appinfo/info.xml'] }).status === 1, 'scope: a change to info.xml is judged (rule 2)')
	assert(run(root, { onlyChanged: ['src/views/settings/AdminSettings.vue'] }).status === 1, 'scope: a change under src/ is judged (rule 4)')
	assert(run(root, { onlyChanged: ['templates/admin.php'] }).status === 1, 'scope: a change under templates/ is judged (rule 4)')
}

// --- ARM 8: tooling fails closed ------------------------------------------------
{
	// A copy of the package layout with no node_modules anywhere above it.
	const pkg = path.join(TMP, 'pkg-copy')
	write(path.join(pkg, 'scripts', 'lib', 'check_connections_declaration.js'), fs.readFileSync(CHECKER, 'utf8'))
	write(path.join(pkg, 'scripts', 'schemas', 'connections.schema.json'), fs.readFileSync(SCHEMA, 'utf8'))
	const copied = path.join(pkg, 'scripts', 'lib', 'check_connections_declaration.js')
	const env = { ...process.env, NODE_PATH: '' }
	const root = makeApp('tooling')
	const noAjv = run(root, { checker: copied, env, cwd: TMP })
	if (fs.existsSync(path.join(os.tmpdir(), 'node_modules')) || fs.existsSync('/node_modules')) {
		console.log('NOTE: a node_modules sits above the tmpdir, so the no-Ajv arm cannot be isolated here; skipped')
	} else {
		assert(noAjv.status === 3 && noAjv.stdout.includes('SCHEMA VALIDATION DID NOT HAPPEN'), `tooling: no Ajv is exit 3 and says validation did not happen (got ${noAjv.status})`)
		assert(!/checked 1 declaration/.test(noAjv.stdout), 'tooling: no Ajv prints no checked line, so the runner cannot read it as a verdict')
	}

	const noComment = JSON.parse(fs.readFileSync(SCHEMA, 'utf8'))
	delete noComment.$comment
	write(path.join(pkg, 'scripts', 'schemas', 'connections.schema.json'), JSON.stringify(noComment))
	const unsourced = run(root, { checker: copied })
	assert(unsourced.status === 2 && unsourced.stdout.includes('does not record source commit'), 'tooling: a vendored schema without its source commit is exit 2')

	fs.rmSync(path.join(pkg, 'scripts', 'schemas', 'connections.schema.json'))
	assert(run(root, { checker: copied }).status === 2, 'tooling: a missing vendored schema is exit 2')
}

// --- the vendored schema records where it came from ----------------------------
{
	const { SOURCE_COMMIT } = require(CHECKER)
	const schema = JSON.parse(fs.readFileSync(SCHEMA, 'utf8'))
	assert(/^[0-9a-f]{40}$/.test(SOURCE_COMMIT), 'the checker pins a full integriq commit sha')
	assert(typeof schema.$comment === 'string' && schema.$comment.includes(SOURCE_COMMIT) && schema.$comment.includes('ConductionNL/integriq'), 'the vendored schema names integriq and the same commit')
}

console.log('')
console.log(`assertions: ${asserts}, failures: ${fails}`)
if (asserts < 28) {
	console.log(`FAIL: only ${asserts} assertions ran; this suite declares 28 or more. A short run is not a green run.`)
	process.exit(1)
}
process.exit(fails > 0 ? 1 : 0)
