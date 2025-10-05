<script lang="ts">
	import { api } from '$lib/api';
	import Notification from '$lib/components/Notification.svelte';
	import type { NotificationObject } from '$lib/components/types';
	import AddAuthKeyForm from '$lib/features/auth-keys/components/AddAuthKeyForm.svelte';
	import AuthKeyTable from '$lib/features/auth-keys/components/AuthKeyTable.svelte';
	import AuthGuard from '$lib/features/auth/components/AuthGuard.svelte';
	import { onMount } from 'svelte';

	interface AuthKey {
		api_key: string;
		alias: string;
		call_count: number;
	}

	let authKeys: AuthKey[] = $state([]);
	let newAlias: string = $state('');
	let editingKey: AuthKey | null = $state(null);
	let editingAlias: string = $state('');
	let notificationObject: NotificationObject = $state({ message: '', type: 'success' });

	onMount(() => {
		fetchAuthKeys();
	});

	async function fetchAuthKeys() {
		try {
			const data = await api.get<AuthKey[]>('/auth_keys');
			if (!data) {
				throw new Error('Failed to fetch auth keys');
			}
			authKeys = data;
		} catch (error) {
			console.error('Error fetching auth keys:', error);
			notificationObject = {
				message: '网络错误或服务器无响应。',
				type: 'error'
			};
		}
	}

	async function createAuthKey() {
		if (!newAlias.trim()) {
			notificationObject = {
				message: '别名不能为空。',
				type: 'error'
			};
			return;
		}
		try {
			const newKey = await api.post<AuthKey>('/auth_keys', { alias: newAlias });
			if (!newKey) {
				throw new Error('Failed to create auth key');
			}
			authKeys = [...authKeys, newKey];
			newAlias = '';
			notificationObject = {
				message: `密钥 "${newKey.alias}" 创建成功！API Key: ${newKey.api_key}`,
				type: 'success'
			};
		} catch (error) {
			notificationObject = {
				message: '网络错误或服务器无响应。',
				type: 'error'
			};
			if (error instanceof Error) {
				notificationObject.message = error.message;
			}
			console.error('Error creating auth key:', error);
		}
	}

	function startEdit(key: AuthKey) {
		editingKey = key;
		editingAlias = key.alias;
	}

	async function updateAuthKey() {
		if (!editingKey) return;
		if (!editingAlias.trim()) {
			notificationObject = {
				message: '别名不能为空。',
				type: 'error'
			};
			return;
		}
		try {
			const updatedKey = await api.put<AuthKey>(`/auth_keys/${editingKey.api_key}`, {
				alias: editingAlias
			});
			if (!updatedKey) {
				throw new Error('Failed to update auth key');
			}
			authKeys = authKeys.map((k) => (k.api_key === updatedKey.api_key ? updatedKey : k));
			editingKey = null;
			editingAlias = '';
			notificationObject = {
				message: `密钥 "${updatedKey.alias}" 更新成功！`,
				type: 'success'
			};
		} catch (error) {
			notificationObject = {
				message: '网络错误或服务器无响应。',
				type: 'error'
			};
			if (error instanceof Error) {
				notificationObject.message = error.message;
			}
			console.error('Error updating auth key:', error);
		}
	}

	function cancelEdit() {
		editingKey = null;
		editingAlias = '';
	}

	async function deleteAuthKey(api_key: string) {
		if (!confirm('确定要删除此密钥吗？此操作不可逆！')) {
			return;
		}
		try {
			await api.delete(`/auth_keys/${api_key}`);
			authKeys = authKeys.filter((k) => k.api_key !== api_key);
			notificationObject = {
				message: '密钥删除成功！',
				type: 'success'
			};
		} catch (error) {
			notificationObject = {
				message: '网络错误或服务器无响应。',
				type: 'error'
			};
			if (error instanceof Error) {
				notificationObject.message = error.message;
			}
			console.error('Error deleting auth key:', error);
		}
	}
</script>

<AuthGuard>
	<div class="container mx-auto p-4 md:p-8">
		<h1 class="mb-6 text-2xl font-bold">管理认证密钥</h1>

		<Notification message={notificationObject.message} type={notificationObject.type} />

		<AddAuthKeyForm bind:newAlias {createAuthKey} />

		<AuthKeyTable
			{authKeys}
			{editingKey}
			bind:editingAlias
			{startEdit}
			{updateAuthKey}
			{cancelEdit}
			{deleteAuthKey}
		/>
	</div>
</AuthGuard>
