<script lang="ts">
	import { UsageStatsUnit } from '$lib/features/stats/service';

	let {
		num_periods = $bindable(),
		min = 7,
		disabled = false,
		currentUnit
	}: {
		num_periods: number;
		min?: number;
		disabled?: boolean;
		currentUnit: UsageStatsUnit;
	} = $props();

	let max = $derived.by(() => {
		return currentUnit === UsageStatsUnit.DAY ? 90 : currentUnit === UsageStatsUnit.WEEK ? 52 : 24;
	});
</script>

<div class="mt-4 flex w-full items-center justify-center gap-2">
	<label for="num_periods_slider" class="text-sm font-medium">显示周期数: {num_periods}</label>
	<input
		id="num_periods_slider"
		type="range"
		{min}
		{max}
		bind:value={num_periods}
		class="range range-primary w-48"
		{disabled}
	/>
</div>
