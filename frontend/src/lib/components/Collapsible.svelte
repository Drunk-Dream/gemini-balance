<script lang="ts">
	import * as Collapsible from '$lib/components/ui/collapsible';
	import CaretUpDown from 'phosphor-svelte/lib/CaretUpDown';
	import { Collapsible as CollapsiblePrimitive, type WithoutChild } from 'bits-ui';

	let {
		open = $bindable(false),
		ref = $bindable(null),
		buttonText,
		children,
		...restProps
	}: WithoutChild<CollapsiblePrimitive.RootProps> & {
		buttonText: string;
	} = $props();
</script>

<Collapsible.Root bind:open bind:ref {...restProps}>
	<Collapsible.Trigger
		class="border-border bg-background text-foreground hover:bg-muted mb-3 inline-flex h-10 items-center justify-center space-x-2 rounded-md border p-2 shadow-sm transition-all active:scale-[0.98]"
		aria-label="Toggle filters"
	>
		<p class="text-lg font-medium">{buttonText}</p>
		<CaretUpDown class="size-4" weight="bold" />
	</Collapsible.Trigger>
	<Collapsible.Content class="space-y-2 overflow-hidden">
		{@render children?.()}
	</Collapsible.Content>
</Collapsible.Root>
