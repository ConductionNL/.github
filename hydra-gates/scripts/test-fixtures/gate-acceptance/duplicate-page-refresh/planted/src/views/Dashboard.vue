<template>
	<CnDashboardPage :title="t('dprfx', 'Dashboard')">
		<template #actions>
			<NcButton variant="primary" @click="create">
				<template #icon>
					<Plus :size="20" />
				</template>
				{{ t('dprfx', 'New thing') }}
			</NcButton>
			<NcButton
				:aria-label="t('dprfx', 'Refresh dashboard')"
				@click="loadDashboardData">
				<template #icon>
					<Refresh :size="20" />
				</template>
			</NcButton>
		</template>
	</CnDashboardPage>
</template>
