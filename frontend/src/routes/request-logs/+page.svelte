<script lang="ts">
	import AuthGuard from '$lib/components/auth/AuthGuard.svelte';
	import Notification from '$lib/components/common/Notification.svelte';
	import Pagination from '$lib/components/common/Pagination.svelte';
	import RequestLogTable from '$lib/components/logs/RequestLogTable.svelte';
	import { getRequestLogs } from '$lib/services/requestLogs';

	let logs: any[] = $state([]);
	let loading: boolean = $state(true);
	let error: string | null = $state(null);
	let currentPage: number = $state(1);
	const itemsPerPage: number = 15;
	let totalItems: number = $state(0);
	let totalPages: number = $state(1);

	function goToPreviousPage() {
		if (currentPage > 1) {
			currentPage--;
		}
	}

	function goToNextPage() {
		if (currentPage < totalPages) {
			currentPage++;
		}
	}

	function goToPage(page: number) {
		if (page >= 1 && page <= totalPages) {
			currentPage = page;
		}
	}

	async function fetchLogs() {
		loading = true;
		error = null;
		try {
			const offset = (currentPage - 1) * itemsPerPage;
			const response = await getRequestLogs({ limit: itemsPerPage, offset });
			logs = response.logs;
			totalItems = response.total;
			totalPages = Math.ceil(totalItems / itemsPerPage);
		} catch (e: any) {
			error = e.message;
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		fetchLogs();
	});
</script>

<AuthGuard>
	<div class="container mx-auto p-4">
		<h1 class="mb-4 text-2xl font-bold">请求日志</h1>

		<Notification message={error} type="error" autoHide={false} />

		{#if loading}
			<p>加载中...</p>
		{:else if logs.length === 0}
			<p class="text-gray-500">没有找到任何请求日志。</p>
		{:else}
			<RequestLogTable {logs} />

			<Pagination
				{currentPage}
				{totalPages}
				{totalItems}
				{goToPreviousPage}
				{goToNextPage}
				{goToPage}
			/>
		{/if}
	</div>
</AuthGuard>
