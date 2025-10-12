<script lang="ts">
	import ArrowClockwise from 'phosphor-svelte/lib/ArrowClockwise';
	import type { Snippet } from 'svelte';
	import { twMerge } from 'tailwind-merge';

	let {
		className,
		header,
		children,
		onRefresh
	}: { className?: string; header?: Snippet; children?: Snippet; onRefresh?: () => void } =
		$props();
</script>

<div class={twMerge('card bg-base-100 shadow-base-content/20 shadow-md', className)}>
	<div class="card-body">
		{#if header}
			<h2 class="card-title mb-4 flex-row items-center justify-between">
				<div class="flex flex-col">
					{@render header()}
				</div>
				{#if onRefresh}
					<button class="btn btn-ghost btn-sm" onclick={onRefresh}>
						<ArrowClockwise size={20} />
					</button>
				{/if}
			</h2>
		{/if}
		<div class="relative h-64 sm:h-80 md:h-96">
			{#if children}
				{@render children()}
			{/if}
		</div>
	</div>
</div>
