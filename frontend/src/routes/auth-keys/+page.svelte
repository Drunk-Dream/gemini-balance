<script lang="ts">
	import { goto } from '$app/navigation';
	import { authToken, isAuthenticated } from '$lib/stores';
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	// 假设你有一个认证状态的 store

	interface AuthKey {
		api_key: string;
		alias: string;
	}

	let authKeys: AuthKey[] = [];
	let newAlias: string = '';
	let editingKey: AuthKey | null = null;
	let editingAlias: string = '';
	let errorMessage: string = '';
	let successMessage: string = '';

	// 检查认证状态
	onMount(() => {
		if (!get(isAuthenticated)) {
			goto('/login');
		} else {
			fetchAuthKeys();
		}
	});

	async function fetchAuthKeys() {
		errorMessage = '';
		successMessage = '';
		try {
			const response = await fetch(`/api/auth_keys`, {
				headers: {
					Authorization: `Bearer ${get(authToken)}`
				}
			});
			if (response.ok) {
				authKeys = await response.json();
			} else if (response.status === 401 || response.status === 403) {
				errorMessage = '认证失败，请重新登录。';
				goto('/login');
			} else {
				const errorData = await response.json();
				errorMessage = errorData.detail || '获取密钥失败。';
			}
		} catch (error) {
			console.error('Error fetching auth keys:', error);
			errorMessage = '网络错误或服务器无响应。';
		}
	}

	async function createAuthKey() {
		errorMessage = '';
		successMessage = '';
		if (!newAlias.trim()) {
			errorMessage = '别名不能为空。';
			return;
		}
		try {
			const response = await fetch(`/api/auth_keys`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${get(authToken)}`
				},
				body: JSON.stringify({ alias: newAlias })
			});
			if (response.ok) {
				const newKey: AuthKey = await response.json();
				authKeys = [...authKeys, newKey];
				newAlias = '';
				successMessage = `密钥 "${newKey.alias}" 创建成功！API Key: ${newKey.api_key}`;
			} else if (response.status === 401 || response.status === 403) {
				errorMessage = '认证失败，请重新登录。';
				goto('/login');
			} else {
				const errorData = await response.json();
				errorMessage = errorData.detail || '创建密钥失败。';
			}
		} catch (error) {
			console.error('Error creating auth key:', error);
			errorMessage = '网络错误或服务器无响应。';
		}
	}

	function startEdit(key: AuthKey) {
		editingKey = key;
		editingAlias = key.alias;
		errorMessage = '';
		successMessage = '';
	}

	async function updateAuthKey() {
		errorMessage = '';
		successMessage = '';
		if (!editingKey) return;
		if (!editingAlias.trim()) {
			errorMessage = '别名不能为空。';
			return;
		}
		try {
			const response = await fetch(`/api/auth_keys/${editingKey.api_key}`, {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${get(authToken)}`
				},
				body: JSON.stringify({ alias: editingAlias })
			});
			if (response.ok) {
				const updatedKey: AuthKey = await response.json();
				authKeys = authKeys.map((k) => (k.api_key === updatedKey.api_key ? updatedKey : k));
				editingKey = null;
				editingAlias = '';
				successMessage = `密钥 "${updatedKey.alias}" 更新成功！`;
			} else if (response.status === 401 || response.status === 403) {
				errorMessage = '认证失败，请重新登录。';
				goto('/login');
			} else {
				const errorData = await response.json();
				errorMessage = errorData.detail || '更新密钥失败。';
			}
		} catch (error) {
			console.error('Error updating auth key:', error);
			errorMessage = '网络错误或服务器无响应。';
		}
	}

	function cancelEdit() {
		editingKey = null;
		editingAlias = '';
		errorMessage = '';
		successMessage = '';
	}

	async function deleteAuthKey(api_key: string) {
		errorMessage = '';
		successMessage = '';
		if (!confirm('确定要删除此密钥吗？此操作不可逆！')) {
			return;
		}
		try {
			const response = await fetch(`/api/auth_keys/${api_key}`, {
				method: 'DELETE',
				headers: {
					Authorization: `Bearer ${get(authToken)}`
				}
			});
			if (response.status === 204) {
				authKeys = authKeys.filter((k) => k.api_key !== api_key);
				successMessage = '密钥删除成功！';
			} else if (response.status === 401 || response.status === 403) {
				errorMessage = '认证失败，请重新登录。';
				goto('/login');
			} else {
				const errorData = await response.json();
				errorMessage = errorData.detail || '删除密钥失败。';
			}
		} catch (error) {
			console.error('Error deleting auth key:', error);
			errorMessage = '网络错误或服务器无响应。';
		}
	}
