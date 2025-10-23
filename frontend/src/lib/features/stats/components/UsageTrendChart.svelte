<script lang="ts">
	import { browser } from '$app/environment';
	import ChartWrapper from '$lib/components/ChartWrapper.svelte';
	import { defaultChartOptions } from '$lib/features/stats//constants/chart-options';
	import UsageUnitToggle from '$lib/features/stats/components/UnitToggle.svelte';
	import { getUsageStats } from '$lib/features/stats/service';
	import { UsageStatsUnit, type ChartData } from '$lib/features/stats/types';
	import { deepmerge } from 'deepmerge-ts';
	import type { EChartsOption, LineSeriesOption } from 'echarts';
	import PeriodSlider from './PeriodSlider.svelte';

	let { type }: { type: 'requests' | 'tokens' } = $props();

	let chartData: ChartData | null = $state(null);
	let loading = $state(true);
	let error: string | null = $state(null);

	let previousUnit: UsageStatsUnit = $state(UsageStatsUnit.DAY);
	let unit: UsageStatsUnit = $state(UsageStatsUnit.DAY);
	let offset: number = $state(0);
	let numPeriods: number = $state(7); // 默认显示 7 个周期
	let timezone: string = $state('Asia/Shanghai'); // 默认时区

	// 获取用户浏览器时区
	if (browser) {
		timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
	}

	async function fetchData() {
		loading = true;
		error = null;
		try {
			chartData = await getUsageStats(unit, offset, numPeriods, timezone, type);
		} catch (e: any) {
			error = e.message;
			console.error('Failed to fetch usage stats data:', e);
		} finally {
			loading = false;
		}
	}

	let options = $derived.by((): EChartsOption => {
		if (!chartData) {
			return defaultChartOptions;
		}

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

		const specificOptions: EChartsOption = {
			legend: {
				data: modelNames
			},
			xAxis: {
				type: 'category',
				data: chartData.labels,
				boundaryGap: true
			},
			yAxis: {
				type: 'value'
			},
			series: series
		};
		return deepmerge(defaultChartOptions, specificOptions);
	});

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
		<PeriodSlider
			bind:value={numPeriods}
			max={unit === UsageStatsUnit.DAY ? 90 : unit === UsageStatsUnit.WEEK ? 52 : 24}
			disabled={loading}
		/>
	</div>

	<div class="flex-grow">
		<ChartWrapper
			{loading}
			{error}
			isReady={(chartData && chartData.labels.length > 0) || false}
			{options}
		/>
	</div>
</div>
