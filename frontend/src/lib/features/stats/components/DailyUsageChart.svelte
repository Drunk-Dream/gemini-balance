<script lang="ts">
	import ChartWrapper from '$lib/components/ChartWrapper.svelte';
	import { getDailyUsageChart } from '$lib/features/stats/service';
	import type { DailyUsageChartData } from '$lib/features/stats/types';
	import type { BarSeriesOption, EChartsOption } from 'echarts';
	import { BarChart } from 'echarts/charts';
	import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components';
	import { use } from 'echarts/core';
	import { CanvasRenderer } from 'echarts/renderers';
	import { onMount } from 'svelte';

	// 注册 ECharts 组件
	use([BarChart, TooltipComponent, LegendComponent, GridComponent, CanvasRenderer]);

	let chartData: DailyUsageChartData | null = $state(null);
	let loading = $state(true);
	let error: string | null = $state(null);

	let options: EChartsOption = $state({});

	async function fetchDataAndRenderChart() {
		loading = true;
		error = null;
		try {
			chartData = await getDailyUsageChart();
			if (chartData) {
				const modelNames = chartData.datasets.map((ds) => ds.label);
				const series: BarSeriesOption[] = chartData.datasets.map((ds) => ({
					// 明确指定类型
					name: ds.label,
					type: 'bar',
					stack: 'total', // 堆叠
					emphasis: {
						focus: 'series'
					},
					data: ds.data
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
						top: '5%',
						bottom: '15%', // 为 legend 留出更多空间
						containLabel: true
					},
					xAxis: {
						type: 'value',
						position: 'top' // 将 x 轴放在顶部
					},
					yAxis: {
						type: 'category',
						data: chartData.labels, // key_identifier 作为 Y 轴
						inverse: true // Y 轴数据从上到下排列
					},
					series: series
				};
			}
		} catch (e: any) {
			error = e.message;
			console.error('Failed to fetch chart data:', e);
		} finally {
			loading = false;
		}
	}

	onMount(fetchDataAndRenderChart);

	export { fetchDataAndRenderChart as refresh };
</script>

<ChartWrapper
	{loading}
	{error}
	isReady={(chartData && chartData.labels.length > 0) || false}
	{options}
/>
