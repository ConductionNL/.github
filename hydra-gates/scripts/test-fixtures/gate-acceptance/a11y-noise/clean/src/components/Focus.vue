<template>
	<div>
		<!-- gate-36 NEAR-MISS: a comment documenting the rule. Reported as a
		     violation of it before 2026-08-12, which is the #236 shape — the
		     better a team documents its focus order, the redder its repo. -->
		<!-- never write tabindex="5"; positive values pull the element out of
		     natural document order -->
		<button tabindex="0">in natural order</button>
		<div tabindex="-1">programmatically focusable only</div>
		<span :tabindex="computedIndex">bound values are reviewer judgement</span>
	</div>
</template>

<script>
// A JS comment mentioning tabindex="9" is prose too, and lives in the SFC
// block markup_mask would have blanked wholesale. This gate masks COMMENTS
// only, so `<script>` stays in scope and this line still has to be exempted
// on its own merits rather than by being in the wrong block.
export default {
	name: 'Focus',
	computed: {
		computedIndex() {
			return 0
		},
	},
}
</script>
