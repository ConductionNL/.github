<!--
  SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
  SPDX-License-Identifier: EUPL-1.2

  Shows the case's "status" badge, see `StatusBadge`.
-->
<template>
	<span>{{ status }}</span>
</template>

<script>
export default {
	name: 'HeaderApostrophe',
	methods: {
		status(item) {
			if (item.closed) {
				return 'closed'
			}
			return 'open'
		},
		refresh() {
			this.$emit('refresh')
		},
	},
}
</script>
