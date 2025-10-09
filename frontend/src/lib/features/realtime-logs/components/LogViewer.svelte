<script lang="ts">
	import { colorizeLog } from '$lib/features/realtime-logs/utils';
	import ArrowDown from 'phosphor-svelte/lib/ArrowDown';
	import { tick } from 'svelte';

	let { logs }: { logs: string[] } = $props();

	let logContainer: HTMLElement;
	let showScrollToBottomButton = $state(false);
	let autoScroll = $state(true); // New state to control auto-scrolling

	function scrollToBottom() {
		if (logContainer) {
			logContainer.scrollTop = logContainer.scrollHeight;
		}
	}

	function forceScrollToBottom() {
		if (logContainer) {
			logContainer.scrollTop = logContainer.scrollHeight;
			showScrollToBottomButton = false; // Hide button after manual scroll
			autoScroll = true; // Re-enable auto-scroll after manual scroll
		}
	}

	function handleScroll() {
		if (logContainer) {
			const { scrollTop, scrollHeight, clientHeight } = logContainer;
			// Show scroll to bottom button if not at the very bottom
			showScrollToBottomButton = scrollHeight - scrollTop > clientHeight + 50;

			// Disable auto-scroll if user scrolls up
			if (scrollHeight - scrollTop > clientHeight + 100) {
				// A bit more buffer to disable auto-scroll
				autoScroll = false;
			} else if (scrollHeight - scrollTop <= clientHeight + 50) {
				// Re-enable if user scrolls back to bottom
				autoScroll = true;
			}
		}
	}

	// React to log changes and scroll AFTER DOM updates
	$effect(() => {
		// By accessing `logs`, we ensure this effect re-runs whenever the logs change.
		logs;

		// We need to wait for the DOM to update after `logs` changes.
		// Using an async IIFE because $effect must be synchronous.
		(async () => {
			await tick(); // Ensure DOM is updated with new logs before scrolling

			// Only scroll if autoScroll is enabled
			if (autoScroll) {
				scrollToBottom();
			}
		})();
	});
</script>

<div
	bind:this={logContainer}
	onscroll={handleScroll}
	class="h-[calc(100vh-180px)] overflow-y-auto rounded-lg bg-gray-900 p-2 font-mono text-sm text-gray-100 shadow-md sm:p-4"
>
	{#each logs as logLine}
		<p class="whitespace-pre-wrap break-words">{@html colorizeLog(logLine)}</p>
	{/each}
	{#if logs.length === 0}
		<p class="text-gray-500">等待日志数据...</p>
	{/if}
</div>

{#if showScrollToBottomButton}
	<button
		onclick={forceScrollToBottom}
		class="btn btn-circle btn-primary fixed right-4 bottom-4"
		aria-label="Scroll to bottom"
	>
		<ArrowDown class="size-6" />
	</button>
{/if}
