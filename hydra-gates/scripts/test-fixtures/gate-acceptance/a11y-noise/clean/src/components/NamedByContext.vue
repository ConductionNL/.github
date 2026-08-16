<template>
	<div>
		<!-- NAMED BY CONTEXT (WCAG H67). The link's accessible name comes from
		     the heading beside the image, so the empty alt is the CORRECT
		     answer: giving this image its own alt would make a screen reader
		     announce the headline twice. The noun test still fires on
		     `thumbnailUrl` — the markup around it is what clears it. -->
		<a :href="item.link">
			<img :src="item.thumbnailUrl" alt="">
			<h4>{{ item.title }}</h4>
		</a>

		<!-- Same rule, `<figure>` + `<figcaption>`. -->
		<figure>
			<img :src="user.photoUrl" alt="">
			<figcaption>{{ user.name }}</figcaption>
		</figure>

		<!-- Same rule, a button labelled by its own text. -->
		<button @click="open">
			<img :src="user.avatarUrl" alt="">
			<span>Open profile</span>
		</button>

		<!-- Static text counts too — it need not be an interpolation. -->
		<a href="/team">
			<img :src="member.headshotUrl" alt="">
			Meet the team
		</a>
	</div>
</template>
