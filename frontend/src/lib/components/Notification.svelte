<script lang="ts">
	import * as Alert from '$lib/components/ui/alert';
	import CheckCircle from 'phosphor-svelte/lib/CheckCircle';
	import XCircle from 'phosphor-svelte/lib/XCircle';

	let {
		message = $bindable(),
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
	<Alert.Root variant={type === 'error' ? 'destructive' : 'default'} class="my-2">
		{#if type === 'success'}
			<CheckCircle class="h-4 w-4" />
		{:else}
			<XCircle class="h-4 w-4" />
		{/if}
		<Alert.Title>{type === 'success' ? '成功' : '错误'}</Alert.Title>
		<Alert.Description>{message}</Alert.Description>
	</Alert.Root>
{/if}
