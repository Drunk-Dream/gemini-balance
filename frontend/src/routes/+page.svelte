<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
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
	let newKey: string = '';
	let bulkKeys: string = '';

	async function fetchKeyStatuses() {
		if (!$authToken) {
			goto(`/login?redirect=${page.url.pathname}`);
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

	async function addSingleKey() {
		if (!newKey.trim()) {
			alert('请输入密钥');
			return;
		}
		try {
			const response = await fetch('/api/keys', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${$authToken}`
				},
				body: JSON.stringify({ api_keys: [newKey.trim()] })
			});
			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
			}
			alert('密钥添加成功！');
			newKey = '';
			fetchKeyStatuses();
		} catch (error: any) {
			alert(`添加密钥失败: ${error.message}`);
			console.error('添加密钥失败:', error);
		}
	}

	async function addBulkKeys() {
		if (!bulkKeys.trim()) {
			alert('请输入批量密钥');
			return;
		}
		const keysArray = bulkKeys
			.split('\n')
			.map((key) => key.trim())
			.filter((key) => key);
		if (keysArray.length === 0) {
			alert('请输入有效的批量密钥');
			return;
		}
		try {
			const response = await fetch('/api/keys', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${$authToken}`
				},
				body: JSON.stringify({ api_keys: keysArray })
			});
			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
			}
			alert('批量密钥添加成功！');
			bulkKeys = '';
			fetchKeyStatuses();
		} catch (error: any) {
			alert(`批量添加密钥失败: ${error.message}`);
			console.error('批量添加密钥失败:', error);
		}
	}

	async function deleteKey(keyIdentifier: string) {
		if (!confirm(`确定要删除密钥标识符为 "${keyIdentifier}" 的密钥吗？`)) {
			return;
		}
		try {
			const response = await fetch(`/api/keys/${keyIdentifier}`, {
				method: 'DELETE',
				headers: {
					Authorization: `Bearer ${$authToken}`
				}
			});
			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
			}
			alert(`密钥 "${keyIdentifier}" 删除成功！`);
			fetchKeyStatuses();
		} catch (error: any) {
			alert(`删除密钥失败: ${error.message}`);
			console.error('删除密钥失败:', error);
		}
	}

	async function resetKey(keyIdentifier: string) {
		if (!confirm(`确定要重置密钥标识符为 "${keyIdentifier}" 的密钥状态吗？`)) {
			return;
		}
		try {
			const response = await fetch(`/api/keys/${keyIdentifier}/reset`, {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${$authToken}`
				}
			});
			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
			}
			alert(`密钥 "${keyIdentifier}" 状态重置成功！`);
			fetchKeyStatuses();
		} catch (error: any) {
			alert(`重置密钥状态失败: ${error.message}`);
			console.error('重置密钥状态失败:', error);
		}
	}

	async function resetAllKeys() {
		if (!confirm('确定要重置所有密钥的状态吗？此操作不可逆！')) {
			return;
		}
		try {
			const response = await fetch('/api/keys/reset', {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${$authToken}`
				}
			});
			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
			}
			alert('所有密钥状态重置成功！');
			fetchKeyStatuses();
		} catch (error: any) {
			alert(`重置所有密钥状态失败: ${error.message}`);
			console.error('重置所有密钥状态失败:', error);
		}
	}

	onMount(() => {
		// 检查认证状态，如果未认证则重定向
		if (!$isAuthenticated) {
			goto(`/login?redirect=${page.url.pathname}`);
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
	<h1 class="mb-4 text-2xl font-bold text-gray-800 sm:mb-6 sm:text-3xl">密钥管理</h1>

	<div
		class="mb-4 flex flex-col space-y-4 sm:flex-row sm:items-center sm:justify-between sm:space-x-4 sm:space-y-0"
	>
		<button
			on:click={fetchKeyStatuses}
			class="focus:shadow-outline rounded bg-blue-500 px-4 py-2 text-sm font-bold text-white hover:bg-blue-700 focus:outline-none sm:text-base"
			disabled={loading}
		>
			{loading ? '刷新中...' : '立即刷新'}
		</button>
		<button
			on:click={resetAllKeys}
			class="focus:shadow-outline rounded bg-red-500 px-4 py-2 text-sm font-bold text-white hover:bg-red-700 focus:outline-none sm:text-base"
		>
			重置所有密钥状态
		</button>
	</div>

	<div class="mb-6 rounded-lg bg-white p-4 shadow-md">
		<h2 class="mb-4 text-xl font-semibold text-gray-800">新增密钥</h2>
		<div class="mb-4">
			<label for="newKey" class="mb-2 block text-sm font-medium text-gray-700">新增单个密钥:</label>
			<input
				type="text"
				id="newKey"
				bind:value={newKey}
				placeholder="输入新的API密钥"
				class="w-full rounded-md border border-gray-300 p-2 focus:border-blue-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50"
			/>
			<button
				on:click={addSingleKey}
				class="focus:shadow-outline mt-2 rounded bg-green-500 px-4 py-2 text-sm font-bold text-white hover:bg-green-700 focus:outline-none"
			>
				添加密钥
			</button>
		</div>
		<div>
			<label for="bulkKeys" class="mb-2 block text-sm font-medium text-gray-700"
				>批量新增密钥 (每行一个):</label
			>
			<textarea
				id="bulkKeys"
				bind:value={bulkKeys}
				placeholder="每行输入一个API密钥"
				rows="5"
				class="w-full rounded-md border border-gray-300 p-2 focus:border-blue-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50"
			></textarea>
			<button
				on:click={addBulkKeys}
				class="focus:shadow-outline mt-2 rounded bg-green-500 px-4 py-2 text-sm font-bold text-white hover:bg-green-700 focus:outline-none"
			>
				批量添加密钥
			</button>
		</div>
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
					<div class="mt-4 flex justify-end space-x-2">
						<button
							on:click={() => resetKey(keyStatus.key_identifier)}
							class="focus:shadow-outline rounded bg-yellow-500 px-3 py-1.5 text-sm font-bold text-white hover:bg-yellow-700 focus:outline-none"
						>
							重置
						</button>
						<button
							on:click={() => deleteKey(keyStatus.key_identifier)}
							class="focus:shadow-outline rounded bg-red-500 px-3 py-1.5 text-sm font-bold text-white hover:bg-red-700 focus:outline-none"
						>
							删除
						</button>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
