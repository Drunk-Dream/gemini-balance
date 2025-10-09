<script lang="ts">
	import { browser } from '$app/environment';
	import UsageUnitToggle from '$lib/components/UnitToggle.svelte';
	import { getUsageStats, UsageStatsUnit, type UsageStatsData } from '$lib/features/stats/service';
	import type { EChartsOption, LineSeriesOption } from 'echarts';
	import { LineChart } from 'echarts/charts';
	import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components';
	import { init, use } from 'echarts/core';
	import { CanvasRenderer } from 'echarts/renderers';
	import CaretLeft from 'phosphor-svelte/lib/CaretLeft';
	import CaretRight from 'phosphor-svelte/lib/CaretRight';
	import { Chart } from 'svelte-echarts';

	// 注册 ECharts 组件
	use([LineChart, TooltipComponent, LegendComponent, GridComponent, CanvasRenderer]);

	let chartData: UsageStatsData | null = $state(null);
	let loading = $state(true);
	let error: string | null = $state(null);

	let options: EChartsOption = $state({});

	let previousUnit: UsageStatsUnit = $state(UsageStatsUnit.DAY);
	let currentUnit: UsageStatsUnit = $state(UsageStatsUnit.DAY);
	let currentOffset: number = $state(0);
	let timezone: string = $state('Asia/Shanghai'); // 默认时区
	// 显示当前统计时间段的文本
	let periodText: string = $state('加载中...');

	// 获取用户浏览器时区
	if (browser) {
		timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
	}

	async function fetchData() {
		loading = true;
		if (previousUnit !== currentUnit) {
			currentOffset = 0;
			previousUnit = currentUnit;
		}
		try {
			chartData = await getUsageStats(currentUnit, currentOffset, timezone);
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
						data: modelNames,
						bottom: 0 // 将 legend 放在底部
					},
					grid: {
						left: '3%',
						right: '4%',
						top: '10%', // 减小上边距
						bottom: '10%', // 为 legend 留出更多空间
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
		fetchData();
	});

	function changeOffset(delta: number) {
		currentOffset += delta;
	}
</script>

<div class="flex h-full flex-col">
	<div class="mb-4 flex items-center justify-between">
		<UsageUnitToggle bind:currentUnit />
		<div class="flex items-center space-x-2">
			<button class="btn btn-ghost btn-sm" onclick={() => changeOffset(-1)} aria-label="上一时间段">
				<CaretLeft class="h-4 w-4" />
			</button>
			<span class="text-sm text-gray-600">{periodText}</span>
			<button class="btn btn-ghost btn-sm" onclick={() => changeOffset(1)} aria-label="下一时间段">
				<CaretRight class="h-4 w-4" />
			</button>
		</div>
	</div>

	<div class="flex-grow">
		{#if loading}
			<p>加载中...</p>
		{:else if error}
			<p class="text-red-500">错误: {error}</p>
		{:else if chartData && chartData.labels.length > 0}
			<Chart {init} {options} style="width: 100%; height: 100%;" />
		{:else}
			<p>暂无数据。</p>
		{/if}
	</div>
</div>
