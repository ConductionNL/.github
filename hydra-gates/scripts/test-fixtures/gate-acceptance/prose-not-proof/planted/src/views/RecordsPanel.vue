<template>
	<div class="records-panel">
		<h2>Records</h2>
		<ul><li v-for="r in records" :key="r.id">{{ r.title }}</li></ul>
	</div>
</template>
<script>
export default { name: 'RecordsPanel', data() { return { records: [] } } }
</script>
