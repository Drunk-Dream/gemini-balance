<script lang="ts">
	import { browser } from '$app/environment';
	import ChartWrapper from '$lib/components/ChartWrapper.svelte';
	import { getHourlySuccessRateStats } from '$lib/features/stats/service';
	import type { HourlySuccessRateChartData } from '$lib/features/stats/types';
	import { UsageStatsUnit } from '$lib/features/stats/types';
	import type { EChartsOption, BarSeriesOption } from 'echarts';
	import { deepmerge } from 'deepmerge-ts';
	import { defaultChartOptions } from './chart-options';
	import PeriodSlider from './PeriodSlider.svelte';

	let chartData = $state<HourlySuccessRateChartData | null>(null);
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
			return {
				title: {
					text: '模型请求成功率 (按小时)'
				}
			};
		}

		const labels = chartData.labels;
		const models = chartData.datasets.map((d) => d.label);

		const series: BarSeriesOption[] = chartData.datasets.map((dataset) => ({
			name: dataset.label,
			type: 'bar',
			data: dataset.data.map((d) => (d !== null ? d.toFixed(2) : null)),
			emphasis: {
				focus: 'series'
			}
		}));

		const specificOptions: EChartsOption = {
			title: {
				text: '模型请求成功率 (按小时)',
				left: 'center'
			},
			tooltip: {
				trigger: 'axis',
				axisPointer: {
					type: 'shadow' // 默认为 'line'，'shadow' 类型更适合柱状图
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
					boundaryGap: true,
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
			isReady={(chartData && chartData.datasets.length > 0) || false}
			options={chartOption}
		/>
	</div>
</div>
