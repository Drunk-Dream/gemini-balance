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

<div class="card bg-card text-card-foreground border shadow-lg">
	<div class="card-body">
		<h2 class="card-title">请求日志</h2>
		<div class="overflow-x-auto">
			<table class="table-zebra table">
				<thead>
					<tr>
						{#each headers as header}
							<th scope="col">{header.label}</th>
						{/each}
					</tr>
				</thead>
				<tbody>
					{#each logs as log (log.id)}
						<tr>
							{#each headers as header}
								<td class="whitespace-nowrap text-sm">
									{#if header.key === 'request_id'}
										<span class="text-foreground font-mono"
											>{log[header.key as keyof RequestLog] || '-'}</span
										>
									{:else if header.key === 'request_time'}
										<span class="text-foreground">{formatDateTime(log[header.key])}</span>
									{:else if header.key === 'key_brief'}
										<span class="text-muted-foreground font-mono"
											>{log[header.key as keyof RequestLog] || '-'}</span
										>
									{:else if header.key === 'auth_key_alias'}
										<span class="text-foreground">{log[header.key as keyof RequestLog] || '-'}</span
										>
									{:else if header.key === 'model_name'}
										<span class="text-foreground">{log[header.key as keyof RequestLog] || '-'}</span
										>
									{:else if header.key === 'token_usage'}
										{#if log.prompt_tokens !== null || log.completion_tokens !== null || log.total_tokens !== null}
											<span class="text-foreground font-mono"
												>{log.prompt_tokens || '0'}->{log.completion_tokens ||
													'0'}({log.total_tokens || '0'})</span
											>
										{:else}
											<span class="text-foreground">-</span>
										{/if}
									{:else if header.key === 'is_success'}
										{#if log[header.key]}
											<span class="badge badge-success px-2 text-xs">是</span>
										{:else}
											<span class="badge badge-error px-2 text-xs">否</span>
										{/if}
									{:else if header.key === 'error_type'}
										<span class="text-foreground">{log[header.key as keyof RequestLog] || '-'}</span
										>
									{:else}
										<span class="text-foreground">{log[header.key as keyof RequestLog] || '-'}</span
										>
									{/if}
								</td>
							{/each}
						</tr>
					{/each}
				</tbody>
			</table>
			{#if logs.length === 0}
				<p class="text-muted-foreground py-4 text-center">暂无数据。</p>
			{/if}
		</div>
	</div>
</div>
