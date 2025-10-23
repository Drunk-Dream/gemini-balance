<script lang="ts">
	import ArrowClockwise from 'phosphor-svelte/lib/ArrowClockwise';
	import type { Snippet } from 'svelte';
	import { twMerge } from 'tailwind-merge';
	import { cn } from "$lib/lib/utils";

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

<div class={cn('bg-card text-card-foreground shadow-lg border', className)}>
	<div class="card-body">
		{#if header}
			<h2 class="card-title mb-4 flex-row items-center justify-between">
				<div class="flex flex-col">
					{@render header()}
				</div>
				{#if onRefresh}
					<button class="btn btn-ghost" onclick={onRefresh}>
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
