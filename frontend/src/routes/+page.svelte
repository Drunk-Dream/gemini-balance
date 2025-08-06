<script lang="ts">
	import { goto } from '$app/navigation';
	import { authToken, isAuthenticated } from '$lib/stores';
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
		if (!$authToken) {
			goto('/login');
			return;
		}

		loading = true;
		errorMessage = null;
		try {
			const response = await fetch('/api/status/keys', {
				headers: {
					Authorization: `Bearer ${$authToken}`
				}
			});
			if (response.status === 401) {
				isAuthenticated.set(false);
				goto('/login');
				return;
			}
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
		// 检查认证状态，如果未认证则重定向
		if (!$isAuthenticated) {
			goto('/login');
			return;
		}

		fetchKeyStatuses();
		const interval = setInterval(fetchKeyStatuses, 5000); // Refresh every 5 seconds
		return () => clearInterval(interval);
	});

	function formatDailyUsage(usage: { [model: string]: number }): string {
		const entries = Object.entries(usage);
		if (entries.length === 0) {
			return '无';
		}
		entries.sort(([modelA], [modelB]) => modelA.localeCompare(modelB)); // 按模型名称排序
		return entries.map(([model, count]) => `${model}: ${count}`).join('<br>');
	}
</script>

<div class="container mx-auto p-2 sm:p-4">
	<h1 class="mb-4 text-2xl font-bold text-gray-800 sm:mb-6 sm:text-3xl">密钥状态监控</h1>

	<div class="mb-4 flex items-center justify-between">
		<button
			on:click={fetchKeyStatuses}
			class="focus:shadow-outline rounded bg-blue-500 px-4 py-2 text-sm font-bold text-white hover:bg-blue-700 focus:outline-none sm:text-base"
			disabled={loading}
		>
			{loading ? '刷新中...' : '立即刷新'}
		</button>
	</div>

	{#if errorMessage}
		<div
			class="relative rounded border border-red-400 bg-red-100 px-4 py-3 text-red-700"
			role="alert"
		>
			<strong class="font-bold">错误!</strong>
			<span class="block sm:inline"> {errorMessage}</span>
		</div>
	{:else if keyStatuses.length === 0 && !loading}
		<p class="text-gray-600">没有可用的密钥状态信息。</p>
	{:else}
		<div class="grid gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
			{#each keyStatuses as keyStatus}
				<div class="rounded-lg bg-white p-4 shadow-md">
					<div class="mb-2 flex items-center justify-between">
						<h3 class="text-md font-semibold text-gray-800">密钥标识:</h3>
						<p class="text-sm text-gray-900">{keyStatus.key_identifier}</p>
					</div>
					<div class="mb-2 flex items-center justify-between">
						<h3 class="text-md font-semibold text-gray-800">状态:</h3>
						<span class="relative inline-block px-2 py-0.5 text-sm font-semibold leading-tight">
							<span
								aria-hidden="true"
								class="absolute inset-0 rounded-full opacity-50 {keyStatus.status === 'active'
									? 'bg-green-200'
									: 'bg-yellow-200'}"
							></span>
							<span class="relative text-gray-900"
								>{keyStatus.status === 'active' ? '活跃' : '冷却中'}</span
							>
						</span>
					</div>
					<div class="mb-2 flex items-center justify-between">
						<h3 class="text-md font-semibold text-gray-800">剩余冷却时间:</h3>
						<p class="text-sm text-gray-900">{keyStatus.cool_down_seconds_remaining} 秒</p>
					</div>
					<div class="mb-2 flex items-center justify-between">
						<h3 class="text-md font-semibold text-gray-800">今日用量:</h3>
						<div class="text-sm text-gray-900">{@html formatDailyUsage(keyStatus.daily_usage)}</div>
					</div>
					<div class="mb-2 flex items-center justify-between">
						<h3 class="text-md font-semibold text-gray-800">失败次数:</h3>
						<p class="text-sm text-gray-900">{keyStatus.failure_count}</p>
					</div>
					<div class="mb-2 flex items-center justify-between">
						<h3 class="text-md font-semibold text-gray-800">进入冷却次数:</h3>
						<p class="text-sm text-gray-900">{keyStatus.cool_down_entry_count}</p>
					</div>
					<div class="flex items-center justify-between">
						<h3 class="text-md font-semibold text-gray-800">当前冷却时长:</h3>
						<p class="text-sm text-gray-900">{keyStatus.current_cool_down_seconds} 秒</p>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
