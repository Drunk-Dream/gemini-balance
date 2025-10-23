<script lang="ts">
	import type { KeyStatus } from '$lib/features/request-keys/types';
	import { flip } from 'svelte/animate';
	import { quintOut } from 'svelte/easing';
	import KeyCard from './KeyCard.svelte';

	let {
		keyStatuses,
		resetKey,
		deleteKey
	}: {
		keyStatuses: KeyStatus[];
		resetKey: (key: { identifier: string; brief: string }) => Promise<void>;
		deleteKey: (key: { identifier: string; brief: string }) => Promise<void>;
	} = $props();
</script>

<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
	{#each keyStatuses as keyStatus (keyStatus.key_identifier)}
		<div animate:flip={{ easing: quintOut }}>
			<KeyCard {keyStatus} {resetKey} {deleteKey} />
		</div>
	{/each}
</div>

{#if keyStatuses.length === 0}
	<p class="text-muted-foreground">没有可用的密钥状态信息。</p>
{/if}
