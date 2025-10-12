<script lang="ts">
	import { browser } from '$app/environment';
	import UsageUnitToggle from '$lib/features/stats/components/UnitToggle.svelte';
	import { getUsageStats, UsageStatsUnit, type UsageStatsData } from '$lib/features/stats/service';
	import { type EChartsOption, type LineSeriesOption } from 'echarts';
	import { LineChart } from 'echarts/charts';
	import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components';
	import { init, use } from 'echarts/core';
	import { CanvasRenderer } from 'echarts/renderers';
	import { Chart } from 'svelte-echarts';
	import PeriodNavigator from './PeriodNavigator.svelte';
	import PeriodSlider from './PeriodSlider.svelte';
	// 导入 PeriodSlider 组件

	// 注册 ECharts 组件
	use([LineChart, TooltipComponent, LegendComponent, GridComponent, CanvasRenderer]);

	let chartData: UsageStatsData | null = $state(null);
	let loading = $state(true);
	let error: string | null = $state(null);

	let options: EChartsOption = $state({});

	let previousUnit: UsageStatsUnit = $state(UsageStatsUnit.DAY);
	let unit: UsageStatsUnit = $state(UsageStatsUnit.DAY);
	let offset: number = $state(0);
	let numPeriods: number = $state(7); // 默认显示 7 个周期
	let timezone: string = $state('Asia/Shanghai'); // 默认时区
	let periodText: string = $state('加载中...');

	// 获取用户浏览器时区
	if (browser) {
		timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
	}

	async function fetchData() {
		loading = true;
		try {
			chartData = await getUsageStats(unit, offset, numPeriods, timezone);
			periodText = chartData ? `${chartData.start_date} 至 ${chartData.end_date}` : 'null';
			if (chartData) {
				const modelNames = Array.from(new Set(chartData.datasets.map((ds) => ds.label)));
				const series: LineSeriesOption[] = chartData.datasets.map((ds) => ({
					name: ds.label,
					type: 'line',
					stack: 'total', // 堆叠
					emphasis: {
						focus: 'series'
					},
					data: ds.data,
					smooth: true // 平滑曲线
				}));

				options = {
					tooltip: {
						trigger: 'axis',
						axisPointer: {
							type: 'shadow'
						}
					},
					legend: {
						type: 'scroll',
						data: modelNames,
						backgroundColor: 'rgba(255, 255, 255, 0.5)',
						borderRadius: 12,
						padding: 10,
						bottom: 0
					},
					grid: {
						left: '3%',
						right: '4%',
						top: '10%',
						bottom: '15%', // 为 legend 留出更多空间
						containLabel: true
					},
					xAxis: {
						type: 'category',
						boundaryGap: false,
						data: chartData.labels
					},
					yAxis: {
						type: 'value'
					},
					series: series
				};
			}
		} catch (e: any) {
			error = e.message;
			console.error('Failed to fetch usage stats data:', e);
		} finally {
			loading = false;
		}
	}

	// 响应式地重新获取数据
	$effect(() => {
		if (previousUnit !== unit) {
			offset = 0;
			previousUnit = unit;
			numPeriods = 7; // 重置周期数
		}
		const timeoutId = setTimeout(fetchData, 300);
		return () => clearTimeout(timeoutId);
	});

	export { fetchData as refresh };
</script>

<div class="flex h-full flex-col">
	<div class="flex flex-col items-center md:flex-row md:justify-between">
		<UsageUnitToggle bind:currentUnit={unit} disabled={loading} />
		<PeriodNavigator bind:offset {periodText} disabled={[loading, loading || offset >= 0]} />
	</div>

	<PeriodSlider bind:num_periods={numPeriods} currentUnit={unit} disabled={loading} />

	<div class="flex-grow">
		{#if loading}
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
		{:else if chartData && chartData.labels.length > 0}
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
	</div>
</div>
