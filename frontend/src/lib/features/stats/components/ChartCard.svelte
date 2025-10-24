<script lang="ts">
	import { cn } from '$lib/lib/utils';
	import ArrowClockwise from 'phosphor-svelte/lib/ArrowClockwise';
	import type { Snippet } from 'svelte';
	import { twMerge } from 'tailwind-merge';

	let {
		className,
		header,
		children,
		onRefresh,
		heightClass = 'h-80 lg:h-96'
	}: {
		className?: string;
		header?: Snippet;
		children?: Snippet;
		onRefresh?: () => void;
		heightClass?: string;
	} = $props();
</script>

<div class={cn('card bg-card text-card-foreground border shadow-lg', className)}>
	<div class="card-body">
		{#if header}
			<h2 class="card-title mb-4 flex-row items-center justify-between">
				<div class="flex flex-col">
					{@render header()}
				</div>
				{#if onRefresh}
					<button class="btn btn-ghost btn-circle" onclick={onRefresh}>
						<ArrowClockwise size={20} />
					</button>
				{/if}
			</h2>
		{/if}
		<div class={twMerge('relative', heightClass)}>
			{#if children}
				{@render children()}
			{/if}
		</div>
	</div>
</div>
