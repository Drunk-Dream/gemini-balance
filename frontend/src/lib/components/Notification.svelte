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
		class="alert my-2 {type === 'success'
			? 'alert-success'
			: 'alert-error'}"
		role="alert"
	>
		{#if type === 'success'}
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="h-6 w-6 shrink-0 stroke-current"
				fill="none"
				viewBox="0 0 24 24"
				><path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
				/></svg
			>
		{:else}
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="h-6 w-6 shrink-0 stroke-current"
				fill="none"
				viewBox="0 0 24 24"
				><path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
				/></svg
			>
		{/if}
		<span class="block sm:inline">{message}</span>
	</div>
{/if}
