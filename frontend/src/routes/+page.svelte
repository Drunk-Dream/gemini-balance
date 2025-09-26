<script lang="ts">
	import AuthGuard from '$lib/components/auth/AuthGuard.svelte';
	import Notification from '$lib/components/common/Notification.svelte';
	import KeyActions from '$lib/components/key-management/KeyActions.svelte';
	import KeyList from '$lib/components/key-management/KeyList.svelte';
	import KeyStatusSummary from '$lib/components/key-management/KeyStatusSummary.svelte';
	import type { KeyStatus } from '$lib/types/key-management';
// 导入 Notification 组件
	import { api } from '$lib/utils/api';
	import { onMount } from 'svelte';

	let keyStatuses: KeyStatus[] = $state([]);
	let errorMessage: string | null = $state(null);
	let loading = $state(true);
	let notificationMessage: string | null = $state(null); // 新增通知消息
	let notificationType: 'success' | 'error' = $state('success'); // 新增通知类型

	async function fetchKeyStatuses() {
		loading = true;
		errorMessage = null;
		try {
			const data = await api.get<{ keys: KeyStatus[] }>('/status/keys');
			if (!data) {
				throw new Error('No response from the server');
			}
			keyStatuses = data.keys;
		} catch (error: any) {
			notificationMessage = `获取密钥状态失败: ${error.message}`;
			notificationType = 'error';
		} finally {
			loading = false;
		}
	}

	async function addKeys(keysInput: string) {
		if (!keysInput.trim()) {
			notificationMessage = '请输入密钥';
			notificationType = 'error';
			return;
		}
		const keysArray = keysInput
			.split('\n')
			.map((key) => key.trim())
			.filter((key) => key);
		if (keysArray.length === 0) {
			notificationMessage = '请输入有效的密钥';
			notificationType = 'error';
			return;
		}
		try {
			await api.post('/keys', { api_keys: keysArray });
			notificationMessage = '密钥添加成功！';
			notificationType = 'success';
			fetchKeyStatuses();
		} catch (error: any) {
			notificationMessage = `添加密钥失败: ${error.message}`;
			notificationType = 'error';
			console.error('添加密钥失败:', error);
		}
	}

	async function deleteKey(keyIdentifier: string) {
		if (!confirm(`确定要删除密钥标识符为 "${keyIdentifier}" 的密钥吗？`)) {
			return;
		}
		try {
			await api.delete(`/keys/${keyIdentifier}`);
			notificationMessage = `密钥 "${keyIdentifier}" 删除成功！`;
			notificationType = 'success';
			fetchKeyStatuses();
		} catch (error: any) {
			notificationMessage = `删除密钥失败: ${error.message}`;
			notificationType = 'error';
			console.error('删除密钥失败:', error);
		}
	}

	async function resetKey(keyIdentifier: string) {
		if (!confirm(`确定要重置密钥标识符为 "${keyIdentifier}" 的密钥状态吗？`)) {
			return;
		}
		try {
			await api.post(`/keys/${keyIdentifier}/reset`, {});
			notificationMessage = `密钥 "${keyIdentifier}" 状态重置成功！`;
			notificationType = 'success';
			fetchKeyStatuses();
		} catch (error: any) {
			notificationMessage = `重置密钥状态失败: ${error.message}`;
			notificationType = 'error';
			console.error('重置密钥状态失败:', error);
		}
	}

	async function resetAllKeys() {
		if (!confirm('确定要重置所有密钥的状态吗？此操作不可逆！')) {
			return;
		}
		try {
			await api.post('/keys/reset', {});
			notificationMessage = '所有密钥状态重置成功！';
			notificationType = 'success';
			fetchKeyStatuses();
		} catch (error: any) {
			notificationMessage = `重置所有密钥状态失败: ${error.message}`;
			notificationType = 'error';
			console.error('重置所有密钥状态失败:', error);
		}
	}

	onMount(() => {
		fetchKeyStatuses();
		const interval = setInterval(fetchKeyStatuses, 5000);
		return () => clearInterval(interval);
	});
</script>

<AuthGuard>
	<div class="container mx-auto p-2 sm:p-4">
		<h1 class="mb-4 text-2xl font-bold text-gray-800 sm:mb-6 sm:text-3xl">密钥管理</h1>

		<KeyActions {fetchKeyStatuses} {resetAllKeys} {addKeys} {loading} />

		<Notification message={notificationMessage} type={notificationType} />

		{#if errorMessage}
			<Notification message={errorMessage} type="error" />
		{:else}
			<KeyStatusSummary {keyStatuses} />
			<KeyList {keyStatuses} {resetKey} {deleteKey} />
		{/if}
	</div>
</AuthGuard>
