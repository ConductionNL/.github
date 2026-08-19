#!/usr/bin/env node
// SPDX-License-Identifier: EUPL-1.2
//
// test_check_duplicate_index_pages.js — gate-68 (duplicate-index-pages)
// checker self-test.
//
// Two layers, mirroring gate-53's test_check_manifest_crossref.js:
//
//   STATE layer (no --base-ref, WARN-only mode — there is no git history in
//   a bare fixture directory): good/ produces zero findings; broken/
//   produces the expected 3-page group spread across a base + two
//   src/manifest.d/ fragments (exercises the fragment-merge path, not just a
//   single-file manifest); case-varied/ proves the grouping key is
//   case-normalized (a fixture pair differing only in
//   config.register/config.schema case groups together) — the orchestrator's
//   binding ruling for this gate.
//
//   RATCHET layer (--base-ref against a real two-commit git fixture, built
//   in a throwaway tmpdir): proves the FAIL/WARN split from design.md
//   Decision 3's table end to end through the checker's own --base-ref
//   handling (assembleAtRef under the hood) — not just the grouping logic.
//
// Run: node scripts/lib/test_check_duplicate_index_pages.js   (exit 0 = pass)

'use strict'

const { spawnSync } = require('child_process')
const fs = require('fs')
const os = require('os')
const path = require('path')

const LIB = __dirname
const FIX = path.resolve(LIB, '..', 'test-fixtures', 'duplicate-index-pages')
const CHECKER = path.join(LIB, 'check_duplicate_index_pages.js')

let fails = 0
function assert(cond, label, detail) {
	if (cond) {
		console.log(`PASS — ${label}`)
	} else {
		console.log(`FAIL — ${label}${detail ? `\n    ${detail}` : ''}`)
		fails++
	}
}

// --- guard the guard --------------------------------------------------------
{
	const required = [
		'good/src/manifest.json',
		'good/src/manifest.d/10-reports.json',
		'broken/src/manifest.json',
		'broken/src/manifest.d/10-verleend.json',
		'broken/src/manifest.d/20-teruggevorderd.json',
		'case-varied/src/manifest.json',
	]
	const missing = required.filter((rel) => !fs.existsSync(path.join(FIX, rel)))
	if (missing.length > 0) {
		console.log(`FAIL — ${missing.length} gate-68 fixture file(s) MISSING under ${FIX}; this suite cannot assert anything:`)
		for (const rel of missing) console.log(`    ${rel}`)
		process.exit(1)
	}
}

function run(appDir, extraArgs) {
	const args = [CHECKER, '--app-dir', appDir, ...(extraArgs || [])]
	const res = spawnSync('node', args, { encoding: 'utf8' })
	return {
		status: res.status,
		stdout: res.stdout || '',
		stderr: res.stderr || '',
	}
}

function findingsCount(stdout) {
	const m = /\[duplicate-index-pages\] findings=(\d+)/.exec(stdout)
	return m ? Number(m[1]) : null
}

function summary(stdout) {
	const lines = stdout.trim().split('\n').filter(Boolean)
	for (let i = lines.length - 1; i >= 0; i--) {
		try {
			const obj = JSON.parse(lines[i])
			if (typeof obj.status === 'string' && typeof obj.checked === 'number') return obj
		} catch (e) { /* not the summary line */ }
	}
	return null
}

// --- STATE layer: good/ ------------------------------------------------------
{
	const { status, stdout, stderr } = run(path.join(FIX, 'good'))
	assert(status === 0, 'good/: checker exits 0', `stderr: ${stderr}`)
	assert(findingsCount(stdout) === 0, 'good/: findings=0 terminal marker printed', `stdout: ${stdout}`)
	const s = summary(stdout)
	assert(s && s.status === 'passed' && s.failed === 0, 'good/: summary line reports passed/failed=0', JSON.stringify(s))
}

// --- STATE layer: broken/ (3-page group across base + two fragments) --------
{
	const { status, stdout, stderr } = run(path.join(FIX, 'broken'))
	// No --base-ref given -> WARN-only mode (design.md "No resolvable base"):
	// the gate never FAILs without a base, so this exits 0 even though it
	// found a real duplicate group.
	assert(status === 0, 'broken/ (no --base-ref): checker exits 0 — WARN-only mode never blocks', `stderr: ${stderr}`)
	assert(findingsCount(stdout) === 1, 'broken/ (no --base-ref): exactly one (register, schema) group reported', `stdout: ${stdout}`)
	assert(/register 'shillinq', schema 'subsidie'/.test(stderr), 'broken/: finding names the (shillinq, Subsidie) pair (case-normalized)', stderr)
	assert(/WARN/.test(stderr), 'broken/ (no --base-ref): the finding is a WARN diagnostic, not a FAIL one', stderr)
	for (const id of ['SubsidiesOverzicht', 'SubsidiesVerleend', 'SubsidiesTeruggevorderd']) {
		assert(stderr.includes(id), `broken/: finding names page '${id}' (fragment-merge path exercised)`, stderr)
	}
	assert(!stderr.includes('SubsidieDetail'), 'broken/: the type:"detail" page over the same pair is NOT counted', stderr)
}

