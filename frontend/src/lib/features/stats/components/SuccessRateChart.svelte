<script lang="ts">
	import { browser } from '$app/environment';
	import ChartWrapper from '$lib/components/ChartWrapper.svelte';
	import { getSuccessRateStats } from '$lib/features/stats/service';
	import type { SuccessRateStatsResponse } from '$lib/features/stats/types';
	import { UsageStatsUnit } from '$lib/features/stats/types';
	import type { EChartsOption } from 'echarts';
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

		const series: any[] = models.flatMap((model) => [
			{
				name: `${model} Success`,
				type: 'bar',
				stack: model,
				emphasis: {
					focus: 'series'
				},
				data: chartData!.stats.map((s) => s.models[model]?.successful_requests ?? 0)
			},
			{
				name: `${model} Total`,
				type: 'bar',
				stack: model,
				emphasis: {
					focus: 'series'
				},
				data: chartData!.stats.map((s) =>
					s.models[model]?.total_requests
						? s.models[model]?.total_requests - s.models[model]?.successful_requests
						: 0
				),
				itemStyle: {
					color: '#cccccc'
				}
			}
		]);

		return {
			title: {
				text: '模型请求成功率',
				left: 'center'
			},
			tooltip: {
				trigger: 'axis',
				axisPointer: {
					type: 'shadow'
				},
				formatter: (params: any) => {
					let tooltipText = `${params[0].axisValue}<br/>`;
					const modelData: { [key: string]: { success: number; total: number } } = {};

					params.forEach((param: any) => {
						const seriesName = param.seriesName;
						const value = param.value;
						const model = seriesName.replace(' Success', '').replace(' Total', '');

						if (!modelData[model]) {
							modelData[model] = { success: 0, total: 0 };
						}

						if (seriesName.includes('Success')) {
							modelData[model].success = value;
						}
						// The "Total" series now represents failures, so we add success to get total.
						const totalRequestsForModel = params
							.filter((p: any) => p.seriesName.startsWith(model))
							.reduce((acc: number, p: any) => acc + p.value, 0);
						modelData[model].total = totalRequestsForModel;
					});

					for (const model in modelData) {
						const success = modelData[model].success;
						const total = modelData[model].total;
						const rate = total > 0 ? ((success / total) * 100).toFixed(2) : '0.00';
						tooltipText += `${model}: ${success} / ${total} (${rate}%)<br/>`;
					}

					return tooltipText;
				}
			},
			legend: {
				data: models.map((m) => `${m} Success`),
				top: 'bottom'
			},
			grid: {
				left: '3%',
				right: '4%',
				bottom: '10%',
				containLabel: true
			},
			xAxis: [
				{
					type: 'category',
					data: dates
				}
			],
			yAxis: [
				{
					type: 'value'
				}
			],
			series: series
		};
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

<!-- <div class="card bg-base-100 shadow-xl">
	<div class="card-body">
		<div class="flex items-center justify-between">
			<h2 class="card-title">模型请求成功率</h2>
			<PeriodSlider bind:value={period} min={7} currentUnit={UsageStatsUnit.DAY} />
		</div>

		{#if isLoading}
			<div class="flex h-96 w-full items-center justify-center">
				<span class="loading loading-lg loading-spinner"></span>
			</div>
		{:else if error}
			<div class="flex h-96 w-full items-center justify-center">
				<div role="alert" class="alert alert-error">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="h-6 w-6 shrink-0 stroke-current"
						fill="none"
						viewBox="0 0 24 24"
						><path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
						/></svg
					>
					<span>{error.message}</span>
				</div>
			</div>
		{:else if chartData && chartData.stats.length > 0}
			<ECharts option={chartOption} style="height: 400px;" />
		{:else}
			<div class="flex h-96 w-full items-center justify-center">
				<p>暂无数据</p>
			</div>
		{/if}
	</div>
</div> -->
