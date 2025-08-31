<script lang="ts">
	interface AuthKey {
		api_key: string;
		alias: string;
		call_count: number;
	}

	let {
		authKeys,
		editingKey,
		editingAlias = $bindable(),
		startEdit,
		updateAuthKey,
		cancelEdit,
		deleteAuthKey
	}: {
		authKeys: AuthKey[];
		editingKey: AuthKey | null;
		editingAlias: string;
		startEdit: (key: AuthKey) => void;
		updateAuthKey: () => Promise<void>;
		cancelEdit: () => void;
		deleteAuthKey: (api_key: string) => Promise<void>;
	} = $props();
</script>

<div class="rounded bg-white px-8 pb-8 pt-6 shadow-md">
	<h2 class="mb-4 text-xl font-semibold">现有密钥列表</h2>
	<div class="overflow-x-auto">
		<table class="min-w-full divide-y divide-gray-200">
			<thead class="bg-gray-50">
				<tr>
					<th
						scope="col"
						class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
					>
						别名
					</th>
					<th
						scope="col"
						class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
					>
						API Key
					</th>
					<th
						scope="col"
						class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
					>
						调用次数
					</th>
					<th
						scope="col"
						class="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500"
					>
						操作
					</th>
				</tr>
			</thead>
			<tbody class="divide-y divide-gray-200 bg-white">
				{#each authKeys as key (key.api_key)}
					<tr>
						<td class="whitespace-nowrap px-6 py-4">
							{#if editingKey?.api_key === key.api_key}
								<input
									type="text"
									bind:value={editingAlias}
									class="focus:shadow-outline w-full appearance-none rounded border px-3 py-2 leading-tight text-gray-700 shadow focus:outline-none"
								/>
							{:else}
								<span class="text-sm text-gray-900">{key.alias}</span>
							{/if}
						</td>
						<td class="whitespace-nowrap px-6 py-4">
							<span class="font-mono text-sm text-gray-500">{key.api_key}</span>
						</td>
						<td class="whitespace-nowrap px-6 py-4">
							<span class="text-sm text-gray-900">{key.call_count}</span>
						</td>
						<td class="space-x-2 whitespace-nowrap px-6 py-4 text-right text-sm font-medium">
							{#if editingKey?.api_key === key.api_key}
								<button onclick={updateAuthKey} class="text-indigo-600 hover:text-indigo-900">
									保存
								</button>
								<button onclick={cancelEdit} class="text-gray-600 hover:text-gray-900">
									取消
								</button>
							{:else}
								<button onclick={() => startEdit(key)} class="text-indigo-600 hover:text-indigo-900"
									>编辑</button
								>
								<button
									onclick={() => deleteAuthKey(key.api_key)}
									class="text-red-600 hover:text-red-900">删除</button
								>
							{/if}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
		{#if authKeys.length === 0}
			<p class="py-4 text-center text-gray-500">暂无数据。</p>
		{/if}
	</div>
</div>
