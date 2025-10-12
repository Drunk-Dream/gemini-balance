<script lang="ts">
	import Container from '$lib/components/Container.svelte';
	import Notification from '$lib/components/Notification.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import AuthGuard from '$lib/features/auth/components/AuthGuard.svelte';
	import DateRangePicker from '$lib/features/request-logs/components/DateRangePicker.svelte';
	import RequestLogTable from '$lib/features/request-logs/components/RequestLogTable.svelte';
	import {
		getRequestLogs,
		type GetRequestLogsParams,
		type RequestLog
	} from '$lib/features/request-logs/service';
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
		try {
			if (!request_time_range.start || !request_time_range.end) {
				return;
			}

			const offset = (currentPage - 1) * itemsPerPage;

			const params: GetRequestLogsParams = {
				limit: itemsPerPage,
				offset,
				request_time_start: request_time_range.start.toDate(getLocalTimeZone()).toISOString(),
				request_time_end: request_time_range.end
					.add({ days: 1 })
					.toDate(getLocalTimeZone())
					.toISOString()
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
		const timeoutId = setTimeout(fetchLogs, 300, request_time_range, currentPage);
		return () => clearTimeout(timeoutId);
	});
</script>

<AuthGuard>
	<Container header="请求日志">
		<div class="mb-4">
			<DateRangePicker
				value={request_time_range}
				limit={request_time_limit}
				onValueChange={handleDateRangeChange}
			/>
		</div>

		<Notification message={error} type="error" autoHide={false} />

		{#if logs.length === 0}
			<p class="text-base-content/50">没有找到任何请求日志。</p>
		{:else}
			<RequestLogTable {logs} />

			<div class="sticky bottom-2 z-10 mt-2 flex justify-center">
				<div
					class="bg-base-100/60 border-base-200/60 shadow-base-content/20 rounded-lg border px-2 shadow-md backdrop-blur-sm"
				>
					<Pagination bind:currentPage perPage={itemsPerPage} {totalItems} />
				</div>
			</div>
		{/if}
	</Container>
</AuthGuard>
