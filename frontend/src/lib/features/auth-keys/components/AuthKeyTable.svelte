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

<div class="card bg-card text-card-foreground shadow-lg border">
	<div class="card-body">
		<h2 class="card-title">现有密钥列表</h2>
		<div class="overflow-x-auto">
			<table class="table-zebra table">
				<thead>
					<tr>
						<th scope="col">别名</th>
						<th scope="col">API Key</th>
						<th scope="col">调用次数</th>
						<th scope="col" class="text-right">操作</th>
					</tr>
				</thead>
				<tbody>
					{#each [...authKeys].sort((a, b) => b.call_count - a.call_count) as key (key.api_key)}
						<tr>
							<td class="whitespace-nowrap">
								{#if editingKey?.api_key === key.api_key}
									<input
										type="text"
										bind:value={editingAlias}
										class="input bg-background border-input text-foreground w-full"
									/>
								{:else}
									<span class="text-foreground text-sm">{key.alias}</span>
								{/if}
							</td>
							<td class="whitespace-nowrap">
								<span class="text-muted-foreground font-mono text-sm">{key.api_key}</span>
							</td>
							<td class="whitespace-nowrap">
									<span class="text-foreground text-sm">{key.call_count}</span>
							</td>
							<td class="space-x-2 whitespace-nowrap text-right text-sm font-medium">
								{#if editingKey?.api_key === key.api_key}
									<button onclick={updateAuthKey} class="btn bg-primary text-primary-foreground btn-sm"> 保存 </button>
									<button onclick={cancelEdit} class="btn btn-ghost btn-sm"> 取消 </button>
								{:else}
									<button onclick={() => startEdit(key)} class="btn btn-ghost btn-sm">
										编辑
									</button>
									<button onclick={() => deleteAuthKey(key.api_key)} class="btn bg-destructive text-destructive-foreground btn-sm">
										删除
									</button>
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
			{#if authKeys.length === 0}
				<p class="py-4 text-center text-muted-foreground">暂无数据。</p>
			{/if}
		</div>
	</div>
</div>
