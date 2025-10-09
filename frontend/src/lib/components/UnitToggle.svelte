<script lang="ts">
	import { UsageStatsUnit } from '$lib/features/stats/service';
	import { ToggleGroup } from 'bits-ui';

	let { currentUnit = $bindable() } = $props();
</script>

<ToggleGroup.Root type="single" bind:value={currentUnit} class="flex space-x-2">
	<ToggleGroup.Item
		aria-label="toggle day"
		value={UsageStatsUnit.DAY}
		class="btn {currentUnit === UsageStatsUnit.DAY ? 'btn-primary btn-active' : 'btn-ghost'}"
	>
		日
	</ToggleGroup.Item>
	<ToggleGroup.Item
		aria-label="toggle week"
		value={UsageStatsUnit.WEEK}
		class="btn {currentUnit === UsageStatsUnit.WEEK ? 'btn-primary btn-active' : 'btn-ghost'}"
	>
		周
	</ToggleGroup.Item>
	<ToggleGroup.Item
		aria-label="toggle month"
		value={UsageStatsUnit.MONTH}
		class="btn {currentUnit === UsageStatsUnit.MONTH ? 'btn-primary btn-active' : 'btn-ghost'}"
	>
		月
	</ToggleGroup.Item>
</ToggleGroup.Root>
