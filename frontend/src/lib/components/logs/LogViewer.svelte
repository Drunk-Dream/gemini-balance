<script lang="ts">
	// 导入 Notification 组件
	import Notification from '$lib/components/common/Notification.svelte';
	import { colorizeLog } from '$lib/utils/logUtils';
	import { onMount } from 'svelte';

	let { logs, errorMessage }: { logs: string[]; errorMessage: string | null } = $props();

	let logContainer: HTMLElement;
	let autoScroll = true;
	let showScrollToBottomButton = $state(false);

	function scrollToBottom() {
		if (logContainer && autoScroll) {
			logContainer.scrollTop = logContainer.scrollHeight;
		}
	}

	function forceScrollToBottom() {
		if (logContainer) {
			logContainer.scrollTop = logContainer.scrollHeight;
			autoScroll = true; // Re-enable auto-scroll after manual scroll
		}
	}

	function handleScroll() {
		if (logContainer) {
			const { scrollTop, scrollHeight, clientHeight } = logContainer;
			if (scrollHeight - scrollTop <= clientHeight + 50) {
				autoScroll = true;
				showScrollToBottomButton = false;
			} else {
				autoScroll = false;
				showScrollToBottomButton = true;
			}
		}
	}

	onMount(() => {
		// Initial scroll to bottom
		scrollToBottom();
	});

	// React to log changes
	$effect(() => {
		scrollToBottom();
	});
</script>

<div class="container mx-auto p-2 sm:p-4">
	<h1 class="mb-4 text-2xl font-bold text-gray-800 sm:mb-6 sm:text-3xl">日志查看器</h1>

	<Notification message={errorMessage} type="error" />

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
			class="fixed bottom-4 right-4 rounded-full bg-blue-600 p-3 text-white shadow-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-75"
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
