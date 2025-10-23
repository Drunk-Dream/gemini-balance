<script lang="ts">
	import ChartWrapper from '$lib/components/ChartWrapper.svelte';
	import { defaultChartOptions } from '$lib/features/stats/constants/chart-options';
	import { getDailyUsageChart } from '$lib/features/stats/service';
	import type { ChartData } from '$lib/features/stats/types';
	import { deepmerge } from 'deepmerge-ts';
	import type { BarSeriesOption, EChartsOption } from 'echarts';
	import { onMount } from 'svelte';


	let chartData: ChartData | null = $state(null);
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

				const specificOptions: EChartsOption = {
					legend: {
						data: modelNames
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

				options = deepmerge(defaultChartOptions, specificOptions);
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
