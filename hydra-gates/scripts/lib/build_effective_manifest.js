#!/usr/bin/env node
// SPDX-License-Identifier: EUPL-1.2
//
// build_effective_manifest.js — Gate-30 vendored effective-manifest builder.
//
// Assembles an app's EFFECTIVE manifest exactly as the library bootstrap
// does: base src/manifest.json + src/manifest.d/*.json fragments (ADR-037,
// ascending filename order) + src/menu-layout.json (ADR-044, applied in the
// order relocations → removals → settingsSection).
//
// SYNC NOTE — vendored port. The merge pipeline below is ported FAITHFULLY
// from @conduction/nextcloud-vue:
//   nextcloud-vue/src/utils/buildManifest.js
// (buildManifest, applyMenuLayout, mergeMenuItems, mergePages,
//  applyMenuRelocations, applyMenuRemovals, applySettingsSection),
//   nextcloud-vue/src/utils/expandPageTemplates.js
// (expandPageTemplates + its substitution helpers — the entity-scaffold
//  templating step buildManifest runs LAST), and
//   nextcloud-vue/src/utils/mergeManifestDelta.js
// (mergeManifestDelta — the keyed base+delta merge expandPageTemplates uses
//  for per-instance `override` blocks).
// hydra has no package.json / node_modules, and the fleet's pinned lib
// generations span beta.30…beta.146 — vendoring gives ONE deterministic
// pipeline fleet-wide, mirroring how check_manifest.js vendors the canonical
// schema. If the lib's buildManifest semantics change, update this file AND
// scripts/lib/test_build_effective_manifest.js (the fixtures pin the
// observable merge behaviour).
//
// EXPANSION ERROR SEMANTICS (gate use vs runtime). The lib's runtime call is
// expandPageTemplates(merged, { throwOnError: false }): a bad instantiation is
// SKIPPED with a console.warn, so a single bad instance never blanks the app.
// The gate mirrors that EFFECTIVE RESULT (the same pages land in `pages[]`)
// but must never let the skip be silent: buildManifest collects the named
// expansion errors into the caller-supplied `meta` object, assembleFromDir
// returns them as `.expansion.errors`, and gate consumers (check_manifest_
// crossref.js) turn each one into an error-severity finding.
//
// Usage (CLI):
//   node scripts/lib/build_effective_manifest.js [--app-dir DIR] [--out FILE]
//                                                [--expansion-out FILE]
//     --app-dir DIR   app repo root (default: CWD). Reads DIR/src/manifest.json,
//                     DIR/src/manifest.d/*.json, DIR/src/menu-layout.json.
//     --out FILE      write the assembled manifest JSON to FILE (default: stdout).
//     --expansion-out FILE
//                     write the page-template expansion report as JSON:
//                     { expandedCount, errors, expandedPages }. All-zero/empty
//                     for an app that declares no pageTemplates/pageInstances.
//                     This is how the Python gate helpers (check_detail_page_
//                     discipline.py, check_icon_vocabulary.py) reach the
//                     expanded pages without a second expansion implementation.
//
// Missing src/manifest.d/ and missing src/menu-layout.json are ABSENT INPUTS,
// not errors: the effective manifest then equals the base manifest.
//
// Exit codes:
//   0 — assembled successfully
//   1 — an input file is not valid JSON (message names the file)
//   2 — base src/manifest.json missing (Tier 0 — caller decides how to treat)
//
// Also require()-able as a module:
//   const { buildManifest, loadAppInputs, assembleFromDir, assembleAtRef } = require('./build_effective_manifest.js')

'use strict'

const fs = require('fs')
const os = require('os')
const path = require('path')
const { spawnSync } = require('child_process')

/**
 * Build an app's effective manifest from its bundled base, its modular
 * `manifest.d/*.json` fragments (ADR-037), and its `menu-layout.json`.
 * Ported verbatim from nextcloud-vue/src/utils/buildManifest.js — including
 * the fragment collection of `pageTemplates` / `pageInstances` / `sets` and
 * the entity-scaffold expansion the lib runs as its FINAL step, so an app
 * using manifest-entity-scaffold-templating is judged on the same concrete
 * `pages[]` the runtime renderer sees.
 *
 * @param {object} base The bundled base manifest (`src/manifest.json`).
 * @param {Array<object>} [fragments] Fragment objects (each may carry `pages`/`menu`).
 * @param {object} [menuLayout] `{ relocations?, removals?, settingsSection? }`.
 * @param {object} [meta] OUT parameter (gate-side addition, not part of the
 *   lib port): when an object is passed, `meta.expansion` is filled with
 *   `{ expandedCount, errors, expandedPages }` — the runtime skips a failing
 *   instantiation, the gate must additionally REPORT it.
 * @return {object} The merged manifest: `{ ...base, pages, menu }`.
 */
