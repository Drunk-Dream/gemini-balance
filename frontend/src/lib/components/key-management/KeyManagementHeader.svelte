<script lang="ts">
	let {
		fetchKeyStatuses,
		resetAllKeys,
		loading
	}: {
		fetchKeyStatuses: () => Promise<void>;
		resetAllKeys: () => Promise<void>;
		loading: boolean;
	} = $props();
</script>

<div
	class="mb-4 flex flex-col space-y-4 sm:flex-row sm:items-center sm:justify-between sm:space-x-4 sm:space-y-0"
>
	<button
		onclick={fetchKeyStatuses}
		class="focus:shadow-outline rounded bg-blue-500 px-4 py-2 text-sm font-bold text-white hover:bg-blue-700 focus:outline-none sm:text-base"
		disabled={loading}
	>
		{loading ? '刷新中...' : '立即刷新'}
	</button>
	<button
		onclick={resetAllKeys}
		class="focus:shadow-outline rounded bg-red-500 px-4 py-2 text-sm font-bold text-white hover:bg-red-700 focus:outline-none sm:text-base"
	>
		重置所有密钥状态
	</button>
</div>
