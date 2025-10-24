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
		resetKey: (key: { identifier: string; brief: string }) => Promise<void>;
		deleteKey: (key: { identifier: string; brief: string }) => Promise<void>;
	} = $props();
	const {
		key_identifier,
		key_brief,
		cool_down_entry_count,
		cool_down_seconds_remaining,
		current_cool_down_seconds,
		failure_count,
		status
	} = $derived(keyStatus);
</script>

<div class="card bg-card border-border shadow-md">
	<div class="card-body">
		<div class="flex items-center justify-between">
			<h3 class="text-md text-card-foreground font-semibold">密钥标识:</h3>
			<span class="text-foreground text-sm">{key_brief}</span>
		</div>
		<div class="flex items-center justify-between">
			<h3 class="text-md text-card-foreground font-semibold">状态:</h3>
			<span
				class="badge px-2 {statusMap.get(status)?.colorClass ||
					'bg-muted text-muted-foreground'} badge-md"
				>{statusMap.get(status)?.text || '未知状态'}</span
			>
		</div>
		<div class="flex items-center justify-between">
			<h3 class="text-md text-card-foreground font-semibold">剩余冷却时间:</h3>
			<span class="text-foreground text-sm">{cool_down_seconds_remaining} 秒</span>
		</div>
		<div class="flex items-center justify-between">
			<h3 class="text-md text-card-foreground font-semibold">连续失败次数:</h3>
			<span class="text-foreground text-sm">{failure_count}</span>
		</div>
		<div class="flex items-center justify-between">
			<h3 class="text-md text-card-foreground font-semibold">连续冷却次数:</h3>
			<span class="text-foreground text-sm">{cool_down_entry_count}</span>
		</div>
		<div class="flex items-center justify-between">
			<h3 class="text-md text-card-foreground font-semibold">当前冷却时长:</h3>
			<span class="text-foreground text-sm">{current_cool_down_seconds} 秒</span>
		</div>
		<div class="card-actions mt-4 justify-end space-x-2">
			<button
				onclick={() => resetKey({ identifier: key_identifier, brief: key_brief })}
				class="btn btn-sm btn-warning"
			>
				重置
			</button>
			<button
				onclick={() => deleteKey({ identifier: key_identifier, brief: key_brief })}
				class="btn bg-error btn-sm"
			>
				删除
			</button>
		</div>
	</div>
</div>
