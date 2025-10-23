<script lang="ts">
	import { browser } from '$app/environment';
	import ChartWrapper from '$lib/components/ChartWrapper.svelte';
	import { defaultChartOptions } from '$lib/features/stats/constants/chart-options';
	import { getHourlySuccessRateStats } from '$lib/features/stats/service';
	import type { ChartData } from '$lib/features/stats/types';
	import { deepmerge } from 'deepmerge-ts';
	import type { EChartsOption, LineSeriesOption } from 'echarts';
	import PeriodSlider from './PeriodSlider.svelte';

	let chartData = $state<ChartData | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let period = $state(30); // 默认查询最近30天
	let timezone: string = $state('UTC'); // 默认时区

	// 获取用户浏览器时区
	if (browser) {
		timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
	}

	async function fetchData() {
		isLoading = true;
		error = null;
		try {
			chartData = await getHourlySuccessRateStats(period, timezone);
		} catch (e) {
			error = (e as Error).message;
		} finally {
			isLoading = false;
		}
	}

	let chartOption = $derived.by((): EChartsOption => {
		if (!chartData) {
			return {};
		}

		const labels = chartData.labels;
		const models = chartData.datasets.map((d) => d.label);

		const series: LineSeriesOption[] = chartData.datasets.map((dataset) => ({
			name: dataset.label,
			type: 'line',
			smooth: true,
			data: dataset.data.map((d) => (d !== null ? d.toFixed(2) : null)),
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
					let tooltipText = `时间: ${params[0].axisValue}:00<br/>`;
					params.forEach((param: any) => {
						const model = param.seriesName;
						const rate = param.value;
						tooltipText += `${model}: ${rate}%<br/>`;
					});
					return tooltipText;
				}
			},
			legend: {
				data: models,
				top: 'bottom'
			},
			xAxis: [
				{
					type: 'category',
					data: labels,
					boundaryGap: false,
					axisLabel: {
						formatter: '{value}:00'
					}
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
		const _ = period; // 依赖 period 的变化
		const timeoutId = setTimeout(fetchData, 300); // 防抖
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
			options={chartOption}
		/>
	</div>
</div>
