<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { authToken, isAuthenticated } from '$lib/stores';
	import { onMount } from 'svelte';

	let password = '';
	let errorMessage: string | null = null;
	let loading = false;

	onMount(() => {
		// 如果已经认证，则直接跳转到主页
		if ($isAuthenticated) {
			goto($page.url.searchParams.get('redirect') || '/');
		}
	});

	async function handleLogin() {
		loading = true;
		errorMessage = null;
		try {
			const response = await fetch('/api/login', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/x-www-form-urlencoded'
				},
				body: `username=user&password=${encodeURIComponent(password)}` // 假设用户名为 'user'
			});

			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
			}

			const data = await response.json();
			authToken.set(data.access_token); // 存储令牌
			isAuthenticated.set(true); // 设置认证状态
			goto($page.url.searchParams.get('redirect') || '/'); // 登录成功后跳转到之前的页面或主页
		} catch (error: any) {
			errorMessage = `登录失败: ${error.message}`;
			console.error(errorMessage);
		} finally {
			loading = false;
		}
	}
</script>

<div class="flex min-h-screen items-center justify-center bg-gray-100 p-4">
	<div class="w-full max-w-md rounded-lg bg-white p-6 shadow-md">
		<h1 class="mb-6 text-center text-2xl font-bold text-gray-800">登录</h1>

		{#if errorMessage}
			<div
				class="relative mb-4 rounded border border-red-400 bg-red-100 px-4 py-3 text-red-700"
				role="alert"
			>
				<strong class="font-bold">错误!</strong>
				<span class="block sm:inline"> {errorMessage}</span>
			</div>
		{/if}

		<form on:submit|preventDefault={handleLogin}>
			<div class="mb-4">
				<label for="password" class="mb-2 block text-sm font-bold text-gray-700">密码:</label>
				<input
					type="password"
					id="password"
					bind:value={password}
					required
					class="focus:shadow-outline w-full appearance-none rounded border px-3 py-2 leading-tight text-gray-700 shadow focus:outline-none"
					placeholder="请输入密码"
				/>
			</div>
			<div class="flex items-center justify-between">
				<button
					type="submit"
					class="focus:shadow-outline rounded bg-blue-500 px-4 py-2 font-bold text-white hover:bg-blue-700 focus:outline-none"
					disabled={loading}
				>
					{loading ? '登录中...' : '登录'}
				</button>
			</div>
		</form>
	</div>
</div>
