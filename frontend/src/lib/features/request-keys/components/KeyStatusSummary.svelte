<script lang="ts">
	import type { KeyStatusResponse } from '$lib/features/request-keys/types';

	let { keyStatusResponse }: { keyStatusResponse: KeyStatusResponse } = $props();
</script>

<div class="mb-6 rounded-lg bg-white p-4 shadow-md sm:p-6">
	<h2 class="mb-4 text-xl font-semibold text-gray-800">密钥状态总览</h2>
	<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-4">
		<div class="rounded-md bg-green-50 p-3 text-center shadow-sm">
			<p class="text-sm font-medium text-green-700">活跃</p>
			<p class="text-2xl font-bold text-green-800">{keyStatusResponse.available_keys_count}</p>
		</div>
		<div class="rounded-md bg-blue-50 p-3 text-center shadow-sm">
			<p class="text-sm font-medium text-blue-700">使用中</p>
			<p class="text-2xl font-bold text-blue-800">{keyStatusResponse.in_use_keys_count}</p>
		</div>
		<div class="rounded-md bg-yellow-50 p-3 text-center shadow-sm">
			<p class="text-sm font-medium text-yellow-700">冷却中</p>
			<p class="text-2xl font-bold text-yellow-800">{keyStatusResponse.cooled_down_keys_count}</p>
		</div>
		<div class="rounded-md bg-gray-50 p-3 text-center shadow-sm">
			<p class="text-sm font-medium text-gray-700">总数</p>
			<p class="text-2xl font-bold text-gray-800">{keyStatusResponse.total_keys_count}</p>
		</div>
	</div>
</div>
