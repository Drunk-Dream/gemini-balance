<script lang="ts">
	import type { RequestLog } from '$lib/features/request-logs/service';
	import * as Table from '$lib/components/ui/table';
	import * as Card from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';

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

<Card.Root class="shadow-lg">
	<Card.Header>
		<Card.Title>请求日志</Card.Title>
	</Card.Header>
	<Card.Content>
		<Table.Root>
			<Table.Header>
				<Table.Row>
					{#each headers as header}
						<Table.Head>{header.label}</Table.Head>
					{/each}
				</Table.Row>
			</Table.Header>
			<Table.Body>
				{#each logs as log (log.id)}
					<Table.Row>
						{#each headers as header}
							<Table.Cell class="whitespace-nowrap">
								{#if header.key === 'request_id'}
									<span class="font-mono">{log[header.key as keyof RequestLog] || '-'}</span>
								{:else if header.key === 'request_time'}
									<span>{formatDateTime(log[header.key])}</span>
								{:else if header.key === 'key_brief'}
									<span class="text-muted-foreground font-mono"
										>{log[header.key as keyof RequestLog] || '-'}</span
									>
								{:else if header.key === 'auth_key_alias'}
									<span>{log[header.key as keyof RequestLog] || '-'}</span>
								{:else if header.key === 'model_name'}
									<span>{log[header.key as keyof RequestLog] || '-'}</span>
								{:else if header.key === 'token_usage'}
									{#if log.prompt_tokens !== null || log.completion_tokens !== null || log.total_tokens !== null}
										<span class="font-mono"
											>{log.prompt_tokens || '0'}->{log.completion_tokens ||
												'0'}({log.total_tokens || '0'})</span
										>
									{:else}
										<span>-</span>
									{/if}
								{:else if header.key === 'is_success'}
									{#if log[header.key]}
										<Badge variant="default" class="bg-green-500 hover:bg-green-600">是</Badge>
									{:else}
										<Badge variant="destructive">否</Badge>
									{/if}
								{:else if header.key === 'error_type'}
									<span>{log[header.key as keyof RequestLog] || '-'}</span>
								{:else}
									<span>{log[header.key as keyof RequestLog] || '-'}</span>
								{/if}
							</Table.Cell>
						{/each}
					</Table.Row>
				{/each}
			</Table.Body>
		</Table.Root>
		{#if logs.length === 0}
			<p class="text-muted-foreground py-4 text-center">暂无数据。</p>
		{/if}
	</Card.Content>
</Card.Root>
