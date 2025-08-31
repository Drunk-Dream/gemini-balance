<script lang="ts">
	let { addKeys }: { addKeys: (keysInput: string) => Promise<void> } = $props();
	let keysInput: string = $state('');

	async function handleSubmit() {
		await addKeys(keysInput);
		keysInput = ''; // Clear input after submission
	}
</script>

<div class="mb-6 rounded-lg bg-white p-4 shadow-md">
	<h2 class="mb-4 text-xl font-semibold text-gray-800">新增密钥</h2>
	<div>
		<label for="keysInput" class="mb-2 block text-sm font-medium text-gray-700"
			>新增密钥 (单个或批量，每行一个):</label
		>
		<textarea
			id="keysInput"
			bind:value={keysInput}
			placeholder="输入新的API密钥，每行一个用于批量添加"
			rows="5"
			class="w-full rounded-md border border-gray-300 p-2 focus:border-blue-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50"
		></textarea>
		<button
			onclick={handleSubmit}
			class="focus:shadow-outline cursor-pointer mt-2 rounded bg-green-500 px-4 py-2 text-sm font-bold text-white hover:bg-green-700 focus:outline-none"
		>
			添加密钥
		</button>
	</div>
</div>
