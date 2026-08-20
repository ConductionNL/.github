<template>
	<CnIndexPage :register="'demo'" :schema="'widget'" />
</template>
<script>
import { CnIndexPage } from '@conduction/nextcloud-vue'

export default { name: 'WidgetsIndex', components: { CnIndexPage } }
</script>
