<script lang="ts">
	import { UsageStatsUnit } from '$lib/features/stats/types';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';

	let {
		currentUnit = $bindable(),
		disabled = false
	}: { currentUnit: UsageStatsUnit; disabled?: boolean } = $props();
</script>

<ToggleGroup.Root type="single" bind:value={currentUnit} class="flex" {disabled}>
	<ToggleGroup.Item aria-label="toggle day" value={UsageStatsUnit.DAY} class="h-8 px-3 text-xs">
		日
	</ToggleGroup.Item>
	<ToggleGroup.Item aria-label="toggle week" value={UsageStatsUnit.WEEK} class="h-8 px-3 text-xs">
		周
	</ToggleGroup.Item>
	<ToggleGroup.Item aria-label="toggle month" value={UsageStatsUnit.MONTH} class="h-8 px-3 text-xs">
		月
	</ToggleGroup.Item>
</ToggleGroup.Root>
