<template>
	<div>
		<!-- A real text alternative on a semantic src is the CORRECT code
		     gate-35 exists to steer people toward. -->
		<img :src="user.avatarUrl" :alt="t('app', 'Profile picture of {name}', { name: user.name })">

		<!-- Decorative BY NAME: neither token is a content noun, so an empty
		     alt is honest here. `uploadIcon` is docudesk's live shape and is
		     the only `alt=""` anywhere in the fleet. -->
		<img :src="uploadIcon" alt="" class="upload-icon">

		<!-- Decorative BY SHAPE: a static asset path. -->
		<img src="/img/decoration.svg" alt="">

		<!-- THE ANTI-WIDENING ARM. A substring matcher taught to see
		     `avatarUrl` would also fire on these. The rule asks for token
		     EQUALITY after camelCase/underscore splitting, so `photographer`
		     is not `photo` and `pictures` is not `picture`. -->
		<img :src="user.photographerBio" alt="">
		<img :src="gallery.pictures" alt="">
		<img :src="thumbnails" alt="">
	</div>
</template>
