<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

	let logs: string[] = [];
	let eventSource: EventSource | null = null;
	let errorMessage: string | null = null;
	let logContainer: HTMLElement;
	let autoScroll = true;
	let showScrollToBottomButton = false;

	// 指数退避重连相关变量
	const BASE_RECONNECT_DELAY = 1000; // 初始重连延迟（毫秒）
	const MAX_RECONNECT_DELAY = 30000; // 最大重连延迟（毫秒）
	let reconnectAttempts = 0; // 重连尝试次数

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
			// If scrolled near the bottom, re-enable auto-scroll
			if (scrollHeight - scrollTop <= clientHeight + 50) {
				// 50px buffer
				autoScroll = true;
				showScrollToBottomButton = false;
			} else {
				autoScroll = false;
				showScrollToBottomButton = true;
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
				reconnectAttempts = 0; // 连接成功时重置重连尝试次数
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

				// 计算指数退避延迟
				const delay = Math.min(
					MAX_RECONNECT_DELAY,
					BASE_RECONNECT_DELAY * Math.pow(2, reconnectAttempts)
				);
				reconnectAttempts++; // 增加重连尝试次数

				console.log(`Attempting to reconnect in ${delay / 1000} seconds...`);
				setTimeout(connectSSE, delay); // 尝试在计算出的延迟后重连
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
			{ regex: /(key_sha256_[a-zA-Z0-9]{8})\b/g, class: 'text-violet-400' }, // Key suffix
			{ regex: /\b(gemini-[\w.-]+|gpt-[\w.-]+)\b/g, class: 'text-pink-400' } // Model name
		];

		let coloredLogLine = logLine;
		for (const pattern of patterns) {
			coloredLogLine = coloredLogLine.replace(
				pattern.regex,
				`<span class="${pattern.class}">$&</span>`
			);
		}
		return coloredLogLine;
	}
</script>

<div class="container mx-auto p-2 sm:p-4">
	<h1 class="mb-4 text-2xl font-bold text-gray-800 sm:mb-6 sm:text-3xl">日志查看器</h1>

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
			on:click={forceScrollToBottom}
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
