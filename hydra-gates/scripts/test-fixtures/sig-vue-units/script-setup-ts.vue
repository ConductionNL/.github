<!--
  SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
  SPDX-License-Identifier: EUPL-1.2
-->
<template>
	<ul>
		<li v-for="row in rows" :key="row.id" @click="(e) => pick(row, e)">
			{{ row.title }}
		</li>
	</ul>
</template>

<script lang="ts">
export function shared(a: number, b: number): number {
	return a + b
}
</script>

<script setup lang="ts">
import { ref } from 'vue'

const rows = ref<Array<{ id: number, title: string }>>([])

function pick(row: { id: number }, event: Event): void {
	if (event.defaultPrevented) {
		return
	}
	rows.value = rows.value.filter((r) => r.id !== row.id)
}
</script>

<style scoped>
li > span { color: var(--color-main-text); }
</style>
