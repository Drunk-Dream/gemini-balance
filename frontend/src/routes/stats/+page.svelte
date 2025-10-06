<script lang="ts">
	import ChartCard from '$lib/components/ChartCard.svelte';
	import AuthGuard from '$lib/features/auth/components/AuthGuard.svelte';
	import UsageChart from '$lib/features/logs/components/UsageChart.svelte';

	// 假设我们从某个地方获取时区，这里暂时硬编码
	const timezone_str = Intl.DateTimeFormat().resolvedOptions().timeZone;
</script>

<AuthGuard>
	<div class="container mx-auto p-2 sm:p-4">
		<h1 class="mb-4 text-2xl font-bold sm:text-3xl">统计看板</h1>

		<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
			<ChartCard className="lg:col-span-2">
				{#snippet header()}
					<h2 class="text-lg font-semibold">每日模型使用统计</h2>
					<p class="text-sm text-gray-500">按服务密钥总使用量排序</p>
				{/snippet}
				{#snippet children()}
					<UsageChart {timezone_str} />
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
	</div>
</AuthGuard>
