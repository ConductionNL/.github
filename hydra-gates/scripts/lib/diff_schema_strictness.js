#!/usr/bin/env node
// SPDX-License-Identifier: EUPL-1.2
//
// diff_schema_strictness.js — name every constraint that got STRICTER between
// two JSON Schema documents.
//
// WHY THIS EXISTS. The manifest schema under scripts/schemas/ is a VENDORED
// copy of the one @conduction/nextcloud-vue publishes, and gates 22 and 53
// judge every app's manifest against it. CI resolves those gates at `@main`,
// so replacing the file reaches all 21 swept apps the minute it merges.
//
// That is safe when the newer schema only ADDS: a manifest valid under the old
// one stays valid, and the bump can only turn red into green. It is not safe
// when the newer schema tightens, because then a manifest that passes today
// starts failing and nothing in the app changed. The two cases look identical
// in a line diff of a three-thousand line schema, which is why this reads the
// structure instead.
//
// What counts as stricter:
//   - a `required` list that gained an entry
//   - an `enum` that lost a member
//   - `additionalProperties` flipped from true to false
//   - a new pattern / minLength / minItems / minimum / maximum / maxLength /
//     maxItems / const where there was none
//   - a declared property that DISAPPEARED from a `properties` block whose
//     sibling `additionalProperties` is false. A removed property is not a
//     relaxation there: the key it used to name becomes an unknown property
//     and the object is refused. This is the case a line diff reads as
//     "fewer rules" and it is the one that reddens a whole fleet.
//
// A key that is ABSENT from the old schema entirely is not reported: it cannot
// constrain a manifest the old schema already rejected as an unknown property.
//
// Usage:  node diff_schema_strictness.js OLD.json NEW.json
//
// Exit codes:
//   0 — the diff is additive: nothing got stricter
//   1 — at least one constraint got stricter (each is printed, one per line)
//   2 — an argument is missing or is not parseable JSON

'use strict'

const fs = require('fs')

const [oldPath, newPath] = process.argv.slice(2)
if (!oldPath || !newPath) {
	console.error('usage: diff_schema_strictness.js OLD.json NEW.json')
	process.exit(2)
}

function load(p) {
	try {
		return JSON.parse(fs.readFileSync(p, 'utf8'))
	} catch (e) {
		console.error(`cannot read ${p}: ${e.message}`)
		process.exit(2)
	}
}

const NEW_CONSTRAINT_KEYS = [
	'pattern', 'minLength', 'maxLength', 'minItems', 'maxItems',
	'minimum', 'maximum', 'const', 'uniqueItems',
]

const findings = []

function walk(a, b, path) {
	if (a === null || b === null) return
	if (typeof a !== 'object' || typeof b !== 'object') return
	if (Array.isArray(a) !== Array.isArray(b)) return

	if (Array.isArray(a)) {
		// Positional. A reordered schema keyword list would read as a change
		// here; that is a false positive worth having over missing a real one.
		for (let i = 0; i < Math.min(a.length, b.length); i++) {
			walk(a[i], b[i], `${path}[${i}]`)
		}
		return
	}

	// A `properties` block under `additionalProperties: false` refuses every
	// key it does not name, so dropping an entry from it is a TIGHTENING even
	// though the file got shorter.
	if (b.additionalProperties === false && a.properties && b.properties
		&& typeof a.properties === 'object' && typeof b.properties === 'object') {
		for (const gone of Object.keys(a.properties)) {
			if (!Object.prototype.hasOwnProperty.call(b.properties, gone)) {
				findings.push(`${path}/properties/${gone}: property removed while additionalProperties is false, so the key is now refused`)
			}
		}
	}

	for (const key of new Set([...Object.keys(a), ...Object.keys(b)])) {
		const here = `${path}/${key}`
		const inA = Object.prototype.hasOwnProperty.call(a, key)
		const inB = Object.prototype.hasOwnProperty.call(b, key)

		if (key === 'required' && Array.isArray(b[key])) {
			const before = Array.isArray(a[key]) ? a[key] : []
			const gained = b[key].filter((v) => !before.includes(v))
			if (gained.length) findings.push(`${here}: newly required ${JSON.stringify(gained)}`)
		}

		if (key === 'enum' && Array.isArray(a[key]) && Array.isArray(b[key])) {
			const after = b[key].map((v) => JSON.stringify(v))
			const lost = a[key].filter((v) => !after.includes(JSON.stringify(v)))
			if (lost.length) findings.push(`${here}: enum no longer allows ${JSON.stringify(lost)}`)
		}

		if (key === 'additionalProperties' && a[key] === true && b[key] === false) {
			findings.push(`${here}: additionalProperties true -> false`)
		}

		if (!inA && inB && NEW_CONSTRAINT_KEYS.includes(key)) {
			findings.push(`${here}: new ${key} constraint ${JSON.stringify(b[key])}`)
		}

		if (inA && inB) walk(a[key], b[key], here)
	}
}

walk(load(oldPath), load(newPath), '')

if (findings.length === 0) {
	console.log('none')
	process.exit(0)
}

for (const f of findings.sort()) console.log(f)
process.exit(1)
