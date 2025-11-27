<script lang="ts">
	import { page } from '$app/state';
	import { Button } from '$lib/components/ui/button';

	let {
		href,
		name,
		onClick,
		icon
	}: {
		href: string;
		name: string;
		onClick: () => void;
		icon: string;
	} = $props();

	const isActive = $derived(page.url.pathname === href);
</script>

<Button
	variant={isActive ? 'secondary' : 'ghost'}
	size="lg"
	class="w-full justify-start text-lg font-semibold"
	{href}
	onclick={onClick}
>
	<i class="{icon} mr-2 w-6 text-lg"></i>
	{name}
</Button>
