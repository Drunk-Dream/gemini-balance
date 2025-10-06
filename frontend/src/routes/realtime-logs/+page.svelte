<script lang="ts">
	import Container from '$lib/components/Container.svelte';
	import Notification from '$lib/components/Notification.svelte';
	import AuthGuard from '$lib/features/auth/components/AuthGuard.svelte';
	import LogViewer from '$lib/features/realtime-logs/components/LogViewer.svelte';
	import { onDestroy, onMount } from 'svelte';

	let logs: string[] = $state([]);
	let errorMessage: string | null = $state(null);
	let eventSource: EventSource | null = null;

	const BASE_RECONNECT_DELAY = 1000;
	const MAX_RECONNECT_DELAY = 30000;
	let reconnectAttempts = 0;

	onMount(() => {
		const connectSSE = () => {
			errorMessage = null;
			eventSource = new EventSource(`/api/status/logs/sse`);

			eventSource.onopen = () => {
				console.log('SSE connection opened for logs.');
				logs = [];
				reconnectAttempts = 0;
			};

			eventSource.onmessage = (event) => {
				let parsedData;
				try {
					parsedData = JSON.parse(event.data);
					logs = [...logs, parsedData.message || event.data];
				} catch (e) {
					logs = [...logs, event.data];
				}
			};

			eventSource.onerror = (error) => {
				console.error('SSE error:', error);
				if (reconnectAttempts >= 3) {
					errorMessage = 'SSE error. Check console for details. Attempting to reconnect...';
				}
				if (eventSource) eventSource.close();

				const delay = Math.min(
					MAX_RECONNECT_DELAY,
					BASE_RECONNECT_DELAY * Math.pow(2, reconnectAttempts)
				);
				reconnectAttempts++;

				console.log(`Attempting to reconnect in ${delay / 1000} seconds...`);
				setTimeout(connectSSE, delay);
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

<AuthGuard>
	<Container header="实时日志">
		<Notification message={errorMessage} type="error" autoHide={false} />

		<LogViewer {logs} />
	</Container>
</AuthGuard>
