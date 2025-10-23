<script lang="ts">
	import Container from '$lib/components/Container.svelte';
	import AuthGuard from '$lib/features/auth/components/AuthGuard.svelte';
	import ChartCard from '$lib/features/stats/components/ChartCard.svelte';
	import ChartSelector from '$lib/features/stats/components/ChartSelector.svelte';
	import DailyUsageChart from '$lib/features/stats/components/DailyUsageChart.svelte';
	import HourlySuccessRateChart from '$lib/features/stats/components/HourlySuccessRateChart.svelte';
	import SuccessRateChart from '$lib/features/stats/components/SuccessRateChart.svelte';
	import UsageTrendChart from '$lib/features/stats/components/UsageTrendChart.svelte';
	import { chartSelectionStore } from '$lib/features/stats/stores/chart-store';
	import { BarChart, LineChart } from 'echarts/charts';
	import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components';
	import { use } from 'echarts/core';
	import { CanvasRenderer } from 'echarts/renderers';

	// 注册 ECharts 组件
	use([BarChart, TooltipComponent, LegendComponent, GridComponent, CanvasRenderer, LineChart]);

	let dailyUsageChart: DailyUsageChart | undefined;
	let usageRequestTrendChart: UsageTrendChart | undefined;
	let usageTokensTrendChart: UsageTrendChart | undefined;
	// let usageRequestsHeatmapChart: UsageHeatmapChart | undefined;
	// let usageTokensHeatmapChart: UsageHeatmapChart | undefined;
	let successRateChart: SuccessRateChart | undefined;
	let hourlySuccessRateChart: HourlySuccessRateChart | undefined;
</script>

<AuthGuard>
	<Container header="统计看板">
		<ChartSelector />
		<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
			{#if $chartSelectionStore.includes('dailyUsage')}
				<ChartCard className="lg:col-span-2" onRefresh={() => dailyUsageChart?.refresh()}>
					{#snippet header()}
						<h2 class="text-lg font-semibold">每日使用</h2>
						<p class="text-foreground/50 text-sm">每个key每日用量</p>
					{/snippet}
					{#snippet children()}
						<DailyUsageChart bind:this={dailyUsageChart} />
					{/snippet}
				</ChartCard>
			{/if}

			{#if $chartSelectionStore.includes('usageRequestTrend')}
				<ChartCard className="lg:col-span-1" onRefresh={() => usageRequestTrendChart?.refresh()}>
					{#snippet header()}
						<h2 class="text-lg font-semibold">请求次数</h2>
						<p class="text-foreground/50 text-sm">按日、周、月统计请求次数</p>
					{/snippet}
					{#snippet children()}
						<UsageTrendChart bind:this={usageRequestTrendChart} type="requests" />
					{/snippet}
				</ChartCard>
			{/if}

			{#if $chartSelectionStore.includes('usageTokensTrend')}
				<ChartCard className="lg:col-span-1" onRefresh={() => usageTokensTrendChart?.refresh()}>
					{#snippet header()}
						<h2 class="text-lg font-semibold">Token用量</h2>
						<p class="text-foreground/50 text-sm">按日、周、月统计Token用量</p>
					{/snippet}
					{#snippet children()}
						<UsageTrendChart bind:this={usageTokensTrendChart} type="tokens" />
					{/snippet}
				</ChartCard>
			{/if}

			{#if $chartSelectionStore.includes('successRate')}
				<ChartCard className="lg:col-span-1" onRefresh={() => successRateChart?.refresh()}>
					{#snippet header()}
						<h2 class="text-lg font-semibold">请求成功率</h2>
						<p class="text-foreground/50 text-sm">每日不同模型请求成功率</p>
					{/snippet}
					{#snippet children()}
						<SuccessRateChart bind:this={successRateChart} />
					{/snippet}
				</ChartCard>
			{/if}

			{#if $chartSelectionStore.includes('hourlySuccessRate')}
				<ChartCard className="lg:col-span-1" onRefresh={() => hourlySuccessRateChart?.refresh()}>
					{#snippet header()}
						<h2 class="text-lg font-semibold">请求成功率(按小时)</h2>
						<p class="text-foreground/50 text-sm">不同时段不同模型请求成功率</p>
					{/snippet}
					{#snippet children()}
						<HourlySuccessRateChart bind:this={hourlySuccessRateChart} />
					{/snippet}
				</ChartCard>
			{/if}
		</div>
	</Container>
</AuthGuard>
