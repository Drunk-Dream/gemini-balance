<script lang="ts">
	import AuthGuard from '$lib/components/auth/AuthGuard.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import Notification from '$lib/components/common/Notification.svelte';
	import Pagination from '$lib/components/common/Pagination.svelte';
	import RequestLogFilters from '$lib/components/logs/RequestLogFilters.svelte';
	import RequestLogTable from '$lib/components/logs/RequestLogTable.svelte';
	import {
		formatToLocalDateTimeString,
		getRequestLogs,
		type GetRequestLogsParams,
		type RequestLog
	} from '$lib/services/requestLogs';
	import { TZDate } from '@date-fns/tz';

	let logs: RequestLog[] = $state([]);
	let error: string | null = $state(null);
	let currentPage: number = $state(1);
	const itemsPerPage: number = 15;
	let totalItems: number = $state(0);
	let filter_choices: {
		key_identifiers?: string[];
		auth_key_aliases?: string[];
		model_names?: string[];
	} = $state({});

	const today = new Date();
	today.setHours(0, 0, 0, 0);

	const endOfDay = new Date();
	endOfDay.setHours(23, 59, 59, 999);

	let request_time_range = $state<[Date, Date]>([today, endOfDay]);

	let filters = $state<GetRequestLogsParams>({
		request_time_start: formatToLocalDateTimeString(today),
		request_time_end: formatToLocalDateTimeString(endOfDay)
	});

	// 用于存储 filters 的上一个状态，以便检测 filters 是否真正发生变化
	let previousFilters: GetRequestLogsParams | null = null;
	let previousPage: number = 0;

	async function fetchLogs() {
		error = null;
		try {
			const offset = (currentPage - 1) * itemsPerPage;

			// 预处理筛选参数，防止将空字符串传递给 API
			const processedFilters: GetRequestLogsParams = {
				...filters,
				request_time_start: new TZDate(filters.request_time_start).toISOString(),
				request_time_end: new TZDate(filters.request_time_end).toISOString()
			};

			const params: GetRequestLogsParams = {
				limit: itemsPerPage,
				offset,
				...processedFilters
			};

			const response = await getRequestLogs(params);
			logs = response.logs;
			totalItems = response.total;
			filter_choices = {
				key_identifiers: response.key_identifiers,
				auth_key_aliases: response.auth_key_aliases,
				model_names: response.model_names
			};
			if (response.request_time_range) {
				request_time_range = [
					new Date(response.request_time_range[0]),
					new Date(response.request_time_range[1])
				];
			}
		} catch (e: any) {
			error = e.message;
		}
	}

	// 当 filters 或 currentPage 变化时，获取日志
	$effect(() => {
		// 检查 filters 是否发生变化（不包括 currentPage 的变化）
		// 这里使用 JSON.stringify 进行浅比较，对于 filters 这种简单对象通常足够
		// 如果 filters 包含嵌套对象，需要更复杂的深比较逻辑
		const filtersChanged = JSON.stringify(filters) !== JSON.stringify(previousFilters ?? {});
		if (filtersChanged) {
			previousFilters = { ...filters }; // 更新 previousFilters
			currentPage = 1; // 筛选条件变化时，重置页码为 1
		}

		const pageChanged = currentPage !== previousPage;
		if (pageChanged) {
			previousPage = currentPage; // 更新 previousPage
		}

		if ((filtersChanged || pageChanged) && filters.request_time_start && filters.request_time_end) {
			fetchLogs();
		}
	});
</script>

<AuthGuard>
	<div class="container mx-auto p-4">
		<h1 class="mb-4 text-2xl font-bold">请求日志</h1>

		<Collapsible buttonText="Filters" open={true}>
			<RequestLogFilters bind:filters {filter_choices} {request_time_range} />
		</Collapsible>

		<Notification message={error} type="error" autoHide={false} />

		{#if logs.length === 0}
			<p class="text-gray-500">没有找到任何请求日志。</p>
		{:else}
			<RequestLogTable {logs} />

			<Pagination bind:currentPage perPage={itemsPerPage} {totalItems} />
		{/if}
	</div>
</AuthGuard>
