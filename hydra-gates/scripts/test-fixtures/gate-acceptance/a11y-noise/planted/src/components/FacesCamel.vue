<template>
	<div>
		<!-- ONLY the forms the `\b`-anchored noun list could NOT see. This
		     file is named as gate-35's subject in expect.conf precisely so a
		     regression to `\b` drops it out of the log: the OTHER planted file
		     would still fire, so the verdict alone would not notice. -->
		<img :src="user.avatarUrl" alt="">
		<img :src="user.thumbnailUrl" alt="">
		<img :src="user.photoUrl" alt="">
		<img :src="user.pictureUrl" alt="">
		<img :src="user.avatar_url" alt="">
	</div>
</template>
