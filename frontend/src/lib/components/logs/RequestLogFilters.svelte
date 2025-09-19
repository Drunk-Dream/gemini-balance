<script lang="ts">
	import type { GetRequestLogsParams } from '$lib/services/requestLogs';

	let { apply, reset } = $props<{
		apply: (filters: GetRequestLogsParams) => void;
		reset: () => void;
	}>();

	let filters = $state<GetRequestLogsParams>({
		request_time_start: undefined,
		request_time_end: undefined,
		key_identifier: undefined,
		auth_key_alias: undefined,
		model_name: undefined,
		is_success: undefined
	});

	function applyFilters() {
		apply({ ...filters });
	}

	function resetFilters() {
		filters = {
			request_time_start: undefined,
			request_time_end: undefined,
			key_identifier: undefined,
			auth_key_alias: undefined,
			model_name: undefined,
			is_success: undefined
		};
		reset();
	}
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
				class="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
				bind:value={filters.request_time_end}
			/>
		</div>
		<div>
			<label for="key_identifier" class="mb-1 block text-sm font-medium text-gray-700"
				>密钥标识符</label
			>
			<input
				type="text"
				id="key_identifier"
				class="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
				bind:value={filters.key_identifier}
				placeholder="输入密钥标识符"
			/>
		</div>
		<div>
			<label for="auth_key_alias" class="mb-1 block text-sm font-medium text-gray-700"
				>用户 (认证密钥别名)</label
			>
			<input
				type="text"
				id="auth_key_alias"
				class="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
				bind:value={filters.auth_key_alias}
				placeholder="输入用户别名"
			/>
		</div>
		<div>
			<label for="model_name" class="mb-1 block text-sm font-medium text-gray-700">模型名称</label>
			<input
				type="text"
				id="model_name"
				class="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
				bind:value={filters.model_name}
				placeholder="输入模型名称"
			/>
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
			>重置</button
		>
		<button
			onclick={applyFilters}
			class="rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
			>应用筛选</button
		>
	</div>
</div>
