<script lang="ts">
	import { cn } from '$lib/lib/utils';
	import ArrowClockwise from 'phosphor-svelte/lib/ArrowClockwise';
	import type { Snippet } from 'svelte';
	import { twMerge } from 'tailwind-merge';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';

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

<Card.Root class={cn('shadow-lg', className)}>
	<Card.Content class="p-6">
		{#if header}
			<div class="mb-4 flex flex-row items-center justify-between">
				<div class="flex flex-col">
					{@render header()}
				</div>
				{#if onRefresh}
					<Button variant="ghost" size="icon" onclick={onRefresh}>
						<ArrowClockwise size={20} />
					</Button>
				{/if}
			</div>
		{/if}
		<div class={twMerge('relative', heightClass)}>
			{#if children}
				{@render children()}
			{/if}
		</div>
	</Card.Content>
</Card.Root>
