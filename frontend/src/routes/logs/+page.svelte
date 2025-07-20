<script lang="ts">
	import { onMount, onDestroy } from 'svelte';

	let logs: string[] = [];
	let eventSource: EventSource | null = null;
	let errorMessage: string | null = null;
	let logContainer: HTMLElement;
	let autoScroll = true;

	function scrollToBottom() {
		if (logContainer && autoScroll) {
			logContainer.scrollTop = logContainer.scrollHeight;
		}
	}

	function handleScroll() {
		if (logContainer) {
			const { scrollTop, scrollHeight, clientHeight } = logContainer;
			// If scrolled near the bottom, re-enable auto-scroll
			if (scrollHeight - scrollTop <= clientHeight + 50) { // 50px buffer
				autoScroll = true;
			} else {
				autoScroll = false;
			}
		}
	}

	onMount(() => {
		const connectSSE = () => {
			errorMessage = null;
			eventSource = new EventSource(`/api/status/logs/sse`);

			eventSource.onopen = () => {
				console.log('SSE connection opened for logs.');
				logs = []; // Clear logs on new connection
			};

			eventSource.onmessage = (event) => {
				let parsedData;
				try {
					parsedData = JSON.parse(event.data);
					// Assuming the actual log message is in a 'message' field if it's JSON
					// Adjust this based on actual backend JSON structure if it changes
					logs = [...logs, parsedData.message || event.data];
				} catch (e) {
					// If not JSON, treat as plain text
					logs = [...logs, event.data];
				}
				scrollToBottom();
			};

			eventSource.onerror = (error) => {
				console.error('SSE error:', error);
				errorMessage = 'SSE error. Check console for details. Attempting to reconnect...';
				if (eventSource) eventSource.close(); // Close to trigger reconnect
				setTimeout(connectSSE, 3000); // Attempt to reconnect after a delay
			};
		};

		connectSSE();

		return () => {
			if (eventSource) {
				eventSource.close();
			}
		};
	});

	onDestroy(() => {
		if (eventSource) {
			eventSource.close();
		}
	});
</script>

<div class="container mx-auto p-4">
	<h1 class="text-3xl font-bold mb-6 text-gray-800">日志查看器</h1>

	{#if errorMessage}
		<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
			<strong class="font-bold">错误!</strong>
			<span class="block sm:inline"> {errorMessage}</span>
		</div>
	{/if}

	<div
		bind:this={logContainer}
		on:scroll={handleScroll}
		class="bg-gray-900 text-gray-100 p-4 rounded-lg shadow-md font-mono text-sm overflow-y-auto h-[calc(100vh-180px)]"
	>
		{#each logs as logLine, i}
			<p class="whitespace-pre-wrap break-words">{logLine}</p>
		{/each}
		{#if logs.length === 0 && !errorMessage}
			<p class="text-gray-500">等待日志数据...</p>
		{/if}
	</div>
</div>
