#!/usr/bin/env node
// SPDX-License-Identifier: EUPL-1.2
//
// test_check_manifest_crossref.js — gate-30 (effective-manifest-crossref)
// fixture-based self-test.
//
// Proves the gate contract over scripts/test-fixtures/effective-manifest/:
//   good/   → assembles, structurally validates (when Ajv is resolvable),
//             and cross-resolves: checker exit 0, summary "passed", exactly
//             ONE warn-severity finding (the open-modal registry WARN) and
//             ZERO error findings — warnings never set the exit code.
//   broken/ → checker exit 1, summary "failed", EXACTLY one error finding
//             per seeded defect class (menu-route, action-target open-page,
//             slug-resolution zaakafhandelapp-shape, deeplink-route,
//             removals-invariant) — none missed, none extra — plus the
//             open-modal WARN; and the ASSEMBLED manifest fails
//             check_manifest.js on the fragment-introduced `layout[]`
//             violation (structural stage, Ajv path only).
//
// Run: node scripts/lib/test_check_manifest_crossref.js   (exit 0 = pass)

'use strict'

const { spawnSync } = require('child_process')
const fs = require('fs')
const os = require('os')
const path = require('path')

const LIB = __dirname
const FIX = path.resolve(LIB, '..', 'test-fixtures', 'effective-manifest')
const BUILDER = path.join(LIB, 'build_effective_manifest.js')
const CHECKER = path.join(LIB, 'check_manifest_crossref.js')
const VALIDATOR = path.join(LIB, 'check_manifest.js')

let fails = 0
function assert(cond, label) {
	if (cond) {
		console.log(`PASS — ${label}`)
	} else {
		console.log(`FAIL — ${label}`)
		fails++
	}
}

// Run a node helper, returning { status, stdout, stderr } without throwing.
function run(args) {
	const r = spawnSync(process.execPath, args, { encoding: 'utf8' })
	return { status: r.status === null ? -1 : r.status, stdout: r.stdout || '', stderr: r.stderr || '' }
}

// Parse the checker stdout: every line must be valid JSON; last line is the
// summary; an optional preceding line carries the findings.
function parseReport(stdout) {
	const lines = stdout.trim().split('\n').filter((l) => l !== '')
	const parsed = lines.map((l) => {
		try { return JSON.parse(l) } catch (e) { return { __invalid: l } }
	})
	const invalid = parsed.filter((p) => p.__invalid)
	const summary = parsed[parsed.length - 1]
	const findingsLine = parsed.find((p) => Array.isArray(p.findings))
	return { invalid, summary, findings: findingsLine ? findingsLine.findings : [] }
}

// --- good fixture ------------------------------------------------------------
{
	const tmp = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'gate30-test-')), 'good-effective.json')
	const build = run([BUILDER, '--app-dir', path.join(FIX, 'good'), '--out', tmp])
	assert(build.status === 0, 'good: effective manifest assembles (builder exit 0)')

	const check = run([CHECKER, '--app-dir', path.join(FIX, 'good'), '--manifest', tmp])
	const rep = parseReport(check.stdout)
	assert(check.status === 0, 'good: checker exits 0')
	assert(rep.invalid.length === 0, 'good: every stdout line is valid JSON')
	assert(rep.summary && rep.summary.status === 'passed' && rep.summary.checked === 1 && rep.summary.failed === 0,
		'good: summary line is {"status":"passed","checked":1,"failed":0}')
	const errors = rep.findings.filter((f) => f.severity === 'error')
	const warns = rep.findings.filter((f) => f.severity === 'warn')
	assert(errors.length === 0, 'good: zero error findings')
	assert(warns.length === 1 && warns[0].check === 'action-target', 'good: exactly one WARN (open-modal registry not statically checkable)')
	assert(/^at .*: WARN /m.test(check.stderr), 'good: WARN reported as "at <path>: WARN …" on stderr')
	fs.rmSync(path.dirname(tmp), { recursive: true, force: true })
}

