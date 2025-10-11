<script lang="ts">
	import type { KeyStatusResponse } from '$lib/features/request-keys/types';

	let { keyStatusResponse }: { keyStatusResponse: KeyStatusResponse } = $props();
</script>

<div class="mb-6 grid grid-cols-2 gap-2 lg:grid-cols-4 lg:gap-4">
	<div
		class="stat bg-success/20 text-success shadow-base-content/20 place-items-center rounded-lg shadow-md"
	>
		<div class="stat-title">活跃</div>
		<div class="stat-value">{keyStatusResponse.available_keys_count}</div>
	</div>
	<div
		class="stat bg-info/20 text-info shadow-base-content/20 place-items-center rounded-lg shadow-md"
	>
		<div class="stat-title">使用中</div>
		<div class="stat-value">{keyStatusResponse.in_use_keys_count}</div>
	</div>
	<div
		class="stat bg-warning/20 text-warning shadow-base-content/20 place-items-center rounded-lg shadow-md"
	>
		<div class="stat-title">冷却中</div>
		<div class="stat-value">{keyStatusResponse.cooled_down_keys_count}</div>
	</div>
	<div
		class="stat bg-base-content/20 text-base-content/80 shadow-base-content/20 place-items-center rounded-lg shadow-md"
	>
		<div class="stat-title">总数</div>
		<div class="stat-value">{keyStatusResponse.total_keys_count}</div>
	</div>
</div>
