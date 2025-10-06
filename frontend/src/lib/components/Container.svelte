<script lang="ts">
	import type { Snippet } from 'svelte';

	let { header, children }: { header?: string; children: Snippet } = $props();
</script>

<div class="sm:p6 container mx-auto p-4 lg:p-8">
	{#if header}
		<h1 class="mb-6 text-3xl font-bold text-gray-900">{header}</h1>
	{/if}

	{@render children()}
</div>
