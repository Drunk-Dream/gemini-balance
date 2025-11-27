<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog';
	import { Button } from '$lib/components/ui/button';
	import { Textarea } from '$lib/components/ui/textarea';
	import { Label } from '$lib/components/ui/label';

	let {
		fetchKeyStatusResponse,
		resetAllKeys,
		addKeys,
		loading
	}: {
		fetchKeyStatusResponse: () => Promise<void>;
		resetAllKeys: () => Promise<void>;
		addKeys: (keysInput: string) => Promise<void>;
		loading: boolean;
	} = $props();

	let keysInput: string = $state('');
	let addKeyDialogOpen = $state(false);

	async function handleAddKeysSubmit() {
		await addKeys(keysInput);
		keysInput = ''; // Clear input after submission
		addKeyDialogOpen = false; // Close dialog
	}
</script>

<div class="mb-6 flex flex-col space-y-2 sm:flex-row sm:space-x-2 sm:space-y-0">
	<Button onclick={fetchKeyStatusResponse} disabled={loading}>
		{loading ? '刷新中...' : '立即刷新'}
	</Button>

	<Dialog.Root bind:open={addKeyDialogOpen}>
		<Dialog.Trigger>
			{#snippet child({ props })}
				<Button {...props}>新增密钥</Button>
			{/snippet}
		</Dialog.Trigger>
		<Dialog.Content class="sm:max-w-[425px]">
			<Dialog.Header>
				<Dialog.Title>新增密钥</Dialog.Title>
				<Dialog.Description>单个或批量添加密钥，每行一个。</Dialog.Description>
			</Dialog.Header>
			<div class="grid gap-4 py-4">
				<div class="grid w-full gap-1.5">
					<Label for="keysInput">API 密钥</Label>
					<Textarea
						id="keysInput"
						bind:value={keysInput}
						placeholder="输入新的API密钥，每行一个用于批量添加"
						rows={5}
					/>
				</div>
			</div>
			<Dialog.Footer>
				<Button type="submit" onclick={handleAddKeysSubmit}>添加密钥</Button>
			</Dialog.Footer>
		</Dialog.Content>
	</Dialog.Root>

	<Button variant="destructive" onclick={resetAllKeys}>重置所有密钥状态</Button>
</div>
