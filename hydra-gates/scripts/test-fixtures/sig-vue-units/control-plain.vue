<!--
  SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
  SPDX-License-Identifier: EUPL-1.2
-->
<template>
	<div>{{ label }}</div>
</template>

<script>
export default {
	name: 'ControlPlain',
	methods: {
		label(a, b) {
			if (a) {
				return b
			}
			return a
		},
		reset() {
			this.value = null
		},
	},
}
</script>