</script>

<div class="container mx-auto p-4 md:p-8">
	<h1 class="mb-6 text-2xl font-bold">管理认证密钥</h1>

	<!-- Notifications -->
	{#if successMessage}
		<div
			class="relative mb-4 rounded border border-green-400 bg-green-100 px-4 py-3 text-green-700"
			role="alert"
		>
			<span class="block sm:inline">{successMessage}</span>
		</div>
	{/if}
	{#if errorMessage}
		<div
			class="relative mb-4 rounded border border-red-400 bg-red-100 px-4 py-3 text-red-700"
			role="alert"
		>
			<span class="block sm:inline">{errorMessage}</span>
		</div>
	{/if}

	<!-- Create New Key Form -->
	<div class="mb-6 rounded bg-white px-8 pb-8 pt-6 shadow-md">
		<h2 class="mb-4 text-xl font-semibold">创建新密钥</h2>
		<form on:submit|preventDefault={createAuthKey} class="flex items-center space-x-4">
			<div class="flex-grow">
				<label for="new-alias" class="sr-only">新别名</label>
				<input
					id="new-alias"
					type="text"
					bind:value={newAlias}
					placeholder="输入新密钥的别名"
					class="focus:shadow-outline w-full appearance-none rounded border px-3 py-2 leading-tight text-gray-700 shadow focus:outline-none"
					required
				/>
			</div>
			<button
				type="submit"
				class="focus:shadow-outline rounded bg-blue-500 px-4 py-2 font-bold text-white hover:bg-blue-700 focus:outline-none"
			>
				创建
			</button>
		</form>
	</div>

	<!-- Auth Keys List -->
	<div class="rounded bg-white px-8 pb-8 pt-6 shadow-md">
		<h2 class="mb-4 text-xl font-semibold">现有密钥列表</h2>
		<div class="overflow-x-auto">
			<table class="min-w-full divide-y divide-gray-200">
				<thead class="bg-gray-50">
					<tr>
						<th
							scope="col"
							class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
						>
							别名
						</th>
						<th
							scope="col"
							class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
						>
							API Key
						</th>
						<th
							scope="col"
							class="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500"
						>
							操作
						</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-gray-200 bg-white">
					{#each authKeys as key (key.api_key)}
						<tr>
							<td class="whitespace-nowrap px-6 py-4">
								{#if editingKey?.api_key === key.api_key}
									<input
										type="text"
										bind:value={editingAlias}
										class="focus:shadow-outline w-full appearance-none rounded border px-3 py-2 leading-tight text-gray-700 shadow focus:outline-none"
									/>
								{:else}
									<span class="text-sm text-gray-900">{key.alias}</span>
								{/if}
							</td>
							<td class="whitespace-nowrap px-6 py-4">
								<span class="font-mono text-sm text-gray-500">{key.api_key}</span>
							</td>
							<td class="space-x-2 whitespace-nowrap px-6 py-4 text-right text-sm font-medium">
								{#if editingKey?.api_key === key.api_key}
									<button on:click={updateAuthKey} class="text-indigo-600 hover:text-indigo-900">
										保存
									</button>
									<button on:click={cancelEdit} class="text-gray-600 hover:text-gray-900">
										取消
									</button>
								{:else}
									<button
										on:click={() => startEdit(key)}
										class="text-indigo-600 hover:text-indigo-900">编辑</button
									>
									<button
										on:click={() => deleteAuthKey(key.api_key)}
										class="text-red-600 hover:text-red-900">删除</button
									>
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
			{#if authKeys.length === 0}
				<p class="py-4 text-center text-gray-500">暂无数据。</p>
			{/if}
		</div>
	</div>
</div>
