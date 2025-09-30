<script lang="ts">
	import {
		type GetRequestLogsParams,
		formatToLocalDateTimeString
	} from '$lib/services/requestLogs';

	let {
		filters = $bindable(),
		request_time_range,
		filter_choices
	}: {
		filters: GetRequestLogsParams;
		request_time_range: [Date, Date];
		filter_choices: {
			key_identifiers?: string[];
			auth_key_aliases?: string[];
			model_names?: string[];
		};
	} = $props();

	let min_request_time = $derived<string>(
		formatToLocalDateTimeString(new Date(request_time_range[0]))
	);
	let max_request_time = $derived<string>(
		formatToLocalDateTimeString(new Date(request_time_range[1]))
	);

	function resetFilters() {
		const today = new Date();
		today.setHours(0, 0, 0, 0);
		const startOfDay = formatToLocalDateTimeString(today);

		const endOfDay = new Date();
		endOfDay.setHours(23, 59, 59, 999);
		const endOfToday = formatToLocalDateTimeString(endOfDay);

		filters.request_time_start = startOfDay;
		filters.request_time_end = endOfToday;
		filters.key_identifier = undefined;
		filters.auth_key_alias = undefined;
		filters.model_name = undefined;
		filters.is_success = undefined;
	}

	// 由于父组件使用 bind:filters 进行双向绑定，applyFilters 函数不再需要
	// 筛选的逻辑将由父组件的 $effect 触发
</script>

<div class="mb-4 rounded-lg bg-white p-4 shadow">
	<div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
		<div>
			<label for="request_time_start" class="mb-1 block text-sm font-medium text-gray-700"
				>请求开始时间</label
			>
			<input
				type="datetime-local"
				id="request_time_start"
				min={min_request_time}
				max={max_request_time}
				class="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
				bind:value={filters.request_time_start}
			/>
		</div>
		<div>
			<label for="request_time_end" class="mb-1 block text-sm font-medium text-gray-700"
				>请求结束时间</label
			>
			<input
				type="datetime-local"
				id="request_time_end"
				min={min_request_time}
				max={max_request_time}
				class="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
				bind:value={filters.request_time_end}
			/>
		</div>
		<div>
			<span class="mb-1 block text-sm font-medium text-gray-700">密钥标识符</span>
			<select
				class="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
				bind:value={filters.key_identifier}
				disabled={true}
			>
				<option value={undefined}>全部</option>
				{#if filter_choices.key_identifiers && filter_choices.key_identifiers.length > 0}
					{#each filter_choices.key_identifiers as choice}
						<option value={choice}>{choice}</option>
					{/each}
				{/if}
			</select>
		</div>
		<div>
			<span class="mb-1 block text-sm font-medium text-gray-700">用户 (认证密钥别名)</span>
			<select
				class="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
				bind:value={filters.auth_key_alias}
			>
				<option value={undefined}>全部</option>
				{#if filter_choices.auth_key_aliases && filter_choices.auth_key_aliases.length > 0}
					{#each filter_choices.auth_key_aliases as choice}
						<option value={choice}>{choice}</option>
					{/each}
				{/if}
			</select>
		</div>
		<div>
			<span class="mb-1 block text-sm font-medium text-gray-700">模型名称</span>
			<select
				class="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
				bind:value={filters.model_name}
			>
				<option value={undefined}>全部</option>
				{#if filter_choices.model_names && filter_choices.model_names.length > 0}
					{#each filter_choices.model_names as choice}
						<option value={choice}>{choice}</option>
					{/each}
				{/if}
			</select>
		</div>
		<div>
			<label for="is_success" class="mb-1 block text-sm font-medium text-gray-700"
				>请求是否成功</label
			>
			<select
				id="is_success"
				class="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
				bind:value={filters.is_success}
			>
				<option value={undefined}>全部</option>
				<option value={true}>是</option>
				<option value={false}>否</option>
			</select>
		</div>
	</div>
	<div class="mt-4 flex justify-end space-x-2">
		<button
			onclick={resetFilters}
			class="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
		>
			重置
		</button>
	</div>
</div>
