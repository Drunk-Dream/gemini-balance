<script lang="ts">
	import { api } from '$lib/api';
	import Container from '$lib/components/Container.svelte';
	import Notification from '$lib/components/Notification.svelte';
	import type { NotificationObject } from '$lib/components/types';
	import AuthGuard from '$lib/features/auth/components/AuthGuard.svelte';
	import KeyActions from '$lib/features/request-keys/components/KeyActions.svelte';
	import KeyList from '$lib/features/request-keys/components/KeyList.svelte';
	import KeyStatusSummary from '$lib/features/request-keys/components/KeyStatusSummary.svelte';
	import type { KeyStatusResponse } from '$lib/features/request-keys/types';
	import { onMount } from 'svelte';

	let keyStatusResponse: KeyStatusResponse = $state({
		keys: [],
		total_keys_count: 0,
		in_use_keys_count: 0,
		cooled_down_keys_count: 0,
		available_keys_count: 0
	});
	let loading = $state(true);
	let notificationObject: NotificationObject = $state({
		message: '',
		type: 'success'
	});

	async function fetchKeyStatusResponse() {
		loading = true;
		try {
			const data = await api.get<KeyStatusResponse>('/keys/status');
			if (!data) {
				throw new Error('No response from the server');
			}
			keyStatusResponse = data;
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
			fetchKeyStatusResponse();
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
			fetchKeyStatusResponse();
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
			fetchKeyStatusResponse();
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
			fetchKeyStatusResponse();
		} catch (error: any) {
			notificationObject = {
				message: `重置所有密钥状态失败: ${error.message}`,
				type: 'error'
			};
			console.error('重置所有密钥状态失败:', error);
		}
	}

	onMount(() => {
		fetchKeyStatusResponse();
		const interval = setInterval(fetchKeyStatusResponse, 5000);
		return () => clearInterval(interval);
	});
</script>

<AuthGuard>
	<Container header="管理请求密钥">
		<KeyActions {fetchKeyStatusResponse} {resetAllKeys} {addKeys} {loading} />

		<Notification message={notificationObject.message} type={notificationObject.type} />

		<KeyStatusSummary {keyStatusResponse} />
		<KeyList keyStatuses={keyStatusResponse.keys} {resetKey} {deleteKey} />
	</Container>
</AuthGuard>
