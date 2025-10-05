<script lang="ts">
	import Notification from '$lib/components/Notification.svelte';
	import AuthGuard from '$lib/features/auth/components/AuthGuard.svelte';
	import KeyActions from '$lib/features/key-management/components/KeyActions.svelte';
	import KeyList from '$lib/features/key-management/components/KeyList.svelte';
	import KeyStatusSummary from '$lib/features/key-management/components/KeyStatusSummary.svelte';
	import type { KeyStatus } from '$lib/features/key-management/types';
// 导入 Notification 组件
	import { api } from '$lib/api';
	import type { NotificationObject } from '$lib/components/types';
	import { onMount } from 'svelte';

	let keyStatuses: KeyStatus[] = $state([]);
	let loading = $state(true);
	let notificationObject: NotificationObject = $state({
		message: '',
		type: 'success'
	});

	async function fetchKeyStatuses() {
		loading = true;
		try {
			const data = await api.get<{ keys: KeyStatus[] }>('/status/keys');
			if (!data) {
				throw new Error('No response from the server');
			}
			keyStatuses = data.keys;
		} catch (error: any) {
			notificationObject = {
				message: `获取密钥状态失败: ${error.message}`,
				type: 'error'
			};
		} finally {
			loading = false;
		}
	}

	async function addKeys(keysInput: string) {
		if (!keysInput.trim()) {
			notificationObject = {
				message: '请输入密钥',
				type: 'error'
			};
			return;
		}
		const keysArray = keysInput
			.split('\n')
			.map((key) => key.trim())
			.filter((key) => key);
		if (keysArray.length === 0) {
			notificationObject = {
				message: '请输入有效的密钥',
				type: 'error'
			};
			return;
		}
		try {
			await api.post('/keys', { api_keys: keysArray });
			notificationObject = {
				message: '密钥添加成功！',
				type: 'success'
			};
			fetchKeyStatuses();
		} catch (error: any) {
			notificationObject = {
				message: `添加密钥失败: ${error.message}`,
				type: 'error'
			};
			console.error('添加密钥失败:', error);
		}
	}

	async function deleteKey(keyIdentifier: string) {
		if (!confirm(`确定要删除密钥标识符为 "${keyIdentifier}" 的密钥吗？`)) {
			return;
		}
		try {
			await api.delete(`/keys/${keyIdentifier}`);
			notificationObject = {
				message: `密钥 "${keyIdentifier}" 删除成功！`,
				type: 'success'
			};
			fetchKeyStatuses();
		} catch (error: any) {
			notificationObject = {
				message: `删除密钥失败: ${error.message}`,
				type: 'error'
			};
			console.error('删除密钥失败:', error);
		}
	}

	async function resetKey(keyIdentifier: string) {
		if (!confirm(`确定要重置密钥标识符为 "${keyIdentifier}" 的密钥状态吗？`)) {
			return;
		}
		try {
			await api.post(`/keys/${keyIdentifier}/reset`, {});
			notificationObject = {
				message: `密钥 "${keyIdentifier}" 状态重置成功！`,
				type: 'success'
			};
			fetchKeyStatuses();
		} catch (error: any) {
			notificationObject = {
				message: `重置密钥状态失败: ${error.message}`,
				type: 'error'
			};
			console.error('重置密钥状态失败:', error);
		}
	}

	async function resetAllKeys() {
		if (!confirm('确定要重置所有密钥的状态吗？此操作不可逆！')) {
			return;
		}
		try {
			await api.post('/keys/reset', {});
			notificationObject = {
				message: '所有密钥状态重置成功！',
				type: 'success'
			};
			fetchKeyStatuses();
		} catch (error: any) {
			notificationObject = {
				message: `重置所有密钥状态失败: ${error.message}`,
				type: 'error'
			};
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

		<Notification message={notificationObject.message} type={notificationObject.type} />

		<KeyStatusSummary {keyStatuses} />
		<KeyList {keyStatuses} {resetKey} {deleteKey} />
	</div>
</AuthGuard>
