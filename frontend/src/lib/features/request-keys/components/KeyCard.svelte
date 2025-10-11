<script lang="ts">
	import type { KeyStatus } from '$lib/features/request-keys/types';
	const statusMap = new Map<string, { text: string; colorClass: string }>();
	statusMap.set('active', { text: '活跃', colorClass: 'badge-success' });
	statusMap.set('cooling_down', { text: '冷却中', colorClass: 'badge-warning' });
	statusMap.set('in_use', { text: '使用中', colorClass: 'badge-info' });

	let {
		keyStatus,
		resetKey,
		deleteKey
	}: {
		keyStatus: KeyStatus;
		resetKey: (keyIdentifier: string) => Promise<void>;
		deleteKey: (keyIdentifier: string) => Promise<void>;
	} = $props();
</script>

<div class="card bg-base-200 shadow-md">
	<div class="card-body">
		<div class="flex items-center justify-between">
			<h3 class="text-md text-base-content/80 font-semibold">密钥标识:</h3>
			<span class="text-base-content/90 text-sm">{keyStatus.key_brief}</span>
		</div>
		<div class="flex items-center justify-between">
			<h3 class="text-md text-base-content/80 font-semibold">状态:</h3>
			<span class="badge {statusMap.get(keyStatus.status)?.colorClass || 'badge-neutral'} badge-md"
				>{statusMap.get(keyStatus.status)?.text || '未知状态'}</span
			>
		</div>
		<div class="flex items-center justify-between">
			<h3 class="text-md text-base-content/80 font-semibold">剩余冷却时间:</h3>
			<span class="text-base-content/90 text-sm">{keyStatus.cool_down_seconds_remaining} 秒</span>
		</div>
		<div class="flex items-center justify-between">
			<h3 class="text-md text-base-content/80 font-semibold">连续失败次数:</h3>
			<span class="text-base-content/90 text-sm">{keyStatus.failure_count}</span>
		</div>
		<div class="flex items-center justify-between">
			<h3 class="text-md text-base-content/80 font-semibold">连续冷却次数:</h3>
			<span class="text-base-content/90 text-sm">{keyStatus.cool_down_entry_count}</span>
		</div>
		<div class="flex items-center justify-between">
			<h3 class="text-md text-base-content/80 font-semibold">当前冷却时长:</h3>
			<span class="text-base-content/90 text-sm">{keyStatus.current_cool_down_seconds} 秒</span>
		</div>
		<div class="card-actions mt-4 justify-end space-x-2">
			<button onclick={() => resetKey(keyStatus.key_identifier)} class="btn btn-warning btn-sm">
				重置
			</button>
			<button onclick={() => deleteKey(keyStatus.key_identifier)} class="btn btn-error btn-sm">
				删除
			</button>
		</div>
	</div>
</div>