// --- STATE layer: case-varied/ (grouping key is case-normalized) ------------
{
	const { status, stdout, stderr } = run(path.join(FIX, 'case-varied'))
	assert(status === 0, 'case-varied/: checker exits 0', `stderr: ${stderr}`)
	assert(findingsCount(stdout) === 1, 'case-varied/: "Shillinq"/"InventoryStock" and "shillinq"/"inventorystock" group into ONE pair', `stdout: ${stdout}`)
	assert(/register 'shillinq', schema 'inventorystock'/.test(stderr), 'case-varied/: the grouped pair is reported lower-cased', stderr)
	assert(stderr.includes('StockLevels') && stderr.includes('StockByLocation'), 'case-varied/: finding names both differently-cased pages', stderr)
}

// --- RATCHET layer: real two-commit git fixture, --base-ref end to end ------
//
// Builds ONE throwaway git repo per scenario in design.md Decision 3's table,
// re-using the same tmp-repo helper style as test_build_effective_manifest.js
// (assembleAtRef's own self-test).
function gitRepoWithCounts(baseCount, headCount) {
	const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'hydra-gate68-ratchet-'))
	const git = (args) => spawnSync('git', ['-C', dir, ...args], { encoding: 'utf8' })
	const pageFor = (n) => ({
		id: `SubsidiePage${n}`,
		route: `/subsidies-${n}`,
		type: 'index',
		title: `Subsidies ${n}`,
		config: { register: 'shillinq', schema: 'Subsidie' },
	})
	const writeManifest = (n) => {
		const manifest = {
			$schema: 'https://raw.githubusercontent.com/ConductionNL/nextcloud-vue/main/src/schemas/app-manifest-v2.schema.json',
			version: '1.0.0',
			pages: Array.from({ length: n }, (_v, i) => pageFor(i + 1)),
			menu: [],
		}
		fs.mkdirSync(path.join(dir, 'src'), { recursive: true })
		fs.writeFileSync(path.join(dir, 'src', 'manifest.json'), JSON.stringify(manifest, null, '\t'))
	}
	git(['init', '-q', '.'])
	git(['config', 'user.email', 'test@example.invalid'])
	git(['config', 'user.name', 'Gate Test'])
	writeManifest(baseCount)
	git(['add', '-A'])
	git(['commit', '-q', '-m', 'base'])
	const baseSha = git(['rev-parse', 'HEAD']).stdout.trim()
	writeManifest(headCount)
	git(['add', '-A'])
	git(['commit', '-q', '-m', 'head', '--allow-empty'])
	return { dir, baseSha }
}

function ratchetCase(label, baseCount, headCount, expect) {
	const { dir, baseSha } = gitRepoWithCounts(baseCount, headCount)
	try {
		const { status, stdout, stderr } = run(dir, ['--base-ref', baseSha])
		if (expect.exit !== undefined) {
			assert(status === expect.exit, `${label}: exit code ${expect.exit}`, `got ${status}; stderr: ${stderr}`)
		}
		if (expect.findings !== undefined) {
			assert(findingsCount(stdout) === expect.findings, `${label}: findings=${expect.findings}`, `stdout: ${stdout}`)
		}
		if (expect.severity) {
			const re = expect.severity === 'error' ? /^at .*: (?!WARN)/m : /^at .*: WARN /m
			assert(re.test(stderr), `${label}: finding severity is ${expect.severity}`, stderr)
		}
		if (expect.namesPair) {
			assert(stderr.includes("register 'shillinq', schema 'subsidie'"), `${label}: finding names the ratcheted pair`, stderr)
		}
	} finally {
		fs.rmSync(dir, { recursive: true, force: true })
	}
}

// BASE_REF absent/1 -> HEAD >=2 : FAIL (new duplicate introduced)
ratchetCase('ratchet: 1 -> 2 (new duplicate)', 1, 2, { exit: 1, findings: 1, severity: 'error', namesPair: true })

// BASE_REF >=2 -> HEAD grew : FAIL (existing duplicate grew)
ratchetCase('ratchet: 6 -> 7 (existing duplicate grew)', 6, 7, { exit: 1, findings: 1, severity: 'error', namesPair: true })

// BASE_REF >=2 -> HEAD unchanged, still >=2 : WARN, exit 0
ratchetCase('ratchet: 6 -> 6 (unchanged, pre-existing)', 6, 6, { exit: 0, findings: 1, severity: 'warn', namesPair: true })

// BASE_REF >=2 -> HEAD shrank but still >1 : WARN, exit 0 (not FAIL)
ratchetCase('ratchet: 4 -> 3 (shrank, still duplicated)', 4, 3, { exit: 0, findings: 1, severity: 'warn', namesPair: true })

// BASE_REF >=2 -> HEAD <=1 : fully resolved, not reported at all
ratchetCase('ratchet: 2 -> 1 (fully resolved)', 2, 1, { exit: 0, findings: 0 })

console.log('')
if (fails === 0) {
	console.log('ALL check_duplicate_index_pages assertions PASSED')
	process.exit(0)
}
console.log(`${fails} check_duplicate_index_pages assertion(s) FAILED`)
process.exit(1)
