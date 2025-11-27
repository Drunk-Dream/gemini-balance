<script lang="ts">
	import type { KeyStatus } from '$lib/features/request-keys/types';
	import * as Card from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { SvelteMap } from 'svelte/reactivity';

	const statusMap = new SvelteMap<
		string,
		{ text: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }
	>();
	statusMap.set('active', { text: '活跃', variant: 'default' }); // Green-ish usually, but default is primary
	statusMap.set('cooling_down', { text: '冷却中', variant: 'secondary' }); // Yellow-ish
	statusMap.set('in_use', { text: '使用中', variant: 'outline' }); // Blue-ish

	// Helper to map status to badge variant more accurately if needed,
	// or we can use custom classes with the Badge component if standard variants don't fit.
	// For now, mapping to standard variants.
	// active -> default (primary)
	// cooling_down -> secondary (yellow/orange often)
	// in_use -> outline (blue often)

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

<Card.Root class="py-0 shadow-md">
	<Card.Content class="px-5 py-4 sm:px-6 sm:py-5">
		<div class="space-y-2">
			<div class="flex items-center justify-between">
				<h3 class="text-md font-semibold">密钥标识:</h3>
				<span class="text-sm">{key_brief}</span>
			</div>
			<div class="flex items-center justify-between">
				<h3 class="text-md font-semibold">状态:</h3>
				<Badge variant={statusMap.get(status)?.variant || 'secondary'}>
					{statusMap.get(status)?.text || '未知状态'}
				</Badge>
			</div>
			<div class="flex items-center justify-between">
				<h3 class="text-md font-semibold">剩余冷却时间:</h3>
				<span class="text-sm">{cool_down_seconds_remaining} 秒</span>
			</div>
			<div class="flex items-center justify-between">
				<h3 class="text-md font-semibold">连续失败次数:</h3>
				<span class="text-sm">{failure_count}</span>
			</div>
			<div class="flex items-center justify-between">
				<h3 class="text-md font-semibold">连续冷却次数:</h3>
				<span class="text-sm">{cool_down_entry_count}</span>
			</div>
			<div class="flex items-center justify-between">
				<h3 class="text-md font-semibold">当前冷却时长:</h3>
				<span class="text-sm">{current_cool_down_seconds} 秒</span>
			</div>
		</div>
		<div class="mt-3 flex justify-end space-x-2">
			<Button
				variant="secondary"
				size="sm"
				onclick={() => resetKey({ identifier: key_identifier, brief: key_brief })}
			>
				重置
			</Button>
			<Button
				variant="destructive"
				size="sm"
				onclick={() => deleteKey({ identifier: key_identifier, brief: key_brief })}
			>
				删除
			</Button>
		</div>
	</Card.Content>
</Card.Root>
