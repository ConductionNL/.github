#!/usr/bin/env node
// SPDX-License-Identifier: EUPL-1.2
//
// test_vendored_schema_freshness.js: the drift between the vendored manifest
// schema and the one @conduction/nextcloud-vue ships is named, never silent.
// Offline: every comparison runs against schema files written here.
//
// Run: node scripts/lib/test_vendored_schema_freshness.js

'use strict'

const fs = require('fs')
const os = require('os')
const path = require('path')
const { spawnSync } = require('child_process')
const f = require('./vendored_schema_freshness.js')

let fails = 0
function check(name, cond) {
	console.log(`  ${cond ? 'PASS' : 'FAIL'}: ${name}`)
	if (!cond) fails++
}

const work = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-fresh-'))
const vendored = f.schemaVersion(f.VENDORED_PATH)
function schemaFile(name, version) {
	const p = path.join(work, name)
	fs.writeFileSync(p, JSON.stringify({ version }))
	return p
}
function run(args, cwd) {
	return spawnSync(process.execPath, [path.join(__dirname, 'vendored_schema_freshness.js'), ...args], { encoding: 'utf8', cwd })
}

try {
	console.log('== compareVersions ==')
	check('2.138.0 > 2.96.0 (numeric, not lexical)', f.compareVersions('2.138.0', '2.96.0') > 0)
	check('2.96.0 < 2.138.0', f.compareVersions('2.96.0', '2.138.0') < 0)
	check('equal versions compare 0', f.compareVersions('2.96.0', '2.96.0') === 0)
	check('pre-release suffix ignored', f.compareVersions('3.0.0-beta.4', '3.0.0') === 0)

	console.log('== behindNote ==')
	check('newer source names the drift', /VENDORED SCHEMA BEHIND/.test(f.behindNote('2.96.0', '2.138.0', 'x') || ''))
	check('same version is silent', f.behindNote('2.96.0', '2.96.0', 'x') === null)
	check('older source is silent', f.behindNote('2.138.0', '2.96.0', 'x') === null)
	check('missing version is silent, not a false alarm', f.behindNote('2.96.0', null, 'x') === null)

	console.log('== the vendored copy declares a version ==')
	check(`vendored schema has a version (${vendored})`, typeof vendored === 'string')

	console.log('== CLI ==')
	const newer = schemaFile('newer.json', '999.0.0')
	let r = run(['--published', newer])
	check('behind: WARN and exit 0 by default', r.status === 0 && /^WARN VENDORED SCHEMA BEHIND/.test(r.stdout))
	r = run(['--published', newer, '--strict'])
	check('behind with --strict: FAIL and exit 1', r.status === 1 && /^FAIL VENDORED SCHEMA BEHIND/.test(r.stdout))
	r = run(['--published', schemaFile('same.json', vendored), '--strict'])
	check('level: OK and exit 0 under --strict', r.status === 0 && /^OK /.test(r.stdout))
	r = run(['--published', schemaFile('nover.json', '')])
	check('unreadable version: exit 2, not a pass', r.status === 2)

	const app = path.join(work, 'app')
	const lib = path.join(app, 'node_modules', '@conduction', 'nextcloud-vue', 'src', 'schemas')
	fs.mkdirSync(lib, { recursive: true })
	fs.writeFileSync(path.join(lib, 'app-manifest-v2.schema.json'), JSON.stringify({ version: '999.0.0' }))
	r = run(['--app-dir', app])
	check('--app-dir reads the installed library schema', r.status === 0 && /installed under/.test(r.stdout))
	r = run(['--app-dir', path.join(work, 'no-such-app')])
	check('--app-dir without the library: exit 2', r.status === 2)

	console.log('== check_manifest.js names the drift in a gate log ==')
	fs.mkdirSync(path.join(app, 'src'), { recursive: true })
	fs.writeFileSync(path.join(app, 'src', 'manifest.json'), '{}')
	r = spawnSync(process.execPath, [path.join(__dirname, 'check_manifest.js'), 'src/manifest.json'], { encoding: 'utf8', cwd: app })
	check('installed library newer than vendored copy: note on stderr', /VENDORED SCHEMA BEHIND/.test(r.stderr))
	fs.writeFileSync(path.join(lib, 'app-manifest-v2.schema.json'), JSON.stringify({ version: vendored }))
	r = spawnSync(process.execPath, [path.join(__dirname, 'check_manifest.js'), 'src/manifest.json'], { encoding: 'utf8', cwd: app })
	check('installed library level with vendored copy: no note', !/VENDORED SCHEMA BEHIND/.test(r.stderr))
} finally {
	fs.rmSync(work, { recursive: true, force: true })
}

console.log(fails === 0 ? '\n== all passed ==' : `\n== ${fails} failed ==`)
process.exit(fails === 0 ? 0 : 1)
