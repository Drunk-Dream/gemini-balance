<script lang="ts">
	import Check from 'phosphor-svelte/lib/Check';
	import CaretUpDown from 'phosphor-svelte/lib/CaretUpDown';
	import { ALL_CHARTS } from '../constants/chart-options';
	import { chartSelectionStore } from '../stores/chart-store';
	import * as Command from '$lib/components/ui/command';
	import * as Popover from '$lib/components/ui/popover';
	import { Button } from '$lib/components/ui/button';
	import { cn } from '$lib/lib/utils';

	let value = $state<string[]>(getInitialValue());
	let open = $state(false);

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

	function toggleValue(currentValue: string) {
		if (value.includes(currentValue)) {
			value = value.filter((v) => v !== currentValue);
		} else {
			value = [...value, currentValue];
		}
	}
</script>

<div class="mb-4 flex items-center gap-4">
	<Popover.Root bind:open>
		<Popover.Trigger>
			{#snippet child({ props })}
				<Button
					variant="outline"
					role="combobox"
					aria-expanded={open}
					class="w-[250px] justify-between"
					{...props}
				>
					{value.length > 0 ? `已选择 ${value.length} 项` : '选择图表...'}
					<CaretUpDown class="ml-2 size-4 shrink-0 opacity-50" />
				</Button>
			{/snippet}
		</Popover.Trigger>
		<Popover.Content class="w-[250px] p-0">
			<Command.Root>
				<Command.Input placeholder="搜索图表..." />
				<Command.List>
					<Command.Empty>未找到图表。</Command.Empty>
					<Command.Group>
						{#each ALL_CHARTS as chart}
							<Command.Item
								value={chart.label}
								onSelect={() => {
									toggleValue(chart.value);
								}}
							>
								<Check
									class={cn(
										'mr-2 size-4',
										value.includes(chart.value) ? 'opacity-100' : 'opacity-0'
									)}
								/>
								{chart.label}
							</Command.Item>
						{/each}
					</Command.Group>
				</Command.List>
			</Command.Root>
		</Popover.Content>
	</Popover.Root>
</div>