function buildManifest(base, fragments = [], menuLayout = {}, meta = undefined) {
	const merged = { ...base, pages: [...(base.pages || [])], menu: [] }
	mergeMenuItems(merged.menu, base.menu || [])
	// Fragments may also carry page-template instantiations/templates/sets;
	// collect them so a fragment-authored entity scaffold expands too.
	const fragTemplates = []
	const fragInstances = []
	for (const frag of (Array.isArray(fragments) ? fragments : [])) {
		if (frag && Array.isArray(frag.pages)) {
			mergePages(merged.pages, frag.pages)
		}
		if (frag && Array.isArray(frag.menu)) {
			mergeMenuItems(merged.menu, frag.menu)
		}
		if (frag && Array.isArray(frag.pageTemplates)) fragTemplates.push(...frag.pageTemplates)
		if (frag && Array.isArray(frag.pageInstances)) fragInstances.push(...frag.pageInstances)
		if (frag && frag.sets && typeof frag.sets === 'object') {
			merged.sets = { ...(merged.sets || {}), ...frag.sets }
		}
	}
	if (fragTemplates.length) merged.pageTemplates = [...(merged.pageTemplates || []), ...fragTemplates]
	if (fragInstances.length) merged.pageInstances = [...(merged.pageInstances || []), ...fragInstances]
	merged.menu = applyMenuLayout(merged.menu, menuLayout)

	// Entity-scaffold expansion (runtime/boot path). No-op unless the manifest
	// declares pageTemplates + pageInstances — an app without templating gets
	// `merged` back untouched, byte-identical to the pre-expansion builder.
	// Runtime fallback semantics (throwOnError:false): a bad instantiation is
	// skipped rather than blanking the whole app — but its named error is
	// handed to the caller via `meta.expansion.errors`, never swallowed.
	if (Array.isArray(merged.pageTemplates) || Array.isArray(merged.pageInstances)) {
		const result = expandPageTemplates(merged, { throwOnError: false })
		if (meta && typeof meta === 'object') {
			meta.expansion = {
				expandedCount: result.expandedCount,
				errors: result.errors,
				// expandPageTemplates appends the materialised pages AFTER the
				// concrete base pages, so the last expandedCount entries are
				// exactly the expanded ones.
				expandedPages: result.pages.slice(result.pages.length - result.expandedCount),
			}
		}
		return result.manifest
	}
	if (meta && typeof meta === 'object') {
		meta.expansion = { expandedCount: 0, errors: [], expandedPages: [] }
	}
	return merged
}

/**
 * Apply the canonical navigation layout (`relocations` → `removals` →
 * `settingsSection`) to an already-merged menu.
 *
 * @param {Array<object>} menu The merged menu (mutated in place by the steps).
 * @param {object} [menuLayout] `{ relocations?, removals?, settingsSection? }`.
 * @return {Array<object>} The laid-out menu.
 */
function applyMenuLayout(menu, menuLayout = {}) {
	let out = applyMenuRelocations(menu, menuLayout.relocations)
	out = applyMenuRemovals(out, menuLayout.removals)
	out = applySettingsSection(out, menuLayout.settingsSection)
	return out
}

/**
 * Merge an array of incoming menu items into a target array, keyed by `id`.
 * New ids are appended; existing ids are merged in place: the first
 * definition of each listed key wins (the base manifest loads first, so its
 * canonical group definitions take precedence), and `children` are unioned
 * recursively by the same rule.
 *
 * @param {Array<object>} target The accumulated menu (mutated in place).
 * @param {Array<object>} incoming Menu items from a fragment.
 * @return {void}
 */
function mergeMenuItems(target, incoming) {
	incoming.forEach((item) => {
		const existing = target.find((t) => t.id === item.id)
		if (!existing) {
			target.push({ ...item, children: Array.isArray(item.children) ? [...item.children] : item.children })
			return
		}
		for (const key of ['label', 'icon', 'route', 'order', 'section', 'featureFlag', 'permission', 'visibleIf', 'href', 'action']) {
			if (existing[key] === undefined && item[key] !== undefined) {
				existing[key] = item[key]
			}
		}
		if (Array.isArray(item.children) && item.children.length > 0) {
			if (!Array.isArray(existing.children)) {
				existing.children = []
			}
			mergeMenuItems(existing.children, item.children)
		}
	})
}

/**
 * Merge fragment pages onto the accumulated page list by `id` — a later
 * declaration REPLACES an earlier one wholesale.
 *
 * @param {Array<object>} target Accumulated pages (mutated in place).
 * @param {Array<object>} incoming Pages from a fragment.
 * @return {void}
 */
function mergePages(target, incoming) {
	incoming.forEach((page) => {
		const idx = target.findIndex((p) => p.id === page.id)
		if (idx === -1) {
			target.push(page)
		} else {
			target[idx] = page
		}
	})
}

/**
 * Re-home merged menu entries onto the canonical navigation layout declared
 * by `menu-layout.json#relocations` (`{ sourceId: targetGroupId }`).
 * Runs in passes until stable; drops empty group shells left behind.
 *
 * @param {Array<object>} menu The merged menu (mutated in place).
 * @param {Record<string, string>|undefined} relocations Source-id → target-group-id map.
 * @return {Array<object>} The menu with relocations applied.
 */
function applyMenuRelocations(menu, relocations) {
	if (!relocations || typeof relocations !== 'object') return menu
	for (let pass = 0; pass < 5; pass++) {
		const moves = []
		for (let i = menu.length - 1; i >= 0; i--) {
			const node = menu[i]
			const target = relocations[node.id]
			if (target && target !== node.id) {
				menu.splice(i, 1)
				moves.push({ node, target })
				continue
			}
			if (!Array.isArray(node.children)) continue
			for (let j = node.children.length - 1; j >= 0; j--) {
				const child = node.children[j]
				const childTarget = relocations[child.id]
				if (!childTarget) continue
				if (childTarget === node.id && !Array.isArray(child.children)) continue
				node.children.splice(j, 1)
				moves.push({ node: child, target: childTarget })
			}
		}
		if (moves.length === 0) break
		moves.forEach(({ node, target }) => {
			const group = menu.find((m) => m.id === target)
			if (!group) {
				menu.push(node)
				return
			}
			if (!Array.isArray(group.children)) group.children = []
			if (Array.isArray(node.children)) {
				mergeMenuItems(group.children, node.children)
			} else {
				mergeMenuItems(group.children, [node])
			}
		})
	}
	// Drop empty group shells left behind by relocations.
	return menu.filter((m) => m.route || m.href || m.action
		|| (Array.isArray(m.children) && m.children.length > 0))
}

