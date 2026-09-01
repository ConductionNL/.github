<template>
	<CnDashboardPage
		:title="t('dprfx', 'Dashboard')"
		:refreshing="loading"
		@refresh="loadDashboardData">
		<template #actions>
			<!-- Refresh is NOT repeated here. The removed markup was
			     <NcButton :aria-label="t('dprfx', 'Refresh')"><Refresh :size="20" /></NcButton>
			     and @refresh above routes the menu item to loadDashboardData. -->
			<NcButton variant="primary" @click="create">
				<template #icon>
					<Plus :size="20" />
				</template>
				{{ t('dprfx', 'New thing') }}
			</NcButton>
		</template>
	</CnDashboardPage>
</template>
