<template>
	<CnDashboardPage page-id="home">
		<template #widget-kpis>
			<CnDashboardPage page-id="kpis-inner" />
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
		return { recent: [] }
	},
}
</script>