// --- broken fixture ------------------------------------------------------------
{
	const tmp = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'gate30-test-')), 'broken-effective.json')
	const build = run([BUILDER, '--app-dir', path.join(FIX, 'broken'), '--out', tmp])
	assert(build.status === 0, 'broken: effective manifest still assembles (defects are semantic, not merge failures)')

	const check = run([CHECKER, '--app-dir', path.join(FIX, 'broken'), '--manifest', tmp])
	const rep = parseReport(check.stdout)
	assert(check.status === 1, 'broken: checker exits 1')
	assert(rep.invalid.length === 0, 'broken: every stdout line is valid JSON')
	assert(rep.summary && rep.summary.status === 'failed' && rep.summary.checked === 1 && rep.summary.failed === 1,
		'broken: summary line is {"status":"failed","checked":1,"failed":1}')

	const errors = rep.findings.filter((f) => f.severity === 'error')
	const warns = rep.findings.filter((f) => f.severity === 'warn')
	const byCheck = (name) => errors.filter((f) => f.check === name)

	assert(byCheck('menu-route').length === 1
		&& byCheck('menu-route')[0].message.includes("'cases-overview'"),
	'broken: exactly one menu-route error (dangling route cases-overview)')
	assert(byCheck('action-target').length === 1
		&& byCheck('action-target')[0].message.includes("'missing-page'"),
	'broken: exactly one action-target error (open-page → missing-page)')
	assert(byCheck('slug-resolution').length === 1
		&& byCheck('slug-resolution')[0].message.includes("'besluit'")
		&& byCheck('slug-resolution')[0].message.includes("'zaak-besluiten'"),
	'broken: exactly one slug-resolution error naming the widget and the missing schema (zaakafhandelapp shape)')
	assert(byCheck('deeplink-route').length === 1
		&& byCheck('deeplink-route')[0].message.includes('/besluiten/{id}'),
	'broken: exactly one deeplink-route error (unroutable /besluiten prefix)')
	assert(byCheck('removals-invariant').length === 1
		&& byCheck('removals-invariant')[0].message.includes("'cases-index'"),
	'broken: exactly one removals-invariant error (orphaned route cases-index, ADR-044)')
	assert(errors.length === 5, `broken: exactly 5 error findings — none missed, none extra (got ${errors.length})`)
	assert(warns.length === 1 && warns[0].check === 'action-target', 'broken: the open-modal WARN present, warn severity')
	fs.rmSync(path.dirname(tmp), { recursive: true, force: true })
}

// --- structural stage on the ASSEMBLED broken manifest (Ajv path) ---------------
// The fragment-introduced `layout[]` page property is invisible to the base
// gate-22 run and to the crossref checker; it must fail check_manifest.js on
// the assembled manifest. Requires Ajv (the structural-lint fallback does not
// re-check page rules) — skip with a notice when Ajv is unresolvable, exactly
// as test_check_manifest.sh skips its no-Ajv leg.
{
	const ajvProbe = run(['-e', "require('ajv/dist/2020')"])
	if (ajvProbe.status !== 0) {
		console.log('SKIP — structural stage: Ajv not resolvable (set NODE_PATH); gate-30 itself fails closed in this state')
	} else {
		const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'gate30-test-'))
		const goodTmp = path.join(tmpDir, 'good-effective.json')
		const brokenTmp = path.join(tmpDir, 'broken-effective.json')
		run([BUILDER, '--app-dir', path.join(FIX, 'good'), '--out', goodTmp])
		run([BUILDER, '--app-dir', path.join(FIX, 'broken'), '--out', brokenTmp])
		const goodVal = run([VALIDATOR, goodTmp])
		assert(goodVal.status === 0, 'good: ASSEMBLED manifest passes canonical validation (check_manifest.js exit 0)')
		const brokenVal = run([VALIDATOR, brokenTmp])
		assert(brokenVal.status === 1, 'broken: ASSEMBLED manifest fails canonical validation (fragment-introduced layout[] violation)')
		assert(/additionalProperties/.test(brokenVal.stderr + brokenVal.stdout),
			'broken: the structural failure is the additionalProperties (layout) violation')
		fs.rmSync(tmpDir, { recursive: true, force: true })
	}
}

console.log('')
if (fails === 0) {
	console.log('ALL gate-30 effective-manifest-crossref assertions PASSED')
	process.exit(0)
}
console.log(`${fails} gate-30 assertion(s) FAILED`)
process.exit(1)
