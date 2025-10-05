<script lang="ts">
	import { Collapsible, type WithoutChild } from 'bits-ui';
	import CaretUpDown from 'phosphor-svelte/lib/CaretUpDown';

	let {
		open = $bindable(false),
		ref = $bindable(null),
		buttonText,
		children,
		...restProps
	}: WithoutChild<Collapsible.RootProps> & {
		buttonText: string;
	} = $props();
</script>

<Collapsible.Root bind:open bind:ref {...restProps}>
	<Collapsible.Trigger
		class="mb-3 inline-flex h-10 items-center justify-center space-x-2 rounded-md border border-gray-300 bg-white p-2 text-gray-700 shadow-sm transition-all hover:bg-gray-50 active:scale-[0.98]"
		aria-label="Toggle filters"
	>
		<p class="text-lg font-medium">{buttonText}</p>
		<CaretUpDown class="size-4" weight="bold" />
	</Collapsible.Trigger>
	<Collapsible.Content
		hiddenUntilFound
		class="data-[state=open]:animate-collapsible-down data-[state=closed]:animate-collapsible-up space-y-2 overflow-hidden"
	>
		{@render children?.()}
	</Collapsible.Content>
</Collapsible.Root>
