#!/usr/bin/env node
// SPDX-License-Identifier: EUPL-1.2
//
// test_diff_schema_strictness.js — assertions for the vendored-schema
// strictness differ.
//
// The property this suite has to protect is that the differ can say NO. A
// checker that answers "additive" to everything reads exactly like one that
// looked, and it would wave through the bump that reddens the fleet. So every
// additive case below is paired with a planted tightening of the same shape,
// and the planted one must be reported.

'use strict'

const assert = require('assert')
const fs = require('fs')
const os = require('os')
const path = require('path')
const { execFileSync } = require('child_process')

const HELPER = path.resolve(__dirname, 'diff_schema_strictness.js')
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'diff-strictness-'))

let failures = 0

function run(oldDoc, newDoc) {
	const a = path.join(TMP, 'old.json')
	const b = path.join(TMP, 'new.json')
	fs.writeFileSync(a, JSON.stringify(oldDoc))
	fs.writeFileSync(b, JSON.stringify(newDoc))
	try {
		return { code: 0, out: execFileSync(process.execPath, [HELPER, a, b], { encoding: 'utf8' }) }
	} catch (e) {
		return { code: e.status, out: (e.stdout || '') + (e.stderr || '') }
	}
}

function check(name, fn) {
	try {
		fn()
		console.log(`PASS — ${name}`)
	} catch (e) {
		failures++
		console.log(`FAIL — ${name}: ${e.message}`)
	}
}

// --- additive cases: the differ must stay quiet -----------------------------

check('a new optional property is additive', () => {
	const r = run(
		{ type: 'object', additionalProperties: false, properties: { a: { type: 'string' } } },
		{ type: 'object', additionalProperties: false, properties: { a: { type: 'string' }, b: { type: 'string' } } },
	)
	assert.strictEqual(r.code, 0, `exit ${r.code}`)
	assert.match(r.out, /none/)
})

check('a widened enum is additive', () => {
	const r = run({ enum: ['a'] }, { enum: ['a', 'b'] })
	assert.strictEqual(r.code, 0, `exit ${r.code}`)
})

check('a new $defs entry is additive', () => {
	const r = run({ $defs: { x: { type: 'string' } } }, { $defs: { x: { type: 'string' }, y: { type: 'number' } } })
	assert.strictEqual(r.code, 0, `exit ${r.code}`)
})

// --- planted tightenings: each additive case has a twin that must be caught --

check('a newly required key is reported', () => {
	const r = run({ required: ['a'] }, { required: ['a', 'b'] })
	assert.strictEqual(r.code, 1, `exit ${r.code}`)
	assert.match(r.out, /newly required \["b"\]/)
})

check('a narrowed enum is reported', () => {
	const r = run({ enum: ['a', 'b'] }, { enum: ['a'] })
	assert.strictEqual(r.code, 1, `exit ${r.code}`)
	assert.match(r.out, /enum no longer allows \["b"\]/)
})

check('additionalProperties true -> false is reported', () => {
	const r = run({ additionalProperties: true }, { additionalProperties: false })
	assert.strictEqual(r.code, 1, `exit ${r.code}`)
	assert.match(r.out, /additionalProperties true -> false/)
})

check('a new pattern where there was none is reported', () => {
	const r = run({ type: 'string' }, { type: 'string', pattern: '^x' })
	assert.strictEqual(r.code, 1, `exit ${r.code}`)
	assert.match(r.out, /new pattern constraint/)
})

check('a property REMOVED under additionalProperties:false is reported', () => {
	// The case a line diff reads as "fewer rules". The key stops being named,
	// so the object refuses it, and every manifest that used it turns red.
	const r = run(
		{ type: 'object', additionalProperties: false, properties: { a: {}, b: {} } },
		{ type: 'object', additionalProperties: false, properties: { a: {} } },
	)
	assert.strictEqual(r.code, 1, `exit ${r.code}`)
	assert.match(r.out, /properties\/b: property removed while additionalProperties is false/)
})

// --- the real pair this helper was written for ------------------------------

check('the shipped 2.41.0 -> 2.42.0 bump reads additive in BOTH directions of the check', () => {
	// Forward: nothing got stricter. Reverse: the same two files DO produce
	// findings, which is the control proving the forward "none" was a
	// measurement and not a checker that cannot speak.
	//
	// The pair is the vendored schema with and without the key its latest bump
	// added. It used to be savedViewPlaces (2.33.0 -> 2.37.0, #785); the
	// library has since dropped that key, so the arm now follows the addition
	// the current copy was vendored for: `onDemand` on a setup step (2.42.0).
	const vendored = path.resolve(__dirname, '..', 'schemas', 'app-manifest-v2.schema.json')
	assert.ok(fs.existsSync(vendored), 'vendored schema is missing')
	const doc = JSON.parse(fs.readFileSync(vendored, 'utf8'))
	const step = doc.properties.setup.properties.steps.items
	assert.ok(step.properties.onDemand, 'the vendored schema no longer declares setup.steps[].onDemand; re-point this arm at the latest addition')
	assert.strictEqual(step.additionalProperties, false, 'setup steps are no longer closed; the reverse control cannot fire')
	const stripped = JSON.parse(JSON.stringify(doc))
	delete stripped.properties.setup.properties.steps.items.properties.onDemand

	const forward = run(stripped, doc)
	assert.strictEqual(forward.code, 0, `adding onDemand back should be additive, got exit ${forward.code}: ${forward.out}`)

	const reverse = run(doc, stripped)
	assert.strictEqual(reverse.code, 1, 'removing onDemand must be reported as a tightening')
	assert.match(reverse.out, /onDemand/)
})

fs.rmSync(TMP, { recursive: true, force: true })

if (failures) {
	console.log(`\n${failures} diff_schema_strictness assertion(s) FAILED`)
	process.exit(1)
}
console.log('\nALL diff_schema_strictness assertions PASSED')