/**
 * Remove individual menu entries by id after relocation — used to retire
 * duplicate navigation entries whose PAGE must stay routable (ADR-044).
 * Only leaf entries are removed; a group is dropped only when left empty
 * and not itself clickable.
 *
 * @param {Array<object>} menu The merged menu.
 * @param {Array<string>|undefined} removals Menu-entry ids to drop.
 * @return {Array<object>} The menu without the removed entries.
 */
function applyMenuRemovals(menu, removals) {
	if (!Array.isArray(removals) || removals.length === 0) return menu
	const drop = new Set(removals)
	const wasGroup = (n) => Array.isArray(n.children) && n.children.length > 0
	const isClickable = (n) => n.route !== undefined || n.href !== undefined || n.action !== undefined
	const prune = (nodes) => nodes.reduce((acc, n) => {
		if (drop.has(n.id) && !wasGroup(n)) return acc
		if (Array.isArray(n.children)) {
			const children = prune(n.children)
			const hadChildren = wasGroup(n)
			if (children.length === 0 && hadChildren && !isClickable(n)) return acc
			acc.push({ ...n, children })
			return acc
		}
		acc.push(n)
		return acc
	}, [])
	return prune(menu)
}

/**
 * Promote the menu entries listed in `menu-layout.json#settingsSection` into
 * Nextcloud's settings foldout: lift each listed id out of wherever it sits,
 * tag it `section: "settings"`, flatten it, append to the top level.
 *
 * @param {Array<object>} menu The merged + relocated + pruned menu.
 * @param {Array<string>|undefined} settingsIds Entry ids to move to the foldout.
 * @return {Array<object>} The menu with the settings entries lifted out.
 */
function applySettingsSection(menu, settingsIds) {
	if (!Array.isArray(settingsIds) || settingsIds.length === 0) return menu
	const want = new Set(settingsIds)
	const isClickable = (n) => n.route !== undefined || n.href !== undefined || n.action !== undefined
	const lifted = []
	const strip = (nodes) => nodes.reduce((acc, n) => {
		if (want.has(n.id)) {
			const { children, ...leaf } = n
			lifted.push({ ...leaf, section: 'settings' })
			return acc
		}
		if (Array.isArray(n.children)) {
			const children = strip(n.children)
			if (children.length === 0 && n.children.length > 0 && !isClickable(n)) return acc
			acc.push({ ...n, children })
			return acc
		}
		acc.push(n)
		return acc
	}, [])
	const remaining = strip(menu)
	return [...remaining, ...lifted]
}

// --- entity-scaffold page-template expansion (vendored port) ----------------
//
// SYNC NOTE — vendored port. Ported FAITHFULLY from @conduction/nextcloud-vue:
//   nextcloud-vue/src/utils/expandPageTemplates.js
// (expandPageTemplates, substitute, substituteString, resolveToken,
//  effectiveParams, declaredParams, instanceLabel, DROP, PLACEHOLDER_RE).
// The lib runs this as buildManifest's FINAL step, so the runtime renderer
// only ever sees concrete pages. Two mechanical deltas from the source, both
// CJS-vendoring artifacts, neither a semantics change:
//   * `import`/`export` became plain functions + module.exports;
//   * `isPlainObject` / `clone` are defined ONCE below and shared with the
//     mergeManifestDelta port (both lib files carry byte-identical copies).
// If the lib's expansion semantics change, update this block AND
// scripts/lib/test_build_effective_manifest.js.
// ---------------------------------------------------------------------------

/**
 * Unique sentinel meaning "drop the containing key" — an exact-match
 * placeholder resolved to an absent OPTIONAL parameter.
 */
const DROP = Symbol('cn-template-drop')

const PLACEHOLDER_RE = /\{\{\s*([^}]+?)\s*\}\}/g

/**
 * Expand a manifest's `pageTemplates[]` + `pageInstances[]` into concrete
 * `pages[]`. Pure: the input manifest is never mutated. See the lib source
 * (nextcloud-vue/src/utils/expandPageTemplates.js) for the full authoring
 * model: `{{param}}` substitution, `{{set:NAME}}` shared sets, and the
 * `override` base+delta merge.
 *
 * @param {object} manifest The manifest (may carry pageTemplates/pageInstances/sets).
 * @param {object} [options] Options.
 * @param {boolean} [options.throwOnError] When true, throw on any named
 *   expansion error (build-time / codemod use). When false (runtime fallback,
 *   and what buildManifest above uses), errors are collected on the returned
 *   `errors` array and the offending instantiation is skipped.
 * @param {boolean} [options.stripTemplates] When true, drop
 *   `pageTemplates` and `sets` from the output as well (build-time ship path).
 * @return {{ manifest: object, pages: object[], expandedCount: number, errors: string[] }}
 *   `manifest` is the new manifest with instantiations materialised into
 *   `pages[]`; `errors` is the (possibly empty) list of named expansion errors.
 */
