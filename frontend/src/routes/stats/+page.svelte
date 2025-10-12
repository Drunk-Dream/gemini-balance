<script lang="ts">
	import Container from '$lib/components/Container.svelte';
	import AuthGuard from '$lib/features/auth/components/AuthGuard.svelte';
	import ChartCard from '$lib/features/stats/components/ChartCard.svelte';
	import DailyUsageChart from '$lib/features/stats/components/DailyUsageChart.svelte';
	import UsageTrendChart from '$lib/features/stats/components/UsageTrendChart.svelte';

	let dailyUsageChart: DailyUsageChart | undefined;
	let usageTrendChart: UsageTrendChart | undefined;
</script>

<AuthGuard>
	<Container header="统计看板">
		<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
			<ChartCard className="lg:col-span-2" onRefresh={() => dailyUsageChart?.refresh()}>
				{#snippet header()}
					<h2 class="text-lg font-semibold">每日模型使用统计</h2>
					<p class="text-base-content/50 text-sm">按服务密钥总使用量排序</p>
				{/snippet}
				{#snippet children()}
					<DailyUsageChart bind:this={dailyUsageChart} />
				{/snippet}
			</ChartCard>

			<ChartCard className="lg:col-span-1" onRefresh={() => usageTrendChart?.refresh()}>
				{#snippet header()}
					<h2 class="text-lg font-semibold">模型使用趋势</h2>
					<p class="text-base-content/50 text-sm">按日、周、月统计模型请求次数</p>
				{/snippet}
				{#snippet children()}
					<UsageTrendChart bind:this={usageTrendChart} />
				{/snippet}
			</ChartCard>
		</div>
	</Container>
</AuthGuard>
