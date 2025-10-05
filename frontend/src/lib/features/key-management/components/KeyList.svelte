<script lang="ts">
	import type { KeyStatus } from '$lib/features/key-management/types';
	import { flip } from 'svelte/animate';
	import { quintOut } from 'svelte/easing';
	import KeyCard from './KeyCard.svelte';

	let {
		keyStatuses,
		resetKey,
		deleteKey
	}: {
		keyStatuses: KeyStatus[];
		resetKey: (keyIdentifier: string) => Promise<void>;
		deleteKey: (keyIdentifier: string) => Promise<void>;
	} = $props();
</script>

<div class="grid gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
	{#each keyStatuses as keyStatus (keyStatus.key_identifier)}
		<div animate:flip={{ easing: quintOut }}>
			<KeyCard {keyStatus} {resetKey} {deleteKey} />
		</div>
	{/each}
</div>

{#if keyStatuses.length === 0}
	<p class="text-gray-600">没有可用的密钥状态信息。</p>
{/if}
