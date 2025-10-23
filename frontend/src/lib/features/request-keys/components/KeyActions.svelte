<script lang="ts">
	import { Dialog } from 'bits-ui';

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
	<button
		onclick={fetchKeyStatusResponse}
		class="btn bg-primary text-primary-foreground"
		disabled={loading}
	>
		{loading ? '刷新中...' : '立即刷新'}
	</button>

	<Dialog.Root bind:open={addKeyDialogOpen}>
		<Dialog.Trigger class="btn bg-primary text-primary-foreground">新增密钥</Dialog.Trigger>
		<Dialog.Portal>
			<Dialog.Overlay
				class="data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 fixed inset-0 z-50 bg-black/50"
			/>
			<Dialog.Content
				class="data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 bg-card fixed left-1/2 top-1/2 z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-lg border p-6 shadow-lg"
			>
				<Dialog.Title class="text-card-foreground mb-4 text-xl font-semibold">新增密钥</Dialog.Title
				>
				<Dialog.Description class="text-muted-foreground mb-4 text-sm">
					单个或批量添加密钥，每行一个。
				</Dialog.Description>
				<div>
					<label for="keysInput" class="text-foreground mb-2 block text-sm font-medium"
						>API 密钥:</label
					>
					<textarea
						id="keysInput"
						bind:value={keysInput}
						placeholder="输入新的API密钥，每行一个用于批量添加"
						rows="5"
						class="border-border focus:border-primary focus:ring-primary w-full rounded-md border p-2 focus:ring focus:ring-opacity-50"
					></textarea>
				</div>
				<div class="mt-6 flex justify-end space-x-2">
					<Dialog.Close class="btn btn-ghost">取消</Dialog.Close>
					<button onclick={handleAddKeysSubmit} class="btn bg-primary text-primary-foreground">
						添加密钥
					</button>
				</div>
			</Dialog.Content>
		</Dialog.Portal>
	</Dialog.Root>

	<button onclick={resetAllKeys} class="btn bg-destructive text-destructive-foreground">
		重置所有密钥状态
	</button>
</div>
