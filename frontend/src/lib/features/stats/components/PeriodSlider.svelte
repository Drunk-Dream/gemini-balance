<script lang="ts">
	import MagnifyingGlassMinus from 'phosphor-svelte/lib/MagnifyingGlassMinus';
	import MagnifyingGlassPlus from 'phosphor-svelte/lib/MagnifyingGlassPlus';
	import { fade } from 'svelte/transition';

	let {
		value = $bindable(),
		min = 7,
		max = 90, // max 作为可自定义参数，默认 90 天
		disabled = false
	}: {
		value: number;
		min?: number;
		max?: number; // 添加 max 到类型定义
		disabled?: boolean;
	} = $props();

	let isDragging = $state(false);
	let isHovering = $state(false);

	let isTooltipVisible = $derived.by(() => isDragging || isHovering);

	let tooltipStyle = $derived.by(() => {
		const range = max - min;
		// 防止除以零
		const percentage = range === 0 ? 0 : (value - min) / range;

		// 根据 daisyUI 样式定义
		const trackWidthRem = 12; // from w-48
		const thumbWidthRem = 1.5; // approx. thumb width

		const travelDistance = trackWidthRem - thumbWidthRem;
		const thumbCenterPosition = percentage * travelDistance + thumbWidthRem / 2;

		// 使用 transform: translateX(-50%) 来让气泡自身居中
		return `left: ${thumbCenterPosition}rem; transform: translateX(-50%);`;
	});
</script>

<div
	class="flex items-center gap-2"
	onpointerenter={() => (isHovering = true)}
	onpointerleave={() => (isHovering = false)}
>
	<button
		class="btn btn-ghost"
		onclick={() => (value = Math.max(min, value - 1))}
		disabled={disabled || value <= min}
	>
		<MagnifyingGlassMinus size={20} />
	</button>
	<div class="relative flex w-48 flex-col items-center gap-2">
		<input
			type="range"
			{min}
			{max}
			bind:value
			class="range ring-accent w-48"
			{disabled}
			onpointermove={(event: PointerEvent) => event.stopPropagation()}
			onpointerdown={() => (isDragging = true)}
			onpointerup={() => (isDragging = false)}
		/>
		{#if isTooltipVisible}
			<div
				class="bg-primary text-primary-foreground border-border pointer-events-none absolute -top-8 z-10 rounded border px-2 py-1 text-xs shadow-lg backdrop-blur-sm"
				style={tooltipStyle}
				transition:fade
			>
				{value}
			</div>
		{/if}
	</div>
	<button
		class="btn btn-ghost btn-circle"
		onclick={() => (value = Math.min(max, value + 1))}
		disabled={disabled || value >= max}
	>
		<MagnifyingGlassPlus size={20} />
	</button>
</div>
