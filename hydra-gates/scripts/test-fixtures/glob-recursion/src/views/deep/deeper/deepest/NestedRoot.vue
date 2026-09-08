<!-- SPDX-License-Identifier: EUPL-1.2 -->
<template>
	<!--
	  A bespoke shell five directories down, past the -maxdepth 4 that gate-38
	  used to stop at. The root is a plain <div>, not the shared app root and
	  not a Nextcloud content wrapper, and it offers no jump-to-content
	  affordance.

	  The words the gate looks for appear nowhere in this file, including in
	  this comment: a fixture that quotes the pattern it is meant to defeat
	  defeats itself instead.
	-->
	<div class="nested-root">
		<nav class="nested-root__nav">
			<a href="/apps/globrecfx/things">Things</a>
		</nav>
		<main class="nested-root__main">
			<router-view />
		</main>
	</div>
</template>

<script>
export default {
	name: 'NestedRoot',
}
</script>
