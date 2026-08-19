// SPDX-License-Identifier: EUPL-1.2
// SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl>
//
// Where does CODE live in a JavaScript file, and where does PROSE live?
//
// WHY THIS EXISTS
// ---------------
// `source_scope.py` answers this for every Python checker in this package.
// The node checkers had no equivalent, so gate-53 carried a two-line regex:
//
//     src.replace(/\/\*[\s\S]*?\*\//g, ' ')
//        .replace(/(^|[^:])\/\/[^\n]*/g, '$1 ')
//
// which is not string-aware. Measured on a registry of the shape this fleet
// actually writes (#424):
//
//     export default {
//         Reports:  { kind: 'page', component: Reports, glob: '/*.vue' },
//         Settings: { /* the admin page */ kind: 'page', component: Settings },
//     }
//
// the `/*` INSIDE the glob string opened a block comment that ran to the
// `*/` of the real comment two lines later. `Settings` vanished from the
// registry, and a manifest page referencing it was reported as
// `FAIL — 1 cross-reference failure`: the gate accused the app of not
// registering a component it registers, and no correct change closes that
// finding except deleting the glob.
//
// The WORSE variant is silent. When the swallowed span is brace-UNBALANCED,
// `parseRegistry` returns `parsed: false` and the caller skips the whole
// cross-reference check — a false GREEN, produced by the same two lines.
//
// THE CONTRACT — deliberately identical to `source_scope.js_comment_mask`
// ----------------------------------------------------------------------
//   * comments and regex literals are BLANKED,
//   * string and template CONTENTS are KEPT — for gate-53 the quoted registry
//     key (`'agent-form'`) and `kind: 'page'` ARE the evidence,
//   * the result is the SAME LENGTH as the input with newlines intact, so an
//     index computed on the mask addresses the original text.
//
// Being byte-identical to the Python is not a comment: `test_js_scope.js`
// runs `source_scope.py --mask js-comments` over a shared corpus and asserts
// equality, and that test is mutation-checked. Two copies that are PROVEN
// equal are a maintenance cost; two copies that MIGHT differ are a defect —
// the same trade `test_source_scope.py::TestSharedWithGate19` already makes.

'use strict'

// Keywords after which a `/` opens a regular expression rather than dividing.
const REGEX_KEYWORDS = new Set([
	'return', 'typeof', 'instanceof', 'in', 'of', 'new', 'delete', 'void',
	'throw', 'case', 'do', 'else', 'yield', 'await',
])

const isWordChar = (c) => /[A-Za-z0-9_$]/.test(c)

// Index just past the quoted string whose opening quote is at `i`. An
// unterminated literal stops at the newline rather than swallowing the rest of
// the file — a lone apostrophe in a comment must not blank a whole registry.
function skipString(text, i) {
	const quote = text[i]
	const n = text.length
	let j = i + 1
	while (j < n) {
		const c = text[j]
		if (c === '\\') { j += 2; continue }
		if (c === quote) return j + 1
		if (c === '\n') return j
		j++
	}
	return n
}

// Index just past the template literal whose backtick is at `i`. `${ … }`
// substitutions are walked because they may contain braces, quotes and
// further templates.
function skipTemplate(text, i) {
	const n = text.length
	let j = i + 1
	let depth = 0
	while (j < n) {
		const c = text[j]
		if (c === '\\') { j += 2; continue }
		if (depth === 0) {
			if (c === '`') return j + 1
			if (c === '$' && j + 1 < n && text[j + 1] === '{') { depth++; j += 2; continue }
			j++
			continue
		}
		if (c === '`') { j = skipTemplate(text, j); continue }
		if (c === "'" || c === '"') { j = skipString(text, j); continue }
		if (c === '{') depth++
		else if (c === '}') depth--
		j++
	}
	return n
}

// Index just past the regex literal starting at `i`, or -1 if it is not one.
// A regex literal cannot span a newline, which is the cheap and reliable
// disambiguator against division.
function skipRegex(text, i) {
	const n = text.length
	let j = i + 1
	let inClass = false
	while (j < n) {
		const c = text[j]
		if (c === '\\') { j += 2; continue }
		if (c === '\n') return -1
		if (inClass) {
			if (c === ']') inClass = false
		} else if (c === '[') {
			inClass = true
		} else if (c === '/') {
			j++
			while (j < n && /[A-Za-z]/.test(text[j])) j++
			return j
		}
		j++
	}
	return -1
}

function regexCanStart(prevChar, prevWord) {
	if (prevChar === '') return true
	if (prevChar === ')' || prevChar === ']') return false
	if (prevChar === "'" || prevChar === '"' || prevChar === '`') return false
	if (isWordChar(prevChar)) return REGEX_KEYWORDS.has(prevWord)
	return true
}

/**
 * A same-length copy of `text` with comments and regex literals blanked and
 * string/template CONTENTS left intact.
 */
function jsCommentMask(text) {
	const out = text.split('')
	const n = text.length
	const blank = (a, b) => {
		for (let k = Math.max(a, 0); k < Math.min(b, n); k++) {
			if (out[k] !== '\n') out[k] = ' '
		}
	}
	let i = 0
	let prevChar = ''
	let prevWord = ''
	while (i < n) {
		const c = text[i]
		if (c === '/' && text.startsWith('//', i)) {
			let j = text.indexOf('\n', i)
			if (j < 0) j = n
			blank(i, j)
			i = j
			continue
		}
		if (c === '/' && text.startsWith('/*', i)) {
			let j = text.indexOf('*/', i + 2)
			j = j < 0 ? n : j + 2
			blank(i, j)
			i = j
			continue
		}
		if (c === "'" || c === '"') {
			i = skipString(text, i)
			prevChar = c
			prevWord = ''
			continue
		}
		if (c === '`') {
			i = skipTemplate(text, i)
			prevChar = '`'
			prevWord = ''
			continue
		}
		if (c === '/' && regexCanStart(prevChar, prevWord)) {
			const j = skipRegex(text, i)
			if (j > 0) {
				blank(i, j)
				prevChar = ')'      // a regex literal is a value
				prevWord = ''
				i = j
				continue
			}
		}
		if (isWordChar(c)) {
			let k = i
			while (k < n && isWordChar(text[k])) k++
			prevWord = text.slice(i, k)
			prevChar = text[k - 1]
			i = k
			continue
		}
		if (!/\s/.test(c)) { prevChar = c; prevWord = '' }
		i++
	}
	return out.join('')
}

module.exports = { jsCommentMask }
