<script lang="ts">
	let { newAlias = $bindable(), createAuthKey }: { newAlias: string; createAuthKey: () => Promise<void> } =
		$props();
</script>

<div class="mb-6 rounded bg-white px-8 pb-8 pt-6 shadow-md">
	<h2 class="mb-4 text-xl font-semibold">创建新密钥</h2>
	<form onsubmit={createAuthKey} class="flex items-center space-x-4">
		<div class="flex-grow">
			<label for="new-alias" class="sr-only">新别名</label>
			<input
				id="new-alias"
				type="text"
				bind:value={newAlias}
				placeholder="输入新密钥的别名"
				class="focus:shadow-outline w-full appearance-none rounded border px-3 py-2 leading-tight text-gray-700 shadow focus:outline-none"
				required
			/>
		</div>
		<button
			type="submit"
			class="focus:shadow-outline rounded bg-blue-500 px-4 py-2 font-bold text-white hover:bg-blue-700 focus:outline-none"
		>
			创建
		</button>
	</form>
</div>
