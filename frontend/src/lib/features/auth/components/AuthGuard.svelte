<script lang="ts">
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { isAuthenticated } from '$lib/features/auth/store';

	let { children } = $props();

	$effect(() => {
		if (browser && !$isAuthenticated) {
			goto(resolve('/login') + '/?redirect=' + page.url.pathname);
		}
	});
</script>

{#if $isAuthenticated}
	{@render children?.()}
{/if}
