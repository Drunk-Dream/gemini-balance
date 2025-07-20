<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

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
			if (scrollHeight - scrollTop <= clientHeight + 50) {
				// 50px buffer
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

	function colorizeLog(logLine: string): string {
		const patterns = [
			{ regex: /(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})/, class: 'text-gray-400' }, // Timestamp
			{ regex: /\b(INFO)\b/, class: 'font-bold text-emerald-400' }, // Log Level INFO
			{ regex: /\b(ERROR)\b/, class: 'font-bold text-red-400' }, // Log Level ERROR
			{ regex: /\b(WARNING)\b/, class: 'font-bold text-amber-400' }, // Log Level WARNING
			{ regex: /\b(DEBUG)\b/, class: 'font-bold text-blue-400' }, // Log Level DEBUG
			{ regex: /\b(true)\b/gi, class: 'text-green-400' }, // Boolean true
			{ regex: /\b(false)\b/gi, class: 'text-red-400' }, // Boolean false
			{ regex: /(\.\.\.[a-zA-Z0-9]{4})\b/g, class: 'text-violet-400' }, // Key suffix
			{ regex: /\b(gemini-[\w.-]+|gpt-[\w.-]+)\b/g, class: 'text-pink-400' } // Model name
		];

		let coloredLogLine = logLine;
		for (const pattern of patterns) {
			coloredLogLine = coloredLogLine.replace(pattern.regex, `<span class="${pattern.class}">$&</span>`);
		}
		return coloredLogLine;
	}
</script>

<div class="container mx-auto p-4">
	<h1 class="mb-6 text-3xl font-bold text-gray-800">日志查看器</h1>

	{#if errorMessage}
		<div
			class="relative mb-4 rounded border border-red-400 bg-red-100 px-4 py-3 text-red-700"
			role="alert"
		>
			<strong class="font-bold">错误!</strong>
			<span class="block sm:inline"> {errorMessage}</span>
		</div>
	{/if}

	<div
		bind:this={logContainer}
		on:scroll={handleScroll}
		class="h-[calc(100vh-180px)] overflow-y-auto rounded-lg bg-gray-900 p-4 font-mono text-sm text-gray-100 shadow-md"
	>
		{#each logs as logLine}
			<p class="whitespace-pre-wrap break-words">{@html colorizeLog(logLine)}</p>
		{/each}
		{#if logs.length === 0 && !errorMessage}
			<p class="text-gray-500">等待日志数据...</p>
		{/if}
	</div>
</div>
