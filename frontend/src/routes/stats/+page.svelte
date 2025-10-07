<script lang="ts">
	import Container from '$lib/components/Container.svelte';
	import AuthGuard from '$lib/features/auth/components/AuthGuard.svelte';
	import ChartCard from '$lib/features/stats/components/ChartCard.svelte';
	import DailyUsageChart from '$lib/features/stats/components/DailyUsageChart.svelte';
	import UsageTrendChart from '$lib/features/stats/components/UsageTrendChart.svelte';
</script>

<AuthGuard>
	<Container header="统计看板">
		<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
			<ChartCard className="lg:col-span-2">
				{#snippet header()}
					<h2 class="text-lg font-semibold">每日模型使用统计</h2>
					<p class="text-sm text-gray-500">按服务密钥总使用量排序</p>
				{/snippet}
				{#snippet children()}
					<DailyUsageChart />
				{/snippet}
			</ChartCard>

			<ChartCard className="lg:col-span-1">
				{#snippet header()}
					<h2 class="text-lg font-semibold">模型使用趋势</h2>
					<p class="text-sm text-gray-500">按日、周、月统计模型请求次数</p>
				{/snippet}
				{#snippet children()}
					<UsageTrendChart />
				{/snippet}
			</ChartCard>
		</div>
	</Container>
</AuthGuard>
