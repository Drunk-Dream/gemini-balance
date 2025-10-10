<script lang="ts">
	import Container from '$lib/components/Container.svelte';
	import { navLinks } from '$lib/layout/navLinks';
</script>

<Container header="欢迎使用 Gemini Balance">
	<p class="text-base-content/50 mb-12 text-center text-lg italic">
		一个高效、安全的 API 请求转发服务
	</p>
	<div class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
		{#each navLinks as link}
			<a
				href={link.href}
				class="border-base-300 bg-base-200 group block transform rounded-lg border p-6 shadow-sm transition-all duration-300 ease-in-out hover:-translate-y-1 hover:shadow-xl"
			>
				<h2 class="text-base-content mb-2 text-2xl font-bold group-hover:text-blue-600">
					{link.name}
				</h2>
				<p class="text-base-content/60">{link.description}</p>
			</a>
		{/each}
	</div>
</Container>
