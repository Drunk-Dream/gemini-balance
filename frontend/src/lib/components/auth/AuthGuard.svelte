<script lang="ts">
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { isAuthenticated } from '$lib/stores';

	let { children } = $props();

	$effect(() => {
		if (browser && !$isAuthenticated) {
			goto('/login/?redirect=' + page.url.pathname);
		}
	});
</script>

{#if $isAuthenticated}
	{@render children?.()}
{/if}