function expandPageTemplates(manifest, options = {}) {
	const { throwOnError = false, stripTemplates = false } = options
	const errors = []

	const templates = Array.isArray(manifest && manifest.pageTemplates) ? manifest.pageTemplates : null
	const instances = Array.isArray(manifest && manifest.pageInstances) ? manifest.pageInstances : null

	// No-op fast path: nothing to expand → return a shallow clone unchanged.
	if (!templates && !instances) {
		return { manifest: { ...manifest }, pages: Array.isArray(manifest && manifest.pages) ? manifest.pages : [], expandedCount: 0, errors }
	}

	const sets = isPlainObject(manifest.sets) ? manifest.sets : {}
	const templateById = new Map()
	for (const tpl of (templates || [])) {
		if (isPlainObject(tpl) && typeof tpl.id === 'string') templateById.set(tpl.id, tpl)
	}

	const basePages = Array.isArray(manifest.pages) ? manifest.pages.map(clone) : []
	const expandedPages = []

	;(instances || []).forEach((instance, index) => {
		const label = instanceLabel(instance, index)
		if (!isPlainObject(instance)) {
			errors.push(`[expandPageTemplates] pageInstances[${index}]: instantiation must be an object`)
			return
		}
		const ref = instance.templateRef
		const template = templateById.get(ref)
		if (!template) {
			errors.push(`[expandPageTemplates] ${label}: references unknown templateRef "${ref}" — no pageTemplates[] entry declares it`)
			return
		}

		// Effective parameter map: register/schema/label shortcuts, then params
		// (params win on conflict).
		const params = effectiveParams(instance)
		const declared = declaredParams(template)

		// Required-parameter check (named error per missing param).
		let missing = false
		for (const [name, spec] of declared) {
			if (spec.required && !(name in params)) {
				errors.push(`[expandPageTemplates] ${label}: template "${ref}" requires parameter "${name}" but the instantiation did not supply it`)
				missing = true
			}
		}
		if (missing) return

		// Substitute placeholders into the template's page shape.
		const localErrors = []
		const substituted = substitute(clone(template.page), params, declared, sets, sets, localErrors, label)
		if (localErrors.length) {
			errors.push(...localErrors)
			return
		}

		// Optional structural override — reuse the base+delta merge (no second
		// merge model). Template page is the base; the instantiation override is
		// the delta over it (layered-versioned-app-deltas alignment).
		let page = substituted
		if (isPlainObject(instance.override)) {
			page = mergeManifestDelta(substituted, instance.override).manifest
		}

		expandedPages.push(page)
	})

	if (errors.length && throwOnError) {
		throw new Error('Page-template expansion failed:\n' + errors.join('\n'))
	}

	const pages = [...basePages, ...expandedPages]
	const out = { ...manifest, pages }
	delete out.pageInstances
	if (stripTemplates) {
		delete out.pageTemplates
		delete out.sets
	}

	return { manifest: out, pages, expandedCount: expandedPages.length, errors }
}

/**
 * Recursively substitute `{{param}}` / `{{set:NAME}}` placeholders in a value.
 *
 * @param {*} node Value to substitute into.
 * @param {object} params Effective parameter map.
 * @param {Map<string, object>} declared Declared params (name → { required }).
 * @param {object} sets Shared named sets registry.
 * @param {object} _sets (unused alias kept for signature symmetry).
 * @param {string[]} errors Accumulator for named errors.
 * @param {string} label Instantiation label for error messages.
 * @return {*} Substituted value, or the DROP sentinel.
 */
function substitute(node, params, declared, sets, _sets, errors, label) {
	if (typeof node === 'string') {
		return substituteString(node, params, declared, sets, errors, label)
	}
	if (Array.isArray(node)) {
		const out = []
		for (const item of node) {
			const v = substitute(item, params, declared, sets, _sets, errors, label)
			if (v !== DROP) out.push(v)
		}
		return out
	}
	if (isPlainObject(node)) {
		const out = {}
		for (const key of Object.keys(node)) {
			const v = substitute(node[key], params, declared, sets, _sets, errors, label)
			if (v !== DROP) out[key] = v // drop keys whose optional param was absent
		}
		return out
	}
	return node
}

/**
 * Substitute placeholders within a single string.
 *
 * @param {string} str The string value.
 * @param {object} params Effective parameter map.
 * @param {Map<string, object>} declared Declared params.
 * @param {object} sets Shared named sets registry.
 * @param {string[]} errors Accumulator for named errors.
 * @param {string} label Instantiation label.
 * @return {*} Substituted value / typed param value / DROP sentinel.
 */
function substituteString(str, params, declared, sets, errors, label) {
	const exact = str.match(/^\{\{\s*([^}]+?)\s*\}\}$/)
	if (exact) {
		const token = exact[1].trim()
		return resolveToken(token, params, declared, sets, errors, label)
	}
	// Embedded placeholders → string interpolation.
	return str.replace(PLACEHOLDER_RE, (_m, tokenRaw) => {
		const token = tokenRaw.trim()
		const v = resolveToken(token, params, declared, sets, errors, label)
		if (v === DROP || v === undefined || v === null) return ''
		return String(v)
	})
}

