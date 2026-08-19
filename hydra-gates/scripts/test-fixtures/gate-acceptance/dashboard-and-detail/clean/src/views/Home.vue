<template>
	<CnDashboardPage page-id="home">
		<template #widget-kpis>
			<CnStatsBlock :items="kpis" />
		</template>
		<template #widget-recent>
			<CnStatsBlock :items="recent" />
		</template>
	</CnDashboardPage>
</template>

<script>
export default {
	name: 'Home',
	data() {
		return { kpis: [], recent: [] }
	},
}
</script>
