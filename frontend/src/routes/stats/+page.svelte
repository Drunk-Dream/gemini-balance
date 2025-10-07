<script lang="ts">
	import Container from '$lib/components/Container.svelte';
	import AuthGuard from '$lib/features/auth/components/AuthGuard.svelte';
	import ChartCard from '$lib/features/stats/components/ChartCard.svelte';
	import UsageChart from '$lib/features/stats/components/UsageChart.svelte';

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
					<UsageChart  />
				{/snippet}
			</ChartCard>

			<!-- 为未来添加新图表预留空间 -->
			<!--
			<ChartCard>
				<div slot="header">
					<h2 class="text-lg font-semibold">另一个图表</h2>
				</div>
				<p>图表内容...</p>
			</ChartCard>
			-->
		</div>
	</Container>
</AuthGuard>
