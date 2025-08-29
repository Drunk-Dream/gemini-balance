<script lang="ts">
	import KeyCard from './KeyCard.svelte';

	interface KeyStatus {
		key_identifier: string;
		status: string;
		cool_down_seconds_remaining: number;
		daily_usage: { [model: string]: number };
		failure_count: number;
		cool_down_entry_count: number;
		current_cool_down_seconds: number;
	}

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
		<KeyCard {keyStatus} {resetKey} {deleteKey} />
	{/each}
</div>

{#if keyStatuses.length === 0}
	<p class="text-gray-600">没有可用的密钥状态信息。</p>
{/if}