/**
 * Resolve a single placeholder token to its value.
 *
 * @param {string} token The inner placeholder text (`register` or `set:NAME`).
 * @param {object} params Effective parameter map.
 * @param {Map<string, object>} declared Declared params.
 * @param {object} sets Shared named sets registry.
 * @param {string[]} errors Accumulator for named errors.
 * @param {string} label Instantiation label.
 * @return {*} Resolved value, or DROP when the parameter is absent.
 */
function resolveToken(token, params, declared, sets, errors, label) {
	if (token.startsWith('set:')) {
		const name = token.slice(4).trim()
		if (!(name in sets)) {
			errors.push(`[expandPageTemplates] ${label}: references unknown set "${name}" — no manifest.sets entry declares it`)
			return DROP
		}
		return clone(sets[name])
	}
	// Plain parameter.
	if (!declared.has(token)) {
		errors.push(`[expandPageTemplates] ${label}: template placeholder "{{${token}}}" is not a declared parameter of the template`)
		return DROP
	}
	if (token in params) {
		return clone(params[token])
	}
	// Absent parameter. Required-absence was already reported; an optional
	// absence drops the containing key on an exact match, or interpolates empty
	// (the caller maps DROP → '' in embedded context).
	return DROP
}

/**
 * Build the effective parameter map from an instantiation.
 * @param {object} instance The instantiation object.
 * @return {object} Parameter map (register/schema/label shortcuts + params).
 */
function effectiveParams(instance) {
	const out = {}
	if (instance.register !== undefined) out.register = instance.register
	if (instance.schema !== undefined) out.schema = instance.schema
	if (instance.label !== undefined) out.label = instance.label
	if (isPlainObject(instance.params)) {
		for (const k of Object.keys(instance.params)) out[k] = instance.params[k]
	}
	return out
}

/**
 * Map declared params name → spec ({ required }).
 * @param {object} template The pageTemplate.
 * @return {Map<string, {required: boolean}>} Declared params by name.
 */
function declaredParams(template) {
	const map = new Map()
	if (Array.isArray(template.params)) {
		for (const p of template.params) {
			if (isPlainObject(p) && typeof p.name === 'string') {
				map.set(p.name, { required: p.required === true })
			}
		}
	}
	return map
}

function instanceLabel(instance, index) {
	const id = isPlainObject(instance) && (instance.id || (isPlainObject(instance.params) && instance.params.id))
	return id ? `pageInstances[${index}] (id "${id}")` : `pageInstances[${index}]`
}

// --- keyed structural delta merge (vendored port) ---------------------------
//
// SYNC NOTE — vendored port. Ported FAITHFULLY from @conduction/nextcloud-vue:
//   nextcloud-vue/src/utils/mergeManifestDelta.js
// (mergeManifestDelta, mergeValue, mergeKeyedArray, applyOrder, stripMarkers,
//  stripOp, KEYED_ARRAYS, DELTA_REMOVE). Used here by expandPageTemplates for
// a pageInstance's optional `override` block — the template page is the BASE
// and the override is a DELTA over it. Same CJS-vendoring deltas as the
// expansion block above (plain functions; shared isPlainObject/clone).
// ---------------------------------------------------------------------------

/**
 * Map of array property name → the field that identifies its entries.
 * Only arrays listed here merge by key; every other array replaces.
 *
 * @type {Readonly<Record<string, string>>}
 */
const KEYED_ARRAYS = Object.freeze({
	pages: 'id',
	widgets: 'id',
	menu: 'id',
	// A menu entry's nested nav children merge by child `id` too, so a delta
	// (or a backend `/api/manifest` override) can add/patch/remove individual
	// children of a group without replacing the whole `children[]` array.
	children: 'id',
})

/** Reserved delta markers — never part of a base manifest. */
const DELTA_REMOVE = 'remove'
const ORDER_KEY = '__order'
const OP_KEY = '$op'

/**
 * Apply a keyed structural delta to a base manifest.
 *
 * @param {object} base The base manifest (bundled manifest or stub).
 * @param {object} delta The delta payload to apply.
 * @return {{ manifest: object, orphanedDeltaPaths: string[] }}
 *   `manifest` is a new merged object (inputs are never mutated);
 *   `orphanedDeltaPaths` lists the paths of delta entries that targeted a
 *   missing base entry and were therefore skipped.
 */
function mergeManifestDelta(base, delta) {
	const orphans = []
	const manifest = mergeValue(base, delta, '', orphans)
	return { manifest, orphanedDeltaPaths: orphans }
}

/**
 * Recursively merge `delta` onto `base` at `path`, collecting orphan paths.
 *
 * @param {*} base Base value.
 * @param {*} delta Delta value (takes precedence).
 * @param {string} path Current JSON-ish path (for orphan reporting).
 * @param {string[]} orphans Accumulator for orphaned delta paths.
 * @return {*} Merged value.
 */
