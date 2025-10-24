<script lang="ts">
	import { browser } from '$app/environment';
	import ChartWrapper from '$lib/components/ChartWrapper.svelte';
	import { getDefaultChartOptions } from '$lib/features/stats/constants/chart-options';
	import { getSuccessRateStats } from '$lib/features/stats/service';
	import type { ChartData } from '$lib/features/stats/types';
	import { theme } from '$lib/features/theme/theme';
	import { deepmerge } from 'deepmerge-ts';
	import type { EChartsOption, LineSeriesOption } from 'echarts';
	import PeriodSlider from './PeriodSlider.svelte';

	let chartData = $state<ChartData | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let period = $state(7);
	let timezone: string = $state('Asia/Shanghai'); // 默认时区
	let defaultChartOptions: EChartsOption = $state(getDefaultChartOptions());

	// 获取用户浏览器时区
	if (browser) {
		timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
	}

	async function fetchData() {
		isLoading = true;
		error = null;
		try {
			chartData = await getSuccessRateStats(period, timezone);
		} catch (e) {
			error = (e as Error).message;
		} finally {
			isLoading = false;
		}
	}

	let options = $derived.by((): EChartsOption => {
		if (!chartData) return getDefaultChartOptions();

		const series: LineSeriesOption[] = chartData.datasets.map((ds) => ({
			name: ds.label,
			type: 'line',
			data: ds.data.map((d) => (d !== null ? d.toFixed(2) : null)),
			emphasis: {
				focus: 'series'
			}
		}));

		const specificOptions: EChartsOption = {
			tooltip: {
				trigger: 'axis',
				axisPointer: {
					type: 'cross'
				},
				formatter: (params: any) => {
					let tooltipText = `${params[0].axisValue}<br/>`;
					params.forEach((param: any) => {
						const model = param.seriesName;
						const rate = param.value;
						tooltipText += `${model}: ${rate}%<br/>`;
					});
					return tooltipText;
				}
			},
			legend: {
				data: chartData.datasets.map((ds) => ds.label),
				top: 'bottom'
			},
			xAxis: [
				{
					type: 'category',
					data: chartData.labels,
					boundaryGap: false
				}
			],
			yAxis: [
				{
					type: 'value',
					axisLabel: {
						formatter: '{value} %'
					}
				}
			],
			series: series
		};
		return deepmerge(defaultChartOptions, specificOptions);
	});

	$effect(() => {
		const _ = $theme;
		defaultChartOptions = getDefaultChartOptions();
	});

	$effect(() => {
		const _ = period;
		const timeoutId = setTimeout(fetchData, 300);
		return () => clearTimeout(timeoutId);
	});

	export { fetchData as refresh };
</script>

<div class="flex h-full flex-col">
	<div class="flex flex-col items-center">
		<PeriodSlider bind:value={period} min={7} max={90} disabled={isLoading} />
	</div>

	<div class="flex-grow">
		<ChartWrapper
			loading={isLoading}
			{error}
			isReady={(chartData && chartData.datasets.length > 0) || false}
			{options}
		/>
	</div>
</div>
