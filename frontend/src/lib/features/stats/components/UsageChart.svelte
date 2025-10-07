<script lang="ts">
	import { getDailyUsageChart, type ChartData } from '$lib/features/stats/service';
	import type { BarSeriesOption, EChartsOption } from 'echarts';
	import * as echarts from 'echarts';
	import { onMount } from 'svelte';
	import { Chart } from 'svelte-echarts';

	let chartData: ChartData | null = $state(null);
	let loading = $state(true);
	let error: string | null = $state(null);

	let option: EChartsOption = $state({});

	onMount(async () => {
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

				option = {
					tooltip: {
						trigger: 'axis',
						axisPointer: {
							type: 'shadow'
						}
					},
					legend: {
						data: modelNames,
						bottom: 0 // 将 legend 放在底部
					},
					grid: {
						left: '3%',
						right: '4%',
						top: '5%', // 减小上边距
						bottom: '10%', // 为 legend 留出更多空间
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
	});
</script>

{#if loading}
	<p>加载中...</p>
{:else if error}
	<p class="text-red-500">错误: {error}</p>
{:else if chartData && chartData.labels.length > 0}
	<Chart init={echarts.init} options={option} style="width: 100%; height: 100%;" />
{:else}
	<p>暂无数据。</p>
{/if}
