<script lang="ts">
	import type { KeyStatus } from '$lib/features/request-keys/types';
	const statusMap = new Map<string, { text: string; colorClass: string }>();
	statusMap.set('active', { text: '活跃', colorClass: 'bg-green-200' });
	statusMap.set('cooling_down', { text: '冷却中', colorClass: 'bg-yellow-200' });
	statusMap.set('in_use', { text: '使用中', colorClass: 'bg-blue-200' });

	let {
		keyStatus,
		resetKey,
		deleteKey
	}: {
		keyStatus: KeyStatus;
		resetKey: (keyIdentifier: string) => Promise<void>;
		deleteKey: (keyIdentifier: string) => Promise<void>;
	} = $props();

	function formatDailyUsage(usage: { [model: string]: number }): string {
		const entries = Object.entries(usage);
		if (entries.length === 0) {
			return '无';
		}
		entries.sort(([modelA], [modelB]) => modelA.localeCompare(modelB));
		return entries.map(([model, count]) => `${model}: ${count}`).join('<br>');
	}
</script>

<div class="rounded-lg bg-white p-4 shadow-md">
	<div class="mb-2 flex items-center justify-between">
		<h3 class="text-md font-semibold text-gray-800">密钥标识:</h3>
		<p class="text-sm text-gray-900">{keyStatus.key_brief}</p>
	</div>
	<div class="mb-2 flex items-center justify-between">
		<h3 class="text-md font-semibold text-gray-800">状态:</h3>
		<span class="relative inline-block px-2 py-0.5 text-sm font-semibold leading-tight">
			<span
				aria-hidden="true"
				class="absolute inset-0 rounded-full opacity-50 {statusMap.get(keyStatus.status)
					?.colorClass || 'bg-gray-200'}"
			></span>
			<span class="relative text-gray-900"
				>{statusMap.get(keyStatus.status)?.text || '未知状态'}</span
			>
		</span>
	</div>
	<div class="mb-2 flex items-center justify-between">
		<h3 class="text-md font-semibold text-gray-800">剩余冷却时间:</h3>
		<p class="text-sm text-gray-900">{keyStatus.cool_down_seconds_remaining} 秒</p>
	</div>
	<div class="mb-2 flex items-center justify-between">
		<h3 class="text-md font-semibold text-gray-800">今日用量:</h3>
		<div class="text-sm text-gray-900">{@html formatDailyUsage(keyStatus.daily_usage)}</div>
	</div>
	<div class="mb-2 flex items-center justify-between">
		<h3 class="text-md font-semibold text-gray-800">连续失败次数:</h3>
		<p class="text-sm text-gray-900">{keyStatus.failure_count}</p>
	</div>
	<div class="mb-2 flex items-center justify-between">
		<h3 class="text-md font-semibold text-gray-800">连续冷却次数:</h3>
		<p class="text-sm text-gray-900">{keyStatus.cool_down_entry_count}</p>
	</div>
	<div class="flex items-center justify-between">
		<h3 class="text-md font-semibold text-gray-800">当前冷却时长:</h3>
		<p class="text-sm text-gray-900">{keyStatus.current_cool_down_seconds} 秒</p>
	</div>
	<div class="mt-4 flex justify-end space-x-2">
		<button
			onclick={() => resetKey(keyStatus.key_identifier)}
			class="focus:shadow-outline cursor-pointer rounded bg-yellow-500 px-3 py-1.5 text-sm font-bold text-white hover:bg-yellow-700 focus:outline-none"
		>
			重置
		</button>
		<button
			onclick={() => deleteKey(keyStatus.key_identifier)}
			class="focus:shadow-outline cursor-pointer rounded bg-red-500 px-3 py-1.5 text-sm font-bold text-white hover:bg-red-700 focus:outline-none"
		>
			删除
		</button>
	</div>
</div>
