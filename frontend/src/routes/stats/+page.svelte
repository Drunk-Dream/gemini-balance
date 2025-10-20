<script lang="ts">
	import Container from '$lib/components/Container.svelte';
	import AuthGuard from '$lib/features/auth/components/AuthGuard.svelte';
	import ChartCard from '$lib/features/stats/components/ChartCard.svelte';
	import DailyUsageChart from '$lib/features/stats/components/DailyUsageChart.svelte';
	import HourlySuccessRateChart from '$lib/features/stats/components/HourlySuccessRateChart.svelte';
	import SuccessRateChart from '$lib/features/stats/components/SuccessRateChart.svelte';
	import UsageHeatmapChart from '$lib/features/stats/components/UsageHeatmapChart.svelte';
	import UsageTrendChart from '$lib/features/stats/components/UsageTrendChart.svelte';

	let dailyUsageChart: DailyUsageChart | undefined;
	let usageRequestTrendChart: UsageTrendChart | undefined;
	let usageTokensTrendChart: UsageTrendChart | undefined;
	let usageRequestsHeatmapChart: UsageHeatmapChart | undefined; // 请求次数热力图
	let usageTokensHeatmapChart: UsageHeatmapChart | undefined; // Token 用量热力图
	let successRateChart: SuccessRateChart | undefined;
	let hourlySuccessRateChart: SuccessRateChart | undefined;
</script>

<AuthGuard>
	<Container header="统计看板">
		<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
			<ChartCard className="lg:col-span-2" onRefresh={() => dailyUsageChart?.refresh()}>
				{#snippet header()}
					<h2 class="text-lg font-semibold">每日使用</h2>
					<p class="text-base-content/50 text-sm">每个key每日用量</p>
				{/snippet}
				{#snippet children()}
					<DailyUsageChart bind:this={dailyUsageChart} />
				{/snippet}
			</ChartCard>

			<!-- <ChartCard className="lg:col-span-2" onRefresh={() => usageRequestsHeatmapChart?.refresh()}>
				{#snippet header()}
					<h2 class="text-lg font-semibold">请求次数热力图</h2>
					<p class="text-base-content/50 text-sm">每日请求次数热力图</p>
				{/snippet}
				{#snippet children()}
					<UsageHeatmapChart bind:this={usageRequestsHeatmapChart} type="requests" />
				{/snippet}
			</ChartCard>

			<ChartCard className="lg:col-span-2" onRefresh={() => usageTokensHeatmapChart?.refresh()}>
				{#snippet header()}
					<h2 class="text-lg font-semibold">Token用量热力图</h2>
					<p class="text-base-content/50 text-sm">每日Token用量热力图</p>
				{/snippet}
				{#snippet children()}
					<UsageHeatmapChart bind:this={usageTokensHeatmapChart} type="tokens" />
				{/snippet}
			</ChartCard> -->

			<ChartCard className="lg:col-span-1" onRefresh={() => usageRequestTrendChart?.refresh()}>
				{#snippet header()}
					<h2 class="text-lg font-semibold">请求次数</h2>
					<p class="text-base-content/50 text-sm">按日、周、月统计请求次数</p>
				{/snippet}
				{#snippet children()}
					<UsageTrendChart bind:this={usageRequestTrendChart} type="requests" />
				{/snippet}
			</ChartCard>
			<ChartCard className="lg:col-span-1" onRefresh={() => usageTokensTrendChart?.refresh()}>
				{#snippet header()}
					<h2 class="text-lg font-semibold">Token用量</h2>
					<p class="text-base-content/50 text-sm">按日、周、月统计Token用量</p>
				{/snippet}
				{#snippet children()}
					<UsageTrendChart bind:this={usageTokensTrendChart} type="tokens" />
				{/snippet}
			</ChartCard>
			<ChartCard className="lg:col-span-1" onRefresh={() => successRateChart?.refresh()}>
				{#snippet header()}
					<h2 class="text-lg font-semibold">请求成功率</h2>
					<p class="text-base-content/50 text-sm">每日不同模型请求成功率</p>
				{/snippet}
				{#snippet children()}
					<SuccessRateChart bind:this={successRateChart} />
				{/snippet}
			</ChartCard>
			<ChartCard className="lg:col-span-1" onRefresh={() => hourlySuccessRateChart?.refresh()}>
				{#snippet header()}
					<h2 class="text-lg font-semibold">请求成功率</h2>
					<p class="text-base-content/50 text-sm">每日不同模型请求成功率</p>
				{/snippet}
				{#snippet children()}
					<HourlySuccessRateChart bind:this={hourlySuccessRateChart} />
				{/snippet}
			</ChartCard>
		</div>
	</Container>
</AuthGuard>
