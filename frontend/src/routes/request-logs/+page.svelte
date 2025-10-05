<script lang="ts">
	import AuthGuard from '$lib/components/auth/AuthGuard.svelte';
	import Notification from '$lib/components/common/Notification.svelte';
	import Pagination from '$lib/components/common/Pagination.svelte';
	import DateRangePicker from '$lib/components/logs/DateRangePicker.svelte';
	import RequestLogTable from '$lib/components/logs/RequestLogTable.svelte';
	import {
		getRequestLogs,
		type GetRequestLogsParams,
		type RequestLog
	} from '$lib/services/requestLogs';
	import { fromDate, getLocalTimeZone, today } from '@internationalized/date';
	import type { DateRange } from 'bits-ui';

	let logs: RequestLog[] = $state([]);
	let error: string | null = $state(null);
	let currentPage: number = $state(1);
	const itemsPerPage: number = 15;
	let totalItems: number = $state(0);

	let request_time_range: DateRange = $state({
		start: today(getLocalTimeZone()),
		end: today(getLocalTimeZone())
	});
	let request_time_limit: DateRange = $state({
		start: today(getLocalTimeZone()),
		end: today(getLocalTimeZone())
	});

	// 当日期范围变化时，重置页码为 1 并更新日期范围
	function handleDateRangeChange(newRange: DateRange) {
		request_time_range = newRange;
		if (newRange.start && newRange.end) {
			currentPage = 1;
		}
	}

	async function fetchLogs() {
		error = null;
		try {
			if (!request_time_range.start || !request_time_range.end) {
				return;
			}

			const offset = (currentPage - 1) * itemsPerPage;

			const filters = {
				request_time_start: request_time_range.start
					? request_time_range.start.toDate(getLocalTimeZone()).toISOString()
					: '',
				request_time_end: request_time_range.end
					? request_time_range.end.add({ days: 1 }).toDate(getLocalTimeZone()).toISOString()
					: ''
			};

			const params: GetRequestLogsParams = {
				limit: itemsPerPage,
				offset,
				...filters
			};

			const response = await getRequestLogs(params);
			logs = response.logs;
			totalItems = response.total;
			if (response.request_time_range) {
				request_time_limit = {
					start: fromDate(new Date(response.request_time_range[0]), getLocalTimeZone()),
					end: fromDate(new Date(response.request_time_range[1]), getLocalTimeZone())
				};
			}
		} catch (e: any) {
			error = e.message;
		}
	}

	// 初始加载和当 filters 或 currentPage 变化时，获取日志
	$effect(() => {
		fetchLogs();
	});
</script>

<AuthGuard>
	<div class="container mx-auto p-4">
		<h1 class="mb-4 text-2xl font-bold">请求日志</h1>

		<div class="mb-4">
			<DateRangePicker
				value={request_time_range}
				limit={request_time_limit}
				onValueChange={handleDateRangeChange}
			/>
		</div>

		<Notification message={error} type="error" autoHide={false} />

		{#if logs.length === 0}
			<p class="text-gray-500">没有找到任何请求日志。</p>
		{:else}
			<RequestLogTable {logs} />

			<Pagination bind:currentPage perPage={itemsPerPage} {totalItems} />
		{/if}
	</div>
</AuthGuard>
