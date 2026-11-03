<!--
  SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
  SPDX-License-Identifier: EUPL-1.2
-->
<template>
	<div>
		<input :value="value" @input="(v) => update(v)">
		<button @click="() => reset()">
			Reset
		</button>
	</div>
</template>

<script>
export default {
	name: 'ArrowHandler',
	methods: {
		update(v) {
			if (v === null) {
				return
			}
			this.value = v
		},
		reset() {
			this.value = null
		},
	},
}
</script>
