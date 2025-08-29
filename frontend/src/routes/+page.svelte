<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import AddKeyForm from '$lib/components/key-management/AddKeyForm.svelte';
	import KeyList from '$lib/components/key-management/KeyList.svelte';
	import KeyManagementHeader from '$lib/components/key-management/KeyManagementHeader.svelte';
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

	async function addKeys(keysInput: string) {
		if (!keysInput.trim()) {
			alert('请输入密钥');
			return;
		}
		const keysArray = keysInput
			.split('\n')
			.map((key) => key.trim())
			.filter((key) => key);
		if (keysArray.length === 0) {
			alert('请输入有效的密钥');
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
			alert('密钥添加成功！');
			fetchKeyStatuses();
		} catch (error: any) {
			alert(`添加密钥失败: ${error.message}`);
			console.error('添加密钥失败:', error);
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
		if (!$isAuthenticated) {
			goto(`/login?redirect=${page.url.pathname}`);
			return;
		}

		fetchKeyStatuses();
		const interval = setInterval(fetchKeyStatuses, 5000);
		return () => clearInterval(interval);
	});
</script>

<div class="container mx-auto p-2 sm:p-4">
	<h1 class="mb-4 text-2xl font-bold text-gray-800 sm:mb-6 sm:text-3xl">密钥管理</h1>

	<KeyManagementHeader {fetchKeyStatuses} {resetAllKeys} {loading} />

	<AddKeyForm {addKeys} />

	{#if errorMessage}
		<div
			class="relative rounded border border-red-400 bg-red-100 px-4 py-3 text-red-700"
			role="alert"
		>
			<strong class="font-bold">错误!</strong>
			<span class="block sm:inline"> {errorMessage}</span>
		</div>
	{:else}
		<KeyList {keyStatuses} {resetKey} {deleteKey} />
	{/if}
</div>
