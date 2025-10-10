<script lang="ts">
    import type { KeyStatus } from '$lib/features/request-keys/types';
    const statusMap = new Map<string, { text: string; colorClass: string }>();
    statusMap.set('active', { text: '活跃', colorClass: 'bg-success/20' });
    statusMap.set('cooling_down', { text: '冷却中', colorClass: 'bg-warning/20' });
    statusMap.set('in_use', { text: '使用中', colorClass: 'bg-info/20' });

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

<div class="bg-base-200 shadow-base-300 rounded-lg p-4 shadow-md">
    <div class="mb-2 flex items-center justify-between">
        <h3 class="text-md text-base-content/80 font-semibold">密钥标识:</h3>
        <p class="text-base-content/90 text-sm">{keyStatus.key_brief}</p>
    </div>
    <div class="mb-2 flex items-center justify-between">
        <h3 class="text-md text-base-content/80 font-semibold">状态:</h3>
        <span class="relative inline-block px-2 py-0.5 text-sm font-semibold leading-tight">
            <span
                aria-hidden="true"
                class="absolute inset-0 rounded-full opacity-50 {statusMap.get(keyStatus.status)
                    ?.colorClass || 'bg-base-content/20'}"
            ></span>
            <span class="text-base-content/90 relative"
                >{statusMap.get(keyStatus.status)?.text || '未知状态'}</span
            >
        </span>
    </div>
    <div class="mb-2 flex items-center justify-between">
        <h3 class="text-md text-base-content/80 font-semibold">剩余冷却时间:</h3>
        <p class="text-sm text-base-content/90">{keyStatus.cool_down_seconds_remaining} 秒</p>
    </div>
    <!-- <div class="mb-2 flex items-center justify-between">
        <h3 class="text-md font-semibold text-gray-800">今日用量:</h3>
        <div class="text-sm text-gray-900">{@html formatDailyUsage(keyStatus.daily_usage)}</div>
    </div> -->
    <div class="mb-2 flex items-center justify-between">
        <h3 class="text-md font-semibold text-base-content/80">连续失败次数:</h3>
        <p class="text-sm text-base-content/90">{keyStatus.failure_count}</p>
    </div>
    <div class="mb-2 flex items-center justify-between">
        <h3 class="text-md font-semibold text-base-content/80">连续冷却次数:</h3>
        <p class="text-sm text-base-content/90">{keyStatus.cool_down_entry_count}</p>
    </div>
    <div class="flex items-center justify-between">
        <h3 class="text-md font-semibold text-base-content/80">当前冷却时长:</h3>
        <p class="text-sm text-base-content/90">{keyStatus.current_cool_down_seconds} 秒</p>
    </div>
    <div class="mt-4 flex justify-end space-x-2">
        <button onclick={() => resetKey(keyStatus.key_identifier)} class="btn btn-warning btn-sm">
            重置
        </button>
        <button onclick={() => deleteKey(keyStatus.key_identifier)} class="btn btn-error btn-sm">
            删除
        </button>
    </div>
</div>
