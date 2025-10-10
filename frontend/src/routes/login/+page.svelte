<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import type { ResolvedPathname } from '$app/types';
	import LoginForm from '$lib/features/auth/components/LoginForm.svelte';
	import { authToken, isAuthenticated } from '$lib/features/auth/store';
	import { onMount } from 'svelte';

	let password = $state('');
	let errorMessage: string | null = $state(null);
	let loading = $state(false);

	const redirectUrl = (page.url.searchParams.get('redirect') as ResolvedPathname) ?? resolve('/');

	onMount(() => {
		if ($isAuthenticated) {
			goto(redirectUrl);
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
			goto(redirectUrl);
		} catch (error: any) {
			errorMessage = `登录失败: ${error.message}`;
			console.error(errorMessage);
		} finally {
			loading = false;
		}
	}
</script>

<div class="bg-base-100 flex h-[calc(100vh-3rem)] items-center justify-center p-4 sm:p-6 lg:p-8">
	<LoginForm bind:password {handleLogin} {loading} {errorMessage} />
</div>
