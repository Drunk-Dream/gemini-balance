<script lang="ts">
	import type { Snippet } from 'svelte';
	import { twMerge } from 'tailwind-merge';

	// let className: string = '';
	// export { className as class };
	let {
		className,
		header,
		children
	}: { className?: string; header?: Snippet; children?: Snippet } = $props();
</script>

<div class={twMerge('rounded-lg bg-base-200 shadow-base-300 p-4 shadow-md sm:p-6 md:p-8', className)}>
	{#if header}
		<div class="mb-4">
			{@render header()}
		</div>
	{/if}
	<div class="relative h-64 sm:h-80 md:h-96">
		{#if children}
			{@render children()}
		{/if}
	</div>
</div>
