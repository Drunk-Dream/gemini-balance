<script lang="ts">
	import { UsageStatsUnit } from '$lib/features/stats/types';
	import { ToggleGroup } from 'bits-ui';

	let {
		currentUnit = $bindable(),
		disabled = false
	}: { currentUnit: UsageStatsUnit; disabled?: boolean } = $props();
</script>

<ToggleGroup.Root type="single" bind:value={currentUnit} class="flex" {disabled}>
	<ToggleGroup.Item
		aria-label="toggle day"
		value={UsageStatsUnit.DAY}
		class="btn btn-sm data-[state=off]:btn-ghost data-[state=on]:btn-primary data-[state=on]:btn-active"
	>
		日
	</ToggleGroup.Item>
	<ToggleGroup.Item
		aria-label="toggle week"
		value={UsageStatsUnit.WEEK}
		class="btn btn-sm data-[state=off]:btn-ghost data-[state=on]:btn-primary data-[state=on]:btn-active"
	>
		周
	</ToggleGroup.Item>
	<ToggleGroup.Item
		aria-label="toggle month"
		value={UsageStatsUnit.MONTH}
		class="btn btn-sm data-[state=off]:btn-ghost data-[state=on]:btn-primary data-[state=on]:btn-active"
	>
		月
	</ToggleGroup.Item>
</ToggleGroup.Root>
