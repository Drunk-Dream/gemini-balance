<script lang="ts">
	import AddAuthKeyForm from '$lib/components/auth-keys/AddAuthKeyForm.svelte';
	import AuthKeyTable from '$lib/components/auth-keys/AuthKeyTable.svelte';
	import AuthGuard from '$lib/components/auth/AuthGuard.svelte';
	import Notification from '$lib/components/common/Notification.svelte';
	import { api } from '$lib/utils/api';
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
	let errorMessage: string | null = $state(null);
	let successMessage: string | null = $state(null);

	onMount(() => {
		fetchAuthKeys();
	});

	async function fetchAuthKeys() {
		errorMessage = null;
		successMessage = null;
		try {
			const data = await api.get<AuthKey[]>('/auth_keys');
			if (!data) {
				throw new Error('Failed to fetch auth keys');
			}
			authKeys = data;
		} catch (error) {
			console.error('Error fetching auth keys:', error);
			errorMessage = '网络错误或服务器无响应。';
		}
	}

	async function createAuthKey() {
		errorMessage = null;
		successMessage = null;
		if (!newAlias.trim()) {
			errorMessage = '别名不能为空。';
			return;
		}
		try {
			const newKey = await api.post<AuthKey>('/auth_keys', { alias: newAlias });
			if (!newKey) {
				throw new Error('Failed to create auth key');
			}
			authKeys = [...authKeys, newKey];
			newAlias = '';
			successMessage = `密钥 "${newKey.alias}" 创建成功！API Key: ${newKey.api_key}`;
		} catch (error) {
			console.error('Error creating auth key:', error);
			errorMessage = '网络错误或服务器无响应。';
		}
	}

	function startEdit(key: AuthKey) {
		editingKey = key;
		editingAlias = key.alias;
		errorMessage = null;
		successMessage = null;
	}

	async function updateAuthKey() {
		errorMessage = null;
		successMessage = null;
		if (!editingKey) return;
		if (!editingAlias.trim()) {
			errorMessage = '别名不能为空。';
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
			successMessage = `密钥 "${updatedKey.alias}" 更新成功！`;
		} catch (error) {
			console.error('Error updating auth key:', error);
			errorMessage = '网络错误或服务器无响应。';
		}
	}

	function cancelEdit() {
		editingKey = null;
		editingAlias = '';
		errorMessage = null;
		successMessage = null;
	}

	async function deleteAuthKey(api_key: string) {
		errorMessage = null;
		successMessage = null;
		if (!confirm('确定要删除此密钥吗？此操作不可逆！')) {
			return;
		}
		try {
			await api.delete(`/auth_keys/${api_key}`);
			authKeys = authKeys.filter((k) => k.api_key !== api_key);
			successMessage = '密钥删除成功！';
		} catch (error) {
			console.error('Error deleting auth key:', error);
			errorMessage = '网络错误或服务器无响应。';
		}
	}
</script>

<AuthGuard>
	<div class="container mx-auto p-4 md:p-8">
		<h1 class="mb-6 text-2xl font-bold">管理认证密钥</h1>

		<Notification message={successMessage} type="success" />
		<Notification message={errorMessage} type="error" />

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
