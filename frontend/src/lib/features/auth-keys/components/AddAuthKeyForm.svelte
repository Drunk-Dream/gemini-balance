<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';

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
		<Dialog.Trigger>
			{#snippet child({ props })}
				<Button {...props}>创建新密钥</Button>
			{/snippet}
		</Dialog.Trigger>
		<Dialog.Content class="sm:max-w-[425px]">
			<Dialog.Header>
				<Dialog.Title>创建新密钥</Dialog.Title>
				<Dialog.Description>为您的认证密钥输入一个别名。</Dialog.Description>
			</Dialog.Header>
			<form
				onsubmit={(e) => {
					e.preventDefault();
					handleSubmit();
				}}
				class="grid gap-4 py-4"
			>
				<div class="grid w-full gap-1.5">
					<Label for="new-alias">新别名</Label>
					<Input
						id="new-alias"
						type="text"
						bind:value={newAlias}
						placeholder="输入新密钥的别名"
						required
					/>
				</div>
				<Dialog.Footer>
					<Button type="submit">创建</Button>
				</Dialog.Footer>
			</form>
		</Dialog.Content>
	</Dialog.Root>
</div>
