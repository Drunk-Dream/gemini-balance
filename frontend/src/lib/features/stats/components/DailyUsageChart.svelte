<script lang="ts">
	import ChartWrapper from '$lib/components/ChartWrapper.svelte';
	import { getDefaultChartOptions } from '$lib/features/stats/constants/chart-options';
	import { getDailyUsageChart } from '$lib/features/stats/service';
	import type { ChartData } from '$lib/features/stats/types';
	import { theme } from '$lib/features/theme/theme';
	import { deepmerge } from 'deepmerge-ts';
	import type { BarSeriesOption, EChartsOption } from 'echarts';
	import { onMount } from 'svelte';

	let chartData: ChartData | null = $state(null);
	let loading = $state(true);
	let error: string | null = $state(null);
	let defaultChartOptions: EChartsOption = $state(getDefaultChartOptions());

	async function fetchDataAndRenderChart() {
		loading = true;
		error = null;
		try {
			chartData = await getDailyUsageChart();
		} catch (e: any) {
			error = e.message;
			console.error('Failed to fetch chart data:', e);
		} finally {
			loading = false;
		}
	}

	const options = $derived.by(() => {
		if (!chartData) return getDefaultChartOptions();
		const modelNames = chartData.datasets.map((ds) => ds.label);
		const series: BarSeriesOption[] = chartData.datasets.map((ds) => ({
			name: ds.label,
			type: 'bar',
			stack: 'total',
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
		return deepmerge(defaultChartOptions, specificOptions);
	});

	onMount(fetchDataAndRenderChart);
	$effect(() => {
		const _ = $theme;
		defaultChartOptions = getDefaultChartOptions();
	});

	export { fetchDataAndRenderChart as refresh };
</script>

<ChartWrapper
	{loading}
	{error}
	isReady={(chartData && chartData.labels.length > 0) || false}
	{options}
/>
