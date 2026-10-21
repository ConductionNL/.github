#!/usr/bin/env node
// SPDX-License-Identifier: EUPL-1.2
//
// vendored_schema_freshness.js: is scripts/schemas/app-manifest-v2.schema.json
// behind the schema @conduction/nextcloud-vue ships?
//
// Gates 22 and 53 validate against the vendored copy. When it falls behind,
// a manifest that uses a key the library already accepts is rejected by the
// gate while the app's own `npm run check:manifest` passes. The weekly sync
// workflow opens a pull request for that, but an unmerged sync PR left the
// copy 42 schema versions behind (2.96.0 against 2.138.0) and the gate's
// findings never said why. This helper names the drift.
//
// Two sources to compare against:
//   - offline: the schema in an app's installed node_modules (used by
//     check_manifest.js, so a gate log says when the app's library is newer);
//   - online: the latest published package on npm (the CLI default).
//
// CLI:
//   node vendored_schema_freshness.js                 compare against npm latest
//   node vendored_schema_freshness.js --published F   compare against schema file F
//   node vendored_schema_freshness.js --app-dir D     compare against D/node_modules
//   --strict   exit 1 when the vendored copy is behind (default: warn, exit 0)
//
// Exit: 0 current (or behind without --strict), 1 behind with --strict,
//       2 the comparison could not be made.

'use strict'

const fs = require('fs')
const os = require('os')
const path = require('path')
const { execFileSync } = require('child_process')

const PACKAGE = '@conduction/nextcloud-vue'
const SCHEMA_IN_PACKAGE = path.join('src', 'schemas', 'app-manifest-v2.schema.json')
const VENDORED_PATH = path.resolve(__dirname, '..', 'schemas', 'app-manifest-v2.schema.json')

// Numeric x.y.z comparison; a pre-release suffix is ignored. Returns <0, 0, >0.
function compareVersions(a, b) {
	const pa = String(a).split('-')[0].split('.').map((n) => parseInt(n, 10) || 0)
	const pb = String(b).split('-')[0].split('.').map((n) => parseInt(n, 10) || 0)
	for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
		const d = (pa[i] || 0) - (pb[i] || 0)
		if (d !== 0) return d
	}
	return 0
}

function schemaVersion(file) {
	try {
		const v = JSON.parse(fs.readFileSync(file, 'utf8')).version
		return typeof v === 'string' && v !== '' ? v : null
	} catch (_) {
		return null
	}
}

// The schema shipped by the library installed under appDir, or null.
function installedSchemaPath(appDir) {
	const p = path.join(appDir, 'node_modules', '@conduction', 'nextcloud-vue', SCHEMA_IN_PACKAGE)
	return fs.existsSync(p) ? p : null
}

// One line naming the drift when `otherVersion` is newer than the vendored
// copy, otherwise null.
function behindNote(vendored, other, source) {
	if (!vendored || !other || compareVersions(other, vendored) <= 0) return null
	return `VENDORED SCHEMA BEHIND: gates 22/53 validate against vendored app-manifest-v2 ${vendored}, `
		+ `but ${source} ships ${other}. A key added since ${vendored} is rejected here while the library accepts it; `
		+ 're-vendor hydra-gates/scripts/schemas/app-manifest-v2.schema.json (workflow hydra-gates-schema-sync).'
}

// Downloads the latest published package into a temp dir and returns
// { lib, file }. Throws when npm cannot answer.
function fetchPublished() {
	const lib = execFileSync('npm', ['view', PACKAGE, 'version'], { encoding: 'utf8', timeout: 60000 }).trim()
	if (!lib) throw new Error(`npm view ${PACKAGE} version returned nothing`)
	const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-schema-'))
	const tgz = execFileSync('npm', ['pack', `${PACKAGE}@${lib}`, '--silent'], { cwd: dir, encoding: 'utf8', timeout: 120000 }).trim().split('\n').pop()
	execFileSync('tar', ['xzf', tgz, 'package/' + SCHEMA_IN_PACKAGE.split(path.sep).join('/')], { cwd: dir, timeout: 60000 })
	return { lib, file: path.join(dir, 'package', SCHEMA_IN_PACKAGE) }
}

function main(argv) {
	let published = null
	let appDir = null
	let strict = false
	for (let i = 0; i < argv.length; i++) {
		if (argv[i] === '--published') published = argv[++i]
		else if (argv[i] === '--app-dir') appDir = argv[++i]
		else if (argv[i] === '--strict') strict = true
		else {
			console.error(`unknown argument: ${argv[i]}`)
			return 2
		}
	}

	const vendored = schemaVersion(VENDORED_PATH)
	if (!vendored) {
		console.error(`[schema-freshness] cannot read a version from ${VENDORED_PATH}`)
		return 2
	}

	let source
	if (published) {
		source = published
	} else if (appDir) {
		published = installedSchemaPath(appDir)
		if (!published) {
			console.error(`[schema-freshness] no ${PACKAGE} installed under ${appDir}`)
			return 2
		}
		source = `${PACKAGE} installed under ${appDir}`
	} else {
		try {
			const got = fetchPublished()
			published = got.file
			source = `${PACKAGE} ${got.lib} (npm latest)`
		} catch (e) {
			console.error(`[schema-freshness] could not fetch ${PACKAGE} from npm: ${e.message.split('\n')[0]}`)
			return 2
		}
	}

	const other = schemaVersion(published)
	if (!other) {
		console.error(`[schema-freshness] cannot read a version from ${published}`)
		return 2
	}

	const note = behindNote(vendored, other, source)
	if (note) {
		console.log(`${strict ? 'FAIL' : 'WARN'} ${note}`)
		return strict ? 1 : 0
	}
	console.log(`OK vendored app-manifest-v2 ${vendored} is level with or ahead of ${source} (${other})`)
	return 0
}

if (require.main === module) {
	process.exit(main(process.argv.slice(2)))
}

module.exports = { compareVersions, schemaVersion, installedSchemaPath, behindNote, VENDORED_PATH }
