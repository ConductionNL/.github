<template>
	<div>
		<!-- THE ANTI-WIDENING ARM for the named-by-context exemption. The
		     image IS inside an `<a>`, but the anchor carries no other content,
		     so the image is the link's ONLY possible accessible name and the
		     empty alt leaves the link nameless. An exemption keyed on "is
		     inside a link" rather than "the link also has text" would let this
		     through, which is exactly the widening this file exists to catch. -->
		<a :href="user.profile"><img :src="user.avatarUrl" alt=""></a>
	</div>
</template>
