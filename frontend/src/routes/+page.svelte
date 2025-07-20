<script lang="ts">
	import { onMount } from 'svelte';

	interface KeyStatus {
		key_identifier: string;
		status: string;
		cool_down_seconds_remaining: number;
		daily_usage: { [model: string]: number };
		failure_count: number;
		cool_down_entry_count: number;
		current_cool_down_seconds: number;
	}

	let keyStatuses: KeyStatus[] = [];
	let errorMessage: string | null = null;
	let loading = true;

	async function fetchKeyStatuses() {
		loading = true;
		errorMessage = null;
		try {
			const response = await fetch('/api/status/keys');
			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}
			const data = await response.json();
			keyStatuses = data.keys; // Access the 'keys' array
		} catch (error: any) {
			errorMessage = `Failed to fetch key statuses: ${error.message}`;
			console.error(errorMessage);
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		fetchKeyStatuses();
		const interval = setInterval(fetchKeyStatuses, 5000); // Refresh every 5 seconds
		return () => clearInterval(interval);
	});

	function formatDailyUsage(usage: { [model: string]: number }): string {
		return Object.entries(usage)
			.map(([model, count]) => `${model}: ${count}`)
			.join(', ');
	}
</script>

<div class="container mx-auto p-4">
	<h1 class="text-3xl font-bold mb-6 text-gray-800">密钥状态监控</h1>

	<div class="flex justify-between items-center mb-4">
		<button
			on:click={fetchKeyStatuses}
			class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
			disabled={loading}
		>
			{loading ? '刷新中...' : '立即刷新'}
		</button>
	</div>

	{#if errorMessage}
		<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
			<strong class="font-bold">错误!</strong>
			<span class="block sm:inline"> {errorMessage}</span>
		</div>
	{:else if keyStatuses.length === 0 && !loading}
		<p class="text-gray-600">没有可用的密钥状态信息。</p>
	{:else}
		<div class="overflow-x-auto bg-white shadow-md rounded-lg">
			<table class="min-w-full leading-normal">
				<thead>
					<tr>
						<th
							class="px-5 py-3 border-b-2 border-gray-200 bg-gray-100 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider"
						>
							密钥标识
						</th>
						<th
							class="px-5 py-3 border-b-2 border-gray-200 bg-gray-100 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider"
						>
							状态
						</th>
						<th
							class="px-5 py-3 border-b-2 border-gray-200 bg-gray-100 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider"
						>
							剩余冷却时间 (秒)
						</th>
						<th
							class="px-5 py-3 border-b-2 border-gray-200 bg-gray-100 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider"
						>
							今日用量
						</th>
						<th
							class="px-5 py-3 border-b-2 border-gray-200 bg-gray-100 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider"
						>
							失败次数
						</th>
						<th
							class="px-5 py-3 border-b-2 border-gray-200 bg-gray-100 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider"
						>
							进入冷却次数
						</th>
						<th
							class="px-5 py-3 border-b-2 border-gray-200 bg-gray-100 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider"
						>
							当前冷却时长 (秒)
						</th>
					</tr>
				</thead>
				<tbody>
					{#each keyStatuses as keyStatus}
						<tr>
							<td class="px-5 py-5 border-b border-gray-200 bg-white text-sm">
								<p class="text-gray-900 whitespace-no-wrap">{keyStatus.key_identifier}</p>
							</td>
							<td class="px-5 py-5 border-b border-gray-200 bg-white text-sm">
								<span
									class="relative inline-block px-3 py-1 font-semibold leading-tight"
								>
									<span
										aria-hidden="true"
										class="absolute inset-0 opacity-50 rounded-full {keyStatus.status === 'active' ? 'bg-green-200' : 'bg-yellow-200'}"
									></span>
									<span class="relative text-gray-900">{keyStatus.status === 'active' ? '活跃' : '冷却中'}</span>
								</span>
							</td>
							<td class="px-5 py-5 border-b border-gray-200 bg-white text-sm">
								<p class="text-gray-900 whitespace-no-wrap">
									{keyStatus.cool_down_seconds_remaining}
								</p>
							</td>
							<td class="px-5 py-5 border-b border-gray-200 bg-white text-sm">
								<p class="text-gray-900 whitespace-no-wrap">{formatDailyUsage(keyStatus.daily_usage)}</p>
							</td>
							<td class="px-5 py-5 border-b border-gray-200 bg-white text-sm">
								<p class="text-gray-900 whitespace-no-wrap">{keyStatus.failure_count}</p>
							</td>
							<td class="px-5 py-5 border-b border-gray-200 bg-white text-sm">
								<p class="text-gray-900 whitespace-no-wrap">{keyStatus.cool_down_entry_count}</p>
							</td>
							<td class="px-5 py-5 border-b border-gray-200 bg-white text-sm">
								<p class="text-gray-900 whitespace-no-wrap">{keyStatus.current_cool_down_seconds}</p>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>
