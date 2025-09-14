<script lang="ts">
	export let logs: any[];

	const headers = [
		{ key: 'request_id', label: '请求 ID' },
		{ key: 'request_time', label: '请求时间' },
		{ key: 'key_identifier', label: '密钥标识符' },
		{ key: 'auth_key_alias', label: '用户' },
		{ key: 'model_name', label: '模型名称' },
		{ key: 'is_success', label: '成功' }
	];

	function formatDateTime(isoString: string): string {
		if (!isoString) return '';
		const date = new Date(isoString);
		return date.toLocaleString();
	}
</script>

<div class="overflow-x-auto rounded-lg bg-white shadow-md">
	<table class="min-w-full divide-y divide-gray-200">
		<thead class="bg-gray-50">
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
							{#if header.key === 'request_time' || header.key === 'response_time'}
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
							{:else}
								{log[header.key] || '-'}
							{/if}
						</td>
					{/each}
				</tr>
			{/each}
		</tbody>
	</table>
</div>
