<script lang="ts">
	import type { Snippet } from 'svelte';
	import { twMerge } from 'tailwind-merge';

	let { className, header, children }: { className?: string; header?: string; children: Snippet } =
		$props();
</script>

<div class={twMerge('sm:p6 container mx-auto p-4 lg:p-8', className)}>
	{#if header}
		<h1 class="mb-6 text-3xl font-bold">{header}</h1>
	{/if}

	{@render children()}
</div>
