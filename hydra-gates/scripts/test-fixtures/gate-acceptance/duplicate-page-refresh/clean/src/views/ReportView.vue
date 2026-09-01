<template>
	<CnDetailPage :title="t('dprfx', 'Report')" :showRefresh="false">
		<template #header-actions>
			<NcButton :aria-label="t('dprfx', 'Refresh report')" @click="load">
				<template #icon>
					<Refresh :size="20" />
				</template>
				{{ t('dprfx', 'Refresh') }}
			</NcButton>
		</template>
	</CnDetailPage>
</template>
