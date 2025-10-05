<script lang="ts">
	// 导入 Notification 组件
	import Notification from '$lib/components/Notification.svelte';
	import { colorizeLog } from '$lib/features/logs/utils';
	import { tick } from 'svelte';

	let { logs, errorMessage }: { logs: string[]; errorMessage: string | null } = $props();

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

<div class="container mx-auto p-2 sm:p-4">
	<h1 class="mb-4 text-2xl font-bold text-gray-800 sm:mb-6 sm:text-3xl">日志查看器</h1>

	<Notification message={errorMessage} type="error" autoHide={false} />

	<div
		bind:this={logContainer}
		onscroll={handleScroll}
		class="h-[calc(100vh-180px)] overflow-y-auto rounded-lg bg-gray-900 p-2 font-mono text-sm text-gray-100 shadow-md sm:p-4"
	>
		{#each logs as logLine}
			<p class="whitespace-pre-wrap break-words">{@html colorizeLog(logLine)}</p>
		{/each}
		{#if logs.length === 0 && !errorMessage}
			<p class="text-gray-500">等待日志数据...</p>
		{/if}
	</div>

	{#if showScrollToBottomButton}
		<button
			onclick={forceScrollToBottom}
			class="fixed bottom-4 right-4 cursor-pointer rounded-full bg-blue-600 p-3 text-white shadow-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-75"
			aria-label="Scroll to bottom"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="h-6 w-6"
				fill="none"
				viewBox="0 0 24 24"
				stroke="currentColor"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M19 14l-7 7m0 0l-7-7m7 7V3"
				/>
			</svg>
		</button>
	{/if}
</div>
