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

<div class={twMerge('card bg-base-100 shadow-base-content/20 shadow-md', className)}>
	<div class="card-body">
		{#if header}
			<h2 class="card-title mb-4 flex-col">
				{@render header()}
			</h2>
		{/if}
		<div class="relative h-64 sm:h-80 md:h-96">
			{#if children}
				{@render children()}
			{/if}
		</div>
	</div>
</div>
