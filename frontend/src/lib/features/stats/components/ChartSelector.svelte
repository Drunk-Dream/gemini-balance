<script lang="ts">
	import { Combobox } from 'bits-ui';
	import { CaretUpDown, Check } from 'phosphor-svelte';
	import { ALL_CHARTS } from '../constants/chart-options';
	import { chartSelectionStore } from '../stores/chart-store';

	let value = $state<string[]>(getInitialValue());
	let searchValue = $state('');

	const filteredCharts = $derived(
		searchValue === ''
			? ALL_CHARTS
			: ALL_CHARTS.filter((c) => c.label.toLowerCase().includes(searchValue.toLocaleLowerCase()))
	);

	function getInitialValue() {
		const saved =
			typeof localStorage !== 'undefined' ? localStorage.getItem('chartSelection') : null;
		if (saved) {
			return JSON.parse(saved);
		}
		return ALL_CHARTS.map((c) => c.value);
	}

	$effect(() => {
		chartSelectionStore.set(value);
		if (typeof localStorage !== 'undefined') {
			localStorage.setItem('chartSelection', JSON.stringify(value));
		}
	});
</script>

<div class="mb-4 flex items-center gap-4">
	<Combobox.Root
		type="multiple"
		onOpenChangeComplete={(o) => {
			if (!o) searchValue = '';
		}}
	>
		<div class="relative">
			<Combobox.Input
				oninput={(e) => (searchValue = e.currentTarget.value)}
				placeholder="选择图表..."
				class="input w-[250px] pr-8"
			/>
			<Combobox.Trigger class="absolute end-3 top-0 z-10 h-full">
				<CaretUpDown class="size-4" />
			</Combobox.Trigger>
		</div>
		<Combobox.Portal>
			<Combobox.Content
				class="bg-base-100 focus-override border-muted bg-background shadow-popover data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2 outline-hidden z-50 mt-1 h-96 max-h-[var(--bits-combobox-content-available-height)] w-[var(--bits-combobox-anchor-width)] min-w-[var(--bits-combobox-anchor-width)] select-none rounded-xl border px-1 py-3 shadow-lg data-[side=bottom]:translate-y-1 data-[side=left]:-translate-x-1 data-[side=right]:translate-x-1  data-[side=top]:-translate-y-1"
			>
				<Combobox.Viewport class="max-h-60 overflow-y-auto p-1">
					{#each filteredCharts as chart (chart.value)}
						<Combobox.Item
							value={chart.value}
							label={chart.label}
							class="hover:bg-base-200 flex cursor-pointer items-center justify-between p-2"
							onclick={() => {
								if (value.includes(chart.value)) {
									value = value.filter((v) => v !== chart.value);
								} else {
									value = [...value, chart.value];
								}
							}}
						>
							{chart.label}
							<Check
								class={'size-4 ' + (value.includes(chart.value) ? 'opacity-100' : 'opacity-0')}
							/>
						</Combobox.Item>
					{/each}
				</Combobox.Viewport>
			</Combobox.Content>
		</Combobox.Portal>
	</Combobox.Root>
</div>
