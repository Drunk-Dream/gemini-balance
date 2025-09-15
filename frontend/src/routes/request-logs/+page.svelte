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
	let totalItems: number = $state(0);
	let totalPages: number = $state(1);

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

	function getPageNumbers(): (number | string)[] {
		const pageNumbers: (number | string)[] = [];
		const maxPagesToShow = 5; // 显示的页码数量 (例如: 1 ... 4 5 6 ... 10)

		if (totalPages <= maxPagesToShow) {
			for (let i = 1; i <= totalPages; i++) {
				pageNumbers.push(i);
			}
		} else {
			const startPage = Math.max(1, currentPage - Math.floor(maxPagesToShow / 2));
			const endPage = Math.min(totalPages, startPage + maxPagesToShow - 1);

			if (startPage > 1) {
				pageNumbers.push(1);
				if (startPage > 2) {
					pageNumbers.push('...');
				}
			}

			for (let i = startPage; i <= endPage; i++) {
				pageNumbers.push(i);
			}

			if (endPage < totalPages) {
				if (endPage < totalPages - 1) {
					pageNumbers.push('...');
				}
				pageNumbers.push(totalPages);
			}
		}
		return pageNumbers;
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

			<div
				class="mt-4 flex flex-col items-center justify-between space-y-4 md:flex-row md:space-y-0"
			>
				<button
					class="cursor-pointer rounded bg-blue-500 px-4 py-2 text-white disabled:opacity-50"
					onclick={goToPreviousPage}
					disabled={currentPage === 1}
				>
					上一页
				</button>

				<div class="flex flex-wrap items-center justify-center space-x-1">
					{#each getPageNumbers() as page}
						{#if page === '...'}
							<span class="px-2 py-1">...</span>
						{:else}
							<button
								class="cursor-pointer rounded px-3 py-1 {currentPage === page
									? 'bg-blue-700 text-white'
									: 'bg-blue-500 text-white'}"
								onclick={() => goToPage(page as number)}
							>
								{page}
							</button>
						{/if}
					{/each}
				</div>

				<div class="flex items-center space-x-2 text-sm md:text-base">
					<span class="whitespace-nowrap"
						>第 {currentPage} / {totalPages} 页 (共 {totalItems} 条)</span
					>
					<input
						type="number"
						min="1"
						max={totalPages}
						value={currentPage}
						onchange={(e) => goToPage(parseInt((e.target as HTMLInputElement).value))}
						class="w-16 rounded border p-1 text-center text-sm md:w-20 md:text-base"
					/>
				</div>

				<button
					class="cursor-pointer rounded bg-blue-500 px-4 py-2 text-white disabled:opacity-50"
					onclick={goToNextPage}
					disabled={currentPage === totalPages}
				>
					下一页
				</button>
			</div>
		{/if}
	</div>
</AuthGuard>
