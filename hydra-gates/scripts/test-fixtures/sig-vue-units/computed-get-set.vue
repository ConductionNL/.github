<!--
  SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
  SPDX-License-Identifier: EUPL-1.2
-->
<template>
	<input v-model="proxy">
</template>

<script>
export default {
	name: 'ComputedGetSet',
	computed: {
		proxy: {
			get() {
				return this.value
			},
			set(v) {
				if (v === this.value) {
					return
				}
				this.$emit('input', v)
			},
		},
	},
	methods: {
		after(a) {
			return a ? 1 : 2
		},
	},
}
</script>
