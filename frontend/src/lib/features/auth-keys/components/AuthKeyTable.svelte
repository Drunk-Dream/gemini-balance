<script lang="ts">
	import * as Table from '$lib/components/ui/table';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';

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

<Card.Root class="shadow-lg">
	<Card.Header>
		<Card.Title>现有密钥列表</Card.Title>
	</Card.Header>
	<Card.Content>
		<Table.Root>
			<Table.Header>
				<Table.Row>
					<Table.Head>别名</Table.Head>
					<Table.Head>API Key</Table.Head>
					<Table.Head>调用次数</Table.Head>
					<Table.Head class="text-right">操作</Table.Head>
				</Table.Row>
			</Table.Header>
			<Table.Body>
				{#each [...authKeys].sort((a, b) => b.call_count - a.call_count) as key (key.api_key)}
					<Table.Row>
						<Table.Cell class="whitespace-nowrap">
							{#if editingKey?.api_key === key.api_key}
								<Input type="text" bind:value={editingAlias} class="w-full" />
							{:else}
								<span class="text-sm">{key.alias}</span>
							{/if}
						</Table.Cell>
						<Table.Cell class="whitespace-nowrap">
							<span class="text-muted-foreground font-mono text-sm">{key.api_key}</span>
						</Table.Cell>
						<Table.Cell class="whitespace-nowrap">
							<span class="text-sm">{key.call_count}</span>
						</Table.Cell>
						<Table.Cell class="space-x-2 whitespace-nowrap text-right">
							{#if editingKey?.api_key === key.api_key}
								<Button size="sm" onclick={updateAuthKey}>保存</Button>
								<Button size="sm" variant="ghost" onclick={cancelEdit}>取消</Button>
							{:else}
								<Button size="sm" variant="ghost" onclick={() => startEdit(key)}>编辑</Button>
								<Button size="sm" variant="destructive" onclick={() => deleteAuthKey(key.api_key)}>
									删除
								</Button>
							{/if}
						</Table.Cell>
					</Table.Row>
				{/each}
			</Table.Body>
		</Table.Root>
		{#if authKeys.length === 0}
			<p class="text-muted-foreground py-4 text-center">暂无数据。</p>
		{/if}
	</Card.Content>
</Card.Root>
