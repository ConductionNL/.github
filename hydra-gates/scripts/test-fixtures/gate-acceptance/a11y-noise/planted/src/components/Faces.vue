<template>
	<div>
		<!-- The three the OLD rule already caught, kept in their own file so a
		     repair cannot trade them for the camelCase ones. -->
		<img :src="user.avatar" alt="">
		<img :src="user.photo" alt="">
		<img :src="user.thumbnail" alt="">

		<!-- Both quote styles, and a literal src in place of a bound one. -->
		<img src='/img/headshot.png' alt=''>
	</div>
</template>
