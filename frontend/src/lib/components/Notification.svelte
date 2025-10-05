<script lang="ts">
	let {
		message,
		type,
		autoHide = true
	}: { message: string | null; type: 'success' | 'error'; autoHide?: boolean } = $props();

	$effect(() => {
		let timer: ReturnType<typeof setTimeout>;
		if (message && autoHide) {
			timer = setTimeout(() => {
				message = null;
			}, 5000); // Hide message after 5 seconds
		}

		return () => {
			clearTimeout(timer);
		};
	});
</script>

{#if message}
	<div
		class="relative mb-4 rounded border px-4 py-3 {type === 'success'
			? 'border-green-400 bg-green-100 text-green-700'
			: 'border-red-400 bg-red-100 text-red-700'}"
		role="alert"
	>
		<span class="block sm:inline">{message}</span>
	</div>
{/if}