function mergeValue(base, delta, path, orphans) {
	// Delta absent → keep base. Base absent / scalar mismatch → delta wins.
	if (delta === undefined) return clone(base)
	if (!isPlainObject(base) || !isPlainObject(delta)) {
		return clone(delta)
	}

	const out = { ...clone(base) }
	for (const key of Object.keys(delta)) {
		if (key === ORDER_KEY) continue
		const childPath = path ? `${path}/${key}` : key
		const baseChild = base[key]
		const deltaChild = delta[key]

		if (Array.isArray(deltaChild) && Array.isArray(baseChild) && KEYED_ARRAYS[key]) {
			out[key] = mergeKeyedArray(baseChild, deltaChild, KEYED_ARRAYS[key], childPath, orphans)
		} else if (isPlainObject(deltaChild) && isPlainObject(baseChild)) {
			out[key] = mergeValue(baseChild, deltaChild, childPath, orphans)
		} else {
			out[key] = clone(deltaChild)
		}
	}

	// Apply `__order` last so a reorder-only delta (which carries no copy of
	// the array itself) still reorders the base array.
	const orderMap = isPlainObject(delta[ORDER_KEY]) ? delta[ORDER_KEY] : {}
	for (const [arrKey, seq] of Object.entries(orderMap)) {
		if (Array.isArray(seq) && Array.isArray(out[arrKey]) && KEYED_ARRAYS[arrKey]) {
			out[arrKey] = applyOrder(out[arrKey], seq, KEYED_ARRAYS[arrKey])
		}
	}
	return out
}

/**
 * Merge two arrays of keyed entries.
 *
 * @param {object[]} baseArr Base array.
 * @param {object[]} deltaArr Delta array.
 * @param {string} keyField Identity field name (e.g. "id").
 * @param {string} path Current path (for orphan reporting).
 * @param {string[]} orphans Accumulator for orphaned delta paths.
 * @return {object[]} Merged array (ordering, if any, is applied by the caller).
 */
function mergeKeyedArray(baseArr, deltaArr, keyField, path, orphans) {
	// Start from a keyed map of the base entries, preserving order.
	const merged = baseArr.map((entry) => clone(entry))
	const indexByKey = new Map()
	merged.forEach((entry, i) => {
		if (isPlainObject(entry) && entry[keyField] !== undefined) {
			indexByKey.set(entry[keyField], i)
		}
	})

	for (const deltaEntry of deltaArr) {
		if (!isPlainObject(deltaEntry)) continue
		const key = deltaEntry[keyField]
		const op = deltaEntry[OP_KEY]
		const entryPath = `${path}/${key}`

		if (op === DELTA_REMOVE) {
			if (indexByKey.has(key)) {
				merged[indexByKey.get(key)] = undefined // tombstone; compacted below
			} else {
				orphans.push(entryPath)
			}
			continue
		}

		if (indexByKey.has(key)) {
			// Patch an existing entry (recurse so nested widgets[] merge AND a
			// nested __order both apply). Keep __order for the recursion —
			// mergeValue consumes it and never copies it into the output; only
			// $op is meaningless past this point.
			const i = indexByKey.get(key)
			merged[i] = mergeValue(merged[i], stripOp(deltaEntry), entryPath, orphans)
		} else {
			// New key → append as an addition.
			merged.push(clone(stripMarkers(deltaEntry)))
		}
	}

	return merged.filter((e) => e !== undefined)
}

/**
 * Reorder entries to the given key sequence; unlisted entries follow in their
 * original relative order.
 *
 * @param {object[]} entries Merged entries.
 * @param {string[]} order Desired key sequence.
 * @param {string} keyField Identity field name.
 * @return {object[]} Reordered entries.
 */
function applyOrder(entries, order, keyField) {
	const byKey = new Map(entries.map((e) => [e && e[keyField], e]))
	const result = []
	const used = new Set()
	for (const key of order) {
		if (byKey.has(key)) {
			result.push(byKey.get(key))
			used.add(key)
		}
	}
	for (const e of entries) {
		if (!used.has(e && e[keyField])) result.push(e)
	}
	return result
}

/**
 * Strip all delta-only markers from an entry before it lands in the manifest.
 *
 * @param {object} entry A delta array entry, possibly carrying the `$op` and
 *   `__order` markers.
 * @return {object} A shallow copy with both markers removed.
 */
function stripMarkers(entry) {
	const out = { ...entry }
	delete out[OP_KEY]
	delete out[ORDER_KEY]
	return out
}

/**
 * Strip only `$op`, preserving `__order` for a recursive merge to consume.
 *
 * @param {object} entry A delta array entry, possibly carrying the `$op` marker.
 * @return {object} A shallow copy with `$op` removed and `__order` intact.
 */
function stripOp(entry) {
	const out = { ...entry }
	delete out[OP_KEY]
	return out
}

function isPlainObject(value) {
	return value !== null && typeof value === 'object' && !Array.isArray(value)
}

/**
 * Structured clone via JSON (manifests are plain JSON — no cycles/functions).
 * @param {*} value The value to clone.
 * @return {*} A deep clone of the value.
 */
function clone(value) {
	if (value === undefined) return undefined
	if (value === null || typeof value !== 'object') return value
	return JSON.parse(JSON.stringify(value))
}

// --- hydra-side input loading (not part of the lib port) --------------------

/**
 * Load the three assembly inputs from an app repo root. Missing manifest.d/
 * and missing menu-layout.json are absent inputs (empty fragments / empty
 * layout), NOT errors. A missing base manifest or invalid JSON throws an
 * Error carrying `.code` ('ENOBASE' | 'EBADJSON') and the offending path.
 *
 * @param {string} appDir App repo root.
 * @return {{ base: object, fragments: Array<object>, fragmentFiles: Array<string>, menuLayout: object, menuLayoutPath: string|null, basePath: string }}
 */
