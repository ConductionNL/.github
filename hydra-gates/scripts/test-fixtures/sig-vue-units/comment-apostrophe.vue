<!--
  SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
  SPDX-License-Identifier: EUPL-1.2
-->
<template>
	<div>
		<!-- the user's own list -->
		<span>{{ count }}</span>
	</div>
</template>

<script>
export default {
	name: 'CommentApostrophe',
	methods: {
		count(items) {
			if (!items) {
				return 0
			}
			return items.length
		},
		clear() {
			this.items = []
		},
	},
}
</script>
