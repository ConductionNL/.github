<!-- SPDX-License-Identifier: EUPL-1.2 -->
<!-- SPDX-FileCopyrightText: 2026 Conduction B.V. -->
<!--
  Fixture for gate-16 arm 5 (.github#435). This is the file BEFORE
  `@nextcloud/prettier-config` is adopted. `ReflowedView.vue.prettier` is the
  same program after the reformat, and `.prettier-changed` is that reformat with
  ONE character of `totalWeights` different.

  Neither method carries an `@spec` tag, both are in `src/`, both have bodies of
  more than two lines and neither is named like an accessor — so both ARE
  subject matter gate-16 would report if it thought they had changed.
-->
<template>
	<div class="reflowed">
		<span class="reflowed__title">{{ row.title || t('app', '(no title)') }}</span>
		<span class="reflowed__total">{{ totalWeights(rows) }}</span>
	</div>
</template>

<script>
import { CnAppRoot, CnObjectSidebar, builtinIntegrations } from '@conduction/nextcloud-vue'

export default {
	name: 'ReflowedView',

	components: { CnAppRoot, CnObjectSidebar },

	data() {
		return { rows: [], row: {}, integrations: builtinIntegrations }
	},

	methods: {
		/**
		 * Sum the weights of every row.
		 *
		 * @param {Array} rows The rows to total.
		 * @return {number}
		 */
		totalWeights(rows) {
			const weights = rows.map(r => r.weight || 0)
			return weights.reduce((carry, w) => carry + w, 0)
		},

		/**
		 * Build the label for one row.
		 *
		 * @param {object} row The row to label.
		 * @return {string}
		 */
		buildLabel(row) {
			const parts = [row.code, row.name]
			return parts.filter(p => !!p).join(' - ')
		},

		/**
		 * True when the row may still be edited.
		 *
		 * @param {object} row The row to test.
		 * @return {boolean}
		 */
		mayEdit(row) {
			return row.status !== 'settled' && row.lockedAt === null && !this.busy
		},

		/**
		 * Persist one row.
		 *
		 * @param {object} row The row to persist.
		 * @return {Promise<void>}
		 */
		async persistRow(row) {
			await this.client.put(this.buildUrl(`/api/rows/${row.id}`), row)
		},
	},
}
</script>