function loadAppInputs(appDir) {
	const basePath = path.join(appDir, 'src', 'manifest.json')
	if (!fs.existsSync(basePath)) {
		const err = new Error(`base manifest missing at ${basePath}`)
		err.code = 'ENOBASE'
		throw err
	}
	const readJson = (file) => {
		try {
			return JSON.parse(fs.readFileSync(file, 'utf8'))
		} catch (e) {
			const err = new Error(`${file} is not valid JSON (${e.message})`)
			err.code = 'EBADJSON'
			throw err
		}
	}
	const base = readJson(basePath)
	const fragDir = path.join(appDir, 'src', 'manifest.d')
	let fragmentFiles = []
	if (fs.existsSync(fragDir) && fs.statSync(fragDir).isDirectory()) {
		// Ascending filename order — mirrors the lib caller's ctx.keys().sort().
		fragmentFiles = fs.readdirSync(fragDir)
			.filter((f) => f.endsWith('.json'))
			.sort()
			.map((f) => path.join(fragDir, f))
	}
	const fragments = fragmentFiles.map(readJson)
	const menuLayoutPath = path.join(appDir, 'src', 'menu-layout.json')
	let menuLayout = {}
	let hasLayout = false
	if (fs.existsSync(menuLayoutPath)) {
		menuLayout = readJson(menuLayoutPath)
		hasLayout = true
	}
	return {
		base,
		fragments,
		fragmentFiles,
		menuLayout,
		menuLayoutPath: hasLayout ? menuLayoutPath : null,
		basePath,
	}
}

/**
 * Assemble the effective manifest for an app repo root.
 *
 * @param {string} appDir App repo root.
 * @return {{ manifest: object, inputs: object, expansion: { expandedCount: number, errors: string[], expandedPages: object[] } }}
 *   The assembled manifest + the raw inputs + the page-template expansion
 *   report (all-zero/empty for an app that declares no templates).
 */
function assembleFromDir(appDir) {
	const inputs = loadAppInputs(appDir)
	const meta = {}
	const manifest = buildManifest(inputs.base, inputs.fragments, inputs.menuLayout, meta)
	return { manifest, inputs, expansion: meta.expansion }
}

/**
 * True when `<ref>:<relPath>` resolves to a blob or tree in `gitRoot` — used
 * to decide which of the three manifest inputs to hand to `git archive`
 * (see the block comment on `assembleAtRef` for why this cannot be skipped).
 *
 * @param {string} gitRoot Git repository root.
 * @param {string} ref A committish.
 * @param {string} relPath Path relative to `gitRoot`.
 * @return {boolean} True when the path exists at that ref.
 */
function _pathExistsAtRef(gitRoot, ref, relPath) {
	const res = spawnSync('git', ['-C', gitRoot, 'cat-file', '-e', `${ref}:${relPath}`])
	return !res.error && res.status === 0
}

/**
 * Assemble an app's effective manifest as it existed at an arbitrary git
 * ref — the base-ref half of gate-68's ratchet (ADR-097 Decision 5). Reuses
 * `assembleFromDir` for 100% of the merge/discovery logic: this function's
 * only job is to materialize the three manifest inputs (`src/manifest.json`,
 * `src/manifest.d/*.json`, `src/menu-layout.json`) as they existed at `ref`
 * into a throwaway directory, via `git archive`, then hand that directory to
 * `assembleFromDir` unchanged.
 *
 * MEASURED, NOT ASSUMED: `git archive <ref> -- <a> <b> <c>` does NOT silently
 * drop a pathspec that matches nothing at `ref` — it exits 128 with
 * `fatal: pathspec '<b>' did not match any files` and produces NO archive at
 * all, for the whole invocation, even though `<a>` and `<c>` exist. (Verified
 * against the git binary in this environment 2026-08-19 — a single
 * `git archive HEAD -- src/manifest.json src/manifest.d` against a tree with
 * no `manifest.d/` exits 128, not a partial archive.) So EACH of the three
 * candidate paths is checked with `git cat-file -e <ref>:<path>` first, and
 * only the paths that exist are ever passed to `git archive` — the "missing
 * input is absent, not an error" contract this function promises is
 * implemented here, not inside `git archive` itself.
 *
 * @param {string} gitRoot Git repository root (absolute or resolvable from CWD).
 * @param {string} ref A committish (branch, tag, or SHA) to assemble at.
 * @param {string} appRelDir The app's root, relative to `gitRoot` (use '.'
 *   when the app repo root IS the git root).
 * @return {{ manifest: object, inputs: object }} Same shape as `assembleFromDir`.
 * @throws {Error} `.code === 'EBADREF'` when `ref` does not resolve to
 *   anything archivable in `gitRoot`; `.code === 'ENOBASE'` when
 *   `src/manifest.json` itself is absent at `ref` (the app had no manifest
 *   yet at that point in history); a plain Error when `git archive`/`tar`
 *   fail for any other reason (corrupt ref, unreadable repo, `tar`
 *   unavailable).
 */
