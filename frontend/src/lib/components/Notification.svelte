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
	<div class="alert {type === 'success' ? 'alert-success' : 'alert-error'}" role="alert">
		<span class="block sm:inline">{message}</span>
	</div>
{/if}
