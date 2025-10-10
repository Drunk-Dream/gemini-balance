<script lang="ts">
	import type { RequestLog } from '$lib/features/request-logs/service';

	let {
		logs
	}: {
		logs: RequestLog[];
	} = $props();

	const headers = [
		{ key: 'request_id', label: '请求 ID' },
		{ key: 'request_time', label: '请求时间' },
		{ key: 'key_brief', label: '密钥' },
		{ key: 'auth_key_alias', label: '用户' },
		{ key: 'model_name', label: '模型名称' },
		{ key: 'token_usage', label: 'Token 使用情况' },
		{ key: 'is_success', label: '成功' },
		{ key: 'error_type', label: '错误类型' }
	];

	function formatDateTime(isoString: string): string {
		if (!isoString) return '';
		const date = new Date(isoString);
		return date.toLocaleString();
	}
</script>

<div class="overflow-x-auto rounded-lg bg-white shadow-md">
	<table class="min-w-full divide-y divide-gray-200">
		<thead class="sticky top-0 bg-gray-50">
			<tr>
				{#each headers as header}
					<th
						scope="col"
						class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
					>
						{header.label}
					</th>
				{/each}
			</tr>
		</thead>
		<tbody class="divide-y divide-gray-200 bg-white">
			{#each logs as log (log.id)}
				<tr>
					{#each headers as header}
						<td class="whitespace-nowrap px-6 py-4 text-sm text-gray-900">
							{#if header.key === 'request_time'}
								{formatDateTime(log[header.key])}
							{:else if header.key === 'is_success'}
								<span
									class="inline-flex rounded-full px-2 text-xs font-semibold leading-5 {log[
										header.key
									]
										? 'bg-green-100 text-green-800'
										: 'bg-red-100 text-red-800'}"
								>
									{log[header.key] ? '是' : '否'}
								</span>
							{:else if header.key === 'token_usage'}
								{#if log.prompt_tokens !== null || log.completion_tokens !== null || log.total_tokens !== null}
									{log.prompt_tokens || '0'}->{log.completion_tokens || '0'}({log.total_tokens ||
										'0'})
								{:else}
									-
								{/if}
							{:else}
								{log[header.key as keyof RequestLog] || '-'}
							{/if}
						</td>
					{/each}
				</tr>
			{/each}
		</tbody>
	</table>
</div>
