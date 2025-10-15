<script lang="ts">
	import { browser } from '$app/environment';
	import ChartWrapper from '$lib/components/ChartWrapper.svelte';
	import { getDailyUsageHeatmap, type DailyUsageHeatmapData } from '$lib/features/stats/service';
	import { type EChartsOption, type HeatmapSeriesOption } from 'echarts';
	import { CalendarComponent, TooltipComponent, VisualMapComponent } from 'echarts/components';
	import { HeatmapChart } from 'echarts/charts';
	import { use, time } from 'echarts/core'; // 回退到 echarts/core 中的 format
	import { CanvasRenderer } from 'echarts/renderers';

	// 注册 ECharts 组件
	use([HeatmapChart, CalendarComponent, TooltipComponent, VisualMapComponent, CanvasRenderer]);

    let {type}: { type: 'requests' | 'tokens' } = $props();

	let chartData: DailyUsageHeatmapData | null = $state(null);
	let loading = $state(true);
	let error: string | null = $state(null);
	let options: EChartsOption = $state({});
	let timezone: string = $state('Asia/Shanghai'); // 默认时区

	// 获取用户浏览器时区
	if (browser) {
		timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
	}

	async function fetchData() {
		loading = true;
		error = null;
		try {
			chartData = await getDailyUsageHeatmap(type, timezone);
			if (chartData) {
				options = getChartOption(chartData);
			}
		} catch (e: any) {
			error = e.message || '加载数据失败';
			console.error('Failed to load heatmap data:', e);
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		// 追踪 type 的变化
		const _ = type;
		const timeoutId = setTimeout(fetchData, 300);
		return () => clearTimeout(timeoutId);
	});

	export { fetchData as refresh };

	function getChartOption(data: DailyUsageHeatmapData): EChartsOption {
		const years = Array.from(new Set(data.map(([date]) => new Date(date).getFullYear())));
		const minYear = Math.min(...years);
		const maxYear = Math.max(...years);

		return {
			tooltip: {
				position: 'top',
				formatter: function (p: any) {
					const formattedDate = time.format(p.data[0], '{yyyy}-{MM}-{dd}', true);
					return formattedDate + ': ' + p.data[1];
				}
			},
			visualMap: {
				min: 0,
				max: Math.max(...data.map(([, value]) => value)),
				calculable: true,
				orient: 'horizontal',
				left: 'center',
				bottom: '0',
				inRange: {
					color: ['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39'] // GitHub green shades
				}
			},
			calendar: years.map((year, index) => ({
				top: 60 + index * 180, // Adjust top position for each year
				range: year,
				cellSize: ['auto', 20],
				itemStyle: {
					borderWidth: 0.5,
					borderColor: '#fff'
				},
				yearLabel: {
					formatter: '{start}年',
					position: 'top',
					margin: 20,
					textStyle: {
						color: '#666'
					}
				},
				dayLabel: {
					firstDay: 1, // Monday
					nameMap: ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
				},
				monthLabel: {
					nameMap: 'cn'
				}
			})),
			series: years.map((year) => ({
				type: 'heatmap',
				coordinateSystem: 'calendar',
				calendarIndex: years.indexOf(year),
				data: data.filter(([date]) => new Date(date).getFullYear() === year)
			})) as HeatmapSeriesOption[]
		};
	}
</script>

<div class="flex h-full flex-col">
	<div class="flex-grow">
		<ChartWrapper {loading} {error} {chartData} {options} />
	</div>
</div>
