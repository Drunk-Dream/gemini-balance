<script lang="ts">
	import { browser } from '$app/environment';
	import ChartWrapper from '$lib/components/ChartWrapper.svelte';
	import { getSuccessRateStats } from '$lib/features/stats/service';
	import type { SuccessRateStatsResponse } from '$lib/features/stats/types';
	import { UsageStatsUnit } from '$lib/features/stats/types';
	import type { EChartsOption, LineSeriesOption } from 'echarts';
	import { deepmerge } from 'deepmerge-ts';
	import { defaultChartOptions } from './chart-options';
	import PeriodSlider from './PeriodSlider.svelte';

	let chartData = $state<SuccessRateStatsResponse | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let period = $state(7);
	let timezone: string = $state('Asia/Shanghai'); // 默认时区

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

	$effect(() => {
		fetchData();
	});

	let chartOption = $derived.by((): EChartsOption => {
		if (!chartData) {
			return {
				title: {
					text: '模型请求成功率'
				}
			};
		}

		const dates = chartData.stats.map((s) => s.date);
		const models = chartData.models;

		const series: LineSeriesOption[] = models.map((model) => ({
			name: model,
			type: 'line',
			data: chartData!.stats.map((s) => s.models[model]?.toFixed(2) ?? 0),
			emphasis: {
				focus: 'series'
			}
		}));

		const specificOptions: EChartsOption = {
			title: {
				text: '模型请求成功率',
				left: 'center'
			},
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
				data: models,
				top: 'bottom'
			},
			xAxis: [
				{
					type: 'category',
					data: dates,
					boundaryGap: true
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

	export { fetchData as refresh };
</script>

<div class="flex h-full flex-col">
	<div class="flex flex-col items-center gap-2 xl:flex-row xl:justify-between xl:gap-0">
		<PeriodSlider
			bind:value={period}
			min={7}
			currentUnit={UsageStatsUnit.DAY}
			disabled={isLoading}
		/>
	</div>

	<div class="flex-grow">
		<ChartWrapper
			loading={isLoading}
			{error}
			isReady={(chartData && chartData.stats.length > 0) || false}
			options={chartOption}
		/>
	</div>
</div>
