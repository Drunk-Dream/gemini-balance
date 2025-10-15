<script lang="ts">
	import type { DailyUsageChartData, DailyUsageHeatmapData, UsageStatsData } from '$lib/features/stats/service';
	import type { EChartsOption } from 'echarts';
	import { init } from 'echarts/core';
	import { Chart } from 'svelte-echarts';

	type ChartDataType = DailyUsageChartData | DailyUsageHeatmapData | UsageStatsData;

	let {
		loading,
		error,
		chartData,
		options
	}: {
		loading: boolean;
		error: string | null;
		chartData: ChartDataType | null;
		options: EChartsOption;
	} = $props();

	let isInitialLoad = $state(true);

	$effect(() => {
		if (isInitialLoad && !loading) {
			isInitialLoad = false;
		}
	});
</script>

{#if loading && isInitialLoad}
	<!-- 使用 skeleton 作为加载占位符 -->
	<div class="skeleton h-full w-full"></div>
{:else if error}
	<!-- 使用 alert 显示错误信息 -->
	<div role="alert" class="alert alert-error">
		<svg
			xmlns="http://www.w3.org/2000/svg"
			class="h-6 w-6 shrink-0 stroke-current"
			fill="none"
			viewBox="0 0 24 24"
		>
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				stroke-width="2"
				d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
			/>
		</svg>
		<span>错误: {error}</span>
	</div>
{:else if chartData && (Array.isArray(chartData) ? chartData.length > 0 : chartData.labels.length > 0)}
	<!-- 图表容器 -->
	<div class="h-full w-full">
		<Chart {init} {options} style="width: 100%; height: 100%;" />
	</div>
{:else}
	<!-- 无数据时的提示 -->
	<div role="alert" class="alert alert-info">
		<svg
			xmlns="http://www.w3.org/2000/svg"
			fill="none"
			viewBox="0 0 24 24"
			class="h-6 w-6 shrink-0 stroke-current"
		>
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				stroke-width="2"
				d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
			></path>
		</svg>
		<span>暂无数据。</span>
	</div>
{/if}
