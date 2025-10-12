<script lang="ts">
	import { UsageStatsUnit } from '$lib/features/stats/service';
	import { fade } from 'svelte/transition';

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

	let isDragging = $state(false);
	let isHovering = $state(false);

	let isTooltipVisible = $derived.by(() => isDragging || isHovering);

	let tooltipStyle = $derived.by(() => {
		const range = max - min;
		// 防止除以零
		const percentage = range === 0 ? 0 : (num_periods - min) / range;

		// 根据 daisyUI 样式定义
		const trackWidthRem = 12; // from w-48
		const thumbWidthRem = 1.5; // approx. thumb width

		const travelDistance = trackWidthRem - thumbWidthRem;
		const thumbCenterPosition = percentage * travelDistance + thumbWidthRem / 2;

		// 使用 transform: translateX(-50%) 来让气泡自身居中
		return `left: ${thumbCenterPosition}rem; transform: translateX(-50%);`;
	});
</script>

<div class="relative flex w-48 flex-col items-center gap-2">
	<!-- <label for="num_periods_slider" class="text-sm font-medium">periods:{num_periods}</label> -->
	<input
		type="range"
		{min}
		{max}
		bind:value={num_periods}
		class="range range-primary w-48"
		{disabled}
		onpointermove={(event: PointerEvent) => event.stopPropagation()}
		onpointerenter={() => (isHovering = true)}
		onpointerleave={() => (isHovering = false)}
		onpointerdown={() => (isDragging = true)}
		onpointerup={() => (isDragging = false)}
	/>
	{#if isTooltipVisible}
		<div
			class="bg-primary/80 text-primary-content border-base-content/10 pointer-events-none absolute -top-8 z-10 rounded border px-2 py-1 text-xs shadow-lg backdrop-blur-sm"
			style={tooltipStyle}
			transition:fade
		>
			{num_periods}
		</div>
	{/if}
</div>
