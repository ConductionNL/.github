// SPDX-License-Identifier: EUPL-1.2
// SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl>
//
// Tests for js_scope.jsCommentMask — the node port of
// source_scope.js_comment_mask (#424).
//
// TWO KINDS OF ASSERTION HERE, AND THE SECOND IS THE IMPORTANT ONE
// ----------------------------------------------------------------
// 1. BEHAVIOUR: the shapes gate-53 got wrong, each paired with the true
//    positive it must not swallow.
// 2. DRIFT: the mask is asserted BYTE-IDENTICAL to the Python original over a
//    corpus, by shelling out to `source_scope.py --mask js-comments -`. Two
//    copies of one rule is what #424 is about; the only honest way to ship a
//    second one is to prove it equal. Mutation-checked: change one branch of
//    either copy and TestDrift goes red.
//
// Run: node scripts/lib/test_js_scope.js   (exit 0 = green)

'use strict'

const { execFileSync } = require('child_process')
const path = require('path')
const { jsCommentMask } = require('./js_scope.js')

let failed = 0
function check(name, cond, detail) {
	if (cond) {
		console.log(`PASS — ${name}`)
	} else {
		console.log(`FAIL — ${name}${detail ? ': ' + detail : ''}`)
		failed++
	}
}

// --- the #424 shape ---------------------------------------------------------
const GLOB = `export default {
	Reports: { kind: 'page', component: Reports, glob: '/*.vue' },
	Settings: { /* the admin page */ kind: 'page', component: Settings },
}
`
const masked = jsCommentMask(GLOB)
check('EVIDENCE: `/*` inside a string does not open a block comment',
	masked.includes('Settings: {'), JSON.stringify(masked))
check('CONTROL: the real block comment beside it IS blanked',
	!masked.includes('the admin page'), JSON.stringify(masked))
check('CONTROL: the quoted registry key survives — it is the evidence',
	masked.includes("kind: 'page'"), JSON.stringify(masked))

check('EVIDENCE: `//` inside a URL string opens nothing',
	jsCommentMask("const u = 'https://x/y'\nconst k = 1\n").includes('const k = 1'))
check('CONTROL: a real line comment is blanked',
	!jsCommentMask("const u = 1 // note here\n").includes('note here'))
check('CONTROL: `:` before `//` no longer needs a special case',
	jsCommentMask("const o = { u: 'https://x' }\n").includes("'https://x'"))

// The offset contract every caller depends on.
for (const src of [GLOB, "a // b\nc\n", "const r = /a\\/b/g\nlet z = 1\n", '`t${1}`\n']) {
	const out = jsCommentMask(src)
	check('offsets survive: same length and same line count',
		out.length === src.length && out.split('\n').length === src.split('\n').length,
		JSON.stringify(src))
}

// --- DRIFT: identical to the Python original over a corpus -------------------
const PY = path.join(__dirname, 'source_scope.py')

function pythonMask(src) {
	return execFileSync('python3', [PY, '--mask', 'js-comments', '-'], {
		input: src,
		encoding: 'utf8',
	})
}

const CORPUS = [
	GLOB,
	"const u = 'https://x/y' // trailing\n",
	"/* block\n   spanning */\nlet q = `t${1 + 2}`\n",
	"const r = /[a-z]\\/+/g\nreturn 1 / 2\n",
	"const s = \"it's fine\" // apostrophe in a string\n",
	"const t = 'unterminated\nconst u = 2 // still a comment\n",
	"export default {\n\t'agent-form': { kind: 'section' },\n\tSettings,\n}\n",
	"function f() { return /x/.test('a') }\n",
	"const n = a /b/ c\n",
	"`outer ${ `inner ${ 'deep' }` } end` // done\n",
]

let compared = 0
for (const src of CORPUS) {
	const js = jsCommentMask(src)
	const py = pythonMask(src)
	check('drift: js_scope agrees with source_scope.js_comment_mask',
		js === py, `\n  js: ${JSON.stringify(js)}\n  py: ${JSON.stringify(py)}`)
	compared++
}

// This package's own .js sources, so the corpus cannot quietly become trivial.
const fs = require('fs')
for (const name of fs.readdirSync(__dirname).sort()) {
	if (!name.endsWith('.js')) continue
	const src = fs.readFileSync(path.join(__dirname, name), 'utf8')
	const js = jsCommentMask(src)
	const py = pythonMask(src)
	check(`drift over this package's own source: ${name}`, js === py)
	compared++
}
check('the drift test actually compared something', compared > 5, String(compared))

console.log()
if (failed) {
	console.log(`FAILED: ${failed}`)
	process.exit(1)
}
console.log('ALL js_scope assertions passed')