function assembleAtRef(gitRoot, ref, appRelDir) {
	const dir = appRelDir || '.'
	const manifestRel = path.join(dir, 'src', 'manifest.json')
	const fragDirRel = path.join(dir, 'src', 'manifest.d')
	const layoutRel = path.join(dir, 'src', 'menu-layout.json')

	// `^{tree}` — not `^{commit}` — deliberately. run-hydra-gates.sh remaps a
	// diff-scoped run whose BASE_REF equals HEAD (the mainline-push shape) to
	// git's canonical EMPTY-TREE sha
	// (4b825dc642cb6eb9a060e54bf8d69288fbee4904), so that a base-vs-head
	// ratchet still means something instead of comparing HEAD with itself.
	// That sha is a valid tree-ish (`git archive`/`git cat-file` both accept
	// it) but is NOT a commit — `${ref}^{commit}` rejects it with "expected
	// commit type, but the object dereferences to tree type" (measured
	// 2026-08-19), which would have made every SAME-COMMIT-AS-HEAD run
	// silently fall back to WARN-only instead of correctly ratcheting against
	// "nothing existed before this commit". `^{tree}` accepts both a real
	// commit (peels to its tree) and a bare tree object, and still rejects a
	// genuinely unresolvable ref.
	const refCheck = spawnSync('git', ['-C', gitRoot, 'rev-parse', '--verify', '--quiet', `${ref}^{tree}`])
	if (refCheck.error || refCheck.status !== 0) {
		const err = new Error(`ref '${ref}' does not resolve to a tree in ${gitRoot}`)
		err.code = 'EBADREF'
		throw err
	}

	if (!_pathExistsAtRef(gitRoot, ref, manifestRel)) {
		const err = new Error(`base manifest missing at ${ref}:${manifestRel}`)
		err.code = 'ENOBASE'
		throw err
	}
	const pathspecs = [manifestRel]
	if (_pathExistsAtRef(gitRoot, ref, fragDirRel)) pathspecs.push(fragDirRel)
	if (_pathExistsAtRef(gitRoot, ref, layoutRel)) pathspecs.push(layoutRel)

	const tmpdir = fs.mkdtempSync(path.join(os.tmpdir(), 'hydra-gate68-assemble-'))
	try {
		const archiveRes = spawnSync('git', ['-C', gitRoot, 'archive', ref, '--', ...pathspecs], {
			maxBuffer: 1024 * 1024 * 256,
		})
		if (archiveRes.error || archiveRes.status !== 0) {
			const msg = archiveRes.stderr ? archiveRes.stderr.toString('utf8').trim()
				: (archiveRes.error ? archiveRes.error.message : `git archive exited ${archiveRes.status}`)
			throw new Error(`git archive ${ref} failed: ${msg}`)
		}
		const tarRes = spawnSync('tar', ['-x', '-C', tmpdir], { input: archiveRes.stdout })
		if (tarRes.error || tarRes.status !== 0) {
			const msg = tarRes.stderr ? tarRes.stderr.toString('utf8').trim()
				: (tarRes.error ? tarRes.error.message : `tar exited ${tarRes.status}`)
			throw new Error(`extracting the ${ref} archive failed: ${msg}`)
		}
		return assembleFromDir(path.join(tmpdir, dir))
	} finally {
		fs.rmSync(tmpdir, { recursive: true, force: true })
	}
}

module.exports = {
	buildManifest,
	applyMenuLayout,
	mergeMenuItems,
	mergePages,
	applyMenuRelocations,
	applyMenuRemovals,
	applySettingsSection,
	expandPageTemplates,
	mergeManifestDelta,
	loadAppInputs,
	assembleFromDir,
	assembleAtRef,
}

// --- CLI --------------------------------------------------------------------

function cliMain() {
	let appDir = process.cwd()
	let outFile = null
	let expansionOutFile = null
	const argv = process.argv.slice(2)
	for (let i = 0; i < argv.length; i++) {
		if (argv[i] === '--app-dir' && argv[i + 1]) { appDir = path.resolve(argv[++i]); continue }
		if (argv[i] === '--out' && argv[i + 1]) { outFile = path.resolve(argv[++i]); continue }
		if (argv[i] === '--expansion-out' && argv[i + 1]) { expansionOutFile = path.resolve(argv[++i]); continue }
		console.error(`[build_effective_manifest] unknown argument: ${argv[i]}`)
		process.exit(1)
	}
	let result
	try {
		result = assembleFromDir(appDir)
	} catch (e) {
		if (e.code === 'ENOBASE') {
			console.error(`[build_effective_manifest] ${e.message}`)
			process.exit(2)
		}
		console.error(`[build_effective_manifest] ${e.message}`)
		process.exit(1)
	}
	const { manifest, inputs, expansion } = result
	console.error(`[build_effective_manifest] base=${inputs.basePath} fragments=${inputs.fragmentFiles.length} menu-layout=${inputs.menuLayoutPath ? 'yes' : 'no'}`)
	if (expansion.expandedCount > 0 || expansion.errors.length > 0) {
		// Say what templating did — and NAME every skipped instantiation. The
		// runtime skips a bad instance silently-but-warned; a gate log must
		// carry the same names so a finding can point at them.
		console.error(`[build_effective_manifest] page-templates: expanded ${expansion.expandedCount} instance(s), ${expansion.errors.length} expansion error(s)`)
		for (const err of expansion.errors) {
			console.error(`[build_effective_manifest] expansion error: ${err}`)
		}
	}
	if (expansionOutFile) {
		try {
			fs.writeFileSync(expansionOutFile, JSON.stringify(expansion, null, '\t') + '\n')
		} catch (e) {
			console.error(`[build_effective_manifest] cannot write ${expansionOutFile} (${e.message})`)
			process.exit(1)
		}
	}
	const json = JSON.stringify(manifest, null, '\t') + '\n'
	if (outFile) {
		try {
			fs.writeFileSync(outFile, json)
		} catch (e) {
			console.error(`[build_effective_manifest] cannot write ${outFile} (${e.message})`)
			process.exit(1)
		}
	} else {
		process.stdout.write(json)
	}
	process.exit(0)
}

if (require.main === module) cliMain()
