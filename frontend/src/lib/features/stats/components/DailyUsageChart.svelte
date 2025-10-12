<script lang="ts">
	import { getDailyUsageChart, type DailyUsageChartData } from '$lib/features/stats/service';
	import type { BarSeriesOption, EChartsOption } from 'echarts';
	import { BarChart } from 'echarts/charts';
	import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components';
	import { init, use } from 'echarts/core';
	import { CanvasRenderer } from 'echarts/renderers';
	import { onMount } from 'svelte';
	import { Chart } from 'svelte-echarts';

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

{#if loading}
	<!-- 使用 skeleton 作为加载占位符 -->
	<div class="skeleton h-full w-full"></div>
{:else if error}
	<!-- 使用 alert 显示错误信息 -->
	<div role="alert" class="alert alert-error">
		<svg
			xmlns="http://www.w3.org/2000/svg"
			class="h-6 w-6 shrink-0 stroke-current"
			fill="none"
			viewBox="0 0 24 24"
		>
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				stroke-width="2"
				d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
			/>
		</svg>
		<span>错误: {error}</span>
	</div>
{:else if chartData && chartData.labels.length > 0}
	<!-- 图表容器 -->
	<div class="h-full w-full">
		<Chart {init} {options} style="width: 100%; height: 100%;" />
	</div>
{:else}
	<!-- 无数据时的提示 -->
	<div role="alert" class="alert alert-info">
		<svg
			xmlns="http://www.w3.org/2000/svg"
			fill="none"
			viewBox="0 0 24 24"
			class="h-6 w-6 shrink-0 stroke-current"
		>
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				stroke-width="2"
				d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
			></path>
		</svg>
		<span>暂无数据。</span>
	</div>
{/if}
