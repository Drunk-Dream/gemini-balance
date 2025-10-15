<script lang="ts">
	import { browser } from '$app/environment';
	import ChartWrapper from '$lib/components/ChartWrapper.svelte';
	import UsageUnitToggle from '$lib/features/stats/components/UnitToggle.svelte';
	import { getUsageStats, UsageStatsUnit, type UsageStatsData } from '$lib/features/stats/service';
	import { type EChartsOption, type LineSeriesOption } from 'echarts';
	import { LineChart } from 'echarts/charts';
	import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components';
	import { use } from 'echarts/core';
	import { CanvasRenderer } from 'echarts/renderers';
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
			chartData = await getUsageStats(unit, offset, numPeriods, timezone, 'request_count');
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
		// 追踪 unit, offset, numPeriods 的变化
		const _1 = unit;
		const _2 = offset;
		const _3 = numPeriods;

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
	<div class="flex flex-col items-center gap-2 xl:flex-row xl:justify-between xl:gap-0">
		<UsageUnitToggle bind:currentUnit={unit} disabled={loading} />
		<PeriodSlider bind:value={numPeriods} currentUnit={unit} disabled={loading} />
		<!-- <PeriodNavigator bind:offset {periodText} disabled={[loading, loading || offset >= 0]} /> -->
	</div>

	<div class="flex-grow">
		<ChartWrapper {loading} {error} {chartData} {options} />
	</div>
</div>
