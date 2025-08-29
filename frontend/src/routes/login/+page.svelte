<script lang="ts">
	import { goto } from '$app/navigation';
	import LoginForm from '$lib/components/auth/LoginForm.svelte';
	import { authToken, isAuthenticated } from '$lib/stores';
	import { onMount } from 'svelte';

	let password = '';
	let errorMessage: string | null = null;
	let loading = false;

	onMount(() => {
		if ($isAuthenticated) {
			goto('/');
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
				body: `username=user&password=${encodeURIComponent(password)}`
			});

			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
			}

			const data = await response.json();
			authToken.set(data.access_token);
			isAuthenticated.set(true);
			goto('/');
		} catch (error: any) {
			errorMessage = `登录失败: ${error.message}`;
			console.error(errorMessage);
		} finally {
			loading = false;
		}
	}
</script>

<div class="flex min-h-screen items-center justify-center bg-gray-100 p-4">
	<LoginForm bind:password {handleLogin} {loading} {errorMessage} />
</div>
