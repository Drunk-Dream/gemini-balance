<script lang="ts">
	import AddAuthKeyForm from '$lib/components/auth-keys/AddAuthKeyForm.svelte';
	import AuthKeyTable from '$lib/components/auth-keys/AuthKeyTable.svelte';
	import AuthGuard from '$lib/components/auth/AuthGuard.svelte';
	import Notification from '$lib/components/common/Notification.svelte';
	import { authToken } from '$lib/stores';
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';

	interface AuthKey {
		api_key: string;
		alias: string;
		call_count: number;
	}

	let authKeys: AuthKey[] = [];
	let newAlias: string = '';
	let editingKey: AuthKey | null = null;
	let editingAlias: string = '';
	let errorMessage: string | null = null;
	let successMessage: string | null = null;

	onMount(() => {
		fetchAuthKeys();
	});

	async function fetchAuthKeys() {
		errorMessage = null;
		successMessage = null;
		try {
			const response = await fetch(`/api/auth_keys`, {
				headers: {
					Authorization: `Bearer ${get(authToken)}`
				}
			});
			if (response.status === 401 || response.status === 403) {
				authToken.set(null); // 清除认证状态，AuthGuard 会处理重定向
				return;
			}
			if (response.ok) {
				authKeys = await response.json();
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
		errorMessage = null;
		successMessage = null;
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
				authToken.set(null); // 清除认证状态，AuthGuard 会处理重定向
				return;
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
				authToken.set(null); // 清除认证状态，AuthGuard 会处理重定向
				return;
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
				authToken.set(null); // 清除认证状态，AuthGuard 会处理重定向
				return;
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
