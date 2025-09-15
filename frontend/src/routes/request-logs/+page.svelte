<script lang="ts">
	import AuthGuard from '$lib/components/auth/AuthGuard.svelte';
	import Notification from '$lib/components/common/Notification.svelte';
	import RequestLogTable from '$lib/components/logs/RequestLogTable.svelte';
	import { getRequestLogs } from '$lib/services/requestLogs';

	let logs: any[] = $state([]);
	let loading: boolean = $state(true);
	let error: string | null = $state(null);
	let currentPage: number = $state(1);
	const itemsPerPage: number = 15;
	let hasMore: boolean = $state(true); // 用于判断是否有更多页

	async function fetchLogs() {
		loading = true;
		error = null;
		try {
			const offset = (currentPage - 1) * itemsPerPage;
			const fetchedLogs = await getRequestLogs({ limit: itemsPerPage, offset });
			logs = fetchedLogs;
			hasMore = fetchedLogs.length === itemsPerPage; // 如果获取到的数量等于每页数量，说明可能还有更多
		} catch (e: any) {
			error = e.message;
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		fetchLogs();
	});

	function goToPreviousPage() {
		if (currentPage > 1) {
			currentPage--;
		}
	}

	function goToNextPage() {
		if (hasMore) {
			currentPage++;
		}
	}
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

			<div class="mt-4 flex items-center justify-between">
				<button
					class="rounded bg-blue-500 px-4 py-2 text-white disabled:opacity-50"
					onclick={goToPreviousPage}
					disabled={currentPage === 1}
				>
					上一页
				</button>
				<span>第 {currentPage} 页</span>
				<button
					class="rounded bg-blue-500 px-4 py-2 text-white disabled:opacity-50"
					onclick={goToNextPage}
					disabled={!hasMore}
				>
					下一页
				</button>
			</div>
		{/if}
	</div>
</AuthGuard>
