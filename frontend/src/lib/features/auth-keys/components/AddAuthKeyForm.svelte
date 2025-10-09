<script lang="ts">
	import { Dialog } from 'bits-ui';

	let {
		newAlias = $bindable(),
		createAuthKey
	}: { newAlias: string; createAuthKey: () => Promise<void> } = $props();
	let open = $state(false);

	async function handleSubmit() {
		await createAuthKey();
		open = false; // Close dialog
	}
</script>

<div class="mb-6">
	<Dialog.Root bind:open>
		<Dialog.Trigger class="btn btn-primary">创建新密钥</Dialog.Trigger>
		<Dialog.Portal>
			<Dialog.Overlay
				class="data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 fixed inset-0 z-50 bg-black/50"
			/>
			<Dialog.Content
				class="data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 fixed left-1/2 top-1/2 z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-lg border bg-white p-6 shadow-lg"
			>
				<Dialog.Title class="mb-4 text-xl font-semibold text-gray-800">创建新密钥</Dialog.Title>
				<Dialog.Description class="mb-4 text-sm text-gray-600">
					为您的认证密钥输入一个别名。
				</Dialog.Description>
				<form
					onsubmit={(e) => {
						e.preventDefault();
						handleSubmit();
					}}
					class="flex flex-col space-y-4"
				>
					<div>
						<label for="new-alias" class="mb-2 block text-sm font-medium text-gray-700"
							>新别名</label
						>
						<input
							id="new-alias"
							type="text"
							bind:value={newAlias}
							placeholder="输入新密钥的别名"
							class="focus:shadow-outline w-full appearance-none rounded border px-3 py-2 leading-tight text-gray-700 shadow focus:outline-none"
							required
						/>
					</div>
					<div class="flex justify-end space-x-2">
						<Dialog.Close
							class="btn btn-neutral btn-soft"
						>
							取消
						</Dialog.Close>
						<button type="submit" class="btn btn-primary btn-soft"> 创建 </button>
					</div>
				</form>
			</Dialog.Content>
		</Dialog.Portal>
	</Dialog.Root>
</div>
