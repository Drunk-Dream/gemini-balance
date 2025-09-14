<script lang="ts">
    import AuthGuard from '$lib/components/auth/AuthGuard.svelte';
    import RequestLogTable from '$lib/components/logs/RequestLogTable.svelte';
    import { getRequestLogs } from '$lib/services/requestLogs';
    import { onMount } from 'svelte';

    let logs: any[] = $state([]);
    let loading: boolean = $state(true);
    let error: string | null = $state(null);

    onMount(async () => {
        try {
            logs = await getRequestLogs();
        } catch (e: any) {
            error = e.message;
        } finally {
            loading = false;
        }
    });
</script>

<AuthGuard>
    <div class="container mx-auto p-4">
        <h1 class="text-2xl font-bold mb-4">请求日志</h1>

        {#if loading}
            <p>加载中...</p>
        {:else if error}
            <p class="text-red-500">错误: {error}</p>
        {:else}
            <RequestLogTable {logs} />
        {/if}
    </div>
</AuthGuard>
