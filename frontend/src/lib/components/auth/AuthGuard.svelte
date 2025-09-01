<script lang="ts">
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { isAuthenticated } from '$lib/stores/auth';
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';

	onMount(async () => {
		if (browser) {
			const authenticated = get(isAuthenticated);
			if (!authenticated) {
				goto('/login');
			}
		}
	});
</script>

{#if get(isAuthenticated)}
	<slot />
{/if}
